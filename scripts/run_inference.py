#!/usr/bin/env python3
"""
Real-time inference script for trading signals.
Generates predictions and manages trades based on the trained ensemble model.
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.predict import ModelInference
from src.risk.position import PositionSizer, RiskManager
from src.trading.rules import TradingRules
from src.monitoring.performance import PerformanceTracker
from src.data_collection.manager import CandleDataManager
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class TradingEngine:
    """Main trading engine for real-time inference and execution."""

    def __init__(
        self,
        model_path: str = "models/current",
        initial_equity: float = 10000.0,
        risk_per_trade: float = 0.01,
        dry_run: bool = True,
    ):
        """
        Initialize trading engine.

        Args:
            model_path: Path to trained model
            initial_equity: Starting capital
            risk_per_trade: Risk per trade as fraction of equity
            dry_run: If True, don't execute real trades (paper trading)
        """
        self.model_path = model_path
        self.dry_run = dry_run

        # Initialize components
        self.inference = ModelInference(model_path=model_path)
        self.position_sizer = PositionSizer(
            initial_equity=initial_equity,
            risk_per_trade=risk_per_trade,
        )
        self.risk_manager = RiskManager(
            position_sizer=self.position_sizer,
            max_open_trades=1,
            max_daily_trades=3,
        )
        self.trading_rules = TradingRules(
            tp_atr_multiple=2.0,
            sl_atr_multiple=1.0,
            max_holding_hours=12,
        )
        self.performance_tracker = PerformanceTracker()
        self.candle_manager = CandleDataManager()

        self.open_trade = None

        logger.info(
            f"TradingEngine initialized: "
            f"equity=${initial_equity:.2f}, risk={risk_per_trade*100:.1f}%, "
            f"dry_run={dry_run}"
        )

    def load_recent_candles(
        self,
        symbol: str = "EURUSD",
        lookback_hours: int = 200,
    ) -> pd.DataFrame:
        """
        Load recent candle data for inference.

        Args:
            symbol: Trading symbol
            lookback_hours: Hours of historical data to load

        Returns:
            DataFrame with recent candles
        """
        logger.info(f"Loading last {lookback_hours} hours of {symbol} data")

        # Load from Parquet
        df = self.candle_manager.load_from_parquet(
            symbol=symbol,
            interval="60min",
        )

        if df.empty:
            raise ValueError(f"No candle data found for {symbol}")

        # Get recent data
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        df = df[df.index >= cutoff_time]

        logger.info(f"Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")

        return df

    def check_and_execute_entry(
        self,
        candles_df: pd.DataFrame,
        prediction_threshold: float = 0.55,
        max_spread: float = 0.0002,
    ) -> bool:
        """
        Check if we should enter a trade and execute if conditions are met.

        Args:
            candles_df: Recent candle data
            prediction_threshold: Confidence threshold for predictions
            max_spread: Maximum allowed spread

        Returns:
            True if trade was entered
        """
        # Check if we can open a trade
        can_trade, reason = self.risk_manager.can_open_trade()
        if not can_trade:
            logger.info(f"Cannot open trade: {reason}")
            return False

        # Get prediction
        prediction = self.inference.predict_single(
            candles_df=candles_df,
            threshold=prediction_threshold,
        )

        # Get current price and spread
        current_price = candles_df.iloc[-1]["close"]
        spread = current_price * 0.0001  # Assume 1 pip spread

        # Check if we should trade
        should_trade, trade_reason = self.inference.should_trade(
            prediction=prediction,
            current_price=current_price,
            spread=spread,
            max_spread=max_spread,
        )

        if not should_trade:
            logger.info(f"Not trading: {trade_reason}")
            return False

        # Execute entry
        direction = prediction["prediction"]
        atr = candles_df.iloc[-1].get("atr_14", current_price * 0.002)

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
            "entry_time": datetime.utcnow(),
            "entry_price": current_price,
            "direction": direction,
            "take_profit": tp_sl["take_profit"],
            "stop_loss": tp_sl["stop_loss"],
            "position_size": position_info["position_size"],
            "position_value": position_info["position_value"],
            "risk_amount": position_info["risk_amount"],
            "atr": atr,
            "regime": prediction["regime"],
            "confidence": prediction[f"confidence_{'long' if direction == 1 else 'short'}"],
        }

        self.risk_manager.register_trade_open()

        logger.info(
            f"{'🔵 [DRY RUN]' if self.dry_run else '🔵'} ENTRY: "
            f"{'LONG' if direction == 1 else 'SHORT'} @ {current_price:.5f}, "
            f"TP={tp_sl['take_profit']:.5f}, SL={tp_sl['stop_loss']:.5f}, "
            f"Size={position_info['position_size']:.2f} units, "
            f"Confidence={self.open_trade['confidence']:.3f}"
        )

        return True

    def check_and_execute_exit(self, candles_df: pd.DataFrame) -> bool:
        """
        Check if open trade should be exited and execute if needed.

        Args:
            candles_df: Recent candle data

        Returns:
            True if trade was exited
        """
        if self.open_trade is None:
            return False

        current_candle = candles_df.iloc[-1]
        current_price = current_candle["close"]
        current_time = datetime.utcnow()
        high = current_candle["high"]
        low = current_candle["low"]

        # Check exit conditions
        should_exit, exit_reason = self.trading_rules.check_exit(
            trade=self.open_trade,
            current_price=current_price,
            current_time=current_time,
            high=high,
            low=low,
        )

        if not should_exit:
            return False

        # Determine exit price
        if exit_reason == "take_profit":
            exit_price = self.open_trade["take_profit"]
        elif exit_reason == "stop_loss":
            exit_price = self.open_trade["stop_loss"]
        else:
            exit_price = current_price

        # Calculate P&L
        pnl_info = self.trading_rules.calculate_pnl(
            entry_price=self.open_trade["entry_price"],
            exit_price=exit_price,
            direction=self.open_trade["direction"],
            position_size=self.open_trade["position_size"],
        )

        # Calculate holding time
        holding_time = current_time - self.open_trade["entry_time"]
        holding_hours = holding_time.total_seconds() / 3600

        # Complete trade record
        completed_trade = {
            **self.open_trade,
            "exit_time": current_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl_info["pnl"],
            "pnl_pct": pnl_info["pnl_pct"],
            "holding_hours": holding_hours,
        }

        # Update equity
        new_equity = self.position_sizer.current_equity + pnl_info["pnl"]
        self.position_sizer.update_equity(new_equity)

        # Update risk manager
        self.risk_manager.register_trade_close()

        # Record trade
        if not self.dry_run:
            self.performance_tracker.record_trade(completed_trade)

        logger.info(
            f"{'🟢' if pnl_info['pnl'] > 0 else '🔴'} {'[DRY RUN]' if self.dry_run else ''} EXIT: "
            f"{exit_reason.upper()} @ {exit_price:.5f}, "
            f"P&L: ${pnl_info['pnl']:+.2f} ({pnl_info['pnl_pct']:+.2f}%), "
            f"Hold: {holding_hours:.1f}h, "
            f"New Equity: ${new_equity:.2f}"
        )

        # Clear open trade
        self.open_trade = None

        return True

    def run_single_iteration(self, symbol: str = "EURUSD") -> None:
        """
        Run a single iteration of the trading loop.

        Args:
            symbol: Trading symbol
        """
        logger.info(f"Running inference iteration for {symbol}")

        try:
            # Load recent candles
            candles_df = self.load_recent_candles(symbol=symbol)

            # Check for exit first (if we have an open trade)
            if self.open_trade is not None:
                exited = self.check_and_execute_exit(candles_df)
                if exited:
                    logger.info("Trade exited")

            # Check for entry (if no open trade)
            if self.open_trade is None:
                entered = self.check_and_execute_entry(candles_df)
                if entered:
                    logger.info("Trade entered")

            # Log current status
            if self.open_trade is not None:
                current_price = candles_df.iloc[-1]["close"]
                unrealized_pnl = self.trading_rules.calculate_pnl(
                    entry_price=self.open_trade["entry_price"],
                    exit_price=current_price,
                    direction=self.open_trade["direction"],
                    position_size=self.open_trade["position_size"],
                )
                logger.info(
                    f"Open trade: Unrealized P&L: ${unrealized_pnl['pnl']:+.2f} "
                    f"({unrealized_pnl['pnl_pct']:+.2f}%)"
                )
            else:
                logger.info("No open trades")

        except Exception as e:
            logger.error(f"Error in iteration: {e}", exc_info=True)

    def run_continuous(
        self,
        symbol: str = "EURUSD",
        check_interval_minutes: int = 60,
    ) -> None:
        """
        Run continuous trading loop.

        Args:
            symbol: Trading symbol
            check_interval_minutes: Minutes between checks
        """
        logger.info(
            f"Starting continuous trading loop: "
            f"symbol={symbol}, interval={check_interval_minutes}min"
        )

        import time

        while True:
            try:
                self.run_single_iteration(symbol=symbol)

                # Wait for next iteration
                logger.info(f"Waiting {check_interval_minutes} minutes until next check...")
                time.sleep(check_interval_minutes * 60)

            except KeyboardInterrupt:
                logger.info("Stopping trading loop...")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                logger.info("Continuing after error...")
                time.sleep(60)  # Wait 1 minute before retrying


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run trading inference")
    parser.add_argument(
        "--model-path",
        default="models/current",
        help="Path to trained model (default: models/current)",
    )
    parser.add_argument(
        "--equity",
        type=float,
        default=10000.0,
        help="Initial equity (default: 10000)",
    )
    parser.add_argument(
        "--risk",
        type=float,
        default=0.01,
        help="Risk per trade as fraction (default: 0.01 = 1%%)",
    )
    parser.add_argument(
        "--symbol",
        default="EURUSD",
        help="Trading symbol (default: EURUSD)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously (default: single iteration)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in minutes for continuous mode (default: 60)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (default: dry run)",
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("TRADING INFERENCE ENGINE")
    logger.info("="*60)
    logger.info(f"Model: {args.model_path}")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Equity: ${args.equity:,.2f}")
    logger.info(f"Risk per trade: {args.risk*100:.1f}%")
    logger.info(f"Mode: {'LIVE' if args.live else 'DRY RUN'}")
    logger.info(f"Continuous: {args.continuous}")
    logger.info("="*60)

    if args.live:
        confirm = input("\n⚠️  LIVE TRADING MODE - Are you sure? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("Cancelled by user")
            return

    # Create trading engine
    engine = TradingEngine(
        model_path=args.model_path,
        initial_equity=args.equity,
        risk_per_trade=args.risk,
        dry_run=not args.live,
    )

    # Run
    if args.continuous:
        engine.run_continuous(
            symbol=args.symbol,
            check_interval_minutes=args.interval,
        )
    else:
        engine.run_single_iteration(symbol=args.symbol)

    logger.info("Done")


if __name__ == "__main__":
    main()
