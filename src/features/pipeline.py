"""
Feature preprocessing pipeline using sklearn.
Handles imputation, scaling, and feature selection.
"""

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import joblib
from typing import Optional, List

from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class FeaturePreprocessor:
    """Preprocessing pipeline for trading features."""

    def __init__(self, pipeline: Optional[Pipeline] = None):
        """
        Initialize feature preprocessor.

        Args:
            pipeline: Optional pre-existing pipeline to use
        """
        if pipeline is None:
            self.pipeline = self._create_default_pipeline()
        else:
            self.pipeline = pipeline

        self.feature_columns: Optional[List[str]] = None
        self.is_fitted = False

        logger.info("FeaturePreprocessor initialized")

    @staticmethod
    def _create_default_pipeline() -> Pipeline:
        """
        Create default preprocessing pipeline.

        Returns:
            sklearn Pipeline with imputer and scaler
        """
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler()),
        ])

        logger.info("Created default preprocessing pipeline (imputer + scaler)")

        return pipeline

    def fit(self, df: pd.DataFrame, feature_columns: Optional[List[str]] = None) -> "FeaturePreprocessor":
        """
        Fit the preprocessing pipeline on training data.

        Args:
            df: DataFrame with features
            feature_columns: List of feature column names to use (default: all numeric)

        Returns:
            Self
        """
        logger.info("Fitting preprocessing pipeline")

        # Select feature columns
        if feature_columns is None:
            # Exclude non-feature columns
            exclude_cols = {
                "open", "high", "low", "close", "volume",
                "symbol", "interval", "regime", "label",
                "forward_return", "threshold", "macro_event_window",
                "spread", "sharpe_last_week",
            }

            feature_columns = [
                col for col in df.columns
                if col not in exclude_cols and df[col].dtype in [np.float64, np.int64, np.float32, np.int32]
            ]

        self.feature_columns = feature_columns

        logger.info(f"Using {len(self.feature_columns)} feature columns")

        # Fit pipeline
        X = df[self.feature_columns].copy()
        self.pipeline.fit(X)

        self.is_fitted = True

        logger.info("✅ Pipeline fitted successfully")

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform features using fitted pipeline.

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with transformed features
        """
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before transform")

        if self.feature_columns is None:
            raise ValueError("Feature columns not set")

        logger.debug(f"Transforming {len(df)} samples")

        # Extract features
        X = df[self.feature_columns].copy()

        # Transform
        X_transformed = self.pipeline.transform(X)

        # Create result dataframe
        result = pd.DataFrame(
            X_transformed,
            index=df.index,
            columns=self.feature_columns,
        )

        # Add back non-feature columns
        for col in df.columns:
            if col not in self.feature_columns:
                result[col] = df[col]

        return result

    def fit_transform(self, df: pd.DataFrame, feature_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fit and transform in one step.

        Args:
            df: DataFrame with features
            feature_columns: Optional list of feature columns

        Returns:
            DataFrame with transformed features
        """
        self.fit(df, feature_columns=feature_columns)
        return self.transform(df)

    def save(self, path: str) -> None:
        """
        Save pipeline to disk.

        Args:
            path: Path to save pipeline (e.g., 'models/current/pipeline.pkl')
        """
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Save pipeline and metadata
        pipeline_data = {
            "pipeline": self.pipeline,
            "feature_columns": self.feature_columns,
            "is_fitted": self.is_fitted,
        }

        joblib.dump(pipeline_data, path_obj)

        logger.info(f"Pipeline saved to {path}")

    @classmethod
    def load(cls, path: str) -> "FeaturePreprocessor":
        """
        Load pipeline from disk.

        Args:
            path: Path to saved pipeline

        Returns:
            FeaturePreprocessor instance
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Pipeline file not found: {path}")

        pipeline_data = joblib.load(path_obj)

        preprocessor = cls(pipeline=pipeline_data["pipeline"])
        preprocessor.feature_columns = pipeline_data["feature_columns"]
        preprocessor.is_fitted = pipeline_data["is_fitted"]

        logger.info(f"Pipeline loaded from {path}")

        return preprocessor

    def get_feature_names(self) -> List[str]:
        """Get list of feature column names."""
        if self.feature_columns is None:
            return []
        return self.feature_columns.copy()

    def get_pipeline_info(self) -> dict:
        """Get information about the pipeline."""
        return {
            "is_fitted": self.is_fitted,
            "num_features": len(self.feature_columns) if self.feature_columns else 0,
            "feature_columns": self.feature_columns,
            "pipeline_steps": [step[0] for step in self.pipeline.steps],
        }
