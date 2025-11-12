#!/usr/bin/env python3
"""
Feature generation script to create features and labels from candle data.

This script should be run after bootstrap_data.py to generate the initial
feature set for model training.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import get_logger
from src.features.manager import FeatureManager
from src.labeling.regimes import RegimeClassifier
from src.labeling.targets import LabelGenerator

logger = get_logger(__name__)


def main():
    """
    Main feature generation process.
    """
    logger.info("🚀 Starting feature generation process...")
    logger.info("=" * 60)

    try:
        # Initialize feature manager
        feature_manager = FeatureManager()

        # Generate features from all available candle data
        logger.info("Step 1: Generating features from candle data")
        logger.info("-" * 60)

        features_path, labels_path = feature_manager.generate_and_save_all(
            symbol="EURUSD"
        )

        if not features_path or not labels_path:
            logger.error("❌ Feature generation failed")
            return False

        logger.info(f"✅ Features saved to: {features_path}")
        logger.info(f"✅ Labels saved to: {labels_path}")

        logger.info("")

        # Load and validate generated features
        logger.info("Step 2: Validating generated features")
        logger.info("-" * 60)

        features_df = feature_manager.load_features(symbol="EURUSD")
        labels_df = feature_manager.load_labels(symbol="EURUSD")

        if features_df.empty or labels_df.empty:
            logger.error("❌ Failed to load generated features/labels")
            return False

        logger.info(f"Features: {len(features_df)} samples × {len(features_df.columns)} columns")
        logger.info(f"Labels: {len(labels_df)} samples × {len(labels_df.columns)} columns")

        # Show feature statistics
        logger.info("")
        logger.info("Step 3: Feature statistics")
        logger.info("-" * 60)

        # Regime distribution
        if "regime" in labels_df.columns:
            regime_counts = labels_df["regime"].value_counts()
            logger.info("Regime distribution:")
            for regime, count in regime_counts.items():
                pct = count / len(labels_df) * 100
                logger.info(f"  {regime}: {count} ({pct:.1f}%)")

        # Label distribution
        if "label" in labels_df.columns:
            logger.info("")
            label_counts = labels_df["label"].value_counts().sort_index()
            logger.info("Label distribution:")
            for label, count in label_counts.items():
                pct = count / len(labels_df) * 100
                label_name = {-1: "Short", 0: "Neutral", 1: "Long"}.get(label, "Unknown")
                logger.info(f"  {label_name} ({label}): {count} ({pct:.1f}%)")

        # Feature completeness
        logger.info("")
        logger.info("Feature completeness:")
        missing_features = features_df.isnull().sum()
        high_missing = missing_features[missing_features > len(features_df) * 0.1]

        if len(high_missing) > 0:
            logger.warning(f"Features with >10% missing values: {len(high_missing)}")
            for feat, missing in high_missing.head(5).items():
                pct = missing / len(features_df) * 100
                logger.warning(f"  {feat}: {missing} ({pct:.1f}%)")
        else:
            logger.info("  All features have <10% missing values ✓")

        logger.info("")
        logger.info("=" * 60)
        logger.info("🎉 Feature generation complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review feature statistics above")
        logger.info("2. Proceed to Session 4 (Model Training)")
        logger.info("3. Use these features to train ensemble models")

        return True

    except KeyboardInterrupt:
        logger.info("🛑 Feature generation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Feature generation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
