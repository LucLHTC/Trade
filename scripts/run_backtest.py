#!/usr/bin/env python3
"""
Backtesting script for evaluating trading strategy on historical data.
Uses the TradeSimulator to simulate trades and calculate performance metrics.
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.simulate import TradeSimulator
from src.data_collection.manager import CandleDataManager
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run trading backtest")
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
        "--start-date",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to backtest (if start-date not specified)",
    )
    parser.add_argument(
        "--tp-atr",
        type=float,
        default=2.0,
        help="Take profit as multiple of ATR (default: 2.0)",
    )
    parser.add_argument(
        "--sl-atr",
        type=float,
        default=1.0,
        help="Stop loss as multiple of ATR (default: 1.0)",
    )
    parser.add_argument(
        "--max-holding-hours",
        type=int,
        default=12,
        help="Maximum holding hours (default: 12)",
    )
    parser.add_argument(
        "--output",
        help="Output path for trade log CSV",
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("TRADING BACKTEST")
    logger.info("="*60)
    logger.info(f"Model: {args.model_path}")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Initial Equity: ${args.equity:,.2f}")
    logger.info(f"Risk per trade: {args.risk*100:.1f}%")
    logger.info(f"TP: {args.tp_atr}×ATR, SL: {args.sl_atr}×ATR")
    logger.info(f"Max holding: {args.max_holding_hours}h")
    logger.info("="*60)

    # Load candle data
    logger.info(f"Loading {args.symbol} candle data...")
    candle_manager = CandleDataManager()
    candles_df = candle_manager.load_from_parquet(
        symbol=args.symbol,
        interval="60min",
    )

    if candles_df.empty:
        logger.error(f"No candle data found for {args.symbol}")
        return

    logger.info(f"Loaded {len(candles_df)} candles from {candles_df.index[0]} to {candles_df.index[-1]}")

    # Parse dates
    start_date = None
    end_date = None

    if args.start_date:
        start_date = pd.to_datetime(args.start_date, utc=True)
    else:
        # Use last N days
        end_date = candles_df.index[-1]
        start_date = end_date - timedelta(days=args.days)

    if args.end_date:
        end_date = pd.to_datetime(args.end_date, utc=True)

    logger.info(f"Backtest period: {start_date} to {end_date or 'latest'}")

    # Create simulator
    simulator = TradeSimulator(
        model_path=args.model_path,
        initial_equity=args.equity,
        risk_per_trade=args.risk,
        tp_atr_multiple=args.tp_atr,
        sl_atr_multiple=args.sl_atr,
        max_holding_hours=args.max_holding_hours,
    )

    # Run simulation
    logger.info("Running backtest...")
    results = simulator.simulate(
        candles_df=candles_df,
        start_date=start_date,
        end_date=end_date,
    )

    # Print summary
    simulator.print_summary(metrics=results["metrics"])

    # Export trade log if requested
    if args.output:
        trade_log = simulator.get_trade_log()
        if not trade_log.empty:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            trade_log.to_csv(output_path, index=False)
            logger.info(f"Trade log exported to {args.output}")

    # Save equity curve
    equity_curve = results["equity_curve"]
    equity_output = Path("data/backtest") / f"equity_curve_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    equity_output.parent.mkdir(parents=True, exist_ok=True)
    equity_curve.to_csv(equity_output)
    logger.info(f"Equity curve saved to {equity_output}")

    logger.info("Backtest complete")


if __name__ == "__main__":
    main()
