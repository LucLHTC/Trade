"""
Individual model trainers for ensemble.
Implements XGBoost, LightGBM, and RandomForest classifiers.
"""

import numpy as np
from typing import Dict, Any, Optional

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

from src.training.base_trainer import BaseModelTrainer
from src.common.logger import get_logger

logger = get_logger(__name__)


class XGBoostTrainer(BaseModelTrainer):
    """XGBoost model trainer."""

    def __init__(self):
        super().__init__(model_name="xgboost")

    def create_model(self, params: Optional[Dict[str, Any]] = None) -> XGBClassifier:
        """Create XGBoost classifier."""
        default_params = {
            "objective": "multi:softmax",
            "num_class": 2,  # -1 and 1 (we exclude 0)
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0,
        }

        if params:
            default_params.update(params)

        # Map labels -1, 1 to 0, 1 for XGBoost
        model = XGBClassifier(**default_params)

        logger.info(f"Created XGBoost model with params: {default_params}")

        return model

    def _train_with_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> None:
        """Train with early stopping."""
        # Map labels -1 → 0, 1 → 1
        y_train_mapped = np.where(y_train == -1, 0, 1)
        y_val_mapped = np.where(y_val == -1, 0, 1)

        self.model.fit(
            X_train,
            y_train_mapped,
            eval_set=[(X_val, y_val_mapped)],
            verbose=False,
        )

    def _train_without_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> None:
        """Train without validation."""
        y_train_mapped = np.where(y_train == -1, 0, 1)
        self.model.fit(X_train, y_train_mapped)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict with label remapping."""
        pred = self.model.predict(X)
        # Map back: 0 → -1, 1 → 1
        return np.where(pred == 0, -1, 1)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities (class 0=-1, class 1=1)."""
        return self.model.predict_proba(X)


class LightGBMTrainer(BaseModelTrainer):
    """LightGBM model trainer."""

    def __init__(self):
        super().__init__(model_name="lightgbm")

    def create_model(self, params: Optional[Dict[str, Any]] = None) -> LGBMClassifier:
        """Create LightGBM classifier."""
        default_params = {
            "objective": "multiclass",
            "num_class": 2,
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": -1,
        }

        if params:
            default_params.update(params)

        model = LGBMClassifier(**default_params)

        logger.info(f"Created LightGBM model with params: {default_params}")

        return model

    def _train_with_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> None:
        """Train with early stopping."""
        y_train_mapped = np.where(y_train == -1, 0, 1)
        y_val_mapped = np.where(y_val == -1, 0, 1)

        self.model.fit(
            X_train,
            y_train_mapped,
            eval_set=[(X_val, y_val_mapped)],
            eval_metric="multi_logloss",
            callbacks=[],  # Disable default logging
        )

    def _train_without_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> None:
        """Train without validation."""
        y_train_mapped = np.where(y_train == -1, 0, 1)
        self.model.fit(X_train, y_train_mapped)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict with label remapping."""
        pred = self.model.predict(X)
        return np.where(pred == 0, -1, 1)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        return self.model.predict_proba(X)


class RandomForestTrainer(BaseModelTrainer):
    """Random Forest model trainer."""

    def __init__(self):
        super().__init__(model_name="randomforest")

    def create_model(self, params: Optional[Dict[str, Any]] = None) -> RandomForestClassifier:
        """Create Random Forest classifier."""
        default_params = {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "random_state": 42,
            "n_jobs": -1,
            "verbose": 0,
        }

        if params:
            default_params.update(params)

        model = RandomForestClassifier(**default_params)

        logger.info(f"Created RandomForest model with params: {default_params}")

        return model

    def _train_with_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> None:
        """Train (RandomForest doesn't use validation for early stopping)."""
        self.model.fit(X_train, y_train)

    def _train_without_validation(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> None:
        """Train without validation."""
        self.model.fit(X_train, y_train)
