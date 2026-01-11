# app/strategies/rsi_momentum.py

from __future__ import annotations

import logging
from typing import List, Dict, Union, Any

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator

from app.strategies.base import BaseStrategy


logger = logging.getLogger("strategies.rsi")


def sanitize_decision(decision: dict) -> dict:
    return {
        k: float(v) if isinstance(v, (np.floating, np.integer)) else v
        for k, v in decision.items()
    }


class RSIMomentumStrategy(BaseStrategy):
    def __init__(self, fee_pct: float = 0.005, rsi_threshold: float = 55):
        self.fee_pct = float(fee_pct)
        self.rsi_threshold = float(rsi_threshold)
        self.min_gain = 2 * self.fee_pct

    def __str__(self) -> str:
        return f"RSIMomentumStrategy(fee_pct={self.fee_pct}, rsi_threshold={self.rsi_threshold})"

    def evaluate(
        self,
        historical: List[Dict[str, Any]],
        forecast: List[Dict[str, Any]],
        klines_df: pd.DataFrame,
    ) -> Dict[str, Union[str, float]]:
        # Basic input checks
        if historical is None or forecast is None or klines_df is None:
            logger.warning("Insufficient data: one or more inputs are None")
            return sanitize_decision({"action": "HOLD", "reason": "Insufficient data"})

        if len(forecast) < 2 or len(historical) < 1 or getattr(klines_df, "empty", True):
            logger.info(
                "Insufficient data: len(historical)=%s len(forecast)=%s df_empty=%s",
                len(historical),
                len(forecast),
                getattr(klines_df, "empty", True),
            )
            return sanitize_decision({"action": "HOLD", "reason": "Insufficient data"})

        try:
            # Defensive copy + numeric close
            df = klines_df.copy()
            if "close" not in df.columns:
                logger.warning("Klines df missing 'close' column. cols=%s", list(df.columns))
                return sanitize_decision({"action": "HOLD", "reason": "Missing close column"})

            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            before = len(df)
            df = df.dropna(subset=["close"])
            after = len(df)

            if after == 0:
                logger.info("No valid close prices after coercion/dropna. before=%s after=%s", before, after)
                return sanitize_decision({"action": "HOLD", "reason": "No valid close prices"})

            if after != before:
                logger.debug("Dropped NaN closes. before=%s after=%s", before, after)

            # RSI calculation
            df["rsi"] = RSIIndicator(close=df["close"]).rsi()
            latest_rsi = float(df["rsi"].iloc[-1])

            if not np.isfinite(latest_rsi):
                logger.info("RSI not ready (latest is NaN/inf). last_5_rsi=%s", df["rsi"].tail(5).tolist())
                return sanitize_decision({"action": "HOLD", "reason": "RSI not ready"})

            entry = float(historical[-1]["price"])
            target = float(forecast[-1]["price"])

            logger.debug(
                "RSI eval | entry=%s target=%s min_gain=%s latest_rsi=%.2f threshold=%.2f",
                entry,
                target,
                self.min_gain,
                latest_rsi,
                self.rsi_threshold,
            )

            # Decision rules
            if target > entry * (1 + self.min_gain) and latest_rsi > self.rsi_threshold:
                decision = {
                    "action": "BUY",
                    "entry": round(entry, 6),
                    "stop_loss": round(entry * (1 - self.min_gain), 6),
                    "take_profit": round(entry * (1 + 2 * self.min_gain), 6),
                    "rsi": round(latest_rsi, 2),
                }
                logger.info("RSI confirmed BUY | %s", decision)
                return sanitize_decision(decision)

            if target < entry * (1 - self.min_gain) and latest_rsi < (100 - self.rsi_threshold):
                decision = {
                    "action": "SHORT",
                    "entry": round(entry, 6),
                    "stop_loss": round(entry * (1 + self.min_gain), 6),
                    "take_profit": round(entry * (1 - 2 * self.min_gain), 6),
                    "rsi": round(latest_rsi, 2),
                }
                logger.info("RSI confirmed SHORT | %s", decision)
                return sanitize_decision(decision)

            decision = {"action": "HOLD", "rsi": round(latest_rsi, 2)}
            logger.info("RSI HOLD | %s", decision)
            return sanitize_decision(decision)

        except Exception:
            logger.exception("RSI strategy evaluate() crashed")
            return sanitize_decision({"action": "HOLD", "reason": "Exception in RSI strategy"})

    def justification_text(self, signal: dict) -> str:
        rsi = signal.get("rsi")
        if rsi is None:
            return "RSI not available."

        threshold = self.rsi_threshold
        if signal.get("action") == "BUY":
            return f"RSI {rsi} is above threshold {threshold}, indicating bullish momentum."
        if signal.get("action") == "SHORT":
            return f"RSI {rsi} is below {100 - threshold}, indicating bearish momentum."
        return f"RSI {rsi} did not confirm a strong move."
