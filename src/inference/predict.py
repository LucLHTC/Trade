"""
Model inference module for real-time predictions.
Loads trained ensemble and generates trading signals.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.training.ensemble import EnsembleTrainer
from src.features.manager import FeatureManager
from src.features.technical import calculate_all_features
from src.features.events import EventFeatures
from src.labeling.regimes import RegimeClassifier
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class ModelInference:
    """Real-time model inference for trading signals."""

    def __init__(self, model_path: str = "models/current"):
        """
        Initialize inference engine.

        Args:
            model_path: Path to saved ensemble model
        """
        self.model_path = Path(model_path)
        self.ensemble: Optional[EnsembleTrainer] = None
        self.event_features = EventFeatures()

        self._load_model()

        logger.info(f"ModelInference initialized with model from {model_path}")

    def _load_model(self) -> None:
        """Load ensemble model from disk."""
        try:
            self.ensemble = EnsembleTrainer.load(str(self.model_path))
            logger.info("✅ Ensemble model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def predict_single(
        self,
        candles_df: pd.DataFrame,
        threshold: float = 0.55,
    ) -> Dict[str, Any]:
        """
        Generate prediction for the latest candle.

        Args:
            candles_df: DataFrame with recent candles (need history for indicators)
            threshold: Confidence threshold for predictions

        Returns:
            Dictionary with prediction details
        """
        if self.ensemble is None:
            raise ValueError("Model not loaded")

        if candles_df.empty:
            raise ValueError("Empty candles dataframe")

        logger.debug(f"Generating prediction for latest candle")

        # Generate features for all candles (need history)
        df = calculate_all_features(candles_df)
        df = self.event_features.calculate_event_features(df)
        df = RegimeClassifier.classify_regime(df)

        # Get latest row
        latest_features = df.iloc[[-1]]  # Keep as DataFrame

        # Extract features for prediction
        X = self._prepare_features(latest_features)

        # Get probabilities
        proba = self.ensemble.predict_proba_ensemble(X)

        # Get prediction
        pred = self.ensemble.predict(X, threshold=threshold)

        # Get SHAP values for top features
        top_features = self.ensemble.get_top_features(X, model_name="xgboost", top_n=5)

        # Build result
        result = {
            "timestamp": latest_features.index[0],
            "prediction": int(pred[0]),
            "confidence_short": float(proba[0, 0]),
            "confidence_long": float(proba[0, 1]),
            "regime": latest_features["regime"].iloc[0] if "regime" in latest_features.columns else "unknown",
            "top_features": top_features,
            "threshold": threshold,
        }

        logger.info(
            f"Prediction: {result['prediction']} "
            f"(short={result['confidence_short']:.3f}, long={result['confidence_long']:.3f}), "
            f"regime={result['regime']}"
        )

        return result

    def predict_batch(
        self,
        candles_df: pd.DataFrame,
        threshold: float = 0.55,
    ) -> pd.DataFrame:
        """
        Generate predictions for multiple candles.

        Args:
            candles_df: DataFrame with candles
            threshold: Confidence threshold

        Returns:
            DataFrame with predictions
        """
        if self.ensemble is None:
            raise ValueError("Model not loaded")

        logger.info(f"Generating batch predictions for {len(candles_df)} candles")

        # Generate features
        df = calculate_all_features(candles_df)
        df = self.event_features.calculate_event_features(df)
        df = RegimeClassifier.classify_regime(df)

        # Prepare features
        X = self._prepare_features(df)

        # Get predictions
        proba = self.ensemble.predict_proba_ensemble(X)
        pred = self.ensemble.predict(X, threshold=threshold)

        # Add to dataframe
        df["prediction"] = pred
        df["confidence_short"] = proba[:, 0]
        df["confidence_long"] = proba[:, 1]

        logger.info(
            f"✅ Generated {len(df)} predictions "
            f"(Long: {(pred == 1).sum()}, Short: {(pred == -1).sum()}, Neutral: {(pred == 0).sum()})"
        )

        return df

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for prediction.

        Args:
            df: DataFrame with features

        Returns:
            Feature array
        """
        if self.ensemble.feature_columns is None:
            raise ValueError("Model feature columns not set")

        # Select feature columns
        X = df[self.ensemble.feature_columns].values

        # Handle NaN
        X = np.nan_to_num(X, nan=0.0)

        return X

    def get_signal_strength(self, prediction: Dict[str, Any]) -> str:
        """
        Assess signal strength based on confidence.

        Args:
            prediction: Prediction dictionary

        Returns:
            Signal strength: 'strong', 'moderate', 'weak'
        """
        pred = prediction["prediction"]

        if pred == 0:
            return "neutral"

        confidence = (
            prediction["confidence_long"] if pred == 1
            else prediction["confidence_short"]
        )

        if confidence > 0.7:
            return "strong"
        elif confidence > 0.6:
            return "moderate"
        else:
            return "weak"

    def should_trade(
        self,
        prediction: Dict[str, Any],
        current_price: float,
        spread: float,
        max_spread: float = 0.0002,
    ) -> Tuple[bool, str]:
        """
        Determine if we should take the trade.

        Args:
            prediction: Prediction dictionary
            current_price: Current market price
            spread: Current spread
            max_spread: Maximum allowed spread

        Returns:
            Tuple of (should_trade, reason)
        """
        # Check prediction
        if prediction["prediction"] == 0:
            return False, "Neutral prediction"

        # Check confidence
        signal_strength = self.get_signal_strength(prediction)
        if signal_strength == "weak":
            return False, "Weak signal"

        # Check spread
        spread_pct = spread / current_price
        if spread_pct > max_spread:
            return False, f"Spread too wide ({spread_pct:.4%} > {max_spread:.4%})"

        # Check regime
        regime = prediction.get("regime", "unknown")
        if regime == "sideways":
            return False, "Sideways regime - no clear trend"

        # Check for upcoming high-impact events
        # This would require checking event features
        # For now, we'll skip this check

        return True, f"{signal_strength.capitalize()} {['short', 'neutral', 'long'][prediction['prediction'] + 1]} signal"

    def reload_model(self) -> None:
        """Reload model from disk (for live updates)."""
        logger.info("Reloading model...")
        self._load_model()
