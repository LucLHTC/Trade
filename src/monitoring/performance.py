"""
Performance tracking and monitoring module.
Tracks trading performance over time and stores metrics in database.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

from src.common.logger import get_logger
from src.common.db import get_connection, execute_query
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class PerformanceTracker:
    """Track and store trading performance metrics."""

    def __init__(self):
        """Initialize performance tracker."""
        self.metrics_cache: List[Dict[str, Any]] = []
        logger.info("PerformanceTracker initialized")

    def record_trade(
        self,
        trade: Dict[str, Any],
        strategy_name: str = "ensemble_v1",
    ) -> None:
        """
        Record a completed trade in the database.

        Args:
            trade: Trade dictionary with all details
            strategy_name: Name of the trading strategy
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trades (
                            strategy_name,
                            entry_time,
                            exit_time,
                            direction,
                            entry_price,
                            exit_price,
                            position_size,
                            take_profit,
                            stop_loss,
                            pnl,
                            pnl_pct,
                            exit_reason,
                            regime,
                            confidence,
                            holding_hours
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING trade_id
                        """,
                        (
                            strategy_name,
                            trade["entry_time"],
                            trade["exit_time"],
                            "long" if trade["direction"] == 1 else "short",
                            trade["entry_price"],
                            trade["exit_price"],
                            trade["position_size"],
                            trade["take_profit"],
                            trade["stop_loss"],
                            trade["pnl"],
                            trade["pnl_pct"],
                            trade["exit_reason"],
                            trade.get("regime", "unknown"),
                            trade.get("confidence", 0.0),
                            trade.get("holding_hours", 0.0),
                        ),
                    )
                    trade_id = cur.fetchone()[0]
                    conn.commit()

                    logger.debug(f"Trade #{trade_id} recorded in database")

        except Exception as e:
            logger.error(f"Failed to record trade: {e}")
            raise

    def record_daily_metrics(
        self,
        date: datetime,
        metrics: Dict[str, Any],
        strategy_name: str = "ensemble_v1",
    ) -> None:
        """
        Record daily performance metrics.

        Args:
            date: Date for metrics
            metrics: Dictionary with performance metrics
            strategy_name: Name of the trading strategy
        """
        metric_entry = {
            "date": date,
            "strategy_name": strategy_name,
            **metrics,
        }

        self.metrics_cache.append(metric_entry)

        logger.debug(f"Daily metrics cached for {date.date()}")

    def flush_metrics_to_db(self) -> None:
        """Flush cached metrics to database."""
        if not self.metrics_cache:
            logger.debug("No metrics to flush")
            return

        try:
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(self.metrics_cache)

            # Store in Parquet for historical analysis
            output_dir = Path("data/performance")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"metrics_{timestamp}.parquet"

            df.to_parquet(output_path, index=False)

            logger.info(f"Flushed {len(self.metrics_cache)} metrics to {output_path}")

            # Clear cache
            self.metrics_cache = []

        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
            raise

    def get_recent_performance(
        self,
        strategy_name: str = "ensemble_v1",
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Get recent trading performance from database.

        Args:
            strategy_name: Name of the trading strategy
            days: Number of days to retrieve

        Returns:
            DataFrame with recent trades
        """
        try:
            with get_connection() as conn:
                query = """
                    SELECT
                        trade_id,
                        entry_time,
                        exit_time,
                        direction,
                        entry_price,
                        exit_price,
                        position_size,
                        pnl,
                        pnl_pct,
                        exit_reason,
                        regime,
                        confidence,
                        holding_hours
                    FROM trades
                    WHERE strategy_name = %s
                      AND exit_time >= NOW() - INTERVAL '%s days'
                    ORDER BY exit_time DESC
                """

                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(strategy_name, days),
                )

                logger.info(f"Retrieved {len(df)} trades from last {days} days")

                return df

        except Exception as e:
            logger.error(f"Failed to get recent performance: {e}")
            return pd.DataFrame()

    def calculate_rolling_metrics(
        self,
        trades_df: pd.DataFrame,
        window_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Calculate rolling performance metrics.

        Args:
            trades_df: DataFrame with trades
            window_size: Window size for rolling calculations

        Returns:
            Dictionary with rolling metrics
        """
        if trades_df.empty or len(trades_df) < window_size:
            return {
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
            }

        # Get last N trades
        recent = trades_df.tail(window_size)

        # Calculate metrics
        winning_trades = (recent["pnl"] > 0).sum()
        win_rate = winning_trades / len(recent) * 100

        avg_pnl = recent["pnl"].mean()

        total_wins = recent[recent["pnl"] > 0]["pnl"].sum()
        total_losses = abs(recent[recent["pnl"] < 0]["pnl"].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        returns = recent["pnl_pct"].values
        sharpe_ratio = (
            np.mean(returns) / np.std(returns) * np.sqrt(252)
            if np.std(returns) > 0 else 0
        )

        return {
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "sample_size": len(recent),
        }

    def detect_performance_degradation(
        self,
        strategy_name: str = "ensemble_v1",
        baseline_window: int = 60,
        recent_window: int = 20,
        degradation_threshold: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Detect if performance has degraded significantly.

        Args:
            strategy_name: Name of the trading strategy
            baseline_window: Window size for baseline performance (days)
            recent_window: Window size for recent performance (days)
            degradation_threshold: Threshold for degradation alert (e.g., 0.20 = 20%)

        Returns:
            Dictionary with degradation analysis
        """
        logger.info("Checking for performance degradation")

        # Get baseline performance
        baseline_trades = self.get_recent_performance(
            strategy_name=strategy_name,
            days=baseline_window,
        )

        if baseline_trades.empty or len(baseline_trades) < 10:
            return {
                "degraded": False,
                "reason": "Insufficient baseline data",
            }

        # Get recent performance
        recent_trades = baseline_trades.head(recent_window)

        if len(recent_trades) < 5:
            return {
                "degraded": False,
                "reason": "Insufficient recent data",
            }

        # Calculate metrics
        baseline_metrics = self.calculate_rolling_metrics(
            baseline_trades,
            window_size=min(len(baseline_trades), 40),
        )

        recent_metrics = self.calculate_rolling_metrics(
            recent_trades,
            window_size=len(recent_trades),
        )

        # Compare metrics
        win_rate_change = (
            (recent_metrics["win_rate"] - baseline_metrics["win_rate"])
            / baseline_metrics["win_rate"]
            if baseline_metrics["win_rate"] > 0 else 0
        )

        sharpe_change = (
            (recent_metrics["sharpe_ratio"] - baseline_metrics["sharpe_ratio"])
            / abs(baseline_metrics["sharpe_ratio"])
            if baseline_metrics["sharpe_ratio"] != 0 else 0
        )

        # Check for degradation
        degraded = (
            win_rate_change < -degradation_threshold or
            sharpe_change < -degradation_threshold
        )

        result = {
            "degraded": degraded,
            "baseline_metrics": baseline_metrics,
            "recent_metrics": recent_metrics,
            "win_rate_change_pct": win_rate_change * 100,
            "sharpe_change_pct": sharpe_change * 100,
            "threshold_pct": degradation_threshold * 100,
        }

        if degraded:
            logger.warning(
                f"⚠️  Performance degradation detected: "
                f"Win rate {win_rate_change*100:+.1f}%, "
                f"Sharpe {sharpe_change*100:+.1f}%"
            )
        else:
            logger.info("✅ No significant performance degradation detected")

        return result

    def get_performance_summary(
        self,
        strategy_name: str = "ensemble_v1",
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.

        Args:
            strategy_name: Name of the trading strategy
            days: Number of days to analyze

        Returns:
            Dictionary with performance summary
        """
        trades_df = self.get_recent_performance(
            strategy_name=strategy_name,
            days=days,
        )

        if trades_df.empty:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
            }

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = (trades_df["pnl"] > 0).sum()
        losing_trades = (trades_df["pnl"] < 0).sum()
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

        # P&L metrics
        total_pnl = trades_df["pnl"].sum()
        avg_pnl = trades_df["pnl"].mean()
        total_wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
        total_losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Average metrics
        avg_win = (
            trades_df[trades_df["pnl"] > 0]["pnl"].mean()
            if winning_trades > 0 else 0
        )
        avg_loss = (
            trades_df[trades_df["pnl"] < 0]["pnl"].mean()
            if losing_trades > 0 else 0
        )

        # Exit reason breakdown
        exit_reasons = trades_df["exit_reason"].value_counts().to_dict()

        # Regime breakdown
        regime_stats = trades_df.groupby("regime").agg({
            "pnl": ["count", "sum", "mean"],
        }).to_dict()

        return {
            "period_days": days,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "exit_reasons": exit_reasons,
            "regime_stats": regime_stats,
        }

    def export_trades_to_csv(
        self,
        output_path: str,
        strategy_name: str = "ensemble_v1",
        days: int = 30,
    ) -> None:
        """
        Export trades to CSV for external analysis.

        Args:
            output_path: Path to save CSV
            strategy_name: Name of the trading strategy
            days: Number of days to export
        """
        trades_df = self.get_recent_performance(
            strategy_name=strategy_name,
            days=days,
        )

        if trades_df.empty:
            logger.warning("No trades to export")
            return

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        trades_df.to_csv(output_file, index=False)

        logger.info(f"Exported {len(trades_df)} trades to {output_path}")


class MetricsReporter:
    """Generate performance reports and visualizations."""

    def __init__(self, tracker: PerformanceTracker):
        """
        Initialize metrics reporter.

        Args:
            tracker: PerformanceTracker instance
        """
        self.tracker = tracker
        logger.info("MetricsReporter initialized")

    def generate_daily_report(
        self,
        date: Optional[datetime] = None,
        strategy_name: str = "ensemble_v1",
    ) -> str:
        """
        Generate daily performance report.

        Args:
            date: Date for report (defaults to yesterday)
            strategy_name: Name of the trading strategy

        Returns:
            Report as formatted string
        """
        if date is None:
            date = datetime.utcnow() - timedelta(days=1)

        summary = self.tracker.get_performance_summary(
            strategy_name=strategy_name,
            days=1,
        )

        report = f"""
{'='*60}
DAILY PERFORMANCE REPORT - {date.strftime('%Y-%m-%d')}
{'='*60}
Strategy: {strategy_name}

TRADES
  Total Trades:        {summary['total_trades']}
  Winning Trades:      {summary['winning_trades']}
  Losing Trades:       {summary['losing_trades']}
  Win Rate:            {summary['win_rate']:.1f}%

P&L
  Total P&L:           ${summary['total_pnl']:+,.2f}
  Average P&L:         ${summary['avg_pnl']:+,.2f}
  Average Win:         ${summary['avg_win']:,.2f}
  Average Loss:        ${summary['avg_loss']:,.2f}
  Profit Factor:       {summary['profit_factor']:.2f}

EXIT REASONS
"""

        for reason, count in summary['exit_reasons'].items():
            report += f"  {reason:20s} {count}\n"

        report += f"\n{'='*60}\n"

        return report

    def generate_weekly_report(
        self,
        strategy_name: str = "ensemble_v1",
    ) -> str:
        """
        Generate weekly performance report.

        Args:
            strategy_name: Name of the trading strategy

        Returns:
            Report as formatted string
        """
        summary = self.tracker.get_performance_summary(
            strategy_name=strategy_name,
            days=7,
        )

        degradation = self.tracker.detect_performance_degradation(
            strategy_name=strategy_name,
        )

        report = f"""
{'='*60}
WEEKLY PERFORMANCE REPORT
{'='*60}
Strategy: {strategy_name}
Period: Last 7 days

TRADES
  Total Trades:        {summary['total_trades']}
  Win Rate:            {summary['win_rate']:.1f}%
  Profit Factor:       {summary['profit_factor']:.2f}

P&L
  Total P&L:           ${summary['total_pnl']:+,.2f}
  Average P&L:         ${summary['avg_pnl']:+,.2f}

PERFORMANCE HEALTH
  Degradation Detected: {'⚠️  YES' if degradation['degraded'] else '✅ NO'}
"""

        if degradation['degraded']:
            report += f"""
  Win Rate Change:     {degradation['win_rate_change_pct']:+.1f}%
  Sharpe Change:       {degradation['sharpe_change_pct']:+.1f}%
"""

        report += f"\n{'='*60}\n"

        return report
