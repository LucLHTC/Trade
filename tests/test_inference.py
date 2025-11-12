"""
Tests for inference and prediction modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.predict import ModelInference
from tests.test_features import create_sample_candles


class TestModelInference:
    """Test model inference functionality."""

    @pytest.fixture
    def model_path(self, tmp_path):
        """Create a temporary model path."""
        model_dir = tmp_path / "models" / "test"
        model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir)

    def test_predict_single_shape(self):
        """Test that predict_single returns correct shape."""
        # This test will skip if model doesn't exist
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        df = create_sample_candles(200)

        prediction = inference.predict_single(df, threshold=0.55)

        # Check prediction structure
        assert "prediction" in prediction
        assert "confidence_short" in prediction
        assert "confidence_long" in prediction
        assert "regime" in prediction
        assert "top_features" in prediction

        # Check prediction value
        assert prediction["prediction"] in [-1, 0, 1]

        # Check confidence range
        assert 0.0 <= prediction["confidence_short"] <= 1.0
        assert 0.0 <= prediction["confidence_long"] <= 1.0

    def test_predict_batch_shape(self):
        """Test that predict_batch returns correct shape."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        df = create_sample_candles(100)

        predictions = inference.predict_batch(df, threshold=0.55)

        # Check shape
        assert len(predictions) == len(df)

        # Check columns
        assert "prediction" in predictions.columns
        assert "confidence_short" in predictions.columns
        assert "confidence_long" in predictions.columns

        # Check values
        assert set(predictions["prediction"].unique()).issubset({-1, 0, 1})

    def test_get_signal_strength(self):
        """Test signal strength assessment."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        # Neutral
        neutral_pred = {"prediction": 0, "confidence_long": 0.5, "confidence_short": 0.5}
        assert inference.get_signal_strength(neutral_pred) == "neutral"

        # Strong long
        strong_long = {"prediction": 1, "confidence_long": 0.75, "confidence_short": 0.25}
        assert inference.get_signal_strength(strong_long) == "strong"

        # Moderate short
        moderate_short = {"prediction": -1, "confidence_long": 0.35, "confidence_short": 0.65}
        assert inference.get_signal_strength(moderate_short) == "moderate"

        # Weak long
        weak_long = {"prediction": 1, "confidence_long": 0.56, "confidence_short": 0.44}
        assert inference.get_signal_strength(weak_long) == "weak"

    def test_should_trade_neutral(self):
        """Test that neutral predictions don't trade."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        neutral_pred = {
            "prediction": 0,
            "confidence_long": 0.5,
            "confidence_short": 0.5,
            "regime": "bullish",
        }

        should_trade, reason = inference.should_trade(
            prediction=neutral_pred,
            current_price=1.0850,
            spread=0.00001,
        )

        assert not should_trade
        assert "neutral" in reason.lower()

    def test_should_trade_weak_signal(self):
        """Test that weak signals don't trade."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        weak_pred = {
            "prediction": 1,
            "confidence_long": 0.56,
            "confidence_short": 0.44,
            "regime": "bullish",
        }

        should_trade, reason = inference.should_trade(
            prediction=weak_pred,
            current_price=1.0850,
            spread=0.00001,
        )

        assert not should_trade
        assert "weak" in reason.lower()

    def test_should_trade_wide_spread(self):
        """Test that wide spread prevents trading."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        strong_pred = {
            "prediction": 1,
            "confidence_long": 0.75,
            "confidence_short": 0.25,
            "regime": "bullish",
        }

        should_trade, reason = inference.should_trade(
            prediction=strong_pred,
            current_price=1.0850,
            spread=0.0005,  # Wide spread
            max_spread=0.0002,
        )

        assert not should_trade
        assert "spread" in reason.lower()

    def test_should_trade_sideways_regime(self):
        """Test that sideways regime prevents trading."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        strong_pred = {
            "prediction": 1,
            "confidence_long": 0.75,
            "confidence_short": 0.25,
            "regime": "sideways",
        }

        should_trade, reason = inference.should_trade(
            prediction=strong_pred,
            current_price=1.0850,
            spread=0.00001,
        )

        assert not should_trade
        assert "sideways" in reason.lower()

    def test_should_trade_strong_signal(self):
        """Test that strong signal in good conditions triggers trade."""
        try:
            inference = ModelInference(model_path="models/current")
        except Exception:
            pytest.skip("Model not available")
            return

        strong_pred = {
            "prediction": 1,
            "confidence_long": 0.75,
            "confidence_short": 0.25,
            "regime": "bullish",
        }

        should_trade, reason = inference.should_trade(
            prediction=strong_pred,
            current_price=1.0850,
            spread=0.00001,
        )

        assert should_trade
        assert "long" in reason.lower()
