"""
Scheduler service for automated tasks.
Runs hourly and daily jobs for data collection, feature engineering, and predictions.
"""

import schedule
import time
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.common.config import get_settings
from src.common.logger import get_logger
from src.common.db import get_db

settings = get_settings()
logger = get_logger(__name__)


def hourly_job():
    """
    Hourly job - runs every hour.

    Tasks:
    - Fetch new candles
    - Update features
    - Generate predictions
    - Check for trade signals
    """
    logger.info(f"⏰ Running hourly job at {datetime.utcnow().isoformat()}")

    # TODO: Implement in Session 2
    # - Fetch candles from Alpha Vantage
    # - Update features
    # - Generate predictions

    logger.info("✅ Hourly job completed")


def daily_job():
    """
    Daily job - runs once per day at midnight UTC.

    Tasks:
    - Fetch macro events
    - Feature/label refresh
    - Drift detection
    - Model retraining (if needed)
    - Database maintenance
    """
    logger.info(f"📅 Running daily job at {datetime.utcnow().isoformat()}")

    # Database health check
    db = get_db()
    if db.health_check():
        logger.info("✅ Database health check passed")
    else:
        logger.error("❌ Database health check failed")

    # TODO: Implement in Session 2-7
    # - Fetch macro events
    # - Regenerate features/labels
    # - Run drift detection
    # - Trigger retraining if needed

    logger.info("✅ Daily job completed")


def health_check_job():
    """
    Health check job - runs every 5 minutes.

    Tasks:
    - Check database connection
    - Log system status
    """
    try:
        db = get_db()
        if db.health_check():
            logger.debug("System health check: OK")
        else:
            logger.warning("System health check: Database unhealthy")
    except Exception as e:
        logger.error(f"System health check failed: {e}")


def main():
    """Main scheduler loop."""
    logger.info("🚀 Starting scheduler service")
    logger.info(f"Scheduler enabled: {settings.scheduler_enabled}")
    logger.info(f"Hourly jobs enabled: {settings.hourly_jobs_enabled}")
    logger.info(f"Daily jobs enabled: {settings.daily_jobs_enabled}")

    if not settings.scheduler_enabled:
        logger.warning("Scheduler is disabled in configuration")
        logger.info("Entering monitoring mode (health checks only)")

    # Schedule jobs
    if settings.hourly_jobs_enabled:
        schedule.every().hour.at(":05").do(hourly_job)
        logger.info("✓ Hourly jobs scheduled")

    if settings.daily_jobs_enabled:
        schedule.every().day.at("00:00").do(daily_job)
        logger.info("✓ Daily jobs scheduled")

    # Always run health checks
    schedule.every(5).minutes.do(health_check_job)
    logger.info("✓ Health check jobs scheduled (every 5 minutes)")

    # Initial health check
    health_check_job()

    # Main loop
    logger.info("📍 Scheduler is now running. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")
        raise


if __name__ == "__main__":
    main()
