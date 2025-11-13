"""
Forex data collection coordinator.
Combines Alpha Vantage client with data management for easy data collection.
"""

from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from src.common.logger import get_logger
from src.data_collection.alpha_vantage import AlphaVantageClient, CandleDataManager

logger = get_logger(__name__)


class ForexCollector:
    """
    High-level coordinator for forex data collection.
    Combines fetching and storage in a single interface.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize forex collector.

        Args:
            api_key: Alpha Vantage API key (defaults to settings)
        """
        self.client = AlphaVantageClient(api_key=api_key)
        self.manager = CandleDataManager()
        logger.info("Forex collector initialized")

    def fetch_and_store(
        self,
        symbol: str = "EURUSD",
        days: int = 90,
        interval: str = "60min",
    ) -> bool:
        """
        Fetch forex data and store in both Parquet and database.

        Args:
            symbol: Trading pair symbol (e.g., EURUSD)
            days: Number of days of historical data to fetch
            interval: Time interval (1min, 5min, 15min, 30min, 60min)

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Starting data collection for {symbol}: {days} days at {interval} interval"
        )

        try:
            # Parse symbol (e.g., EURUSD -> EUR/USD)
            if len(symbol) == 6:
                from_symbol = symbol[:3]
                to_symbol = symbol[3:]
            else:
                logger.error(f"Invalid symbol format: {symbol}")
                return False

            # Determine if we need intraday or daily data
            if interval in ["1min", "5min", "15min", "30min", "60min"]:
                # Fetch intraday data
                logger.info(f"Fetching intraday {from_symbol}/{to_symbol} data...")
                df = self.client.fetch_forex_intraday(
                    from_symbol=from_symbol,
                    to_symbol=to_symbol,
                    interval=interval,
                    outputsize="full",
                )
            else:
                # Fetch daily data
                logger.info(f"Fetching daily {from_symbol}/{to_symbol} data...")
                df = self.client.fetch_forex_daily(
                    from_symbol=from_symbol,
                    to_symbol=to_symbol,
                    outputsize="full",
                )

            if df is None or df.empty:
                logger.error("No data received from API")
                return False

            # Filter to requested number of days
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff_date]

            logger.info(f"Received {len(df)} candles from {df.index.min()} to {df.index.max()}")

            # Save to Parquet files
            logger.info("Saving to Parquet files...")
            parquet_files = self.manager.save_to_parquet(df, symbol)
            logger.info(f"Saved to {len(parquet_files)} Parquet files")

            # Save to database
            logger.info("Saving to database...")
            rows_saved = self.manager.save_to_database(df)
            logger.info(f"Saved {rows_saved} rows to database")

            logger.info(f"✅ Data collection complete for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Data collection failed: {e}", exc_info=True)
            return False

    def fetch_multiple(
        self,
        symbols: list[str],
        days: int = 90,
        interval: str = "60min",
    ) -> dict[str, bool]:
        """
        Fetch data for multiple symbols.

        Args:
            symbols: List of trading pair symbols
            days: Number of days of historical data
            interval: Time interval

        Returns:
            Dictionary mapping symbols to success status
        """
        results = {}
        for symbol in symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {symbol}")
            logger.info(f"{'='*60}")
            results[symbol] = self.fetch_and_store(symbol, days, interval)

        return results
