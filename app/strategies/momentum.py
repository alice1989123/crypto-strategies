from typing import List, Dict, Union
from .base import BaseStrategy
class MomentumStrategy(BaseStrategy):
    def __init__(self, fee_pct: float = 0.002, extra_gain: float = 0.005, extra_loss: float = 0.01):
        self.fee_pct = fee_pct
        self.min_gain = 2 * self.fee_pct + extra_gain
        self.min_loss = 2 * self.fee_pct + extra_loss

    def evaluate(self, historical: List[Dict], forecast: List[Dict]) -> Dict[str, Union[str, float]]:
        if len(forecast) < 2 or not historical:
            return {"action": "HOLD"}

        start = historical[-1]["price"]  # ✅ current (entry) price
        end = forecast[-1]["price"]

        if end > start * (1 + self.min_gain) and sum(p['price'] > start for p in forecast[-5:]) >= 4:
            return {
                "action": "BUY",
                "entry": start,
                "stop_loss": round(start * (1 - self.min_loss), 2),
                "take_profit": round(start * (1 + 2 * self.min_gain), 2)
            }

        elif end < start * (1 - self.min_gain) and sum(p['price'] < start for p in forecast[-5:]) >= 4:
            return {
                "action": "SHORT",
                "entry": start,
                "stop_loss": round(start * (1 + self.min_loss), 2),
                "take_profit": round(start * (1 - 2 * self.min_gain), 2)
            }

        return {"action": "HOLD"}
