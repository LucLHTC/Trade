"""
Trading rules and entry/exit logic.
Implements TP/SL calculation, ATR-based exits, and time-based exits.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from src.common.logger import get_logger

logger = get_logger(__name__)


class TradingRules:
    """Trading rules for entry and exit."""

    def __init__(
        self,
        tp_atr_multiple: float = 2.0,
        sl_atr_multiple: float = 1.0,
        max_holding_hours: int = 12,
    ):
        """
        Initialize trading rules.

        Args:
            tp_atr_multiple: Take profit as multiple of ATR
            sl_atr_multiple: Stop loss as multiple of ATR
            max_holding_hours: Maximum hours to hold a trade
        """
        self.tp_atr_multiple = tp_atr_multiple
        self.sl_atr_multiple = sl_atr_multiple
        self.max_holding_hours = max_holding_hours

        logger.info(
            f"TradingRules initialized: TP={tp_atr_multiple}×ATR, "
            f"SL={sl_atr_multiple}×ATR, max_hold={max_holding_hours}h"
        )

    def calculate_tp_sl(
        self,
        entry_price: float,
        direction: int,  # 1 for long, -1 for short
        atr: float,
    ) -> Dict[str, float]:
        """
        Calculate take profit and stop loss levels.

        Args:
            entry_price: Entry price
            direction: 1 for long, -1 for short
            atr: Average True Range value

        Returns:
            Dictionary with TP and SL levels
        """
        tp_distance = atr * self.tp_atr_multiple
        sl_distance = atr * self.sl_atr_multiple

        if direction == 1:  # Long
            take_profit = entry_price + tp_distance
            stop_loss = entry_price - sl_distance
        else:  # Short
            take_profit = entry_price - tp_distance
            stop_loss = entry_price + sl_distance

        result = {
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "tp_distance": tp_distance,
            "sl_distance": sl_distance,
            "rr_ratio": tp_distance / sl_distance if sl_distance > 0 else 0,
        }

        logger.debug(
            f"{'Long' if direction == 1 else 'Short'} @ {entry_price:.5f}: "
            f"TP={take_profit:.5f}, SL={stop_loss:.5f}, RR={result['rr_ratio']:.2f}"
        )

        return result

    def check_exit(
        self,
        trade: Dict[str, Any],
        current_price: float,
        current_time: datetime,
        high: Optional[float] = None,
        low: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Check if trade should be exited.

        Args:
            trade: Trade dictionary with entry details
            current_price: Current market price
            current_time: Current timestamp
            high: High of current candle (optional)
            low: Low of current candle (optional)

        Returns:
            Tuple of (should_exit, exit_reason)
        """
        direction = trade["direction"]
        take_profit = trade["take_profit"]
        stop_loss = trade["stop_loss"]
        entry_time = trade["entry_time"]

        # Check TP hit
        if direction == 1:  # Long
            if high is not None and high >= take_profit:
                return True, "take_profit"
            elif current_price >= take_profit:
                return True, "take_profit"
        else:  # Short
            if low is not None and low <= take_profit:
                return True, "take_profit"
            elif current_price <= take_profit:
                return True, "take_profit"

        # Check SL hit
        if direction == 1:  # Long
            if low is not None and low <= stop_loss:
                return True, "stop_loss"
            elif current_price <= stop_loss:
                return True, "stop_loss"
        else:  # Short
            if high is not None and high >= stop_loss:
                return True, "stop_loss"
            elif current_price >= stop_loss:
                return True, "stop_loss"

        # Check max holding time
        holding_time = current_time - entry_time
        if holding_time.total_seconds() / 3600 >= self.max_holding_hours:
            return True, "max_time"

        return False, ""

    def calculate_pnl(
        self,
        entry_price: float,
        exit_price: float,
        direction: int,
        position_size: float,
    ) -> Dict[str, float]:
        """
        Calculate P&L for a trade.

        Args:
            entry_price: Entry price
            exit_price: Exit price
            direction: 1 for long, -1 for short
            position_size: Position size in units

        Returns:
            Dictionary with P&L details
        """
        if direction == 1:  # Long
            pnl_per_unit = exit_price - entry_price
        else:  # Short
            pnl_per_unit = entry_price - exit_price

        pnl = pnl_per_unit * position_size
        pnl_pct = (pnl_per_unit / entry_price) * 100

        result = {
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "pnl_per_unit": pnl_per_unit,
        }

        return result
