#!/usr/bin/env python3
"""
Bootstrap script to initialize historical data for the trading system.

This script:
1. Fetches historical EUR/USD candle data from Alpha Vantage
2. Creates sample macro events for testing
3. Validates data quality and reports statistics

Run this script after initial system setup to populate the database.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import get_logger
from src.common.db import get_db
from src.data_collection.alpha_vantage import bootstrap_historical_data
from src.data_collection.macro_feeds import create_sample_events, MacroEventManager

logger = get_logger(__name__)


def validate_data():
    """
    Validate bootstrapped data and report statistics.
    """
    logger.info("🔍 Validating bootstrapped data...")

    db = get_db()

    # Check candles
    candle_query = """
        SELECT
            COUNT(*) as total_candles,
            MIN(timestamp) as earliest_candle,
            MAX(timestamp) as latest_candle,
            symbol,
            interval
        FROM raw_candles
        GROUP BY symbol, interval
    """

    candles_stats = db.execute_query(candle_query, fetch=True)

    if candles_stats:
        logger.info("📊 Candle Data Statistics:")
        for stat in candles_stats:
            logger.info(
                f"  {stat['symbol']} ({stat['interval']}): "
                f"{stat['total_candles']} candles from "
                f"{stat['earliest_candle']} to {stat['latest_candle']}"
            )
    else:
        logger.warning("⚠️  No candle data found in database")

    # Check macro events
    events_query = """
        SELECT
            COUNT(*) as total_events,
            COUNT(CASE WHEN impact = 'high' THEN 1 END) as high_impact,
            COUNT(CASE WHEN impact = 'medium' THEN 1 END) as medium_impact,
            COUNT(CASE WHEN impact = 'low' THEN 1 END) as low_impact,
            MIN(timestamp) as earliest_event,
            MAX(timestamp) as latest_event
        FROM macro_events
    """

    events_stats = db.execute_query(events_query, fetch=True)

    if events_stats and events_stats[0]['total_events'] > 0:
        stat = events_stats[0]
        logger.info("📰 Macro Events Statistics:")
        logger.info(f"  Total events: {stat['total_events']}")
        logger.info(f"  High impact: {stat['high_impact']}")
        logger.info(f"  Medium impact: {stat['medium_impact']}")
        logger.info(f"  Low impact: {stat['low_impact']}")
        logger.info(f"  Date range: {stat['earliest_event']} to {stat['latest_event']}")
    else:
        logger.warning("⚠️  No macro events found in database")

    # Currency breakdown
    currency_query = """
        SELECT currency, COUNT(*) as count
        FROM macro_events
        GROUP BY currency
        ORDER BY count DESC
    """

    currency_stats = db.execute_query(currency_query, fetch=True)

    if currency_stats:
        logger.info("💱 Events by Currency:")
        for stat in currency_stats:
            logger.info(f"  {stat['currency']}: {stat['count']} events")

    # Classification breakdown
    classification_query = """
        SELECT
            COUNT(CASE WHEN bullish THEN 1 END) as bullish_count,
            COUNT(CASE WHEN bearish THEN 1 END) as bearish_count,
            COUNT(CASE WHEN neutral THEN 1 END) as neutral_count
        FROM macro_events
    """

    class_stats = db.execute_query(classification_query, fetch=True)

    if class_stats:
        stat = class_stats[0]
        logger.info("📈 Event Classification:")
        logger.info(f"  Bullish (EUR/USD): {stat['bullish_count']}")
        logger.info(f"  Bearish (EUR/USD): {stat['bearish_count']}")
        logger.info(f"  Neutral: {stat['neutral_count']}")


def main():
    """
    Main bootstrap process.
    """
    logger.info("🚀 Starting data bootstrap process...")
    logger.info("=" * 60)

    # Step 1: Bootstrap historical candle data
    logger.info("Step 1: Fetching historical EUR/USD candle data")
    logger.info("-" * 60)

    candle_success = bootstrap_historical_data(months=3)

    if candle_success:
        logger.info("✅ Historical candle data bootstrapped successfully")
    else:
        logger.error("❌ Failed to bootstrap historical candle data")
        logger.warning("This may be due to Alpha Vantage API limits or network issues")

    logger.info("")

    # Step 2: Create sample macro events
    logger.info("Step 2: Creating sample macro events")
    logger.info("-" * 60)

    sample_count = create_sample_events()

    if sample_count > 0:
        logger.info(f"✅ Created {sample_count} sample macro events")
    else:
        logger.warning("⚠️  No sample events created (may already exist)")

    logger.info("")

    # Step 3: Try to fetch real macro events
    logger.info("Step 3: Fetching real macro events from sources")
    logger.info("-" * 60)

    try:
        manager = MacroEventManager()
        real_events = manager.fetch_and_store_events()

        if real_events > 0:
            logger.info(f"✅ Fetched {real_events} real macro events")
        else:
            logger.warning("⚠️  No real events fetched (using sample events only)")
    except Exception as e:
        logger.error(f"❌ Failed to fetch real macro events: {e}")
        logger.info("Using sample events only")

    logger.info("")

    # Step 4: Validate data
    logger.info("Step 4: Validating bootstrapped data")
    logger.info("-" * 60)

    validate_data()

    logger.info("")
    logger.info("=" * 60)
    logger.info("🎉 Bootstrap process complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Check the Streamlit UI (http://localhost:8501)")
    logger.info("2. Verify candle data in data/forex/ directory")
    logger.info("3. Review macro events in the database")
    logger.info("4. Proceed to Session 3 (Feature Engineering)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bootstrap interrupted by user")
    except Exception as e:
        logger.error(f"❌ Bootstrap failed: {e}", exc_info=True)
        sys.exit(1)
