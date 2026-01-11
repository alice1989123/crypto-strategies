# app/strategies/forecast.py

from __future__ import annotations

import logging
from typing import List, Dict, Union, Optional, Any

import pandas as pd

from .base import BaseStrategy


logger = logging.getLogger("strategies.forecast")


class ForecastStrategy(BaseStrategy):
    """
    Less trigger-happy ForecastStrategy.

    Changes vs your current version:
    - Adds a minimum move floor (min_abs_gain_pct) so tiny forecast moves don't trigger signals.
    - Makes "votes" stricter by default: require ALL of lastN points to be in direction (vote_strict=True).
    - Adds a path sanity check: forecast must not cross the stop-loss level before reaching the end.
      (prevents "ends up but would stop out" cases)
    """

    def __init__(
        self,
        fee_pct: float = 0.002,
        extra_gain: float = 0.005,
        extra_loss: float = 0.01,
        label_width: int = 12,
        *,
        min_abs_gain_pct: float = 0.0020,  # 0.20% absolute floor on required move (tune)
        vote_window: int = 5,
        vote_strict: bool = True,          # require stronger consensus
        enforce_path_stop: bool = True,    # ensure forecast path doesn't violate stop
    ):
        self.fee_pct = float(fee_pct)
        self.min_gain = 2 * self.fee_pct + float(extra_gain)
        self.min_loss = 2 * self.fee_pct + float(extra_loss)
        self.label_width = int(label_width)

        self.min_abs_gain_pct = float(min_abs_gain_pct)
        self.vote_window = int(vote_window)
        self.vote_strict = bool(vote_strict)
        self.enforce_path_stop = bool(enforce_path_stop)

    def __str__(self) -> str:
        return (
            "ForecastStrategy("
            f"fee_pct={self.fee_pct}, min_gain={self.min_gain}, min_loss={self.min_loss}, "
            f"label_width={self.label_width}, min_abs_gain_pct={self.min_abs_gain_pct}, "
            f"vote_window={self.vote_window}, vote_strict={self.vote_strict}, "
            f"enforce_path_stop={self.enforce_path_stop})"
        )

    def evaluate(
        self,
        historical: List[Dict[str, Any]],
        forecast: List[Dict[str, Any]],
        klines_df: Optional[pd.DataFrame] = None,
        use_forecast_only: bool = True,
    ) -> Dict[str, Union[str, float]]:
        # Input validation + visibility
        if historical is None or forecast is None:
            logger.warning("Insufficient data: historical or forecast is None")
            return {"action": "HOLD", "reason": "Insufficient data"}

        if not historical or len(forecast) < 2:
            logger.info(
                "Insufficient data | len(historical)=%s len(forecast)=%s",
                len(historical),
                len(forecast),
            )
            return {"action": "HOLD", "reason": "Insufficient data"}

        preds = forecast[-self.label_width:] if use_forecast_only else forecast
        if len(preds) < 2:
            logger.info(
                "Not enough forecast points after slicing | len(preds)=%s label_width=%s use_forecast_only=%s",
                len(preds),
                self.label_width,
                use_forecast_only,
            )
            return {"action": "HOLD", "reason": "Not enough forecast points"}

        try:
            entry = float(historical[-1]["price"])
            end = float(preds[-1]["price"])
            pred_prices = [float(p["price"]) for p in preds]
        except Exception:
            logger.exception("Failed to parse prices from historical/forecast")
            return {"action": "HOLD", "reason": "Bad price data"}

        # --- Thresholds ---
        # Require BOTH:
        #   (A) move exceeds min_gain (fees + extras)
        #   (B) move exceeds an absolute floor (min_abs_gain_pct)
        required_gain_pct = max(self.min_gain, self.min_abs_gain_pct)

        # --- Voting window ---
        lastN = preds[-self.vote_window :] if len(preds) >= self.vote_window else preds
        try:
            up_votes = sum(float(p["price"]) > entry for p in lastN)
            down_votes = sum(float(p["price"]) < entry for p in lastN)
        except Exception:
            logger.exception("Failed computing votes from forecast prices")
            return {"action": "HOLD", "reason": "Bad forecast price data"}

        required_votes = len(lastN) if self.vote_strict else max(1, len(lastN) - 1)

        # --- Path stop enforcement ---
        # If forecast path dips below stop level for BUY (or above stop for SHORT), skip.
        buy_stop_level = entry * (1 - self.min_loss)
        short_stop_level = entry * (1 + self.min_loss)
        min_pred = min(pred_prices)
        max_pred = max(pred_prices)

        logger.debug(
            "Forecast eval | entry=%s end=%s required_gain_pct=%s (min_gain=%s floor=%s) "
            "min_loss=%s len(preds)=%s votes(up=%s down=%s required=%s) "
            "path(min=%s max=%s) stops(buy_stop=%s short_stop=%s)",
            entry,
            end,
            required_gain_pct,
            self.min_gain,
            self.min_abs_gain_pct,
            self.min_loss,
            len(preds),
            up_votes,
            down_votes,
            required_votes,
            min_pred,
            max_pred,
            buy_stop_level,
            short_stop_level,
        )

        # BUY conditions
        buy_move_ok = end > entry * (1 + required_gain_pct)
        buy_votes_ok = up_votes >= required_votes
        buy_path_ok = (not self.enforce_path_stop) or (min_pred >= buy_stop_level)

        if buy_move_ok and buy_votes_ok and buy_path_ok:
            decision = {
                "action": "BUY",
                "entry": round(entry, 4),
                "stop_loss": round(buy_stop_level, 4),
                "take_profit": round(entry * (1 + 2 * required_gain_pct), 4),
                "reason": "Forecast up + votes + path ok",
            }
            logger.info("Forecast BUY | %s", decision)
            return decision

        # SHORT conditions
        short_move_ok = end < entry * (1 - required_gain_pct)
        short_votes_ok = down_votes >= required_votes
        short_path_ok = (not self.enforce_path_stop) or (max_pred <= short_stop_level)

        if short_move_ok and short_votes_ok and short_path_ok:
            decision = {
                "action": "SHORT",
                "entry": round(entry, 4),
                "stop_loss": round(short_stop_level, 4),
                "take_profit": round(entry * (1 - 2 * required_gain_pct), 4),
                "reason": "Forecast down + votes + path ok",
            }
            logger.info("Forecast SHORT | %s", decision)
            return decision

        # Explain *why* we held (super useful in logs)
        reasons = []
        if not buy_move_ok and not short_move_ok:
            reasons.append("move<required")
        if buy_move_ok and not buy_votes_ok:
            reasons.append("buy_votes<required")
        if short_move_ok and not short_votes_ok:
            reasons.append("short_votes<required")
        if buy_move_ok and buy_votes_ok and not buy_path_ok:
            reasons.append("buy_path_hits_stop")
        if short_move_ok and short_votes_ok and not short_path_ok:
            reasons.append("short_path_hits_stop")

        reason = ",".join(reasons) if reasons else "no_signal"
        logger.info("Forecast HOLD | entry=%s end=%s reason=%s", round(entry, 4), round(end, 4), reason)
        return {"action": "HOLD", "reason": reason}
