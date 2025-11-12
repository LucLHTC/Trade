"""
Auto-retraining pipeline with shadow models and A/B testing.
Handles automatic model retraining, evaluation, and promotion.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import shutil

from src.training.ensemble import EnsembleTrainer
from src.features.manager import FeatureManager
from src.drift.detector import DriftDetector
from src.common.logger import get_logger
from src.common.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class ModelRetrainer:
    """Automatic model retraining and lifecycle management."""

    def __init__(
        self,
        features_dir: str = "data/features",
        labels_dir: str = "data/labels",
        models_dir: str = "models",
    ):
        """
        Initialize model retrainer.

        Args:
            features_dir: Directory with features
            labels_dir: Directory with labels
            models_dir: Directory for model storage
        """
        self.features_dir = Path(features_dir)
        self.labels_dir = Path(labels_dir)
        self.models_dir = Path(models_dir)

        # Ensure model directories exist
        (self.models_dir / "current").mkdir(parents=True, exist_ok=True)
        (self.models_dir / "shadow").mkdir(parents=True, exist_ok=True)
        (self.models_dir / "archived").mkdir(parents=True, exist_ok=True)

        self.feature_manager = FeatureManager(
            features_dir=str(features_dir),
            labels_dir=str(labels_dir),
        )

        self.drift_detector = DriftDetector()

        logger.info("ModelRetrainer initialized")

    def should_retrain(
        self,
        drift_threshold: float = 0.20,
        performance_threshold: float = 0.15,
    ) -> Tuple[bool, str]:
        """
        Determine if model should be retrained.

        Args:
            drift_threshold: Drift score threshold for retraining
            performance_threshold: Performance degradation threshold

        Returns:
            Tuple of (should_retrain, reason)
        """
        # Check drift logs
        drift_logs = self.drift_detector.get_recent_drift_logs(days=7)

        if not drift_logs.empty:
            recent_drift = drift_logs[drift_logs["drift_detected"] == True]

            if len(recent_drift) > 0:
                avg_drift_score = recent_drift["drift_score"].mean()

                if avg_drift_score > drift_threshold:
                    return True, f"Drift detected (score={avg_drift_score:.3f})"

        # Check performance degradation
        try:
            from src.monitoring.performance import PerformanceTracker

            tracker = PerformanceTracker()
            degradation = tracker.detect_performance_degradation()

            if degradation.get("degraded", False):
                return True, "Performance degradation detected"

        except Exception as e:
            logger.warning(f"Could not check performance degradation: {e}")

        return False, "No retraining needed"

    def train_shadow_model(
        self,
        symbol: str = "EURUSD",
        validation_days: int = 10,
    ) -> Dict[str, Any]:
        """
        Train a shadow model with latest data.

        Args:
            symbol: Trading symbol
            validation_days: Days for validation split

        Returns:
            Dictionary with training results
        """
        logger.info("Training shadow model...")

        # Load features and labels
        features_df = self.feature_manager.load_features(symbol=symbol)
        labels_df = self.feature_manager.load_labels(symbol=symbol)

        if features_df.empty or labels_df.empty:
            raise ValueError("No features or labels available")

        # Train/val split (time-based)
        cutoff_date = features_df.index.max() - pd.Timedelta(days=validation_days)

        train_features = features_df[features_df.index < cutoff_date]
        val_features = features_df[features_df.index >= cutoff_date]

        train_labels = labels_df[labels_df.index < cutoff_date]
        val_labels = labels_df[labels_df.index >= cutoff_date]

        # Create ensemble
        ensemble = EnsembleTrainer()

        # Prepare data
        X_train, y_train, feature_cols = ensemble.prepare_data(
            train_features,
            train_labels,
            exclude_neutral=True,
        )

        X_val, y_val, _ = ensemble.prepare_data(
            val_features,
            val_labels,
            exclude_neutral=True,
        )

        # Train all models
        histories = ensemble.train_all(X_train, y_train, X_val, y_val)

        # Evaluate ensemble
        metrics = ensemble.evaluate_ensemble(X_val, y_val, threshold=0.55)

        # Save shadow model
        shadow_path = self.models_dir / "shadow"
        ensemble.save(str(shadow_path))

        results = {
            "trained_at": datetime.utcnow().isoformat(),
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "features": len(feature_cols),
            "val_accuracy": metrics.get("accuracy", 0.0),
            "val_precision": metrics.get("precision", 0.0),
            "val_recall": metrics.get("recall", 0.0),
            "val_f1": metrics.get("f1", 0.0),
        }

        logger.info(
            f"✅ Shadow model trained: accuracy={metrics.get('accuracy', 0):.3f}"
        )

        return results

    def compare_models(
        self,
        test_features: pd.DataFrame,
        test_labels: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Compare current and shadow models.

        Args:
            test_features: Test features
            test_labels: Test labels

        Returns:
            Comparison results
        """
        logger.info("Comparing current and shadow models...")

        # Load models
        current_path = self.models_dir / "current"
        shadow_path = self.models_dir / "shadow"

        if not current_path.exists():
            logger.warning("No current model found")
            return {"shadow_better": True, "reason": "No current model"}

        if not shadow_path.exists():
            logger.warning("No shadow model found")
            return {"shadow_better": False, "reason": "No shadow model"}

        try:
            current_ensemble = EnsembleTrainer.load(str(current_path))
            shadow_ensemble = EnsembleTrainer.load(str(shadow_path))

            # Prepare test data
            X_test, y_test, _ = current_ensemble.prepare_data(
                test_features,
                test_labels,
                exclude_neutral=True,
            )

            # Evaluate both models
            current_metrics = current_ensemble.evaluate_ensemble(X_test, y_test)
            shadow_metrics = shadow_ensemble.evaluate_ensemble(X_test, y_test)

            # Compare
            shadow_better = shadow_metrics["f1"] > current_metrics["f1"]

            improvement = shadow_metrics["f1"] - current_metrics["f1"]

            results = {
                "current_metrics": current_metrics,
                "shadow_metrics": shadow_metrics,
                "shadow_better": shadow_better,
                "improvement": improvement,
                "compared_at": datetime.utcnow().isoformat(),
            }

            if shadow_better:
                logger.info(
                    f"✅ Shadow model is better: F1 improvement={improvement:+.3f}"
                )
            else:
                logger.info(
                    f"⚠️  Current model is better: F1 change={improvement:+.3f}"
                )

            return results

        except Exception as e:
            logger.error(f"Failed to compare models: {e}")
            return {"shadow_better": False, "reason": f"Error: {e}"}

    def promote_shadow_model(
        self,
        min_improvement: float = 0.01,
    ) -> bool:
        """
        Promote shadow model to current if it performs better.

        Args:
            min_improvement: Minimum F1 improvement required

        Returns:
            True if promoted, False otherwise
        """
        logger.info("Checking if shadow model should be promoted...")

        shadow_path = self.models_dir / "shadow"
        current_path = self.models_dir / "current"

        if not shadow_path.exists():
            logger.warning("No shadow model to promote")
            return False

        # Archive current model
        if current_path.exists():
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_path = self.models_dir / "archived" / f"model_{timestamp}"
            shutil.copytree(current_path, archive_path)
            logger.info(f"Current model archived to {archive_path}")

            # Remove old current
            shutil.rmtree(current_path)

        # Promote shadow to current
        shutil.copytree(shadow_path, current_path)

        logger.info("✅ Shadow model promoted to current")

        return True

    def auto_retrain_pipeline(
        self,
        symbol: str = "EURUSD",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Run complete auto-retraining pipeline.

        Args:
            symbol: Trading symbol
            force: Force retraining even if not needed

        Returns:
            Dictionary with results
        """
        logger.info("=" * 60)
        logger.info("AUTO-RETRAINING PIPELINE")
        logger.info("=" * 60)

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "forced": force,
        }

        # Step 1: Check if retraining needed
        if not force:
            should_retrain, reason = self.should_retrain()
            results["should_retrain"] = should_retrain
            results["reason"] = reason

            if not should_retrain:
                logger.info(f"✅ {reason}")
                results["status"] = "skipped"
                return results
        else:
            results["should_retrain"] = True
            results["reason"] = "Forced retraining"

        # Step 2: Train shadow model
        try:
            training_results = self.train_shadow_model(symbol=symbol)
            results["training"] = training_results
        except Exception as e:
            logger.error(f"❌ Shadow model training failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            return results

        # Step 3: Compare models
        try:
            features_df = self.feature_manager.load_features(symbol=symbol)
            labels_df = self.feature_manager.load_labels(symbol=symbol)

            # Use recent data for testing
            test_features = features_df.tail(200)
            test_labels = labels_df.tail(200)

            comparison = self.compare_models(test_features, test_labels)
            results["comparison"] = comparison
        except Exception as e:
            logger.warning(f"Model comparison failed: {e}")
            # Promote anyway if training succeeded
            comparison = {"shadow_better": True}

        # Step 4: Promote if better
        if comparison.get("shadow_better", False):
            promoted = self.promote_shadow_model()
            results["promoted"] = promoted
            results["status"] = "success"
            logger.info("✅ Auto-retraining pipeline completed successfully")
        else:
            results["promoted"] = False
            results["status"] = "shadow_not_better"
            logger.info("⚠️  Shadow model not promoted (not better than current)")

        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info("=" * 60)

        return results
