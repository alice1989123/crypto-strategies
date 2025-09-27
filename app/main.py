import asyncio
from datetime import datetime, timedelta
import argparse

from app.db.fetch import fetch_latest_prediction_with_metadata, get_stored_klines
from app.strategies.forecast import ForecastStrategy
from app.db.strategy import save_strategy_signal
from app.db.get_all_tracked_coins import get_all_tracked_coins
from app.notifications.telegram import send_strategy_signal_via_telegram
from app.strategies.rsi_momentum import RSIMomentumStrategy


async def run_for_coin(coin: str, since_days: int = 21):
    print(f"🔍 Fetching predictions for {coin}...")
    model = "GRU"

    end = datetime.utcnow()
    start = end - timedelta(days=since_days)

    historical, forecast, metadata = fetch_latest_prediction_with_metadata(coin, model)
    df = get_stored_klines(coin, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

    # Strategy 1: forecast
    strategy = ForecastStrategy(fee_pct=0.005, extra_gain=0.002, extra_loss=0.0025)
    decision = strategy.evaluate(historical, forecast)

    # Strategy 2: RSI confirmation
    rsi_strategy = RSIMomentumStrategy(fee_pct=0.005, rsi_threshold=55)
    decision_rsi = rsi_strategy.evaluate(historical, forecast, df)

    # Persist individual signals
    save_strategy_signal(coin, model, decision)
    save_strategy_signal(coin, "RSIMomentumStrategy", decision_rsi)

    # Combine
    final_decision = {"action": "HOLD", "source": "Confirmed"}
    if decision["action"] in ["BUY", "SHORT"] and decision_rsi["action"] == decision["action"]:
        final_decision = {
            **decision,
            "rsi": decision_rsi.get("rsi"),
            "confirmed_by": "RSI",
            "source": "Confirmed",
        }

    save_strategy_signal(coin, f"{model}+RSIMomentumStrategy", final_decision)

    if final_decision.get("action") in ["BUY", "SHORT"]:
        print(f"📈 RSI confirmation: {final_decision}")
        await send_strategy_signal_via_telegram(final_decision, coin, confirmations=[rsi_strategy])
        await asyncio.sleep(2)  # gentle rate limit


async def main():
    parser = argparse.ArgumentParser(description="Run strategies and emit signals.")
    parser.add_argument("--symbol", help="Single symbol, e.g. BTCUSDT")
    parser.add_argument("--symbols", help="Comma-separated symbols, e.g. BTCUSDT,ETHUSDT")
    parser.add_argument("--since-days", type=int, default=21, help="History window in days (default: 21)")
    args = parser.parse_args()

    # Resolve target list
    if args.symbol:
        coins = [args.symbol.strip().upper()]
    elif args.symbols:
        coins = [c.strip().upper() for c in args.symbols.split(",") if c.strip()]
    else:
        coins = get_all_tracked_coins()

    # Run sequentially (simple & deterministic). If you want, gather() to parallelize.
    for coin in coins:
        try:
            await run_for_coin(coin, since_days=args.since_days)
        except Exception as e:
            # don't stop the whole batch on one failure
            print(f"❌ Error processing {coin}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
