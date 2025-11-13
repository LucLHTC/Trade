"""
Label generation manager.
High-level interface for generating trading labels.
"""

import pandas as pd
from typing import Optional

from src.common.logger import get_logger
from src.common.db import get_db
from src.labeling.targets import LabelGenerator
from src.labeling.regimes import RegimeClassifier

logger = get_logger(__name__)


class LabelManager:
    """Manages the complete label generation pipeline."""

    def __init__(
        self,
        lookahead_periods: int = 3,
        threshold_multiplier: float = 0.7,
        rolling_window: int = 1000,
    ):
        """
        Initialize label manager.

        Args:
            lookahead_periods: Number of periods to look ahead
            threshold_multiplier: Multiplier for threshold calculation
            rolling_window: Rolling window for statistics
        """
        self.label_gen = LabelGenerator(
            lookahead_periods=lookahead_periods,
            threshold_multiplier=threshold_multiplier,
            rolling_window=rolling_window,
        )
        self.regime_classifier = RegimeClassifier()
        self.db = get_db()
        logger.info("Label manager initialized")

    def generate_labels_from_db(
        self,
        symbol: str = "EURUSD",
        regime_aware: bool = True,
        save_to_db: bool = True,
    ) -> pd.DataFrame:
        """
        Generate labels from data in database.

        Args:
            symbol: Trading symbol
            regime_aware: Whether to use regime-aware labeling
            save_to_db: Whether to save results back to database

        Returns:
            DataFrame with labels
        """
        logger.info(f"Generating labels for {symbol}")

        try:
            # Load candle data from database
            query = """
                SELECT timestamp, open, high, low, close, volume, interval
                FROM candles
                WHERE symbol = %s
                ORDER BY timestamp
            """
            result = self.db.execute_query(query, (symbol,))

            if not result:
                logger.error(f"No data found for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(result)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)

            logger.info(f"Loaded {len(df)} candles from database")

            # Classify market regimes if requested
            if regime_aware:
                logger.info("Classifying market regimes...")
                df = self.regime_classifier.classify_regimes(df)

            # Generate labels
            logger.info("Generating labels...")
            df = self.label_gen.generate_labels(df, regime_aware=regime_aware)

            # Save to database if requested
            if save_to_db and "label" in df.columns:
                logger.info("Saving labels to database...")
                rows_updated = self._save_labels_to_db(df, symbol)
                logger.info(f"Updated {rows_updated} rows with labels")

            logger.info(f"✅ Label generation complete for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Label generation failed: {e}", exc_info=True)
            return pd.DataFrame()

    def _save_labels_to_db(self, df: pd.DataFrame, symbol: str) -> int:
        """
        Save generated labels to database.

        Args:
            df: DataFrame with labels
            symbol: Trading symbol

        Returns:
            Number of rows updated
        """
        rows_updated = 0

        # Check if labels column exists in candles table
        # For now, we'll create a separate labels table if needed
        # TODO: Add labels column to candles table or create labels table

        logger.info("Label saving to database not yet implemented - labels exist in memory only")
        return rows_updated

    def generate_and_save(
        self,
        symbol: str = "EURUSD",
        regime_aware: bool = True,
    ) -> bool:
        """
        Convenience method to generate and save labels.

        Args:
            symbol: Trading symbol
            regime_aware: Whether to use regime-aware labeling

        Returns:
            True if successful, False otherwise
        """
        df = self.generate_labels_from_db(symbol, regime_aware, save_to_db=True)
        return not df.empty
