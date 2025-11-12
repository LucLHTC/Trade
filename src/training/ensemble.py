"""
Ensemble model trainer with soft voting.
Combines XGBoost, LightGBM, and RandomForest predictions.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import joblib
from datetime import datetime

import shap

from src.training.models import XGBoostTrainer, LightGBMTrainer, RandomForestTrainer
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class EnsembleTrainer:
    """Ensemble of multiple models with soft voting."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        use_shap: bool = True,
    ):
        """
        Initialize ensemble trainer.

        Args:
            weights: Voting weights for each model (default: equal)
            use_shap: Whether to calculate SHAP values
        """
        self.models: Dict[str, Any] = {
            "xgboost": XGBoostTrainer(),
            "lightgbm": LightGBMTrainer(),
            "randomforest": RandomForestTrainer(),
        }

        self.weights = weights or {
            "xgboost": 0.4,
            "lightgbm": 0.4,
            "randomforest": 0.2,
        }

        self.use_shap = use_shap
        self.is_fitted = False
        self.feature_columns: Optional[List[str]] = None
        self.shap_explainers: Dict[str, Any] = {}

        logger.info(f"Initialized ensemble with weights: {self.weights}")

    def train_all(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        model_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Train all models in the ensemble.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            model_params: Hyperparameters for each model

        Returns:
            Dictionary of training histories for each model
        """
        logger.info("Training ensemble models")

        histories = {}
        model_params = model_params or {}

        for model_name, trainer in self.models.items():
            logger.info(f"Training {model_name}...")

            params = model_params.get(model_name)

            history = trainer.train(
                X_train, y_train,
                X_val, y_val,
                params=params,
            )

            histories[model_name] = history

            # Store feature columns from first model
            if self.feature_columns is None:
                self.feature_columns = trainer.feature_columns

        self.is_fitted = True

        # Calculate SHAP values
        if self.use_shap:
            self._calculate_shap_values(X_train)

        logger.info("✅ Ensemble training complete")

        return histories

    def _calculate_shap_values(self, X_sample: np.ndarray, max_samples: int = 100):
        """
        Calculate SHAP explainers for interpretability.

        Args:
            X_sample: Sample data for SHAP background
            max_samples: Maximum samples for SHAP background
        """
        logger.info("Calculating SHAP explainers...")

        # Use subset for efficiency
        if len(X_sample) > max_samples:
            indices = np.random.choice(len(X_sample), max_samples, replace=False)
            X_background = X_sample[indices]
        else:
            X_background = X_sample

        try:
            # XGBoost SHAP
            if "xgboost" in self.models:
                self.shap_explainers["xgboost"] = shap.TreeExplainer(
                    self.models["xgboost"].model
                )

            # LightGBM SHAP
            if "lightgbm" in self.models:
                self.shap_explainers["lightgbm"] = shap.TreeExplainer(
                    self.models["lightgbm"].model
                )

            # RandomForest SHAP
            if "randomforest" in self.models:
                self.shap_explainers["randomforest"] = shap.TreeExplainer(
                    self.models["randomforest"].model
                )

            logger.info("✅ SHAP explainers calculated")

        except Exception as e:
            logger.warning(f"Failed to calculate SHAP explainers: {e}")

    def predict_proba_ensemble(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities using ensemble soft voting.

        Args:
            X: Features

        Returns:
            Ensemble probabilities (shape: n_samples × 2)
        """
        if not self.is_fitted:
            raise ValueError("Ensemble must be trained before prediction")

        # Get probabilities from each model
        probas = []
        weights = []

        for model_name, trainer in self.models.items():
            if trainer.is_fitted:
                proba = trainer.predict_proba(X)
                probas.append(proba)
                weights.append(self.weights[model_name])

        # Weighted average
        probas = np.array(probas)
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize

        ensemble_proba = np.average(probas, axis=0, weights=weights)

        return ensemble_proba

    def predict(self, X: np.ndarray, threshold: float = 0.55) -> np.ndarray:
        """
        Predict labels using ensemble.

        Args:
            X: Features
            threshold: Confidence threshold for predictions

        Returns:
            Predicted labels (-1, 0, 1)
        """
        proba = self.predict_proba_ensemble(X)

        # proba[:, 0] = P(class=-1), proba[:, 1] = P(class=1)
        predictions = np.where(
            proba[:, 1] > threshold,
            1,  # Long
            np.where(
                proba[:, 0] > threshold,
                -1,  # Short
                0,  # Neutral
            ),
        )

        return predictions

    def get_shap_values(
        self,
        X: np.ndarray,
        model_name: str = "xgboost",
    ) -> Optional[np.ndarray]:
        """
        Get SHAP values for interpretability.

        Args:
            X: Features
            model_name: Which model to use for SHAP

        Returns:
            SHAP values array or None
        """
        if model_name not in self.shap_explainers:
            logger.warning(f"No SHAP explainer for {model_name}")
            return None

        try:
            shap_values = self.shap_explainers[model_name].shap_values(X)
            return shap_values
        except Exception as e:
            logger.error(f"Failed to calculate SHAP values: {e}")
            return None

    def get_top_features(
        self,
        X: np.ndarray,
        model_name: str = "xgboost",
        top_n: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Get top N most important features for a prediction.

        Args:
            X: Single sample features (shape: 1 × n_features)
            model_name: Which model to use
            top_n: Number of top features

        Returns:
            List of (feature_name, importance) tuples
        """
        shap_values = self.get_shap_values(X, model_name)

        if shap_values is None or self.feature_columns is None:
            return []

        # Get absolute SHAP values
        if len(shap_values.shape) == 3:  # Multi-class
            shap_values = shap_values[:, :, 1]  # Use class=1 (long)

        abs_shap = np.abs(shap_values[0])

        # Get top indices
        top_indices = np.argsort(abs_shap)[::-1][:top_n]

        top_features = [
            (self.feature_columns[idx], abs_shap[idx])
            for idx in top_indices
        ]

        return top_features

    def evaluate_ensemble(
        self,
        X: np.ndarray,
        y_true: np.ndarray,
        threshold: float = 0.55,
    ) -> Dict[str, float]:
        """
        Evaluate ensemble performance.

        Args:
            X: Features
            y_true: True labels
            threshold: Prediction threshold

        Returns:
            Dictionary of metrics
        """
        y_pred = self.predict(X, threshold=threshold)

        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        # Filter out neutral predictions for some metrics
        non_neutral_mask = y_pred != 0
        y_true_filtered = y_true[non_neutral_mask]
        y_pred_filtered = y_pred[non_neutral_mask]

        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "accuracy_non_neutral": accuracy_score(y_true_filtered, y_pred_filtered) if len(y_true_filtered) > 0 else 0,
            "precision": precision_score(y_true_filtered, y_pred_filtered, average="weighted", zero_division=0) if len(y_true_filtered) > 0 else 0,
            "recall": recall_score(y_true_filtered, y_pred_filtered, average="weighted", zero_division=0) if len(y_true_filtered) > 0 else 0,
            "f1": f1_score(y_true_filtered, y_pred_filtered, average="weighted", zero_division=0) if len(y_true_filtered) > 0 else 0,
            "prediction_rate": non_neutral_mask.sum() / len(y_pred) if len(y_pred) > 0 else 0,
        }

        return metrics

    def save(self, path: str) -> None:
        """
        Save ensemble to disk.

        Args:
            path: Directory path to save ensemble
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)

        # Save individual models
        for model_name, trainer in self.models.items():
            if trainer.is_fitted:
                model_path = path_obj / f"{model_name}.pkl"
                trainer.save(str(model_path))

        # Save ensemble metadata
        ensemble_data = {
            "weights": self.weights,
            "feature_columns": self.feature_columns,
            "is_fitted": self.is_fitted,
            "use_shap": self.use_shap,
            "timestamp": datetime.utcnow().isoformat(),
        }

        metadata_path = path_obj / "ensemble_metadata.pkl"
        joblib.dump(ensemble_data, metadata_path)

        logger.info(f"Ensemble saved to {path}")

    @classmethod
    def load(cls, path: str) -> "EnsembleTrainer":
        """
        Load ensemble from disk.

        Args:
            path: Directory path with saved ensemble

        Returns:
            Loaded ensemble trainer
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Ensemble directory not found: {path}")

        # Load metadata
        metadata_path = path_obj / "ensemble_metadata.pkl"
        ensemble_data = joblib.load(metadata_path)

        # Create ensemble
        ensemble = cls(
            weights=ensemble_data["weights"],
            use_shap=ensemble_data.get("use_shap", True),
        )

        # Load individual models
        for model_name in ["xgboost", "lightgbm", "randomforest"]:
            model_path = path_obj / f"{model_name}.pkl"
            if model_path.exists():
                trainer_cls = {
                    "xgboost": XGBoostTrainer,
                    "lightgbm": LightGBMTrainer,
                    "randomforest": RandomForestTrainer,
                }[model_name]

                ensemble.models[model_name] = trainer_cls.load(str(model_path))

        ensemble.is_fitted = ensemble_data["is_fitted"]
        ensemble.feature_columns = ensemble_data["feature_columns"]

        logger.info(f"Ensemble loaded from {path}")

        return ensemble
