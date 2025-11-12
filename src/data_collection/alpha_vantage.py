"""
Alpha Vantage API client for fetching forex candle data.
Handles API calls with retry logic and stores data in Parquet format.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Optional, Dict, List, Tuple
import pytz

from src.common.config import get_settings
from src.common.logger import get_logger
from src.common.db import get_db

settings = get_settings()
logger = get_logger(__name__)


class AlphaVantageClient:
    """Client for Alpha Vantage API with retry logic and error handling."""

    BASE_URL = "https://www.alphavantage.co/query"
    MAX_RETRIES = 3
    RETRY_DELAY = 10  # seconds

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage client.

        Args:
            api_key: Alpha Vantage API key (defaults to settings)
        """
        self.api_key = api_key or settings.alphavantage_api_key
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")

        self.session = requests.Session()
        logger.info("Alpha Vantage client initialized")

    def _make_request(
        self, params: Dict, retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Make API request with retry logic.

        Args:
            params: Query parameters for API call
            retry_count: Current retry attempt

        Returns:
            JSON response or None if failed
        """
        params["apikey"] = self.api_key

        try:
            response = self.session.get(
                self.BASE_URL, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"API Error: {data['Error Message']}")
                return None

            if "Note" in data:
                # API rate limit reached
                logger.warning(f"API Rate Limit: {data['Note']}")
                if retry_count < self.MAX_RETRIES:
                    logger.info(
                        f"Retrying in {self.RETRY_DELAY} seconds... "
                        f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                    )
                    time.sleep(self.RETRY_DELAY)
                    return self._make_request(params, retry_count + 1)
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if retry_count < self.MAX_RETRIES:
                logger.info(
                    f"Retrying in {self.RETRY_DELAY} seconds... "
                    f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                )
                time.sleep(self.RETRY_DELAY)
                return self._make_request(params, retry_count + 1)
            return None

    def fetch_forex_intraday(
        self,
        from_symbol: str = "EUR",
        to_symbol: str = "USD",
        interval: str = "60min",
        outputsize: str = "full",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch intraday forex data.

        Args:
            from_symbol: Base currency (e.g., EUR)
            to_symbol: Quote currency (e.g., USD)
            interval: Time interval (1min, 5min, 15min, 30min, 60min)
            outputsize: 'compact' (100 points) or 'full' (full history)

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        logger.info(
            f"Fetching {from_symbol}/{to_symbol} {interval} data "
            f"(outputsize={outputsize})"
        )

        params = {
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": interval,
            "outputsize": outputsize,
            "datatype": "json",
        }

        data = self._make_request(params)
        if not data:
            return None

        # Parse time series data
        time_series_key = f"Time Series FX ({interval})"
        if time_series_key not in data:
            logger.error(f"Expected key '{time_series_key}' not found in response")
            return None

        time_series = data[time_series_key]

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df.index.name = "timestamp"

        # Rename columns
        df.columns = [col.split(". ")[1] for col in df.columns]
        df = df.rename(columns={"close": "close", "open": "open", "high": "high", "low": "low"})

        # Convert to numeric
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Add volume (Alpha Vantage doesn't provide forex volume, set to 0)
        df["volume"] = 0

        # Convert to UTC and sort
        df.index = df.index.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
        df = df.sort_index()

        # Add metadata columns
        df["symbol"] = f"{from_symbol}{to_symbol}"
        df["interval"] = interval

        logger.info(f"Fetched {len(df)} candles from {df.index.min()} to {df.index.max()}")

        return df

    def fetch_forex_daily(
        self,
        from_symbol: str = "EUR",
        to_symbol: str = "USD",
        outputsize: str = "full",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch daily forex data.

        Args:
            from_symbol: Base currency
            to_symbol: Quote currency
            outputsize: 'compact' or 'full'

        Returns:
            DataFrame with daily OHLC data
        """
        logger.info(f"Fetching {from_symbol}/{to_symbol} daily data")

        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "outputsize": outputsize,
            "datatype": "json",
        }

        data = self._make_request(params)
        if not data:
            return None

        # Parse time series
        time_series = data.get("Time Series FX (Daily)", {})
        if not time_series:
            logger.error("No daily time series data found")
            return None

        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df.index.name = "timestamp"

        # Rename and convert
        df.columns = [col.split(". ")[1] for col in df.columns]
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["volume"] = 0
        df["symbol"] = f"{from_symbol}{to_symbol}"
        df["interval"] = "1day"

        df.index = df.index.tz_localize("UTC")
        df = df.sort_index()

        logger.info(f"Fetched {len(df)} daily candles")

        return df


