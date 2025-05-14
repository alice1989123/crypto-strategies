from typing import List, Dict, Union
from .base import BaseStrategy


class ForecastStrategy(BaseStrategy):
    def __init__(self, fee_pct: float = 0.002, extra_gain: float = 0.005, extra_loss: float = 0.01, label_width: int = 12):
        self.fee_pct = fee_pct
        self.min_gain = 2 * self.fee_pct + extra_gain
        self.min_loss = 2 * self.fee_pct + extra_loss
        self.label_width = label_width

    def evaluate(self, predictions: List[Dict], use_forecast_only: bool = True) -> Dict[str, Union[str, float]]:
        if use_forecast_only:
          
            predictions = predictions[-self.label_width:]

        if len(predictions) < 2:
            return {"action": "HOLD"}

        start = predictions[0]["price"]
        end = predictions[-1]["price"]

        if end > start * (1 + self.min_gain) and sum(p['price'] > start for p in predictions[-5:]) >= 4:
            return {
                "action": "BUY",
                "entry": start,
                "stop_loss": round(start * (1 - self.min_loss), 2),
                "take_profit": round(start * (1 + 2 * self.min_gain), 2)
            }

        elif end < start * (1 - self.min_gain) and sum(p['price'] < start for p in predictions[-5:]) >= 4:
            return {
                "action": "SHORT",
                "entry": start,
                "stop_loss": round(start * (1 + self.min_loss), 2),
                "take_profit": round(start * (1 - 2 * self.min_gain), 2)
            }

        return {"action": "HOLD"}
    