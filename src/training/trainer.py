"""
Model training manager.
High-level interface for training ensemble models.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path
from sklearn.model_selection import train_test_split

from src.common.logger import get_logger
from src.common.db import get_db
from src.common.config import get_settings
from src.training.ensemble import EnsembleTrainer
from src.features.manager import FeatureManager

settings = get_settings()
logger = get_logger(__name__)


class ModelTrainer:
    """Manages the complete model training pipeline."""

    def __init__(
        self,
        test_size: float = 0.2,
        val_size: float = 0.1,
        random_state: int = 42,
    ):
        """
        Initialize model trainer.

        Args:
            test_size: Proportion of data for test set
            val_size: Proportion of training data for validation
            random_state: Random seed for reproducibility
        """
        self.test_size = test_size
        self.val_size = val_size
        self.random_state = random_state
        self.db = get_db()
        self.feature_manager = FeatureManager()
        logger.info("Model trainer initialized")

    def train_from_db(
        self,
        symbol: str = "EURUSD",
        min_samples: int = 1000,
        save_model: bool = True,
    ) -> Dict[str, Any]:
        """
        Train ensemble model from data in database.

        Args:
            symbol: Trading symbol
            min_samples: Minimum number of samples required
            save_model: Whether to save trained models

        Returns:
            Dictionary with training results
        """
        logger.info(f"Starting model training for {symbol}")

        try:
            # Load feature data from database
            logger.info("Loading features from database...")
            query = """
                SELECT * FROM features
                WHERE symbol = %s
                ORDER BY timestamp
            """
            result = self.db.execute_query(query, (symbol,))

            if not result:
                logger.error(f"No features found for {symbol}")
                return {"success": False, "error": "No features found"}

            df = pd.DataFrame(result)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)

            logger.info(f"Loaded {len(df)} feature samples")

            # Check if we have labels
            if "label" not in df.columns:
                logger.error("No labels found in features table")
                return {"success": False, "error": "No labels found"}

            # Filter valid labels (remove NaN and zeros if needed)
            df_labeled = df[df["label"].notna()].copy()

            if len(df_labeled) < min_samples:
                logger.error(
                    f"Insufficient labeled samples: {len(df_labeled)} < {min_samples}"
                )
                return {
                    "success": False,
                    "error": f"Insufficient samples: {len(df_labeled)} < {min_samples}",
                }

            logger.info(f"Using {len(df_labeled)} labeled samples for training")

            # Separate features and labels
            feature_cols = [
                col
                for col in df_labeled.columns
                if col not in ["label", "symbol", "interval"]
            ]
            X = df_labeled[feature_cols].values
            y = df_labeled["label"].values

            logger.info(f"Feature matrix shape: {X.shape}")
            logger.info(f"Label distribution: {np.unique(y, return_counts=True)}")

            # Split data: train, validation, test
            X_train_full, X_test, y_train_full, y_test = train_test_split(
                X, y, test_size=self.test_size, random_state=self.random_state, stratify=y
            )

            X_train, X_val, y_train, y_val = train_test_split(
                X_train_full,
                y_train_full,
                test_size=self.val_size,
                random_state=self.random_state,
                stratify=y_train_full,
            )

            logger.info(f"Train set: {X_train.shape}")
            logger.info(f"Validation set: {X_val.shape}")
            logger.info(f"Test set: {X_test.shape}")

            # Initialize and train ensemble
            logger.info("Initializing ensemble trainer...")
            ensemble = EnsembleTrainer(use_shap=True)

            logger.info("Training ensemble models (this may take 10-15 minutes)...")
            histories = ensemble.train_all(
                X_train, y_train, X_val, y_val
            )

            # Evaluate on test set
            logger.info("Evaluating ensemble on test set...")
            test_metrics = ensemble.evaluate(X_test, y_test)

            logger.info(f"Test metrics: {test_metrics}")

            # Save model if requested
            if save_model:
                logger.info("Saving ensemble model...")
                model_path = Path(settings.model_path)
                model_path.mkdir(parents=True, exist_ok=True)

                ensemble.save(model_path / "ensemble_model.pkl")
                logger.info(f"Model saved to {model_path}")

            logger.info(f"✅ Model training complete for {symbol}")

            return {
                "success": True,
                "histories": histories,
                "test_metrics": test_metrics,
                "num_samples": len(df_labeled),
                "num_features": len(feature_cols),
            }

        except Exception as e:
            logger.error(f"Model training failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def train_and_save(
        self,
        symbol: str = "EURUSD",
        min_samples: int = 1000,
    ) -> bool:
        """
        Convenience method to train and save model.

        Args:
            symbol: Trading symbol
            min_samples: Minimum number of samples

        Returns:
            True if successful, False otherwise
        """
        result = self.train_from_db(symbol, min_samples, save_model=True)
        return result.get("success", False)
