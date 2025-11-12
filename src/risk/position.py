"""
Position sizing and risk management module.
Calculates position sizes based on risk per trade and stop loss distance.
"""

import numpy as np
from typing import Dict, Any, Optional
from decimal import Decimal

from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class PositionSizer:
    """Calculate position sizes based on risk management rules."""

    def __init__(
        self,
        initial_equity: float = 10000.0,
        risk_per_trade: float = 0.01,
        max_position_size: float = 0.1,
    ):
        """
        Initialize position sizer.

        Args:
            initial_equity: Starting account equity
            risk_per_trade: Fraction of equity to risk per trade (default: 1%)
            max_position_size: Maximum position size as fraction of equity
        """
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size

        logger.info(
            f"PositionSizer initialized: equity=${initial_equity:.2f}, "
            f"risk={risk_per_trade*100:.1f}%"
        )

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: int,  # 1 for long, -1 for short
    ) -> Dict[str, float]:
        """
        Calculate position size based on risk per trade.

        Formula: Position Size = (Equity × Risk%) / Stop Loss Distance

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 1 for long, -1 for short

        Returns:
            Dictionary with position sizing details
        """
        # Calculate stop loss distance
        if direction == 1:  # Long
            sl_distance = abs(entry_price - stop_loss)
        else:  # Short
            sl_distance = abs(stop_loss - entry_price)

        if sl_distance == 0:
            logger.warning("Stop loss distance is zero, using minimum distance")
            sl_distance = entry_price * 0.001  # 0.1% minimum

        # Risk amount in currency
        risk_amount = self.current_equity * self.risk_per_trade

        # Position size in units
        position_size = risk_amount / sl_distance

        # Position size in currency value
        position_value = position_size * entry_price

        # Check maximum position size
        max_value = self.current_equity * self.max_position_size
        if position_value > max_value:
            logger.warning(
                f"Position size ${position_value:.2f} exceeds max ${max_value:.2f}, "
                f"reducing to max"
            )
            position_value = max_value
            position_size = position_value / entry_price

        result = {
            "position_size": position_size,
            "position_value": position_value,
            "risk_amount": risk_amount,
            "sl_distance": sl_distance,
            "sl_distance_pct": sl_distance / entry_price * 100,
            "position_pct": position_value / self.current_equity * 100,
        }

        logger.debug(
            f"Position: {position_size:.4f} units (${position_value:.2f}, "
            f"{result['position_pct']:.1f}% of equity), "
            f"Risk: ${risk_amount:.2f} ({self.risk_per_trade*100:.1f}%)"
        )

        return result

    def update_equity(self, new_equity: float) -> None:
        """
        Update current equity (after trades).

        Args:
            new_equity: New equity value
        """
        old_equity = self.current_equity
        self.current_equity = new_equity

        pnl = new_equity - old_equity
        pnl_pct = pnl / old_equity * 100 if old_equity > 0 else 0

        logger.info(
            f"Equity updated: ${old_equity:.2f} → ${new_equity:.2f} "
            f"({pnl:+.2f}, {pnl_pct:+.2f}%)"
        )

    def get_current_drawdown(self) -> float:
        """
        Calculate current drawdown from peak equity.

        Returns:
            Drawdown as percentage
        """
        if self.current_equity >= self.initial_equity:
            return 0.0

        drawdown = (self.initial_equity - self.current_equity) / self.initial_equity
        return drawdown * 100

    def should_reduce_risk(self, drawdown_threshold: float = 10.0) -> bool:
        """
        Check if risk should be reduced due to drawdown.

        Args:
            drawdown_threshold: Drawdown percentage to trigger risk reduction

        Returns:
            True if risk should be reduced
        """
        drawdown = self.get_current_drawdown()

        if drawdown > drawdown_threshold:
            logger.warning(
                f"Drawdown {drawdown:.1f}% exceeds threshold {drawdown_threshold:.1f}%"
            )
            return True

        return False


class RiskManager:
    """Overall risk management for trading system."""

    def __init__(
        self,
        position_sizer: PositionSizer,
        max_open_trades: int = 1,
        max_daily_trades: int = 3,
        max_drawdown_pct: float = 15.0,
    ):
        """
        Initialize risk manager.

        Args:
            position_sizer: PositionSizer instance
            max_open_trades: Maximum number of open trades
            max_daily_trades: Maximum trades per day
            max_drawdown_pct: Maximum allowed drawdown before stopping
        """
        self.position_sizer = position_sizer
        self.max_open_trades = max_open_trades
        self.max_daily_trades = max_daily_trades
        self.max_drawdown_pct = max_drawdown_pct

        self.daily_trade_count = 0
        self.open_trades_count = 0

        logger.info(
            f"RiskManager initialized: max_open={max_open_trades}, "
            f"max_daily={max_daily_trades}, max_dd={max_drawdown_pct}%"
        )

    def can_open_trade(self) -> tuple[bool, str]:
        """
        Check if a new trade can be opened.

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check open trades limit
        if self.open_trades_count >= self.max_open_trades:
            return False, f"Max open trades reached ({self.max_open_trades})"

        # Check daily trades limit
        if self.daily_trade_count >= self.max_daily_trades:
            return False, f"Max daily trades reached ({self.max_daily_trades})"

        # Check drawdown
        drawdown = self.position_sizer.get_current_drawdown()
        if drawdown > self.max_drawdown_pct:
            return False, f"Max drawdown exceeded ({drawdown:.1f}% > {self.max_drawdown_pct}%)"

        return True, "OK"

    def register_trade_open(self) -> None:
        """Register that a trade was opened."""
        self.open_trades_count += 1
        self.daily_trade_count += 1
        logger.info(f"Trade opened: {self.open_trades_count} open, {self.daily_trade_count} today")

    def register_trade_close(self) -> None:
        """Register that a trade was closed."""
        self.open_trades_count = max(0, self.open_trades_count - 1)
        logger.info(f"Trade closed: {self.open_trades_count} open")

    def reset_daily_counter(self) -> None:
        """Reset daily trade counter (call at start of each day)."""
        logger.info(f"Resetting daily counter (was {self.daily_trade_count})")
        self.daily_trade_count = 0
