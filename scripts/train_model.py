#!/usr/bin/env python3
"""
Model training script for ensemble ML models.
Trains XGBoost, LightGBM, and RandomForest on features.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import get_logger
from src.features.manager import FeatureManager
from src.features.pipeline import FeaturePreprocessor
from src.training.ensemble import EnsembleTrainer

logger = get_logger(__name__)


def main():
    """Train ensemble models."""
    logger.info("🚀 Starting model training...")
    logger.info("=" * 60)

    try:
        # Load features and labels
        logger.info("Step 1: Loading features and labels")
        logger.info("-" * 60)

        feature_manager = FeatureManager()
        features_df = feature_manager.load_features(symbol="EURUSD")
        labels_df = feature_manager.load_labels(symbol="EURUSD")

        if features_df.empty or labels_df.empty:
            logger.error("No features/labels found. Run generate_features.py first.")
            return False

        logger.info(f"Loaded {len(features_df)} feature samples")
        logger.info(f"Loaded {len(labels_df)} label samples")

        # Split train/val (time-based)
        logger.info("")
        logger.info("Step 2: Splitting train/validation sets")
        logger.info("-" * 60)

        cutoff_date = features_df.index.max() - timedelta(days=10)
        train_features = features_df[features_df.index < cutoff_date]
        val_features = features_df[features_df.index >= cutoff_date]

        train_labels = labels_df[labels_df.index < cutoff_date]
        val_labels = labels_df[labels_df.index >= cutoff_date]

        logger.info(f"Train: {len(train_features)} samples")
        logger.info(f"Val: {len(val_features)} samples")

        # Prepare data
        logger.info("")
        logger.info("Step 3: Preparing data for training")
        logger.info("-" * 60)

        ensemble = EnsembleTrainer()
        X_train, y_train, feature_cols = ensemble.models["xgboost"].prepare_data(
            train_features, train_labels, exclude_neutral=True
        )
        X_val, y_val, _ = ensemble.models["xgboost"].prepare_data(
            val_features, val_labels, exclude_neutral=True
        )

        logger.info(f"Train: X={X_train.shape}, y={y_train.shape}")
        logger.info(f"Val: X={X_val.shape}, y={y_val.shape}")

        # Train ensemble
        logger.info("")
        logger.info("Step 4: Training ensemble models")
        logger.info("-" * 60)

        histories = ensemble.train_all(X_train, y_train, X_val, y_val)

        # Evaluate
        logger.info("")
        logger.info("Step 5: Evaluating ensemble")
        logger.info("-" * 60)

        metrics = ensemble.evaluate_ensemble(X_val, y_val, threshold=0.55)

        logger.info("Ensemble metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")

        # Save models
        logger.info("")
        logger.info("Step 6: Saving models")
        logger.info("-" * 60)

        ensemble.save("models/current")
        logger.info("✅ Models saved to models/current/")

        logger.info("")
        logger.info("=" * 60)
        logger.info("🎉 Training complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review metrics above")
        logger.info("2. Proceed to Session 5 (Inference & Risk Management)")

        return True

    except KeyboardInterrupt:
        logger.info("🛑 Training interrupted")
        return False
    except Exception as e:
        logger.error(f"❌ Training failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
