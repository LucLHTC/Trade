"""
Paper Trading Engine for 24/7 automated trading simulation.
Manages live paper positions, executes trades based on model signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from src.inference.predict import ModelInference
from src.risk.position import PositionSizer, RiskManager
from src.trading.rules import TradingRules
from src.common.logger import get_logger
from src.common.config import get_settings
from src.common.db import get_db

settings = get_settings()
logger = get_logger(__name__)


class PaperTradingEngine:
    """
    Automated paper trading engine that runs 24/7.
    Simulates real trading with position tracking and performance metrics.
    """

    def __init__(
        self,
        model_path: str = "models/current/ensemble_model.pkl",
        initial_equity: float = None,
        risk_per_trade: float = None,
    ):
        """
        Initialize paper trading engine.

        Args:
            model_path: Path to trained model
            initial_equity: Starting capital
            risk_per_trade: Risk per trade as fraction
        """
        self.db = get_db()
        self.inference = ModelInference(model_path=model_path)

        initial_equity = initial_equity or settings.initial_equity
        risk_per_trade = risk_per_trade or settings.risk_per_trade

        self.position_sizer = PositionSizer(
            initial_equity=initial_equity,
            risk_per_trade=risk_per_trade,
        )
        self.risk_manager = RiskManager(
            position_sizer=self.position_sizer,
            max_open_trades=1,  # One position at a time
            max_daily_trades=3,
        )
        self.trading_rules = TradingRules(
            tp_atr_multiple=2.0,
            sl_atr_multiple=1.0,
            max_holding_hours=12,
        )

        self.prediction_threshold = 0.55
        self.max_spread = 0.0002

        logger.info(
            f"Paper Trading Engine initialized: "
            f"equity=${initial_equity:.2f}, risk={risk_per_trade*100:.1f}%"
        )

    def get_open_position(self) -> Optional[Dict[str, Any]]:
        """
        Get currently open paper position from database.

        Returns:
            Position dict or None
        """
        query = """
            SELECT * FROM paper_positions
            WHERE status = 'open'
            ORDER BY entry_time DESC
            LIMIT 1
        """
        result = self.db.execute_query(query)

        if result:
            return result[0]
        return None

    def get_current_equity(self) -> float:
        """
        Get current equity from latest portfolio snapshot.

        Returns:
            Current equity value
        """
        query = """
            SELECT equity FROM paper_portfolio
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.db.execute_query(query)

        if result:
            return float(result[0]["equity"])
        return settings.initial_equity

    def update_portfolio_snapshot(self) -> None:
        """Create portfolio snapshot with current metrics."""
        # Get all closed positions
        query = """
            SELECT * FROM paper_positions
            WHERE status = 'closed'
        """
        trades = self.db.execute_query(query)

        if not trades:
            # First snapshot
            insert_query = """
                INSERT INTO paper_portfolio
                (timestamp, equity, open_positions, total_trades)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_query(
                insert_query,
                (datetime.utcnow(), settings.initial_equity, 0, 0),
                fetch=False,
            )
            return

        trades_df = pd.DataFrame(trades)
        total_trades = len(trades_df)
        winning_trades = (trades_df["pnl"] > 0).sum()
        losing_trades = (trades_df["pnl"] < 0).sum()
        total_pnl = trades_df["pnl"].sum()
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
        total_losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        current_equity = settings.initial_equity + total_pnl
        self.position_sizer.update_equity(current_equity)

        # Calculate max drawdown
        equity_curve = [settings.initial_equity]
        for pnl in trades_df["pnl"]:
            equity_curve.append(equity_curve[-1] + pnl)

        peak = settings.initial_equity
        max_drawdown = 0.0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Get open positions count
        open_pos = self.get_open_position()
        open_count = 1 if open_pos else 0

        # Insert snapshot
        insert_query = """
            INSERT INTO paper_portfolio
            (timestamp, equity, open_positions, total_trades, winning_trades,
             losing_trades, total_pnl, win_rate, profit_factor, max_drawdown_pct)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute_query(
            insert_query,
            (
                datetime.utcnow(),
                current_equity,
                open_count,
                total_trades,
                winning_trades,
                losing_trades,
                total_pnl,
                win_rate,
                profit_factor,
                max_drawdown,
            ),
            fetch=False,
        )

        logger.info(
            f"Portfolio snapshot: equity=${current_equity:.2f}, "
            f"trades={total_trades}, win_rate={win_rate:.1f}%"
        )

    def process_tick(self, current_candle: pd.DataFrame) -> None:
        """
        Process new candle tick - check for entry/exit signals.

        Args:
            current_candle: DataFrame with latest candle and features
        """
        timestamp = current_candle.index[0]
        logger.info(f"Processing tick at {timestamp}")

        # Check for exit first
        open_position = self.get_open_position()
        if open_position:
            self._check_and_execute_exit(open_position, current_candle)
            return  # Don't enter new trade if we just exited

        # Check for entry
        self._check_and_execute_entry(current_candle)

    def _check_and_execute_entry(self, current_candle: pd.DataFrame) -> None:
        """
        Check if we should enter a trade.

        Args:
            current_candle: Latest candle with features
        """
        # Check risk management
        can_trade, reason = self.risk_manager.can_open_trade()
        if not can_trade:
            logger.info(f"Cannot open trade: {reason}")
            return

        # Get prediction
        try:
            prediction = self.inference.predict_single(
                current_candle, threshold=self.prediction_threshold
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return

        # Log prediction to database
        self._save_prediction(prediction)

        current_price = float(current_candle["close"].iloc[0])
        spread = current_price * 0.0001  # 1 pip for EUR/USD

        # Check if we should trade
        should_trade, trade_reason = self.inference.should_trade(
            prediction=prediction,
            current_price=current_price,
            spread=spread,
            max_spread=self.max_spread,
        )

        if not should_trade:
            logger.info(f"Not trading: {trade_reason}")
            return

        # Execute entry
        direction = prediction["prediction"]
        atr = float(current_candle.get("atr_14", current_price * 0.002).iloc[0])

        # Calculate TP/SL
        tp_sl = self.trading_rules.calculate_tp_sl(
            entry_price=current_price, direction=direction, atr=atr
        )

        # Update equity from latest snapshot
        current_equity = self.get_current_equity()
        self.position_sizer.update_equity(current_equity)

        # Calculate position size
        position_info = self.position_sizer.calculate_position_size(
            entry_price=current_price,
            stop_loss=tp_sl["stop_loss"],
            direction=direction,
        )

        # Insert position into database
        insert_query = """
            INSERT INTO paper_positions
            (symbol, direction, entry_time, entry_price, position_size, position_value,
             stop_loss, take_profit, risk_amount, atr, regime, confidence, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute_query(
            insert_query,
            (
                "EURUSD",
                direction,
                prediction["timestamp"],
                current_price,
                position_info["position_size"],
                position_info["position_value"],
                tp_sl["stop_loss"],
                tp_sl["take_profit"],
                position_info["risk_amount"],
                atr,
                prediction.get("regime", "unknown"),
                prediction["confidence_long"]
                if direction == 1
                else prediction["confidence_short"],
                "open",
            ),
            fetch=False,
        )

        self.risk_manager.register_trade_open()

        logger.info(
            f"🔵 PAPER ENTRY: {'LONG' if direction == 1 else 'SHORT'} @ {current_price:.5f}, "
            f"TP={tp_sl['take_profit']:.5f}, SL={tp_sl['stop_loss']:.5f}, "
            f"Size={position_info['position_size']:.2f} units"
        )

    def _check_and_execute_exit(
        self, position: Dict[str, Any], current_candle: pd.DataFrame
    ) -> None:
        """
        Check if open position should be exited.

        Args:
            position: Open position dict
            current_candle: Latest candle
        """
        timestamp = current_candle.index[0]
        current_price = float(current_candle["close"].iloc[0])
        high = float(current_candle["high"].iloc[0])
        low = float(current_candle["low"].iloc[0])

        # Check exit conditions
        should_exit, exit_reason = self.trading_rules.check_exit(
            trade=position,
            current_price=current_price,
            current_time=timestamp,
            high=high,
            low=low,
        )

        if should_exit:
            # Determine exit price
            if exit_reason == "take_profit":
                exit_price = float(position["take_profit"])
            elif exit_reason == "stop_loss":
                exit_price = float(position["stop_loss"])
            else:
                exit_price = current_price

            # Calculate P&L
            pnl_info = self.trading_rules.calculate_pnl(
                entry_price=float(position["entry_price"]),
                exit_price=exit_price,
                direction=int(position["direction"]),
                position_size=float(position["position_size"]),
            )

            # Calculate holding time
            holding_time = timestamp - position["entry_time"]
            holding_hours = holding_time.total_seconds() / 3600

            # Update position in database
            update_query = """
                UPDATE paper_positions
                SET status = 'closed',
                    exit_time = %s,
                    exit_price = %s,
                    exit_reason = %s,
                    pnl = %s,
                    pnl_pct = %s,
                    holding_hours = %s
                WHERE position_id = %s
            """
            self.db.execute_query(
                update_query,
                (
                    timestamp,
                    exit_price,
                    exit_reason,
                    pnl_info["pnl"],
                    pnl_info["pnl_pct"],
                    holding_hours,
                    position["position_id"],
                ),
                fetch=False,
            )

            self.risk_manager.register_trade_close()

            # Update portfolio snapshot
            self.update_portfolio_snapshot()

            logger.info(
                f"{'🟢' if pnl_info['pnl'] > 0 else '🔴'} PAPER EXIT: "
                f"{exit_reason.upper()} @ {exit_price:.5f}, "
                f"P&L: ${pnl_info['pnl']:+.2f} ({pnl_info['pnl_pct']:+.2f}%), "
                f"Hold: {holding_hours:.1f}h"
            )

    def _save_prediction(self, prediction: Dict[str, Any]) -> None:
        """
        Save prediction to database for chart visualization.

        Args:
            prediction: Prediction dict from inference
        """
        # Convert top_features to JSON
        top_features_json = json.dumps(prediction.get("top_features", {}))

        signal_strength = self.inference.get_signal_strength(prediction)

        insert_query = """
            INSERT INTO predictions
            (timestamp, symbol, prediction, confidence_short, confidence_long,
             regime, signal_strength, top_features)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute_query(
            insert_query,
            (
                prediction["timestamp"],
                "EURUSD",
                prediction["prediction"],
                prediction["confidence_short"],
                prediction["confidence_long"],
                prediction.get("regime", "unknown"),
                signal_strength,
                top_features_json,
            ),
            fetch=False,
        )

    def run_hourly_cycle(self) -> None:
        """
        Run one hourly paper trading cycle.
        This is called by the scheduler every hour.
        """
        logger.info("=" * 60)
        logger.info("PAPER TRADING: Hourly Cycle Started")
        logger.info("=" * 60)

        try:
            # Get latest candles from database
            query = """
                SELECT * FROM candles
                WHERE symbol = 'EURUSD'
                ORDER BY timestamp DESC
                LIMIT 100
            """
            candles_result = self.db.execute_query(query)

            if not candles_result:
                logger.warning("No candles found in database")
                return

            candles_df = pd.DataFrame(candles_result)
            candles_df["timestamp"] = pd.to_datetime(candles_df["timestamp"])
            candles_df.set_index("timestamp", inplace=True)
            candles_df.sort_index(inplace=True)

            logger.info(f"Loaded {len(candles_df)} candles for analysis")

            # Process latest tick
            self.process_tick(candles_df.tail(100))  # Pass history for indicators

            logger.info("=" * 60)
            logger.info("PAPER TRADING: Hourly Cycle Completed")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Paper trading cycle failed: {e}", exc_info=True)

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get current performance summary.

        Returns:
            Dict with performance metrics
        """
        latest_snapshot = self.db.execute_query(
            "SELECT * FROM paper_portfolio ORDER BY timestamp DESC LIMIT 1"
        )

        if not latest_snapshot:
            return {
                "equity": settings.initial_equity,
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
            }

        snapshot = latest_snapshot[0]
        return {
            "equity": float(snapshot["equity"]),
            "total_trades": snapshot["total_trades"],
            "winning_trades": snapshot["winning_trades"],
            "losing_trades": snapshot["losing_trades"],
            "win_rate": float(snapshot["win_rate"]) if snapshot["win_rate"] else 0.0,
            "profit_factor": (
                float(snapshot["profit_factor"]) if snapshot["profit_factor"] else 0.0
            ),
            "total_pnl": float(snapshot["total_pnl"]),
            "max_drawdown_pct": (
                float(snapshot["max_drawdown_pct"])
                if snapshot["max_drawdown_pct"]
                else 0.0
            ),
            "open_positions": snapshot["open_positions"],
        }
