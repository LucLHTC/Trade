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
from src.data_collection.alpha_vantage import AlphaVantageClient, CandleDataManager
from src.data_collection.macro_feeds import MacroEventManager
from src.features.manager import FeatureManager
from src.trading.paper_trader import PaperTradingEngine

settings = get_settings()
logger = get_logger(__name__)

# Initialize paper trading engine (global instance for scheduler)
paper_trader = None

def init_paper_trader():
    """Initialize paper trading engine."""
    global paper_trader
    if paper_trader is None:
        try:
            paper_trader = PaperTradingEngine()
            logger.info("✅ Paper trading engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize paper trader: {e}")
    return paper_trader


def fetch_candles_hourly():
    """
    Fetch latest EUR/USD candles from Alpha Vantage.
    """
    logger.info("📊 Fetching latest candles...")

    try:
        client = AlphaVantageClient()
        manager = CandleDataManager()

        # Fetch latest intraday data (compact = last 100 data points)
        df = client.fetch_forex_intraday(
            from_symbol="EUR",
            to_symbol="USD",
            interval="60min",
            outputsize="compact",
        )

        if df is None or df.empty:
            logger.warning("No candle data fetched")
            return False

        # Save to Parquet
        saved_files = manager.save_to_parquet(df, "EURUSD")
        logger.info(f"Saved candles to {len(saved_files)} Parquet files")

        # Save to database
        rows = manager.save_to_database(df)
        logger.info(f"Saved {rows} candles to database")

        logger.info("✅ Candle fetch complete")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to fetch candles: {e}")
        return False


def update_features():
    """
    Update features and labels from latest candle data.
    """
    logger.info("🔧 Updating features and labels...")

    try:
        feature_manager = FeatureManager()

        # Generate features from all available candle data
        features_path, labels_path = feature_manager.generate_and_save_all(
            symbol="EURUSD"
        )

        if features_path and labels_path:
            logger.info(f"✅ Features updated: {features_path}")
            logger.info(f"✅ Labels updated: {labels_path}")
            return True
        else:
            logger.warning("Feature update failed")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to update features: {e}")
        return False


def run_paper_trading():
    """
    Run paper trading cycle.
    Generates predictions and manages paper positions.
    """
    logger.info("🤖 Running paper trading cycle...")

    try:
        trader = init_paper_trader()
        if trader:
            trader.run_hourly_cycle()
            logger.info("✅ Paper trading cycle complete")
            return True
        else:
            logger.warning("Paper trader not initialized")
            return False
    except Exception as e:
        logger.error(f"❌ Paper trading cycle failed: {e}", exc_info=True)
        return False


def hourly_job():
    """
    Hourly job - runs every hour.

    Tasks:
    - Fetch new candles
    - Update features (every 6h)
    - Run paper trading (every hour)
    """
    logger.info(f"⏰ Running hourly job at {datetime.utcnow().isoformat()}")

    # 1. Fetch latest candles
    candles_fetched = fetch_candles_hourly()

    # 2. Update features (every 6 hours to reduce computation)
    if datetime.utcnow().hour % 6 == 0:
        update_features()

    # 3. Run paper trading cycle
    if candles_fetched:
        run_paper_trading()

    logger.info("✅ Hourly job completed")


def fetch_macro_events_daily():
    """
    Fetch macro economic events from all sources.
    """
    logger.info("📰 Fetching macro events...")

    try:
        manager = MacroEventManager()
        count = manager.fetch_and_store_events()

        if count > 0:
            logger.info(f"✅ Stored {count} macro events")
        else:
            logger.warning("No new macro events fetched")

        return count

    except Exception as e:
        logger.error(f"❌ Failed to fetch macro events: {e}")
        return 0


def daily_job():
    """
    Daily job - runs once per day at midnight UTC.

    Tasks:
    - Fetch macro events
    - Full feature/label refresh
    - Drift detection (Session 7)
    - Model retraining (if needed) (Session 7)
    - Database maintenance
    """
    logger.info(f"📅 Running daily job at {datetime.utcnow().isoformat()}")

    # Database health check
    db = get_db()
    if db.health_check():
        logger.info("✅ Database health check passed")
    else:
        logger.error("❌ Database health check failed")

    # Fetch macro events
    fetch_macro_events_daily()

    # Full feature/label refresh
    logger.info("Starting daily feature/label refresh")
    update_features()

    # TODO: Implement in Session 7
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

    # Initialize paper trading engine
    logger.info("Initializing paper trading engine...")
    init_paper_trader()

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
