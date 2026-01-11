#!/usr/bin/env python3
"""
run_strategies.py

Runs ForecastStrategy + RSIMomentumStrategy for a single symbol and:
- saves individual strategy signals
- saves a combined "confirmed" signal
- optionally sends Telegram if confirmed BUY/SHORT
"""

import asyncio
import argparse
import logging
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from logging.handlers import RotatingFileHandler

from app.db.fetch import fetch_latest_prediction_with_metadata, get_stored_klines
from app.strategies.forecast import ForecastStrategy
from app.strategies.rsi_momentum import RSIMomentumStrategy
from app.db.strategy import save_strategy_signal
from app.notifications.telegram import send_strategy_signal_via_telegram


logger = logging.getLogger("strategies")


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure console logging + optional rotating file logging.
    """
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Optional file handler
    if log_file:
        fh = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
        )
        fh.setLevel(getattr(logging, level.upper(), logging.INFO))
        fh.setFormatter(fmt)
        logger.addHandler(fh)


def _safe_action(d: Optional[Dict[str, Any]]) -> str:
    if not isinstance(d, dict):
        return "HOLD"
    return str(d.get("action", "HOLD") or "HOLD").upper()


async def run_for_coin(coin: str, interval: str, since_days: int = 21) -> None:
    fee_pct = 0.0
    model = "GRU"

    logger.info("Starting run | coin=%s interval=%s since_days=%s model=%s", coin, interval, since_days, model)

    end = datetime.utcnow()
    start = end - timedelta(days=since_days)
    logger.debug("Time window | start=%s end=%s (UTC)", start.isoformat(), end.isoformat())

    # Fetch latest prediction package
    logger.info("Fetching latest prediction package...")
    historical, forecast, metadata = fetch_latest_prediction_with_metadata(coin, interval, model)
    logger.debug("Fetched predictions | historical=%s forecast=%s metadata_keys=%s",
                 len(historical) if historical else 0,
                 len(forecast) if forecast else 0,
                 list(metadata.keys()) if isinstance(metadata, dict) else type(metadata).__name__)

    # Fetch klines for RSI confirmation
    logger.info("Fetching stored klines...")
    df = get_stored_klines(
        coin,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval=interval,
    )
    try:
        rows = 0 if df is None else len(df)
        cols = [] if df is None else list(df.columns)
        logger.debug("Fetched klines | rows=%s cols=%s", rows, cols)
    except Exception:
        logger.debug("Could not introspect klines df (non-pandas or custom type).")

    # ----------------------------
    # Strategy 1: Forecast
    # ----------------------------
    forecast_strategy = ForecastStrategy(
        fee_pct=fee_pct,
        extra_gain=0.00001,
        extra_loss=0.000015,
    )
    logger.info("Evaluating ForecastStrategy | %s", forecast_strategy)

    decision = forecast_strategy.evaluate(historical, forecast)
    logger.info("ForecastStrategy decision | %s", decision)

    # ----------------------------
    # Strategy 2: RSI Confirmation
    # ----------------------------
    rsi_strategy = RSIMomentumStrategy(fee_pct=fee_pct, rsi_threshold=55)
    logger.info("Evaluating RSIMomentumStrategy | %s", rsi_strategy)

    decision_rsi = rsi_strategy.evaluate(historical, forecast, df)
    logger.info("RSIMomentumStrategy decision | %s", decision_rsi)

    # Persist individual signals (best-effort)
    logger.info("Persisting individual signals...")
    try:
        save_strategy_signal(coin, model, decision)
        logger.debug("Saved ForecastStrategy signal")
    except Exception:
        logger.exception("Failed to save ForecastStrategy signal")

    try:
        save_strategy_signal(coin, "RSIMomentumStrategy", decision_rsi)
        logger.debug("Saved RSIMomentumStrategy signal")
    except Exception:
        logger.exception("Failed to save RSIMomentumStrategy signal")

    # ----------------------------
    # Combine signals
    # ----------------------------
    action_forecast = _safe_action(decision)
    action_rsi = _safe_action(decision_rsi)

    final_decision: Dict[str, Any] = {"action": "HOLD", "source": "Unconfirmed"}

    if action_forecast in ("BUY", "SHORT") and action_rsi == action_forecast:
        final_decision = {
            **(decision or {}),
            "action": action_forecast,
            "rsi": (decision_rsi or {}).get("rsi"),
            "confirmed_by": "RSI",
            "source": "Confirmed",
        }

    logger.info("Final decision | %s", final_decision)

    # Persist combined signal
    logger.info("Persisting combined signal...")
    try:
        save_strategy_signal(coin, f"{model}+RSIMomentumStrategy", final_decision)
        logger.debug("Saved combined signal")
    except Exception:
        logger.exception("Failed to save combined signal")

    # ----------------------------
    # Notify (Telegram)
    # ----------------------------
    if _safe_action(final_decision) in ("BUY", "SHORT") and final_decision.get("source") == "Confirmed":
        logger.info("Sending Telegram signal...")
        try:
            await send_strategy_signal_via_telegram(final_decision, coin, confirmations=[rsi_strategy])
            logger.info("Telegram sent successfully")
            await asyncio.sleep(2)  # gentle rate limit
        except Exception:
            logger.exception("Failed to send Telegram signal")
    else:
        logger.info("No Telegram notification (not confirmed BUY/SHORT).")

    logger.info("Run finished | coin=%s interval=%s", coin, interval)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run strategies and emit signals.")
    parser.add_argument("--symbol", required=True, help="Single symbol, e.g. BTCUSDT")
    parser.add_argument("--since-days", type=int, default=21, help="History window in days (default: 21)")
    parser.add_argument("--interval", type=str, default="1h", help="Kline interval (default: 1h)")
    parser.add_argument("--log-level", type=str, default="INFO", help="DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--log-file", type=str, default=None, help="Optional log file path (rotating)")
    args = parser.parse_args()

    setup_logging(args.log_level, args.log_file)

    logger.info("CLI args | symbol=%s interval=%s since_days=%s log_level=%s log_file=%s",
                args.symbol, args.interval, args.since_days, args.log_level, args.log_file)

    try:
        await run_for_coin(args.symbol, args.interval, since_days=args.since_days)
    except Exception as e:
        logger.exception("Fatal error processing %s: %s", args.symbol, e)
        raise  # keep non-zero exit code


if __name__ == "__main__":
    asyncio.run(main())
