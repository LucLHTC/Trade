"""
Feature and label management for storage and retrieval.
Handles Parquet storage, database operations, and end-to-end pipeline.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import numpy as np

from src.common.logger import get_logger
from src.common.db import get_db
from src.data_collection.alpha_vantage import CandleDataManager
from src.features.technical import calculate_all_features
from src.features.events import EventFeatures
from src.labeling.regimes import RegimeClassifier
from src.labeling.targets import generate_all_labels
from src.features.pipeline import FeaturePreprocessor

logger = get_logger(__name__)


class FeatureManager:
    """Manages feature generation, storage, and retrieval."""

    def __init__(
        self,
        features_dir: str = "data/features",
        labels_dir: str = "data/labels",
    ):
        """
        Initialize feature manager.

        Args:
            features_dir: Directory for storing feature Parquet files
            labels_dir: Directory for storing label Parquet files
        """
        self.features_dir = Path(features_dir)
        self.labels_dir = Path(labels_dir)

        self.features_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        self.db = get_db()
        self.candle_manager = CandleDataManager()
        self.event_features = EventFeatures()

        logger.info(
            f"FeatureManager initialized: features_dir={features_dir}, "
            f"labels_dir={labels_dir}"
        )

    def generate_features_from_candles(
        self,
        symbol: str = "EURUSD",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Generate complete feature set from raw candle data.

        This is the main pipeline:
        1. Load candles
        2. Calculate technical indicators
        3. Add event-based features
        4. Classify regimes
        5. Generate labels

        Args:
            symbol: Trading symbol
            start_date: Start date filter
            end_date: End date filter

        Returns:
            DataFrame with all features and labels
        """
        logger.info(
            f"Generating features for {symbol} "
            f"({start_date or 'earliest'} to {end_date or 'latest'})"
        )

        # Step 1: Load candles
        candles_df = self.candle_manager.load_from_parquet(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if candles_df.empty:
            logger.error(f"No candle data found for {symbol}")
            return pd.DataFrame()

        logger.info(f"Loaded {len(candles_df)} candles")

        # Step 2: Calculate technical features
        df = calculate_all_features(candles_df)

        # Step 3: Add event-based features
        df = self.event_features.calculate_event_features(df)

        # Step 4: Classify regimes
        df = RegimeClassifier.classify_regime(df)

        # Step 5: Generate labels
        df = generate_all_labels(df, regime_aware=True)

        # Clean NaN values from early periods (insufficient data for indicators)
        original_len = len(df)
        df = df.dropna(subset=["label", "forward_return"])
        dropped = original_len - len(df)

        if dropped > 0:
            logger.info(f"Dropped {dropped} rows with NaN labels/returns")

        logger.info(f"✅ Feature generation complete: {len(df)} samples, {len(df.columns)} total columns")

        return df

    def save_features(
        self,
        df: pd.DataFrame,
        symbol: str = "EURUSD",
        suffix: Optional[str] = None,
    ) -> Path:
        """
        Save features to Parquet file.

        Args:
            df: DataFrame with features
            symbol: Trading symbol
            suffix: Optional suffix for filename (e.g., 'train', 'test')

        Returns:
            Path to saved file
        """
        if df.empty:
            logger.warning("Empty dataframe, nothing to save")
            return None

        # Filename: SYMBOL_features_YYYYMMDD[_suffix].parquet
        date_str = df.index.min().strftime("%Y%m%d")
        filename = f"{symbol}_features_{date_str}"

        if suffix:
            filename += f"_{suffix}"

        filename += ".parquet"

        file_path = self.features_dir / filename

        # Select only feature columns (exclude labels and metadata)
        exclude_cols = {
            "label", "forward_return", "threshold",
            "macro_event_window", "spread", "sharpe_last_week",
        }

        feature_cols = [col for col in df.columns if col not in exclude_cols]
        features_df = df[feature_cols]

        features_df.to_parquet(file_path, compression="snappy")

        logger.info(
            f"Saved {len(features_df)} samples × {len(feature_cols)} features to {file_path}"
        )

        return file_path

    def save_labels(
        self,
        df: pd.DataFrame,
        symbol: str = "EURUSD",
        suffix: Optional[str] = None,
    ) -> Path:
        """
        Save labels to Parquet file.

        Args:
            df: DataFrame with labels
            symbol: Trading symbol
            suffix: Optional suffix for filename

        Returns:
            Path to saved file
        """
        if df.empty:
            logger.warning("Empty dataframe, nothing to save")
            return None

        # Filename: SYMBOL_labels_YYYYMMDD[_suffix].parquet
        date_str = df.index.min().strftime("%Y%m%d")
        filename = f"{symbol}_labels_{date_str}"

        if suffix:
            filename += f"_{suffix}"

        filename += ".parquet"

        file_path = self.labels_dir / filename

        # Select label and metadata columns
        label_cols = [
            "label", "forward_return", "threshold", "regime",
            "macro_event_window", "spread", "sharpe_last_week",
        ]

        # Only include columns that exist
        available_label_cols = [col for col in label_cols if col in df.columns]
        labels_df = df[available_label_cols]

        labels_df.to_parquet(file_path, compression="snappy")

        logger.info(
            f"Saved {len(labels_df)} labels with {len(available_label_cols)} columns to {file_path}"
        )

        return file_path

    def load_features(
        self,
        symbol: str = "EURUSD",
        date: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load features from Parquet file.

        Args:
            symbol: Trading symbol
            date: Date string (YYYYMMDD) - if None, loads latest
            suffix: Optional suffix

        Returns:
            DataFrame with features
        """
        # Find matching files
        pattern = f"{symbol}_features_"

        if date:
            pattern += f"{date}"

        if suffix:
            pattern += f"_{suffix}"

        pattern += ".parquet"

        matching_files = list(self.features_dir.glob(pattern))

        if not matching_files:
            logger.warning(f"No feature files found matching: {pattern}")
            return pd.DataFrame()

        # Load latest file
        latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
        df = pd.read_parquet(latest_file)

        logger.info(f"Loaded {len(df)} samples from {latest_file}")

        return df

    def load_labels(
        self,
        symbol: str = "EURUSD",
        date: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load labels from Parquet file.

        Args:
            symbol: Trading symbol
            date: Date string (YYYYMMDD)
            suffix: Optional suffix

        Returns:
            DataFrame with labels
        """
        # Find matching files
        pattern = f"{symbol}_labels_"

        if date:
            pattern += f"{date}"

        if suffix:
            pattern += f"_{suffix}"

        pattern += ".parquet"

        matching_files = list(self.labels_dir.glob(pattern))

        if not matching_files:
            logger.warning(f"No label files found matching: {pattern}")
            return pd.DataFrame()

        # Load latest file
        latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
        df = pd.read_parquet(latest_file)

        logger.info(f"Loaded {len(df)} labels from {latest_file}")

        return df

    def save_to_database(self, df: pd.DataFrame) -> int:
        """
        Save feature metadata to database.

        Args:
            df: DataFrame with features and regime

        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0

        if "regime" not in df.columns:
            logger.warning("Missing 'regime' column, skipping database save")
            return 0

        # Prepare records for database
        records = []

        for timestamp, row in df.iterrows():
            # Extract feature data (excluding OHLCV and label columns)
            exclude_cols = {
                "open", "high", "low", "close", "volume",
                "symbol", "interval", "label", "forward_return",
                "threshold", "macro_event_window", "spread", "sharpe_last_week",
            }

            feature_data = {
                col: float(row[col]) if pd.notna(row[col]) else None
                for col in row.index
                if col not in exclude_cols and pd.api.types.is_numeric_dtype(type(row[col]))
            }

            records.append({
                "timestamp": timestamp,
                "feature_data": feature_data,
                "regime": row.get("regime"),
            })

        # Insert into database (in batches to avoid memory issues)
        batch_size = 1000
        total_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            inserted = self.db.insert_many("features", batch)
            total_inserted += inserted

        logger.info(f"Inserted {total_inserted} feature records into database")

        return total_inserted

    def generate_and_save_all(
        self,
        symbol: str = "EURUSD",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[Path, Path]:
        """
        Complete pipeline: generate, save features and labels.

        Args:
            symbol: Trading symbol
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Tuple of (features_path, labels_path)
        """
        logger.info("Starting complete feature generation and storage pipeline")

        # Generate features
        df = self.generate_features_from_candles(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            logger.error("Feature generation failed, no data to save")
            return None, None

        # Save features
        features_path = self.save_features(df, symbol=symbol)

        # Save labels
        labels_path = self.save_labels(df, symbol=symbol)

        # Save to database (optional, for quick queries)
        try:
            self.save_to_database(df)
        except Exception as e:
            logger.warning(f"Failed to save to database: {e}")

        logger.info("✅ Feature generation and storage pipeline complete")

        return features_path, labels_path
