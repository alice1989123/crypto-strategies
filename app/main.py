import asyncio
from time import sleep
from app.db.fetch import fetch_latest_prediction_with_metadata
from app.strategies.forecast import ForecastStrategy
from app.db.strategy import save_strategy_signal
from app.db.get_all_tracked_coins import get_all_tracked_coins
from app.notifications.telegram import send_strategy_signal_via_telegram
from datetime import datetime, timedelta
from app.db.fetch import get_stored_klines
from app.strategies.rsi_momentum import RSIMomentumStrategy  # new





async def main():
    coins = get_all_tracked_coins()
    end = datetime.utcnow()
    start = end - timedelta(days=21)
    for coin in coins:
        print(f"🔍 Fetching predictions for {coin}...")
        model = "LSTMModel"

        historical, forecast, metadata = fetch_latest_prediction_with_metadata(coin, model)

        
        df = get_stored_klines(coin, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
      
        # Strategy
        strategy = ForecastStrategy(
            fee_pct=0.005,
            extra_gain=0.002,
            extra_loss=0.0025
        )

        # Step 1: Core decision
        decision = strategy.evaluate(historical, forecast)

        # Step 2: RSI confirmation
        rsi_strategy = RSIMomentumStrategy(fee_pct=0.005, rsi_threshold=55)
        decision_rsi = rsi_strategy.evaluate(historical, forecast, df)

        #print(f"🧠 Core strategy: {decision}")
        #print(f"📈 RSI confirmation: {decision_rsi}")

        # Step 3: Combine signals
        final_decision = {"action": "HOLD"}

        save_strategy_signal(coin, model, decision)
        save_strategy_signal(coin, "RSIMomentumStrategy", decision_rsi)

        final_decision = {"action": "HOLD", "source": "Confirmed"}
        if decision["action"] in ["BUY", "SHORT"] and decision_rsi["action"] == decision["action"]:
            final_decision = {
                **decision,
                "rsi": decision_rsi.get("rsi"),
                "confirmed_by": "RSI",
                "source": "Confirmed"
            }
         
        save_strategy_signal(coin, model + "RSIMomentumStrategy" , final_decision)

        if final_decision.get("action") in ["BUY", "SHORT"]:
            print(f"📈 RSI confirmation: {final_decision}")
            
            await send_strategy_signal_via_telegram(final_decision, coin, confirmations=[rsi_strategy])
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
