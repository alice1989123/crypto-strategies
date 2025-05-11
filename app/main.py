import asyncio
from time import sleep
from app.db.fetch import fetch_latest_prediction_with_metadata
from app.strategies.momentum import MomentumStrategy
from app.db.strategy import save_strategy_signal
from app.db.get_all_tracked_coins import get_all_tracked_coins
from app.notifications.telegram import send_strategy_signal_via_telegram

async def main():
    coins = get_all_tracked_coins()
    for coin in coins:
        print(f"🔍 Fetching predictions for {coin}...")
        model = "LSTMModel"

        historical, forecast, metadata = fetch_latest_prediction_with_metadata(coin, model)

        strategy = MomentumStrategy(
            fee_pct=0.005,
            extra_gain=0.002,
            extra_loss=0.0025
        )

        decision = strategy.evaluate(historical, forecast)
        print(f"🧠 Strategy decision for {coin}: {decision}")
        save_strategy_signal(coin, model, decision)

        if decision.get("action") in ["BUY", "SHORT"]:
            await send_strategy_signal_via_telegram(decision, coin)
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
