"""
Base trainer class for ML models.
Provides common functionality for training, evaluation, and persistence.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import joblib
from abc import ABC, abstractmethod

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class BaseModelTrainer(ABC):
    """Abstract base class for model trainers."""

    def __init__(self, model_name: str):
        """
        Initialize base trainer.

        Args:
            model_name: Name of the model (e.g., 'xgboost', 'lightgbm')
        """
        self.model_name = model_name
        self.model = None
        self.is_fitted = False
        self.feature_columns: Optional[List[str]] = None
        self.training_history: Dict[str, Any] = {}

        logger.info(f"Initialized {model_name} trainer")

    @abstractmethod
    def create_model(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Create a new model instance with given parameters.

        Args:
            params: Model hyperparameters

        Returns:
            Model instance
        """
        pass

    def prepare_data(
        self,
        features_df: pd.DataFrame,
        labels_df: pd.DataFrame,
        exclude_neutral: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare features and labels for training.

        Args:
            features_df: DataFrame with features
            labels_df: DataFrame with labels
            exclude_neutral: Whether to exclude neutral labels (label=0)

        Returns:
            Tuple of (X, y, feature_columns)
        """
        # Align indices
        common_index = features_df.index.intersection(labels_df.index)

        if len(common_index) == 0:
            raise ValueError("No common timestamps between features and labels")

        features_df = features_df.loc[common_index]
        labels_df = labels_df.loc[common_index]

        # Get labels
        y = labels_df["label"].values

        # Optionally exclude neutral labels
        if exclude_neutral:
            non_neutral_mask = y != 0
            features_df = features_df[non_neutral_mask]
            y = y[non_neutral_mask]

            logger.info(
                f"Excluded {(~non_neutral_mask).sum()} neutral labels, "
                f"keeping {len(y)} labeled samples"
            )

        # Select feature columns (exclude non-numeric and metadata)
        exclude_cols = {
            "open", "high", "low", "close", "volume",
            "symbol", "interval", "regime",
        }

        feature_cols = [
            col for col in features_df.columns
            if col not in exclude_cols and
            pd.api.types.is_numeric_dtype(features_df[col])
        ]

        X = features_df[feature_cols].values

        # Handle NaN values
        nan_count = np.isnan(X).sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values, filling with 0")
            X = np.nan_to_num(X, nan=0.0)

        # Store feature columns
        self.feature_columns = feature_cols

        logger.info(
            f"Prepared data: X shape {X.shape}, y shape {y.shape}, "
            f"{len(feature_cols)} features"
        )

        return X, y, feature_cols

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Train the model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            params: Model hyperparameters

        Returns:
            Training history dictionary
        """
        logger.info(f"Training {self.model_name} model")
        logger.info(f"Train: {X_train.shape}, Val: {X_val.shape if X_val is not None else 'None'}")

        # Create model
        self.model = self.create_model(params)

        # Train
        start_time = datetime.utcnow()

        if X_val is not None and y_val is not None:
            self._train_with_validation(X_train, y_train, X_val, y_val)
        else:
            self._train_without_validation(X_train, y_train)

        train_time = (datetime.utcnow() - start_time).total_seconds()

        self.is_fitted = True

        # Evaluate
        train_metrics = self.evaluate(X_train, y_train, dataset_name="train")

        val_metrics = {}
        if X_val is not None and y_val is not None:
            val_metrics = self.evaluate(X_val, y_val, dataset_name="validation")

        # Store history
        self.training_history = {
            "model_name": self.model_name,
            "train_time": train_time,
            "train_samples": len(y_train),
            "val_samples": len(y_val) if y_val is not None else 0,
            "num_features": X_train.shape[1],
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"✅ Training complete in {train_time:.2f}s")
        logger.info(f"Train accuracy: {train_metrics.get('accuracy', 0):.3f}")
        if val_metrics:
            logger.info(f"Val accuracy: {val_metrics.get('accuracy', 0):.3f}")

        return self.training_history

    @abstractmethod
    def _train_with_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> None:
        """Train with validation set (early stopping)."""
        pass

    @abstractmethod
    def _train_without_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> None:
        """Train without validation set."""
        pass

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict labels.

        Args:
            X: Features

        Returns:
            Predicted labels
        """
        if not self.is_fitted:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.

        Args:
            X: Features

        Returns:
            Class probabilities
        """
        if not self.is_fitted:
            raise ValueError("Model must be trained before prediction")

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        else:
            raise NotImplementedError(
                f"{self.model_name} does not support predict_proba"
            )

    def evaluate(
        self,
        X: np.ndarray,
        y_true: np.ndarray,
        dataset_name: str = "test",
    ) -> Dict[str, float]:
        """
        Evaluate model performance.

        Args:
            X: Features
            y_true: True labels
            dataset_name: Name of dataset for logging

        Returns:
            Dictionary of evaluation metrics
        """
        y_pred = self.predict(X)

        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average="weighted", zero_division=0)
        recall = recall_score(y_true, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

        # Per-class metrics
        precision_per_class = precision_score(
            y_true, y_pred, average=None, zero_division=0, labels=[-1, 1]
        )
        recall_per_class = recall_score(
            y_true, y_pred, average=None, zero_division=0, labels=[-1, 1]
        )

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "precision_short": precision_per_class[0] if len(precision_per_class) > 0 else 0,
            "precision_long": precision_per_class[1] if len(precision_per_class) > 1 else 0,
            "recall_short": recall_per_class[0] if len(recall_per_class) > 0 else 0,
            "recall_long": recall_per_class[1] if len(recall_per_class) > 1 else 0,
        }

        logger.debug(f"{dataset_name} metrics: {metrics}")

        return metrics

    def save(self, path: str) -> None:
        """
        Save model to disk.

        Args:
            path: Path to save model (e.g., 'models/current/xgboost.pkl')
        """
        if not self.is_fitted:
            raise ValueError("Cannot save untrained model")

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "model": self.model,
            "model_name": self.model_name,
            "feature_columns": self.feature_columns,
            "is_fitted": self.is_fitted,
            "training_history": self.training_history,
        }

        joblib.dump(model_data, path_obj)

        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> "BaseModelTrainer":
        """
        Load model from disk.

        Args:
            path: Path to saved model

        Returns:
            Loaded model trainer instance
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        model_data = joblib.load(path_obj)

        # Create trainer instance
        trainer = cls(model_name=model_data["model_name"])
        trainer.model = model_data["model"]
        trainer.feature_columns = model_data["feature_columns"]
        trainer.is_fitted = model_data["is_fitted"]
        trainer.training_history = model_data.get("training_history", {})

        logger.info(f"Model loaded from {path}")

        return trainer

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "model_name": self.model_name,
            "is_fitted": self.is_fitted,
            "num_features": len(self.feature_columns) if self.feature_columns else 0,
            "feature_columns": self.feature_columns,
            "training_history": self.training_history,
        }
