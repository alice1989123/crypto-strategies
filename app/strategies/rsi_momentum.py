# strategies/rsi_momentum.py

from ta.momentum import RSIIndicator
from typing import List, Dict, Union
import pandas as pd
from app.strategies.base import BaseStrategy
import numpy as np

def sanitize_decision(decision: dict) -> dict:
    return {
        k: float(v) if isinstance(v, (np.floating, np.integer)) else v
        for k, v in decision.items()
    }

class RSIMomentumStrategy(BaseStrategy):
    def __init__(self, fee_pct=0.005, rsi_threshold=55):
        self.fee_pct = fee_pct
        self.rsi_threshold = rsi_threshold
        self.min_gain = 2 * fee_pct

    def evaluate(self, historical: List[Dict], forecast: List[Dict], klines_df: pd.DataFrame) -> Dict[str, Union[str, float]]:
        if len(forecast) < 2 or len(historical) < 1 or klines_df.empty:
            return sanitize_decision({"action": "HOLD", "reason": "Insufficient data"})

        # Compute RSI
        klines_df["rsi"] = RSIIndicator(close=klines_df["close"]).rsi()
        latest_rsi = klines_df["rsi"].iloc[-1]

        entry = historical[-1]["price"]
        target = forecast[-1]["price"]

        if target > entry * (1 + self.min_gain) and latest_rsi > self.rsi_threshold:
            return sanitize_decision({
                "action": "BUY",
                "entry": entry,
                "stop_loss": round(entry * (1 - self.min_gain), 4),
                "take_profit": round(entry * (1 + 2 * self.min_gain), 4),
                "rsi": round(latest_rsi, 2)
            })

        if target < entry * (1 - self.min_gain) and latest_rsi < (100 - self.rsi_threshold):
            return sanitize_decision({
                "action": "SHORT",
                "entry": entry,
                "stop_loss": round(entry * (1 + self.min_gain), 4),
                "take_profit": round(entry * (1 - 2 * self.min_gain), 4),
                "rsi": round(latest_rsi, 2)
            })

        return sanitize_decision({"action": "HOLD", "rsi": round(latest_rsi, 2)})
    
    def justification_text(self, signal: dict) -> str:
        rsi = signal.get("rsi")
        if rsi is None:
            return "RSI not available."

        threshold = self.rsi_threshold
        if signal["action"] == "BUY":
            return f"RSI {rsi} is above threshold {threshold}, indicating bullish momentum."
        elif signal["action"] == "SHORT":
            return f"RSI {rsi} is below {100 - threshold}, indicating bearish momentum."
        else:
            return f"RSI {rsi} did not confirm a strong move."
