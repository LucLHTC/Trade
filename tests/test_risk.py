"""
Tests for risk management and position sizing modules.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.risk.position import PositionSizer, RiskManager


class TestPositionSizer:
    """Test position sizing functionality."""

    def test_initialization(self):
        """Test position sizer initialization."""
        sizer = PositionSizer(
            initial_equity=10000.0,
            risk_per_trade=0.01,
        )

        assert sizer.initial_equity == 10000.0
        assert sizer.current_equity == 10000.0
        assert sizer.risk_per_trade == 0.01

    def test_calculate_position_size_long(self):
        """Test position size calculation for long trade."""
        sizer = PositionSizer(
            initial_equity=10000.0,
            risk_per_trade=0.01,  # 1% risk = $100
        )

        result = sizer.calculate_position_size(
            entry_price=1.0850,
            stop_loss=1.0800,  # 50 pips stop
            direction=1,  # Long
        )

        # Risk amount should be $100
        assert result["risk_amount"] == 100.0

        # SL distance should be 0.0050
        assert abs(result["sl_distance"] - 0.0050) < 0.0001

        # Position size = risk / sl_distance = 100 / 0.005 = 20,000 units
        expected_size = 100.0 / 0.0050
        assert abs(result["position_size"] - expected_size) < 0.01

    def test_calculate_position_size_short(self):
        """Test position size calculation for short trade."""
        sizer = PositionSizer(
            initial_equity=10000.0,
            risk_per_trade=0.01,
        )

        result = sizer.calculate_position_size(
            entry_price=1.0850,
            stop_loss=1.0900,  # 50 pips stop
            direction=-1,  # Short
        )

        # Same risk and distance as long
        assert result["risk_amount"] == 100.0
        assert abs(result["sl_distance"] - 0.0050) < 0.0001

    def test_position_size_limits(self):
        """Test that position size is limited by max_position_size."""
        sizer = PositionSizer(
            initial_equity=10000.0,
            risk_per_trade=0.05,  # 5% risk
            max_position_size=0.1,  # Max 10% of equity
        )

        # Very tight stop loss would normally give huge position
        result = sizer.calculate_position_size(
            entry_price=1.0850,
            stop_loss=1.0849,  # 1 pip stop
            direction=1,
        )

        # Position value should be limited to $1000 (10% of equity)
        assert result["position_value"] <= 1000.0

    def test_update_equity(self):
        """Test equity update."""
        sizer = PositionSizer(initial_equity=10000.0)

        sizer.update_equity(10500.0)

        assert sizer.current_equity == 10500.0
        assert sizer.initial_equity == 10000.0

    def test_get_current_drawdown_no_loss(self):
        """Test drawdown calculation with no loss."""
        sizer = PositionSizer(initial_equity=10000.0)

        drawdown = sizer.get_current_drawdown()

        assert drawdown == 0.0

    def test_get_current_drawdown_with_loss(self):
        """Test drawdown calculation with loss."""
        sizer = PositionSizer(initial_equity=10000.0)
        sizer.update_equity(9000.0)  # 10% loss

        drawdown = sizer.get_current_drawdown()

        assert abs(drawdown - 10.0) < 0.01

    def test_should_reduce_risk(self):
        """Test risk reduction trigger."""
        sizer = PositionSizer(initial_equity=10000.0)

        # No drawdown
        assert not sizer.should_reduce_risk(drawdown_threshold=10.0)

        # 15% drawdown
        sizer.update_equity(8500.0)
        assert sizer.should_reduce_risk(drawdown_threshold=10.0)


class TestRiskManager:
    """Test risk manager functionality."""

    def test_initialization(self):
        """Test risk manager initialization."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(
            position_sizer=sizer,
            max_open_trades=2,
            max_daily_trades=5,
        )

        assert manager.max_open_trades == 2
        assert manager.max_daily_trades == 5
        assert manager.open_trades_count == 0
        assert manager.daily_trade_count == 0

    def test_can_open_trade_ok(self):
        """Test that trade can be opened when conditions are good."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(
            position_sizer=sizer,
            max_open_trades=2,
        )

        can_trade, reason = manager.can_open_trade()

        assert can_trade
        assert reason == "OK"

    def test_can_open_trade_max_open_reached(self):
        """Test that trade is blocked when max open trades reached."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(
            position_sizer=sizer,
            max_open_trades=1,
        )

        # Open one trade
        manager.register_trade_open()

        can_trade, reason = manager.can_open_trade()

        assert not can_trade
        assert "max open trades" in reason.lower()

    def test_can_open_trade_max_daily_reached(self):
        """Test that trade is blocked when max daily trades reached."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(
            position_sizer=sizer,
            max_daily_trades=2,
        )

        # Open and close 2 trades
        manager.register_trade_open()
        manager.register_trade_close()
        manager.register_trade_open()
        manager.register_trade_close()

        can_trade, reason = manager.can_open_trade()

        assert not can_trade
        assert "max daily trades" in reason.lower()

    def test_can_open_trade_max_drawdown(self):
        """Test that trade is blocked when max drawdown exceeded."""
        sizer = PositionSizer(initial_equity=10000.0)
        sizer.update_equity(8000.0)  # 20% drawdown

        manager = RiskManager(
            position_sizer=sizer,
            max_drawdown_pct=15.0,
        )

        can_trade, reason = manager.can_open_trade()

        assert not can_trade
        assert "max drawdown" in reason.lower()

    def test_register_trade_open(self):
        """Test trade open registration."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(position_sizer=sizer)

        manager.register_trade_open()

        assert manager.open_trades_count == 1
        assert manager.daily_trade_count == 1

    def test_register_trade_close(self):
        """Test trade close registration."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(position_sizer=sizer)

        manager.register_trade_open()
        manager.register_trade_close()

        assert manager.open_trades_count == 0
        assert manager.daily_trade_count == 1  # Daily count not reset

    def test_reset_daily_counter(self):
        """Test daily counter reset."""
        sizer = PositionSizer(initial_equity=10000.0)
        manager = RiskManager(position_sizer=sizer)

        manager.register_trade_open()
        manager.register_trade_close()

        assert manager.daily_trade_count == 1

        manager.reset_daily_counter()

        assert manager.daily_trade_count == 0


class TestIntegration:
    """Integration tests for risk management."""

    def test_typical_trading_day(self):
        """Test a typical trading day scenario."""
        sizer = PositionSizer(
            initial_equity=10000.0,
            risk_per_trade=0.01,
        )
        manager = RiskManager(
            position_sizer=sizer,
            max_open_trades=1,
            max_daily_trades=3,
        )

        # Trade 1: Win
        can_trade, _ = manager.can_open_trade()
        assert can_trade

        manager.register_trade_open()
        position = sizer.calculate_position_size(1.0850, 1.0800, 1)
        manager.register_trade_close()
        sizer.update_equity(10050.0)  # +$50

        # Trade 2: Loss
        can_trade, _ = manager.can_open_trade()
        assert can_trade

        manager.register_trade_open()
        position = sizer.calculate_position_size(1.0860, 1.0810, 1)
        manager.register_trade_close()
        sizer.update_equity(9950.0)  # -$100

        # Trade 3: Win
        can_trade, _ = manager.can_open_trade()
        assert can_trade

        manager.register_trade_open()
        position = sizer.calculate_position_size(1.0870, 1.0820, 1)
        manager.register_trade_close()
        sizer.update_equity(10050.0)  # +$100

        # Trade 4: Should be blocked (max daily trades)
        can_trade, reason = manager.can_open_trade()
        assert not can_trade
        assert "max daily trades" in reason.lower()

        # Reset day
        manager.reset_daily_counter()

        # Trade 5: Should be allowed
        can_trade, _ = manager.can_open_trade()
        assert can_trade
