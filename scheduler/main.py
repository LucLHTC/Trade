#!/usr/bin/env python3
"""
Scheduler for automated trading system tasks.
Manages periodic jobs for data collection, feature generation, training, and inference.
"""

import sys
from pathlib import Path
import schedule
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


def job_collect_data():
    """Collect latest forex data and macro events."""
    logger.info("📊 Running data collection job...")

    try:
        from src.data_collection.alpha_vantage import CandleDataManager
        from src.data_collection.macro_feeds import MacroEventManager

        # Collect candle data
        candle_manager = CandleDataManager()
        candle_manager.fetch_and_store_latest(symbol="EUR", to_symbol="USD")

        # Collect macro events
        event_manager = MacroEventManager()
        event_manager.fetch_and_store_events(days_ahead=7)

        logger.info("✅ Data collection complete")

    except Exception as e:
        logger.error(f"❌ Data collection failed: {e}", exc_info=True)


def job_generate_features():
    """Generate features and labels from collected data."""
    logger.info("🔧 Running feature generation job...")

    try:
        from src.features.manager import FeatureManager

        manager = FeatureManager()
        manager.generate_and_save_all(symbol="EURUSD")

        logger.info("✅ Feature generation complete")

    except Exception as e:
        logger.error(f"❌ Feature generation failed: {e}", exc_info=True)


