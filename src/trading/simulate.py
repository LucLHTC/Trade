"""
Trade simulator for backtesting and paper trading.
Simulates trades using historical data with realistic execution logic.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from src.inference.predict import ModelInference
from src.risk.position import PositionSizer, RiskManager
from src.trading.rules import TradingRules
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class TradeSimulator:
    """Simulate trading with realistic execution and tracking."""

    def __init__(
        self,
        model_path: str = "models/current",
        initial_equity: float = 10000.0,
        risk_per_trade: float = 0.01,
        tp_atr_multiple: float = 2.0,
        sl_atr_multiple: float = 1.0,
        max_holding_hours: int = 12,
        max_open_trades: int = 1,
        max_daily_trades: int = 3,
        prediction_threshold: float = 0.55,
        max_spread: float = 0.0002,
    ):
        """
        Initialize trade simulator.

        Args:
            model_path: Path to trained model
            initial_equity: Starting capital
            risk_per_trade: Risk per trade as fraction of equity
            tp_atr_multiple: Take profit as multiple of ATR
            sl_atr_multiple: Stop loss as multiple of ATR
            max_holding_hours: Maximum hours to hold a trade
            max_open_trades: Maximum concurrent trades
            max_daily_trades: Maximum trades per day
            prediction_threshold: Confidence threshold for predictions
            max_spread: Maximum allowed spread
        """
        self.inference = ModelInference(model_path=model_path)
        self.position_sizer = PositionSizer(
            initial_equity=initial_equity,
            risk_per_trade=risk_per_trade,
        )
        self.risk_manager = RiskManager(
            position_sizer=self.position_sizer,
            max_open_trades=max_open_trades,
            max_daily_trades=max_daily_trades,
        )
        self.trading_rules = TradingRules(
            tp_atr_multiple=tp_atr_multiple,
            sl_atr_multiple=sl_atr_multiple,
            max_holding_hours=max_holding_hours,
        )

        self.prediction_threshold = prediction_threshold
        self.max_spread = max_spread

        self.trades: List[Dict[str, Any]] = []
        self.open_trade: Optional[Dict[str, Any]] = None
        self.current_day: Optional[datetime] = None

        logger.info(
            f"TradeSimulator initialized: equity=${initial_equity:.2f}, "
            f"risk={risk_per_trade*100:.1f}%, TP={tp_atr_multiple}×ATR, SL={sl_atr_multiple}×ATR"
        )

    def simulate(
        self,
        candles_df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run simulation on historical data.

        Args:
            candles_df: DataFrame with OHLCV data
            start_date: Start date for simulation (optional)
            end_date: End date for simulation (optional)

        Returns:
            Dictionary with simulation results and metrics
        """
        logger.info("Starting trade simulation")

        # Filter by date range
        if start_date:
            candles_df = candles_df[candles_df.index >= start_date]
        if end_date:
            candles_df = candles_df[candles_df.index <= end_date]

        if candles_df.empty:
            raise ValueError("No data in specified date range")

        logger.info(
            f"Simulating on {len(candles_df)} candles "
            f"from {candles_df.index[0]} to {candles_df.index[-1]}"
        )

        # Get predictions for all candles
        predictions_df = self.inference.predict_batch(
            candles_df, threshold=self.prediction_threshold
        )

        # Simulate trading
        for i in range(len(predictions_df)):
            current_candle = predictions_df.iloc[i]
            timestamp = current_candle.name

            # Reset daily counter at start of new day
            if self.current_day is None or timestamp.date() != self.current_day.date():
                self.current_day = timestamp
                self.risk_manager.reset_daily_counter()

            # Check for exit first (if we have an open trade)
            if self.open_trade is not None:
                self._check_and_execute_exit(current_candle)

            # Check for entry (if no open trade)
            if self.open_trade is None:
                self._check_and_execute_entry(current_candle, predictions_df.iloc[:i+1])

        # Close any remaining open trade at end
        if self.open_trade is not None:
            logger.info("Closing open trade at end of simulation")
            last_candle = predictions_df.iloc[-1]
            self._execute_exit(
                exit_price=last_candle["close"],
                exit_time=last_candle.name,
                exit_reason="end_of_simulation",
                high=last_candle["high"],
                low=last_candle["low"],
            )

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics()

        logger.info(
            f"✅ Simulation complete: {len(self.trades)} trades executed, "
            f"Final equity: ${self.position_sizer.current_equity:.2f}"
        )

        return {
            "trades": self.trades,
            "metrics": metrics,
            "equity_curve": self._generate_equity_curve(predictions_df.index),
        }

    def _check_and_execute_entry(
        self,
        current_candle: pd.Series,
        history_df: pd.DataFrame,
    ) -> None:
        """
        Check if we should enter a trade and execute if conditions are met.

        Args:
            current_candle: Current candle data
            history_df: Historical data up to current candle
        """
        timestamp = current_candle.name

        # Check risk management
        can_trade, reason = self.risk_manager.can_open_trade()
        if not can_trade:
            logger.debug(f"Cannot open trade: {reason}")
            return

        # Get prediction
        prediction = {
            "prediction": int(current_candle["prediction"]),
            "confidence_short": current_candle["confidence_short"],
            "confidence_long": current_candle["confidence_long"],
            "regime": current_candle.get("regime", "unknown"),
        }

        # Check if we should trade
        current_price = current_candle["close"]
        spread = current_price * 0.0001  # Assume 1 pip spread for EUR/USD

        should_trade, trade_reason = self.inference.should_trade(
            prediction=prediction,
            current_price=current_price,
            spread=spread,
            max_spread=self.max_spread,
        )

        if not should_trade:
            logger.debug(f"Not trading: {trade_reason}")
            return

        # Execute entry
        direction = prediction["prediction"]
        atr = current_candle.get("atr_14", current_price * 0.002)  # Default 0.2%

        # Calculate TP/SL
        tp_sl = self.trading_rules.calculate_tp_sl(
            entry_price=current_price,
            direction=direction,
            atr=atr,
        )

        # Calculate position size
        position_info = self.position_sizer.calculate_position_size(
            entry_price=current_price,
            stop_loss=tp_sl["stop_loss"],
            direction=direction,
        )

        # Create trade record
        self.open_trade = {
            "trade_id": len(self.trades) + 1,
            "entry_time": timestamp,
            "entry_price": current_price,
            "direction": direction,
            "take_profit": tp_sl["take_profit"],
            "stop_loss": tp_sl["stop_loss"],
            "position_size": position_info["position_size"],
            "position_value": position_info["position_value"],
            "risk_amount": position_info["risk_amount"],
            "atr": atr,
            "regime": prediction["regime"],
            "confidence": (
                prediction["confidence_long"] if direction == 1
                else prediction["confidence_short"]
            ),
        }

        self.risk_manager.register_trade_open()

        logger.info(
            f"🔵 ENTRY #{self.open_trade['trade_id']}: "
            f"{'LONG' if direction == 1 else 'SHORT'} @ {current_price:.5f}, "
            f"TP={tp_sl['take_profit']:.5f}, SL={tp_sl['stop_loss']:.5f}, "
            f"Size={position_info['position_size']:.2f} units"
        )

    def _check_and_execute_exit(self, current_candle: pd.Series) -> None:
        """
        Check if open trade should be exited and execute if needed.

        Args:
            current_candle: Current candle data
        """
        if self.open_trade is None:
            return

        timestamp = current_candle.name
        current_price = current_candle["close"]
        high = current_candle["high"]
        low = current_candle["low"]

        # Check exit conditions
        should_exit, exit_reason = self.trading_rules.check_exit(
            trade=self.open_trade,
            current_price=current_price,
            current_time=timestamp,
            high=high,
            low=low,
        )

        if should_exit:
            # Determine exit price based on reason
            if exit_reason == "take_profit":
                exit_price = self.open_trade["take_profit"]
            elif exit_reason == "stop_loss":
                exit_price = self.open_trade["stop_loss"]
            else:  # max_time or other
                exit_price = current_price

            self._execute_exit(
                exit_price=exit_price,
                exit_time=timestamp,
                exit_reason=exit_reason,
                high=high,
                low=low,
            )

    def _execute_exit(
        self,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        high: float,
        low: float,
    ) -> None:
        """
        Execute trade exit and update equity.

        Args:
            exit_price: Exit price
            exit_time: Exit timestamp
            exit_reason: Reason for exit
            high: High of exit candle
            low: Low of exit candle
        """
        if self.open_trade is None:
            return

        # Calculate P&L
        pnl_info = self.trading_rules.calculate_pnl(
            entry_price=self.open_trade["entry_price"],
            exit_price=exit_price,
            direction=self.open_trade["direction"],
            position_size=self.open_trade["position_size"],
        )

        # Calculate holding time
        holding_time = exit_time - self.open_trade["entry_time"]
        holding_hours = holding_time.total_seconds() / 3600

        # Complete trade record
        completed_trade = {
            **self.open_trade,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl_info["pnl"],
            "pnl_pct": pnl_info["pnl_pct"],
            "holding_hours": holding_hours,
        }

        self.trades.append(completed_trade)

        # Update equity
        new_equity = self.position_sizer.current_equity + pnl_info["pnl"]
        self.position_sizer.update_equity(new_equity)

        # Update risk manager
        self.risk_manager.register_trade_close()

        logger.info(
            f"{'🟢' if pnl_info['pnl'] > 0 else '🔴'} EXIT #{completed_trade['trade_id']}: "
            f"{exit_reason.upper()} @ {exit_price:.5f}, "
            f"P&L: ${pnl_info['pnl']:+.2f} ({pnl_info['pnl_pct']:+.2f}%), "
            f"Hold: {holding_hours:.1f}h"
        )

        # Clear open trade
        self.open_trade = None

    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "total_return_pct": 0.0,
            }

        trades_df = pd.DataFrame(self.trades)

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = (trades_df["pnl"] > 0).sum()
        losing_trades = (trades_df["pnl"] < 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # P&L metrics
        total_pnl = trades_df["pnl"].sum()
        total_wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
        total_losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Return metrics
        initial_equity = self.position_sizer.initial_equity
        final_equity = self.position_sizer.current_equity
        total_return_pct = (final_equity - initial_equity) / initial_equity * 100

        # Average metrics
        avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if losing_trades > 0 else 0
        avg_holding_hours = trades_df["holding_hours"].mean()

        # Exit reason breakdown
        exit_reasons = trades_df["exit_reason"].value_counts().to_dict()

        # Drawdown
        equity_curve = [initial_equity]
        for pnl in trades_df["pnl"]:
            equity_curve.append(equity_curve[-1] + pnl)

        peak = initial_equity
        max_drawdown = 0.0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Sharpe ratio (simplified)
        if len(trades_df) > 1:
            returns = trades_df["pnl_pct"].values
            sharpe_ratio = (
                np.mean(returns) / np.std(returns) * np.sqrt(252)
                if np.std(returns) > 0 else 0
            )
        else:
            sharpe_ratio = 0.0

        metrics = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_holding_hours": avg_holding_hours,
            "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "initial_equity": initial_equity,
            "final_equity": final_equity,
            "exit_reasons": exit_reasons,
        }

        return metrics

    def _generate_equity_curve(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Generate equity curve over time.

        Args:
            timestamps: All timestamps from simulation

        Returns:
            DataFrame with equity curve
        """
        if not self.trades:
            return pd.DataFrame({
                "timestamp": timestamps,
                "equity": [self.position_sizer.initial_equity] * len(timestamps),
            })

        trades_df = pd.DataFrame(self.trades)

        # Create equity series
        equity_data = []
        current_equity = self.position_sizer.initial_equity

        for timestamp in timestamps:
            # Find trades that exited at or before this timestamp
            exited_trades = trades_df[trades_df["exit_time"] <= timestamp]

            if not exited_trades.empty:
                # Sum all P&L up to this point
                total_pnl = exited_trades["pnl"].sum()
                current_equity = self.position_sizer.initial_equity + total_pnl

            equity_data.append({
                "timestamp": timestamp,
                "equity": current_equity,
            })

        equity_df = pd.DataFrame(equity_data)
        equity_df.set_index("timestamp", inplace=True)

        return equity_df

    def get_trade_log(self) -> pd.DataFrame:
        """
        Get detailed trade log as DataFrame.

        Returns:
            DataFrame with all trades
        """
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame(self.trades)

    def print_summary(self, metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Print simulation summary.

        Args:
            metrics: Pre-calculated metrics (optional)
        """
        if metrics is None:
            metrics = self._calculate_performance_metrics()

        print("\n" + "="*60)
        print("TRADE SIMULATION SUMMARY")
        print("="*60)
        print(f"Total Trades:        {metrics['total_trades']}")
        print(f"Winning Trades:      {metrics['winning_trades']}")
        print(f"Losing Trades:       {metrics['losing_trades']}")
        print(f"Win Rate:            {metrics['win_rate']:.1f}%")
        print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
        print("-"*60)
        print(f"Initial Equity:      ${metrics['initial_equity']:,.2f}")
        print(f"Final Equity:        ${metrics['final_equity']:,.2f}")
        print(f"Total P&L:           ${metrics['total_pnl']:+,.2f}")
        print(f"Total Return:        {metrics['total_return_pct']:+.2f}%")
        print("-"*60)
        print(f"Average Win:         ${metrics['avg_win']:,.2f}")
        print(f"Average Loss:        ${metrics['avg_loss']:,.2f}")
        print(f"Avg Holding Time:    {metrics['avg_holding_hours']:.1f} hours")
        print(f"Max Drawdown:        {metrics['max_drawdown_pct']:.2f}%")
        print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
        print("-"*60)
        print("Exit Reasons:")
        for reason, count in metrics['exit_reasons'].items():
            print(f"  {reason:20s} {count}")
        print("="*60 + "\n")
