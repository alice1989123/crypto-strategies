# app/strategies/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Union

class BaseStrategy(ABC):
    @abstractmethod
    def evaluate(self, predictions: List[Dict]) -> Dict[str, Union[str, float]]:
        """
        Should return a dictionary like:
        {
            "action": "BUY" | "SHORT" | "HOLD",
            "entry": float,
            "stop_loss": float,
            "take_profit": float
        }
        """
        pass
    def justification_text(self, signal: dict) -> str:
        return "No specific justification provided."