class CandleDataManager:
    """Manages candle data storage and retrieval with Parquet format."""

    def __init__(self, base_dir: str = "data/forex"):
        """
        Initialize candle data manager.

        Args:
            base_dir: Base directory for storing Parquet files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db = get_db()
        logger.info(f"Candle data manager initialized with base_dir={base_dir}")

    def save_to_parquet(self, df: pd.DataFrame, symbol: str) -> List[Path]:
        """
        Save candle data to Parquet files organized by year/month.

        Args:
            df: DataFrame with candle data (must have datetime index)
            symbol: Trading symbol (e.g., EURUSD)

        Returns:
            List of file paths where data was saved
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to save")
            return []

        # Group by year and month
        df["year"] = df.index.year
        df["month"] = df.index.month

        saved_files = []

        for (year, month), group in df.groupby(["year", "month"]):
            # Create directory structure: data/forex/YYYY/MM/
            dir_path = self.base_dir / str(year) / f"{month:02d}"
            dir_path.mkdir(parents=True, exist_ok=True)

            # File name: SYMBOL_interval.parquet (e.g., EURUSD_hourly.parquet)
            interval_name = group["interval"].iloc[0].replace("min", "m")
            file_path = dir_path / f"{symbol}_{interval_name}.parquet"

            # Drop temporary columns
            save_df = group.drop(columns=["year", "month"])

            # Check if file exists and merge
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                # Combine and remove duplicates
                combined_df = pd.concat([existing_df, save_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
                combined_df = combined_df.sort_index()
                save_df = combined_df

            # Save to Parquet
            save_df.to_parquet(file_path, index=True, compression="snappy")
            logger.info(
                f"Saved {len(save_df)} candles to {file_path} "
                f"({save_df.index.min()} to {save_df.index.max()})"
            )
            saved_files.append(file_path)

        return saved_files

    def load_from_parquet(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load candle data from Parquet files.

        Args:
            symbol: Trading symbol
            start_date: Start date filter (inclusive)
            end_date: End date filter (inclusive)

        Returns:
            DataFrame with candle data
        """
        all_files = list(self.base_dir.rglob(f"{symbol}_*.parquet"))

        if not all_files:
            logger.warning(f"No Parquet files found for {symbol}")
            return pd.DataFrame()

        # Load all files
        dfs = []
        for file_path in all_files:
            df = pd.read_parquet(file_path)
            dfs.append(df)

        # Combine
        combined_df = pd.concat(dfs)
        combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
        combined_df = combined_df.sort_index()

        # Apply date filters
        if start_date:
            combined_df = combined_df[combined_df.index >= start_date]
        if end_date:
            combined_df = combined_df[combined_df.index <= end_date]

        logger.info(f"Loaded {len(combined_df)} candles for {symbol}")

        return combined_df

    def save_to_database(self, df: pd.DataFrame) -> int:
        """
        Save candle data to PostgreSQL database.

        Args:
            df: DataFrame with candle data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0

        records = []
        for timestamp, row in df.iterrows():
            records.append({
                "symbol": row["symbol"],
                "interval": row["interval"],
                "timestamp": timestamp,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })

        rows_inserted = self.db.insert_many("raw_candles", records)
        logger.info(f"Inserted {rows_inserted} candles into database")

        return rows_inserted

    def detect_gaps(self, df: pd.DataFrame, interval_minutes: int = 60) -> List[Tuple[datetime, datetime]]:
        """
        Detect gaps in candle data.

        Args:
            df: DataFrame with candle data (sorted by timestamp)
            interval_minutes: Expected interval between candles in minutes

        Returns:
            List of (gap_start, gap_end) tuples
        """
        if len(df) < 2:
            return []

        expected_delta = timedelta(minutes=interval_minutes)
        gaps = []

        for i in range(1, len(df)):
            prev_time = df.index[i - 1]
            curr_time = df.index[i]
            actual_delta = curr_time - prev_time

            # Allow some tolerance (e.g., weekends for forex)
            if actual_delta > expected_delta * 1.5:
                gaps.append((prev_time, curr_time))

        if gaps:
            logger.warning(f"Detected {len(gaps)} gaps in data")
            for gap_start, gap_end in gaps[:5]:  # Log first 5
                logger.warning(f"  Gap: {gap_start} to {gap_end} ({gap_end - gap_start})")

        return gaps


def bootstrap_historical_data(months: int = 3) -> bool:
    """
    Bootstrap historical data for EUR/USD.

    Args:
        months: Number of months to fetch

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Bootstrapping {months} months of EUR/USD data")

    try:
        client = AlphaVantageClient()
        manager = CandleDataManager()

        # Fetch full intraday data (Alpha Vantage provides last ~30 days for 60min)
        df = client.fetch_forex_intraday(
            from_symbol="EUR",
            to_symbol="USD",
            interval="60min",
            outputsize="full",
        )

        if df is None or df.empty:
            logger.error("Failed to fetch historical data")
            return False

        # Save to Parquet
        saved_files = manager.save_to_parquet(df, "EURUSD")
        logger.info(f"Saved data to {len(saved_files)} Parquet files")

        # Save to database
        rows = manager.save_to_database(df)
        logger.info(f"Saved {rows} rows to database")

        # Detect gaps
        gaps = manager.detect_gaps(df, interval_minutes=60)
        logger.info(f"Detected {len(gaps)} gaps in data")

        logger.info("✅ Historical data bootstrap complete")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to bootstrap historical data: {e}")
        return False
