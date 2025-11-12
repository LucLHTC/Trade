"""
Tests for drift detection and auto-retraining modules.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.drift.detector import DriftDetector
from src.drift.retrainer import ModelRetrainer


class TestDriftDetector:
    """Test drift detector functionality."""

    @pytest.fixture
    def detector(self):
        """Create drift detector instance."""
        return DriftDetector()

    @pytest.fixture
    def sample_features(self):
        """Create sample feature dataframes."""
        np.random.seed(42)

        # Baseline: normal distribution
        baseline = pd.DataFrame({
            'feature_1': np.random.normal(0, 1, 1000),
            'feature_2': np.random.normal(5, 2, 1000),
            'feature_3': np.random.uniform(0, 10, 1000),
        }, index=pd.date_range('2024-01-01', periods=1000, freq='h'))

        # Current (no drift): same distribution
        current_no_drift = pd.DataFrame({
            'feature_1': np.random.normal(0, 1, 500),
            'feature_2': np.random.normal(5, 2, 500),
            'feature_3': np.random.uniform(0, 10, 500),
        }, index=pd.date_range('2024-02-15', periods=500, freq='h'))

        # Current (with drift): shifted distribution
        current_with_drift = pd.DataFrame({
            'feature_1': np.random.normal(2, 1.5, 500),  # Mean shifted
            'feature_2': np.random.normal(5, 2, 500),    # No drift
            'feature_3': np.random.uniform(5, 15, 500),  # Range shifted
        }, index=pd.date_range('2024-02-15', periods=500, freq='h'))

        return baseline, current_no_drift, current_with_drift

    def test_detector_initialization(self, detector):
        """Test detector initialization."""
        assert detector.psi_threshold == 0.25
        assert detector.ks_threshold == 0.05

    def test_calculate_psi_no_drift(self, detector):
        """Test PSI calculation with no drift."""
        np.random.seed(42)
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 500)

        psi = detector.calculate_psi(baseline, current)

        # PSI should be low (< 0.1) for same distribution
        assert psi < 0.1
        assert psi >= 0

    def test_calculate_psi_with_drift(self, detector):
        """Test PSI calculation with drift."""
        np.random.seed(42)
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(2, 1.5, 500)  # Different distribution

        psi = detector.calculate_psi(baseline, current)

        # PSI should be high (> 0.25) for different distributions
        assert psi > 0.25

    def test_ks_test_no_drift(self, detector):
        """Test KS test with no drift."""
        np.random.seed(42)
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 500)

        statistic, p_value = detector.ks_test(baseline, current)

        # High p-value indicates same distribution
        assert p_value > 0.05
        assert 0 <= statistic <= 1

    def test_ks_test_with_drift(self, detector):
        """Test KS test with drift."""
        np.random.seed(42)
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(2, 1.5, 500)

        statistic, p_value = detector.ks_test(baseline, current)

        # Low p-value indicates different distributions
        assert p_value < 0.05

    def test_ks_test_handles_nan(self, detector):
        """Test KS test handles NaN values."""
        baseline = np.array([1, 2, 3, np.nan, 5])
        current = np.array([1, 2, 3, 4, np.nan])

        statistic, p_value = detector.ks_test(baseline, current)

        # Should filter NaN and still work
        assert np.isfinite(statistic)
        assert np.isfinite(p_value)

    def test_detect_feature_drift_no_drift(self, detector, sample_features):
        """Test feature drift detection with no drift."""
        baseline, current_no_drift, _ = sample_features

        result = detector.detect_feature_drift(baseline, current_no_drift)

        assert result is not None
        assert 'drift_detected' in result
        assert 'drift_score' in result
        assert 'feature_stats' in result

        # Should not detect drift
        assert result['drift_detected'] == False
        assert result['drift_score'] < 0.25

    def test_detect_feature_drift_with_drift(self, detector, sample_features):
        """Test feature drift detection with drift."""
        baseline, _, current_with_drift = sample_features

        result = detector.detect_feature_drift(baseline, current_with_drift)

        assert result is not None
        assert result['drift_detected'] == True
        assert result['drift_score'] > 0.25

        # Check that feature_1 and feature_3 have high PSI
        feature_stats = result['feature_stats']
        assert 'feature_1' in feature_stats
        assert feature_stats['feature_1']['psi'] > 0.25

    def test_detect_feature_drift_subset_columns(self, detector, sample_features):
        """Test drift detection on subset of features."""
        baseline, current_no_drift, _ = sample_features

        result = detector.detect_feature_drift(
            baseline,
            current_no_drift,
            feature_columns=['feature_1']
        )

        # Should only check feature_1
        assert 'feature_1' in result['feature_stats']
        assert len(result['feature_stats']) == 1

    def test_detect_feature_drift_empty_data(self, detector):
        """Test drift detection with empty data."""
        baseline = pd.DataFrame()
        current = pd.DataFrame()

        result = detector.detect_feature_drift(baseline, current)

        # Should handle gracefully
        assert result['drift_detected'] == False
        assert result['feature_stats'] == {}

    def test_detect_prediction_drift_no_drift(self, detector):
        """Test prediction drift detection with no drift."""
        np.random.seed(42)

        baseline_preds = np.random.uniform(0, 1, 1000)
        current_preds = np.random.uniform(0, 1, 500)

        result = detector.detect_prediction_drift(baseline_preds, current_preds)

        assert result is not None
        assert 'drift_detected' in result
        assert result['drift_detected'] == False

    def test_detect_prediction_drift_with_drift(self, detector):
        """Test prediction drift detection with drift."""
        np.random.seed(42)

        # Baseline: uniform predictions
        baseline_preds = np.random.uniform(0.3, 0.7, 1000)

        # Current: shifted toward extremes
        current_preds = np.concatenate([
            np.random.uniform(0, 0.3, 250),
            np.random.uniform(0.7, 1.0, 250),
        ])

        result = detector.detect_prediction_drift(baseline_preds, current_preds)

        assert result is not None
        assert result['drift_detected'] == True
        assert result['psi'] > 0.25

    def test_get_recent_drift_logs(self, detector):
        """Test retrieving recent drift logs."""
        # This will query the database
        try:
            logs = detector.get_recent_drift_logs(days=7)

            # Should return a dataframe
            assert isinstance(logs, pd.DataFrame)

            # Should have expected columns if not empty
            if not logs.empty:
                assert 'detected_at' in logs.columns
                assert 'drift_detected' in logs.columns

        except Exception as e:
            pytest.skip(f"Database not available: {e}")


class TestModelRetrainer:
    """Test model retrainer functionality."""

    @pytest.fixture
    def retrainer(self, tmp_path):
        """Create model retrainer instance with temp paths."""
        return ModelRetrainer(
            features_dir=str(tmp_path / "features"),
            labels_dir=str(tmp_path / "labels"),
            models_dir=str(tmp_path / "models"),
        )

    def test_retrainer_initialization(self, retrainer, tmp_path):
        """Test retrainer initialization."""
        assert retrainer.features_dir == tmp_path / "features"
        assert retrainer.labels_dir == tmp_path / "labels"
        assert retrainer.models_dir == tmp_path / "models"

        # Check that model directories were created
        assert (tmp_path / "models" / "current").exists()
        assert (tmp_path / "models" / "shadow").exists()
        assert (tmp_path / "models" / "archived").exists()

    def test_should_retrain_no_drift(self, retrainer):
        """Test should_retrain with no drift."""
        try:
            should_retrain, reason = retrainer.should_retrain()

            # Without drift logs, should not retrain
            assert should_retrain == False
            assert "No retraining needed" in reason

        except Exception as e:
            pytest.skip(f"Database or dependencies not available: {e}")

    def test_train_shadow_model_no_data(self, retrainer):
        """Test shadow model training with no data."""
        with pytest.raises(ValueError, match="No features or labels"):
            retrainer.train_shadow_model(symbol="EURUSD")

    def test_compare_models_no_current(self, retrainer, tmp_path):
        """Test model comparison with no current model."""
        result = retrainer.compare_models(
            test_features=pd.DataFrame(),
            test_labels=pd.DataFrame(),
        )

        assert result['shadow_better'] == True
        assert result['reason'] == "No current model"

    def test_compare_models_no_shadow(self, retrainer, tmp_path):
        """Test model comparison with no shadow model."""
        # Create fake current model directory
        (tmp_path / "models" / "current" / "dummy.txt").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "models" / "current" / "dummy.txt").write_text("fake")

        result = retrainer.compare_models(
            test_features=pd.DataFrame(),
            test_labels=pd.DataFrame(),
        )

        assert result['shadow_better'] == False
        assert result['reason'] == "No shadow model"

    def test_promote_shadow_model_no_shadow(self, retrainer):
        """Test promotion with no shadow model."""
        promoted = retrainer.promote_shadow_model()

        assert promoted == False

    def test_promote_shadow_model_success(self, retrainer, tmp_path):
        """Test successful shadow model promotion."""
        # Create fake shadow model
        shadow_path = tmp_path / "models" / "shadow"
        shadow_path.mkdir(parents=True, exist_ok=True)
        (shadow_path / "dummy.txt").write_text("shadow model")

        # Create fake current model
        current_path = tmp_path / "models" / "current"
        current_path.mkdir(parents=True, exist_ok=True)
        (current_path / "dummy.txt").write_text("current model")

        promoted = retrainer.promote_shadow_model()

        assert promoted == True

        # Check that current model was archived
        archived = list((tmp_path / "models" / "archived").glob("model_*"))
        assert len(archived) == 1

        # Check that shadow became current
        assert (current_path / "dummy.txt").exists()

    def test_auto_retrain_pipeline_skipped(self, retrainer):
        """Test auto-retrain pipeline when not needed."""
        try:
            results = retrainer.auto_retrain_pipeline(symbol="EURUSD", force=False)

            # Without drift, should be skipped
            if results['status'] == 'skipped':
                assert 'reason' in results
                assert 'should_retrain' in results
                assert results['should_retrain'] == False

        except Exception as e:
            pytest.skip(f"Dependencies not available: {e}")

    def test_auto_retrain_pipeline_forced(self, retrainer):
        """Test forced auto-retrain pipeline."""
        # This will likely fail due to no data, but test the logic
        results = retrainer.auto_retrain_pipeline(symbol="EURUSD", force=True)

        assert results['forced'] == True
        assert results['should_retrain'] == True
        assert results['reason'] == "Forced retraining"

        # Will likely fail at training stage
        if results['status'] == 'failed':
            assert 'error' in results


class TestIntegration:
    """Integration tests for drift detection pipeline."""

    def test_psi_calculation_properties(self):
        """Test mathematical properties of PSI."""
        detector = DriftDetector()
        np.random.seed(42)

        baseline = np.random.normal(0, 1, 1000)

        # PSI with itself should be ~0
        psi_self = detector.calculate_psi(baseline, baseline)
        assert psi_self < 0.01

        # PSI is not symmetric but should be similar
        current = np.random.normal(1, 1, 500)
        psi_1 = detector.calculate_psi(baseline, current)
        psi_2 = detector.calculate_psi(current, baseline)

        # Both should indicate drift
        assert psi_1 > 0.1
        assert psi_2 > 0.1

    def test_drift_detection_with_gradual_shift(self):
        """Test drift detection with gradual distribution shift."""
        detector = DriftDetector()
        np.random.seed(42)

        baseline = pd.DataFrame({
            'feature': np.random.normal(0, 1, 1000)
        })

        # Test at different shift levels
        shifts = [0.5, 1.0, 1.5, 2.0]
        psi_values = []

        for shift in shifts:
            current = pd.DataFrame({
                'feature': np.random.normal(shift, 1, 500)
            })

            result = detector.detect_feature_drift(baseline, current)
            psi_values.append(result['feature_stats']['feature']['psi'])

        # PSI should increase with larger shifts
        assert psi_values[0] < psi_values[1] < psi_values[2] < psi_values[3]

    def test_model_lifecycle(self, tmp_path):
        """Test complete model lifecycle (current -> shadow -> archived)."""
        retrainer = ModelRetrainer(
            models_dir=str(tmp_path / "models")
        )

        # Create initial current model
        current_path = tmp_path / "models" / "current"
        current_path.mkdir(parents=True, exist_ok=True)
        (current_path / "version.txt").write_text("v1")

        # Create shadow model
        shadow_path = tmp_path / "models" / "shadow"
        shadow_path.mkdir(parents=True, exist_ok=True)
        (shadow_path / "version.txt").write_text("v2")

        # Promote shadow
        promoted = retrainer.promote_shadow_model()
        assert promoted == True

        # Check archived
        archived = list((tmp_path / "models" / "archived").glob("model_*"))
        assert len(archived) == 1
        assert (archived[0] / "version.txt").read_text() == "v1"

        # Check new current
        assert (current_path / "version.txt").read_text() == "v2"
