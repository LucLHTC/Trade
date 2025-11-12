"""
Target generation for supervised learning.
Creates trading labels based on forward returns with dynamic thresholds.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple

from src.common.config import get_settings
from src.common.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class LabelGenerator:
    """Generate trading labels from price data."""

    def __init__(
        self,
        lookahead_periods: int = 3,
        threshold_multiplier: float = 0.7,
        rolling_window: int = 1000,
    ):
        """
        Initialize label generator.

        Args:
            lookahead_periods: Number of periods to look ahead for returns
            threshold_multiplier: Multiplier for dynamic threshold (× rolling STD)
            rolling_window: Window for calculating rolling statistics
        """
        self.lookahead_periods = lookahead_periods
        self.threshold_multiplier = threshold_multiplier
        self.rolling_window = rolling_window

        logger.info(
            f"LabelGenerator initialized: lookahead={lookahead_periods}, "
            f"threshold_mult={threshold_multiplier}, window={rolling_window}"
        )

    def generate_labels(
        self,
        df: pd.DataFrame,
        regime_aware: bool = True,
    ) -> pd.DataFrame:
        """
        Generate trading labels based on forward returns.

        Labels:
        - 1: Long signal (bullish)
        - 0: Neutral (no trade)
        - -1: Short signal (bearish)

        Args:
            df: DataFrame with price data (must have 'close' column)
            regime_aware: Whether to only label in directional regimes

        Returns:
            DataFrame with label columns added
        """
        if df.empty:
            logger.warning("Empty dataframe provided to generate_labels")
            return df

        logger.info(f"Generating labels for {len(df)} candles")

        result = df.copy()

        # Calculate forward returns
        result["forward_return"] = (
            result["close"].pct_change(periods=self.lookahead_periods).shift(-self.lookahead_periods)
        )

        # Calculate dynamic threshold based on rolling volatility
        result["threshold"] = (
            result["forward_return"]
            .rolling(self.rolling_window, min_periods=50)
            .std()
            * self.threshold_multiplier
        )

        # Initialize label column
        result["label"] = 0

        # Apply thresholds to generate labels
        result.loc[result["forward_return"] > result["threshold"], "label"] = 1
        result.loc[result["forward_return"] < -result["threshold"], "label"] = -1

        # Regime-aware labeling (only label in directional regimes)
        if regime_aware and "regime" in result.columns:
            logger.info("Applying regime-aware labeling")

            # Only allow labels in directional regimes (bullish, bearish, volatile)
            # Set to neutral in sideways markets
            sideways_mask = result["regime"] == "sideways"
            result.loc[sideways_mask, "label"] = 0

            logger.info(
                f"Neutralized {sideways_mask.sum()} labels in sideways regime"
            )

        # Calculate label statistics
        label_counts = result["label"].value_counts().sort_index()
        total_labeled = len(result[result["label"] != 0])

        logger.info(f"Label distribution: {label_counts.to_dict()}")
        logger.info(
            f"Labeled periods: {total_labeled} ({total_labeled/len(result)*100:.1f}%)"
        )

        return result

    def generate_labels_with_metadata(
        self,
        df: pd.DataFrame,
        regime_aware: bool = True,
    ) -> pd.DataFrame:
        """
        Generate labels with additional metadata for analysis.

        Adds metadata columns:
        - label: Trading signal (-1, 0, 1)
        - forward_return: Actual forward return
        - threshold: Dynamic threshold used
        - regime: Market regime (if available)
        - macro_event_window: Whether event overlaps (if available)

        Args:
            df: DataFrame with all features
            regime_aware: Whether to use regime-aware labeling

        Returns:
            DataFrame with labels and metadata
        """
        result = self.generate_labels(df, regime_aware=regime_aware)

        # Add macro event window if event features exist
        if "has_event_next_3h" in result.columns:
            result["macro_event_window"] = (
                (result["has_event_last_3h"] == 1) |
                (result["has_event_next_3h"] == 1)
            ).astype(int)
        else:
            result["macro_event_window"] = 0

        # Add spread placeholder (will be filled later with actual spread data)
        if "spread" not in result.columns:
            result["spread"] = np.nan

        # Add Sharpe ratio of last week (if possible)
        if "returns" in result.columns:
            result["sharpe_last_week"] = (
                result["returns"]
                .rolling(168)  # 7 days * 24 hours
                .apply(
                    lambda x: (
                        x.mean() / x.std() * np.sqrt(252)
                        if len(x) > 0 and x.std() > 0
                        else 0
                    )
                )
            )
        else:
            result["sharpe_last_week"] = np.nan

        logger.info("✅ Generated labels with metadata")

        return result

    @staticmethod
    def validate_labels(df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate that labels are correctly generated.

        Args:
            df: DataFrame with labels

        Returns:
            Tuple of (is_valid, message)
        """
        if "label" not in df.columns:
            return False, "Missing 'label' column"

        if "forward_return" not in df.columns:
            return False, "Missing 'forward_return' column"

        if "threshold" not in df.columns:
            return False, "Missing 'threshold' column"

        # Check label values
        valid_labels = {-1, 0, 1}
        unique_labels = set(df["label"].dropna().unique())
        if not unique_labels.issubset(valid_labels):
            return False, f"Invalid label values: {unique_labels - valid_labels}"

        # Check for sufficient labeled examples
        label_counts = df["label"].value_counts()
        min_examples = 10

        for label_val in [-1, 1]:
            if label_val not in label_counts or label_counts[label_val] < min_examples:
                return (
                    False,
                    f"Insufficient examples for label {label_val}: "
                    f"{label_counts.get(label_val, 0)} < {min_examples}",
                )

        # Check for data leakage (forward_return should not be NaN for labeled periods)
        labeled_mask = df["label"] != 0
        forward_return_na = df.loc[labeled_mask, "forward_return"].isna().sum()

        if forward_return_na > 0:
            return (
                False,
                f"Found {forward_return_na} labeled periods with NaN forward_return",
            )

        return True, "Labels validated successfully"

    @staticmethod
    def get_label_statistics(df: pd.DataFrame) -> dict:
        """
        Get detailed statistics about generated labels.

        Args:
            df: DataFrame with labels

        Returns:
            Dictionary with label statistics
        """
        if "label" not in df.columns:
            return {}

        total = len(df)
        label_counts = df["label"].value_counts()

        stats = {
            "total_periods": total,
            "long_signals": label_counts.get(1, 0),
            "short_signals": label_counts.get(-1, 0),
            "neutral_periods": label_counts.get(0, 0),
            "long_pct": label_counts.get(1, 0) / total * 100 if total > 0 else 0,
            "short_pct": label_counts.get(-1, 0) / total * 100 if total > 0 else 0,
            "neutral_pct": label_counts.get(0, 0) / total * 100 if total > 0 else 0,
            "labeled_pct": (
                (label_counts.get(1, 0) + label_counts.get(-1, 0)) / total * 100
                if total > 0
                else 0
            ),
        }

        # Average forward returns by label
        if "forward_return" in df.columns:
            for label_val in [-1, 0, 1]:
                label_mask = df["label"] == label_val
                if label_mask.sum() > 0:
                    avg_return = df.loc[label_mask, "forward_return"].mean()
                    stats[f"avg_return_label_{label_val}"] = avg_return

        # Regime breakdown if available
        if "regime" in df.columns:
            for regime in ["bullish", "bearish", "sideways", "volatile"]:
                regime_mask = df["regime"] == regime
                if regime_mask.sum() > 0:
                    regime_labels = df.loc[regime_mask, "label"].value_counts()
                    stats[f"labels_in_{regime}"] = regime_labels.to_dict()

        return stats