def job_train_model():
    """Train ensemble model on latest data."""
    logger.info("🧠 Running model training job...")

    try:
        import subprocess

        result = subprocess.run(
            ["python", "scripts/train_model.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("✅ Model training complete")
        else:
            logger.error(f"❌ Model training failed: {result.stderr}")

    except Exception as e:
        logger.error(f"❌ Model training failed: {e}", exc_info=True)


def job_run_inference():
    """Run inference for trading signals."""
    logger.info("🎯 Running inference job...")

    try:
        import subprocess

        result = subprocess.run(
            ["python", "scripts/run_inference.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("✅ Inference complete")
            logger.info(result.stdout)
        else:
            logger.error(f"❌ Inference failed: {result.stderr}")

    except Exception as e:
        logger.error(f"❌ Inference failed: {e}", exc_info=True)


def job_performance_report():
    """Generate daily performance report."""
    logger.info("📈 Generating performance report...")

    try:
        from src.monitoring.performance import PerformanceTracker, MetricsReporter

        tracker = PerformanceTracker()
        reporter = MetricsReporter(tracker)

        daily_report = reporter.generate_daily_report()
        logger.info(f"\n{daily_report}")

        logger.info("✅ Performance report complete")

    except Exception as e:
        logger.error(f"❌ Performance report failed: {e}", exc_info=True)


def job_check_model_drift():
    """Check for model performance drift."""
    logger.info("🔍 Checking for model drift...")

    try:
        from src.monitoring.performance import PerformanceTracker

        tracker = PerformanceTracker()
        degradation = tracker.detect_performance_degradation()

        if degradation["degraded"]:
            logger.warning(
                f"⚠️  Performance degradation detected! "
                f"Win rate change: {degradation['win_rate_change_pct']:+.1f}%, "
                f"Sharpe change: {degradation['sharpe_change_pct']:+.1f}%"
            )
            # TODO: Trigger retraining
        else:
            logger.info("✅ No drift detected")

    except Exception as e:
        logger.error(f"❌ Drift check failed: {e}", exc_info=True)


def job_system_health_check():
    """Check overall system health."""
    logger.info("❤️  Running system health check...")

    try:
        from src.common.db import get_connection

        # Check database connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        logger.info("✅ Database: OK")

        # Check model availability
        model_path = Path("models/current/ensemble_metadata.pkl")
        if model_path.exists():
            logger.info("✅ Model: OK")
        else:
            logger.warning("⚠️  Model: Missing")

        logger.info("✅ System health check complete")

    except Exception as e:
        logger.error(f"❌ System health check failed: {e}", exc_info=True)


def setup_schedule():
    """Set up the schedule for all jobs."""
    logger.info("Setting up job schedule...")

    # Data collection: Every hour
    schedule.every().hour.at(":05").do(job_collect_data)
    logger.info("  ✓ Data collection: Every hour at :05")

    # Feature generation: Every hour (after data collection)
    schedule.every().hour.at(":15").do(job_generate_features)
    logger.info("  ✓ Feature generation: Every hour at :15")

    # Inference: Every hour (after features)
    schedule.every().hour.at(":25").do(job_run_inference)
    logger.info("  ✓ Inference: Every hour at :25")

    # Model training: Once per week (Sunday at 02:00)
    schedule.every().sunday.at("02:00").do(job_train_model)
    logger.info("  ✓ Model training: Every Sunday at 02:00")

    # Performance report: Daily at 23:00
    schedule.every().day.at("23:00").do(job_performance_report)
    logger.info("  ✓ Performance report: Daily at 23:00")

    # Performance degradation: Every 3 days at 01:00
    schedule.every(3).days.at("01:00").do(job_check_model_drift)
    logger.info("  ✓ Performance drift: Every 3 days at 01:00")

    # Feature drift detection: Every 2 days at 02:00
    schedule.every(2).days.at("02:00").do(job_check_drift)
    logger.info("  ✓ Feature drift: Every 2 days at 02:00")

    # Auto-retraining: Every Monday at 03:00
    schedule.every().monday.at("03:00").do(job_auto_retrain)
    logger.info("  ✓ Auto-retrain: Every Monday at 03:00")

    # System health check: Every 6 hours
    schedule.every(6).hours.do(job_system_health_check)
    logger.info("  ✓ System health: Every 6 hours")

    logger.info("Schedule setup complete")


def main():
    """Main scheduler loop."""
    logger.info("="*60)
    logger.info("TRADING SYSTEM SCHEDULER")
    logger.info("="*60)

    # Setup schedule
    setup_schedule()

    # Run initial health check
    logger.info("Running initial system health check...")
    job_system_health_check()

    logger.info("="*60)
    logger.info("Scheduler started - waiting for jobs...")
    logger.info("="*60)

    # Run scheduler loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break

        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    main()


def job_check_drift():
    """Check for model drift."""
    logger.info("🔍 Running drift detection job...")

    try:
        from src.drift.detector import DriftDetector
        from src.features.manager import FeatureManager

        detector = DriftDetector()
        feature_manager = FeatureManager()

        # Load features
        features_df = feature_manager.load_features(symbol="EURUSD")

        if features_df.empty:
            logger.warning("No features available for drift detection")
            return

        # Split into baseline and current
        split_date = features_df.index.max() - pd.Timedelta(days=7)
        baseline = features_df[features_df.index < split_date]
        current = features_df[features_df.index >= split_date]

        if baseline.empty or current.empty:
            logger.warning("Insufficient data for drift detection")
            return

        # Detect drift
        drift_results = detector.detect_feature_drift(baseline, current)

        # Save to database
        detector.save_drift_log(drift_results, drift_type="feature")

        if drift_results["drift_detected"]:
            logger.warning(
                f"⚠️  Drift detected! Score: {drift_results['drift_score']:.3f}"
            )
        else:
            logger.info("✅ No drift detected")

    except Exception as e:
        logger.error(f"❌ Drift detection failed: {e}", exc_info=True)


def job_auto_retrain():
    """Auto-retrain model if needed."""
    logger.info("🔄 Running auto-retrain job...")

    try:
        from src.drift.retrainer import ModelRetrainer

        retrainer = ModelRetrainer()

        # Run auto-retrain pipeline
        results = retrainer.auto_retrain_pipeline(symbol="EURUSD", force=False)

        if results["status"] == "success":
            logger.info("✅ Auto-retrain completed successfully")
        elif results["status"] == "skipped":
            logger.info(f"⏭️  Auto-retrain skipped: {results['reason']}")
        else:
            logger.warning(f"⚠️  Auto-retrain status: {results['status']}")

    except Exception as e:
        logger.error(f"❌ Auto-retrain failed: {e}", exc_info=True)
