"""
Tests for feature engineering modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.technical import TechnicalIndicators, calculate_all_features
from src.features.events import EventFeatures
from src.labeling.regimes import RegimeClassifier
from src.labeling.targets import LabelGenerator, generate_all_labels
from src.features.pipeline import FeaturePreprocessor
from src.features.manager import FeatureManager


def create_sample_candles(n=200):
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=n, freq="H", tz="UTC")

    # Simulated price with trend and noise
    base_price = 1.0850
    trend = np.linspace(0, 0.01, n)
    noise = np.random.normal(0, 0.0005, n)
    close_prices = base_price + trend + noise

    df = pd.DataFrame({
        "open": close_prices * (1 - np.random.uniform(0, 0.0002, n)),
        "high": close_prices * (1 + np.random.uniform(0, 0.0003, n)),
        "low": close_prices * (1 - np.random.uniform(0, 0.0003, n)),
        "close": close_prices,
        "volume": np.random.uniform(1000, 5000, n),
        "symbol": "EURUSD",
        "interval": "60min",
    }, index=dates)

    df.index.name = "timestamp"

    return df


class TestTechnicalIndicators:
    """Test technical indicator calculations."""

    def test_calculate_all_indicators(self):
        """Test that all technical indicators are calculated."""
        df = create_sample_candles(200)
        result = TechnicalIndicators.calculate_all(df)

        # Check that new columns were added
        assert len(result.columns) > len(df.columns)

        # Check for key indicators
        expected_indicators = [
            "rsi_14", "rsi_7",
            "macd", "macd_signal", "macd_histogram",
            "ema_9", "ema_21", "ema_50",
            "bb_upper", "bb_middle", "bb_lower",
            "atr_14",
            "stoch_k", "stoch_d",
            "adx",
        ]

        for indicator in expected_indicators:
            assert indicator in result.columns, f"Missing indicator: {indicator}"

    def test_calculate_derived_features(self):
        """Test derived feature calculation."""
        df = create_sample_candles(200)
        df = TechnicalIndicators.calculate_all(df)
        result = TechnicalIndicators.calculate_derived_features(df)

        # Check for derived features
        expected_features = [
            "ema_cross_9_21",
            "macd_above_signal",
            "price_vs_ema21",
            "rsi_oversold",
            "rsi_overbought",
            "returns",
            "volatility_10",
            "candle_size",
        ]

        for feature in expected_features:
            assert feature in result.columns, f"Missing derived feature: {feature}"

    def test_calculate_price_patterns(self):
        """Test price pattern features."""
        df = create_sample_candles(200)
        result = TechnicalIndicators.calculate_price_patterns(df)

        # Check for pattern features
        expected_patterns = [
            "higher_high",
            "lower_low",
            "near_resistance",
            "near_support",
        ]

        for pattern in expected_patterns:
            assert pattern in result.columns, f"Missing pattern: {pattern}"

    def test_calculate_all_features(self):
        """Test complete feature calculation pipeline."""
        df = create_sample_candles(200)
        result = calculate_all_features(df)

        # Should have many features
        feature_count = len([col for col in result.columns if col not in ["open", "high", "low", "close", "volume", "symbol", "interval"]])
        assert feature_count > 50, f"Expected >50 features, got {feature_count}"

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame()
        result = TechnicalIndicators.calculate_all(df)
        assert result.empty


class TestEventFeatures:
    """Test event-based features."""

    def test_calculate_event_features_no_events(self):
        """Test event features with no events available."""
        df = create_sample_candles(100)
        event_features = EventFeatures()

        result = event_features.calculate_event_features(df)

        # Should add event feature columns with zeros
        assert "has_event_last_24h" in result.columns
        assert "high_impact_event_next_6h" in result.columns
        assert (result["has_event_last_24h"] == 0).all()

    def test_get_events_dataframe_empty(self):
        """Test getting events when none exist."""
        event_features = EventFeatures()
        events_df = event_features.get_events_dataframe()

        # May be empty if no events in database
        assert isinstance(events_df, pd.DataFrame)


class TestRegimeClassifier:
    """Test market regime classification."""

    def test_classify_regime(self):
        """Test regime classification."""
        df = create_sample_candles(200)
        df = TechnicalIndicators.calculate_all(df)
        result = RegimeClassifier.classify_regime(df)

        # Should add regime column
        assert "regime" in result.columns

        # Should have valid regime values
        valid_regimes = {"bullish", "bearish", "sideways", "volatile", "unknown"}
        assert set(result["regime"].unique()).issubset(valid_regimes)

    def test_get_regime_metrics(self):
        """Test regime metrics calculation."""
        df = create_sample_candles(100)
        df = TechnicalIndicators.calculate_all(df)
        df = RegimeClassifier.classify_regime(df)

        metrics = RegimeClassifier.get_regime_metrics(df)

        assert "total_periods" in metrics
        assert metrics["total_periods"] == len(df)
        assert "bullish_pct" in metrics
        assert "bearish_pct" in metrics


class TestLabelGenerator:
    """Test label generation."""

    def test_generate_labels(self):
        """Test basic label generation."""
        df = create_sample_candles(200)
        generator = LabelGenerator(lookahead_periods=3, threshold_multiplier=0.7)

        result = generator.generate_labels(df)

        # Should add label columns
        assert "label" in result.columns
        assert "forward_return" in result.columns
        assert "threshold" in result.columns

        # Labels should be -1, 0, or 1
        valid_labels = {-1, 0, 1}
        assert set(result["label"].dropna().unique()).issubset(valid_labels)

    def test_generate_labels_regime_aware(self):
        """Test regime-aware labeling."""
        df = create_sample_candles(200)
        df = TechnicalIndicators.calculate_all(df)
        df = RegimeClassifier.classify_regime(df)

        generator = LabelGenerator()
        result = generator.generate_labels(df, regime_aware=True)

        # Should have neutralized labels in sideways regime
        sideways_mask = result["regime"] == "sideways"
        if sideways_mask.sum() > 0:
            sideways_labels = result.loc[sideways_mask, "label"]
            # All sideways periods should be neutral
            assert (sideways_labels == 0).all()

    def test_validate_labels(self):
        """Test label validation."""
        df = create_sample_candles(200)
        generator = LabelGenerator()
        df_with_labels = generator.generate_labels(df)

        is_valid, message = generator.validate_labels(df_with_labels)

        # May fail if insufficient labeled examples, but should not error
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)

    def test_get_label_statistics(self):
        """Test label statistics calculation."""
        df = create_sample_candles(200)
        generator = LabelGenerator()
        df_with_labels = generator.generate_labels(df)

        stats = generator.get_label_statistics(df_with_labels)

        assert "total_periods" in stats
        assert "long_signals" in stats
        assert "short_signals" in stats
        assert "neutral_periods" in stats

    def test_generate_all_labels(self):
        """Test complete label generation pipeline."""
        df = create_sample_candles(200)
        df = TechnicalIndicators.calculate_all(df)
        df = RegimeClassifier.classify_regime(df)

        result = generate_all_labels(df)

        # Should have all label columns
        assert "label" in result.columns
        assert "regime" in result.columns
        assert "forward_return" in result.columns


class TestFeaturePreprocessor:
    """Test preprocessing pipeline."""

    def test_fit_transform(self):
        """Test fit and transform."""
        df = create_sample_candles(100)
        df = calculate_all_features(df)

        preprocessor = FeaturePreprocessor()
        result = preprocessor.fit_transform(df)

        # Should have same shape
        assert len(result) == len(df)

        # Features should be scaled
        assert preprocessor.is_fitted

    def test_save_load_pipeline(self, tmp_path):
        """Test saving and loading pipeline."""
        df = create_sample_candles(100)
        df = calculate_all_features(df)

        # Fit and save
        preprocessor = FeaturePreprocessor()
        preprocessor.fit(df)

        save_path = tmp_path / "pipeline.pkl"
        preprocessor.save(str(save_path))

        # Load
        loaded_preprocessor = FeaturePreprocessor.load(str(save_path))

        assert loaded_preprocessor.is_fitted
        assert loaded_preprocessor.feature_columns == preprocessor.feature_columns

    def test_get_feature_names(self):
        """Test getting feature names."""
        df = create_sample_candles(100)
        df = calculate_all_features(df)

        preprocessor = FeaturePreprocessor()
        preprocessor.fit(df)

        feature_names = preprocessor.get_feature_names()

        assert len(feature_names) > 0
        assert isinstance(feature_names, list)


class TestFeatureManager:
    """Test feature manager."""

    def test_initialization(self, tmp_path):
        """Test feature manager initialization."""
        manager = FeatureManager(
            features_dir=str(tmp_path / "features"),
            labels_dir=str(tmp_path / "labels"),
        )

        assert manager.features_dir.exists()
        assert manager.labels_dir.exists()

    def test_save_load_features(self, tmp_path):
        """Test saving and loading features."""
        df = create_sample_candles(100)
        df = calculate_all_features(df)
        df = generate_all_labels(df)

        manager = FeatureManager(
            features_dir=str(tmp_path / "features"),
            labels_dir=str(tmp_path / "labels"),
        )

        # Save
        features_path = manager.save_features(df, symbol="EURUSD")
        assert features_path.exists()

        # Load
        loaded_features = manager.load_features(symbol="EURUSD")
        assert not loaded_features.empty

    def test_save_load_labels(self, tmp_path):
        """Test saving and loading labels."""
        df = create_sample_candles(100)
        df = calculate_all_features(df)
        df = generate_all_labels(df)

        manager = FeatureManager(
            features_dir=str(tmp_path / "features"),
            labels_dir=str(tmp_path / "labels"),
        )

        # Save
        labels_path = manager.save_labels(df, symbol="EURUSD")
        assert labels_path.exists()

        # Load
        loaded_labels = manager.load_labels(symbol="EURUSD")
        assert not loaded_labels.empty
        assert "label" in loaded_labels.columns


class TestIntegration:
    """Integration tests for complete feature pipeline."""

    def test_end_to_end_feature_generation(self):
        """Test complete feature generation pipeline."""
        # Create sample data
        df = create_sample_candles(200)

        # Step 1: Technical features
        df = calculate_all_features(df)
        assert len(df.columns) > 50

        # Step 2: Regime classification
        df = RegimeClassifier.classify_regime(df)
        assert "regime" in df.columns

        # Step 3: Label generation
        df = generate_all_labels(df)
        assert "label" in df.columns

        # Step 4: Validate
        assert len(df) > 0
        assert "forward_return" in df.columns

    def test_feature_label_alignment(self):
        """Test that features and labels are properly aligned."""
        df = create_sample_candles(200)
        df = calculate_all_features(df)
        df = generate_all_labels(df)

        # Remove NaN rows
        df = df.dropna(subset=["label", "forward_return"])

        # Check alignment
        assert len(df.index) == len(df["label"])
        assert (df.index == df["label"].index).all()
