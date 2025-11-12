"""
Drift detection module with PSI and KS tests.
Monitors feature and prediction distributions for model degradation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from scipy import stats
import json

from src.common.logger import get_logger
from src.common.db import get_connection

logger = get_logger(__name__)


class DriftDetector:
    """Detect data and prediction drift using statistical tests."""

    def __init__(
        self,
        psi_threshold: float = 0.25,
        ks_pvalue_threshold: float = 0.05,
    ):
        """
        Initialize drift detector.

        Args:
            psi_threshold: PSI threshold for drift detection (default: 0.25)
            ks_pvalue_threshold: KS test p-value threshold (default: 0.05)
        """
        self.psi_threshold = psi_threshold
        self.ks_pvalue_threshold = ks_pvalue_threshold
        
        logger.info(
            f"DriftDetector initialized: PSI<{psi_threshold}, "
            f"KS p-value<{ks_pvalue_threshold}"
        )

    @staticmethod
    def calculate_psi(
        baseline: np.ndarray,
        current: np.ndarray,
        bins: int = 10,
    ) -> float:
        """
        Calculate Population Stability Index (PSI).

        Formula: PSI = sum((current% - baseline%) * ln(current% / baseline%))

        Args:
            baseline: Baseline distribution
            current: Current distribution
            bins: Number of bins for discretization

        Returns:
            PSI score
        """
        # Remove NaN and inf
        baseline = baseline[np.isfinite(baseline)]
        current = current[np.isfinite(current)]

        if len(baseline) == 0 or len(current) == 0:
            logger.warning("Empty distributions for PSI calculation")
            return 0.0

        # Create bins based on baseline
        try:
            breakpoints = np.quantile(baseline, np.linspace(0, 1, bins + 1))
            breakpoints = np.unique(breakpoints)  # Remove duplicates
        except Exception as e:
            logger.error(f"Failed to create bins: {e}")
            return 0.0

        # Calculate proportions
        baseline_counts = np.histogram(baseline, bins=breakpoints)[0]
        current_counts = np.histogram(current, bins=breakpoints)[0]

        # Add small epsilon to avoid division by zero
        epsilon = 1e-10
        baseline_pct = (baseline_counts + epsilon) / (len(baseline) + epsilon * len(breakpoints))
        current_pct = (current_counts + epsilon) / (len(current) + epsilon * len(breakpoints))

        # Calculate PSI
        psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))

        return float(psi)

    @staticmethod
    def ks_test(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Perform Kolmogorov-Smirnov test.

        Args:
            baseline: Baseline distribution
            current: Current distribution

        Returns:
            Tuple of (statistic, p_value)
        """
        # Remove NaN and inf
        baseline = baseline[np.isfinite(baseline)]
        current = current[np.isfinite(current)]

        if len(baseline) == 0 or len(current) == 0:
            logger.warning("Empty distributions for KS test")
            return 0.0, 1.0

        statistic, p_value = stats.ks_2samp(baseline, current)

        return float(statistic), float(p_value)

    def detect_feature_drift(
        self,
        baseline_features: pd.DataFrame,
        current_features: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect drift in feature distributions.

        Args:
            baseline_features: Baseline feature DataFrame
            current_features: Current feature DataFrame
            feature_columns: Columns to check (all numeric if None)

        Returns:
            Dictionary with drift results
        """
        logger.info("Detecting feature drift...")

        if feature_columns is None:
            # Use all numeric columns
            feature_columns = baseline_features.select_dtypes(
                include=[np.number]
            ).columns.tolist()

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "n_features": len(feature_columns),
            "features": {},
            "drift_detected": False,
            "drift_score": 0.0,
        }

        drift_features = []

        for feature in feature_columns:
            if feature not in current_features.columns:
                continue

            baseline_values = baseline_features[feature].values
            current_values = current_features[feature].values

            # Calculate PSI
            psi = self.calculate_psi(baseline_values, current_values)

            # Perform KS test
            ks_stat, ks_pvalue = self.ks_test(baseline_values, current_values)

            # Determine if drift detected
            drift = psi > self.psi_threshold or ks_pvalue < self.ks_pvalue_threshold

            results["features"][feature] = {
                "psi": psi,
                "ks_statistic": ks_stat,
                "ks_pvalue": ks_pvalue,
                "drift": drift,
            }

            if drift:
                drift_features.append(feature)

        # Overall drift detection
        if drift_features:
            results["drift_detected"] = True
            results["drift_features"] = drift_features
            results["drift_score"] = len(drift_features) / len(feature_columns)

            logger.warning(
                f"⚠️  Feature drift detected in {len(drift_features)}/{len(feature_columns)} features: "
                f"{drift_features[:5]}"
            )
        else:
            logger.info("✅ No feature drift detected")

        return results

    def detect_prediction_drift(
        self,
        baseline_predictions: np.ndarray,
        current_predictions: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Detect drift in prediction distributions.

        Args:
            baseline_predictions: Baseline predictions
            current_predictions: Current predictions

        Returns:
            Dictionary with drift results
        """
        logger.info("Detecting prediction drift...")

        # PSI for predictions
        psi = self.calculate_psi(baseline_predictions, current_predictions)

        # KS test for predictions
        ks_stat, ks_pvalue = self.ks_test(baseline_predictions, current_predictions)

        # Drift detection
        drift = psi > self.psi_threshold or ks_pvalue < self.ks_pvalue_threshold

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "psi": psi,
            "ks_statistic": ks_stat,
            "ks_pvalue": ks_pvalue,
            "drift_detected": drift,
            "psi_threshold": self.psi_threshold,
            "ks_threshold": self.ks_pvalue_threshold,
        }

        if drift:
            logger.warning(
                f"⚠️  Prediction drift detected: PSI={psi:.3f}, KS p-value={ks_pvalue:.4f}"
            )
        else:
            logger.info("✅ No prediction drift detected")

        return results

    def save_drift_log(
        self,
        drift_results: Dict[str, Any],
        drift_type: str = "feature",
    ) -> None:
        """
        Save drift detection results to database.

        Args:
            drift_results: Drift detection results
            drift_type: Type of drift (feature, prediction, performance)
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO drift_log (
                            drift_type,
                            drift_detected,
                            drift_score,
                            psi_score,
                            ks_pvalue,
                            details
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            drift_type,
                            drift_results.get("drift_detected", False),
                            drift_results.get("drift_score", 0.0),
                            drift_results.get("psi", 0.0),
                            drift_results.get("ks_pvalue", 1.0),
                            json.dumps(drift_results),
                        ),
                    )
                    conn.commit()

                    logger.info(f"Drift log saved: {drift_type}")

        except Exception as e:
            logger.error(f"Failed to save drift log: {e}")

    def get_recent_drift_logs(self, days: int = 30) -> pd.DataFrame:
        """
        Get recent drift logs from database.

        Args:
            days: Number of days to retrieve

        Returns:
            DataFrame with drift logs
        """
        try:
            with get_connection() as conn:
                query = """
                    SELECT
                        log_id,
                        detected_at,
                        drift_type,
                        drift_detected,
                        drift_score,
                        psi_score,
                        ks_pvalue
                    FROM drift_log
                    WHERE detected_at >= NOW() - INTERVAL '%s days'
                    ORDER BY detected_at DESC
                """

                df = pd.read_sql_query(query, conn, params=(days,))

                return df

        except Exception as e:
            logger.error(f"Failed to get drift logs: {e}")
            return pd.DataFrame()
