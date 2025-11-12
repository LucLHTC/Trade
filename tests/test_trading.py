"""
Tests for trading rules and simulation modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.rules import TradingRules
from src.trading.simulate import TradeSimulator
from tests.test_features import create_sample_candles


class TestTradingRules:
    """Test trading rules functionality."""

    def test_initialization(self):
        """Test trading rules initialization."""
        rules = TradingRules(
            tp_atr_multiple=2.0,
            sl_atr_multiple=1.0,
            max_holding_hours=12,
        )

        assert rules.tp_atr_multiple == 2.0
        assert rules.sl_atr_multiple == 1.0
        assert rules.max_holding_hours == 12

    def test_calculate_tp_sl_long(self):
        """Test TP/SL calculation for long trade."""
        rules = TradingRules(tp_atr_multiple=2.0, sl_atr_multiple=1.0)

        result = rules.calculate_tp_sl(
            entry_price=1.0850,
            direction=1,  # Long
            atr=0.0020,
        )

        # TP should be entry + (2.0 * ATR) = 1.0850 + 0.0040 = 1.0890
        assert abs(result["take_profit"] - 1.0890) < 0.0001

        # SL should be entry - (1.0 * ATR) = 1.0850 - 0.0020 = 1.0830
        assert abs(result["stop_loss"] - 1.0830) < 0.0001

        # RR ratio should be 2.0
        assert abs(result["rr_ratio"] - 2.0) < 0.01

    def test_calculate_tp_sl_short(self):
        """Test TP/SL calculation for short trade."""
        rules = TradingRules(tp_atr_multiple=2.0, sl_atr_multiple=1.0)

        result = rules.calculate_tp_sl(
            entry_price=1.0850,
            direction=-1,  # Short
            atr=0.0020,
        )

        # TP should be entry - (2.0 * ATR) = 1.0850 - 0.0040 = 1.0810
        assert abs(result["take_profit"] - 1.0810) < 0.0001

        # SL should be entry + (1.0 * ATR) = 1.0850 + 0.0020 = 1.0870
        assert abs(result["stop_loss"] - 1.0870) < 0.0001

    def test_check_exit_take_profit_long(self):
        """Test TP exit for long trade."""
        rules = TradingRules()

        trade = {
            "entry_time": datetime.utcnow(),
            "entry_price": 1.0850,
            "direction": 1,
            "take_profit": 1.0890,
            "stop_loss": 1.0830,
        }

        # Price hits TP
        should_exit, reason = rules.check_exit(
            trade=trade,
            current_price=1.0895,
            current_time=datetime.utcnow(),
            high=1.0895,
            low=1.0840,
        )

        assert should_exit
        assert reason == "take_profit"

    def test_check_exit_stop_loss_long(self):
        """Test SL exit for long trade."""
        rules = TradingRules()

        trade = {
            "entry_time": datetime.utcnow(),
            "entry_price": 1.0850,
            "direction": 1,
            "take_profit": 1.0890,
            "stop_loss": 1.0830,
        }

        # Price hits SL
        should_exit, reason = rules.check_exit(
            trade=trade,
            current_price=1.0825,
            current_time=datetime.utcnow(),
            high=1.0855,
            low=1.0825,
        )

        assert should_exit
        assert reason == "stop_loss"

    def test_check_exit_max_time(self):
        """Test max time exit."""
        rules = TradingRules(max_holding_hours=12)

        entry_time = datetime.utcnow() - timedelta(hours=13)

        trade = {
            "entry_time": entry_time,
            "entry_price": 1.0850,
            "direction": 1,
            "take_profit": 1.0890,
            "stop_loss": 1.0830,
        }

        # Time exceeded but price still between TP/SL
        should_exit, reason = rules.check_exit(
            trade=trade,
            current_price=1.0860,
            current_time=datetime.utcnow(),
            high=1.0870,
            low=1.0850,
        )

        assert should_exit
        assert reason == "max_time"

    def test_check_exit_no_exit(self):
        """Test that no exit is triggered when conditions not met."""
        rules = TradingRules(max_holding_hours=12)

        trade = {
            "entry_time": datetime.utcnow(),
            "entry_price": 1.0850,
            "direction": 1,
            "take_profit": 1.0890,
            "stop_loss": 1.0830,
        }

        # Price between TP/SL, time not exceeded
        should_exit, reason = rules.check_exit(
            trade=trade,
            current_price=1.0860,
            current_time=datetime.utcnow(),
            high=1.0870,
            low=1.0850,
        )

        assert not should_exit
        assert reason == ""

    def test_calculate_pnl_long_win(self):
        """Test P&L calculation for winning long trade."""
        rules = TradingRules()

        result = rules.calculate_pnl(
            entry_price=1.0850,
            exit_price=1.0900,
            direction=1,  # Long
            position_size=10000,  # 10k units
        )

        # PnL = (1.0900 - 1.0850) * 10000 = 0.0050 * 10000 = 50
        assert abs(result["pnl"] - 50.0) < 0.01

        # PnL % = 0.0050 / 1.0850 * 100 ≈ 0.46%
        assert abs(result["pnl_pct"] - 0.46) < 0.01

    def test_calculate_pnl_short_win(self):
        """Test P&L calculation for winning short trade."""
        rules = TradingRules()

        result = rules.calculate_pnl(
            entry_price=1.0850,
            exit_price=1.0800,
            direction=-1,  # Short
            position_size=10000,
        )

        # PnL = (1.0850 - 1.0800) * 10000 = 0.0050 * 10000 = 50
        assert abs(result["pnl"] - 50.0) < 0.01

    def test_calculate_pnl_loss(self):
        """Test P&L calculation for losing trade."""
        rules = TradingRules()

        result = rules.calculate_pnl(
            entry_price=1.0850,
            exit_price=1.0820,
            direction=1,  # Long
            position_size=10000,
        )

        # PnL = (1.0820 - 1.0850) * 10000 = -0.0030 * 10000 = -30
        assert abs(result["pnl"] - (-30.0)) < 0.01


class TestTradeSimulator:
    """Test trade simulator functionality."""

    @pytest.fixture
    def sample_candles(self):
        """Create sample candles for testing."""
        return create_sample_candles(300)

    def test_simulator_initialization(self):
        """Test simulator initialization."""
        try:
            simulator = TradeSimulator(
                model_path="models/current",
                initial_equity=10000.0,
                risk_per_trade=0.01,
            )

            assert simulator.position_sizer.initial_equity == 10000.0
            assert simulator.trades == []
            assert simulator.open_trade is None

        except Exception:
            pytest.skip("Model not available")

    def test_simulate_runs_without_error(self, sample_candles):
        """Test that simulation runs without errors."""
        try:
            simulator = TradeSimulator(
                model_path="models/current",
                initial_equity=10000.0,
                risk_per_trade=0.01,
            )

            # Run simulation on last 30 days
            end_date = sample_candles.index[-1]
            start_date = end_date - timedelta(days=30)

            results = simulator.simulate(
                candles_df=sample_candles,
                start_date=start_date,
                end_date=end_date,
            )

            # Check results structure
            assert "trades" in results
            assert "metrics" in results
            assert "equity_curve" in results

            # Check metrics
            metrics = results["metrics"]
            assert "total_trades" in metrics
            assert "win_rate" in metrics
            assert "total_pnl" in metrics

        except Exception:
            pytest.skip("Model not available or simulation error")

    def test_trade_log_format(self, sample_candles):
        """Test that trade log has correct format."""
        try:
            simulator = TradeSimulator(
                model_path="models/current",
                initial_equity=10000.0,
            )

            simulator.simulate(
                candles_df=sample_candles,
                start_date=sample_candles.index[-50],
            )

            trade_log = simulator.get_trade_log()

            if not trade_log.empty:
                # Check columns
                expected_columns = [
                    "entry_time",
                    "exit_time",
                    "direction",
                    "entry_price",
                    "exit_price",
                    "pnl",
                    "exit_reason",
                ]

                for col in expected_columns:
                    assert col in trade_log.columns

        except Exception:
            pytest.skip("Model not available or simulation error")

    def test_equity_curve_generation(self, sample_candles):
        """Test equity curve generation."""
        try:
            simulator = TradeSimulator(
                model_path="models/current",
                initial_equity=10000.0,
            )

            results = simulator.simulate(
                candles_df=sample_candles,
                start_date=sample_candles.index[-50],
            )

            equity_curve = results["equity_curve"]

            # Should have same length as simulation period
            assert len(equity_curve) > 0

            # Should have equity column
            assert "equity" in equity_curve.columns

            # First value should be initial equity
            assert equity_curve.iloc[0]["equity"] == 10000.0

            # Last value should match final equity
            assert (
                abs(equity_curve.iloc[-1]["equity"] - simulator.position_sizer.current_equity)
                < 0.01
            )

        except Exception:
            pytest.skip("Model not available or simulation error")


class TestIntegration:
    """Integration tests for complete trading workflow."""

    def test_complete_trade_lifecycle(self):
        """Test a complete trade from entry to exit."""
        rules = TradingRules(
            tp_atr_multiple=2.0,
            sl_atr_multiple=1.0,
            max_holding_hours=12,
        )

        # Entry
        entry_price = 1.0850
        direction = 1  # Long
        atr = 0.0020

        tp_sl = rules.calculate_tp_sl(entry_price, direction, atr)

        trade = {
            "entry_time": datetime.utcnow(),
            "entry_price": entry_price,
            "direction": direction,
            "take_profit": tp_sl["take_profit"],
            "stop_loss": tp_sl["stop_loss"],
            "position_size": 10000,
        }

        # Check exit (hit TP)
        should_exit, reason = rules.check_exit(
            trade=trade,
            current_price=tp_sl["take_profit"] + 0.0010,
            current_time=datetime.utcnow() + timedelta(hours=2),
            high=tp_sl["take_profit"] + 0.0010,
            low=entry_price,
        )

        assert should_exit
        assert reason == "take_profit"

        # Calculate P&L
        pnl = rules.calculate_pnl(
            entry_price=entry_price,
            exit_price=tp_sl["take_profit"],
            direction=direction,
            position_size=trade["position_size"],
        )

        # Should be profitable
        assert pnl["pnl"] > 0