def generate_all_labels(
    df: pd.DataFrame,
    lookahead_periods: Optional[int] = None,
    threshold_multiplier: Optional[float] = None,
    regime_aware: bool = True,
) -> pd.DataFrame:
    """
    Main entry point for label generation.

    Args:
        df: DataFrame with features and regime
        lookahead_periods: Lookahead for forward returns (default from config)
        threshold_multiplier: Threshold multiplier (default from config)
        regime_aware: Whether to use regime-aware labeling

    Returns:
        DataFrame with labels and metadata
    """
    logger.info("Starting label generation pipeline")

    # Use config defaults if not provided
    if lookahead_periods is None:
        lookahead_periods = settings.lookahead_periods

    if threshold_multiplier is None:
        threshold_multiplier = settings.label_threshold_multiplier

    # Create label generator
    generator = LabelGenerator(
        lookahead_periods=lookahead_periods,
        threshold_multiplier=threshold_multiplier,
        rolling_window=1000,
    )

    # Generate labels with metadata
    df_with_labels = generator.generate_labels_with_metadata(
        df, regime_aware=regime_aware
    )

    # Validate labels
    is_valid, message = generator.validate_labels(df_with_labels)

    if is_valid:
        logger.info(f"✅ Label validation: {message}")
    else:
        logger.warning(f"⚠️  Label validation: {message}")

    # Get statistics
    stats = generator.get_label_statistics(df_with_labels)
    logger.info(f"Label statistics: {stats}")

    return df_with_labels
