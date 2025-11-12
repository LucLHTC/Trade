"""
Market regime classification for trading signals.
Classifies market conditions as bullish, bearish, sideways, or volatile.
"""

import pandas as pd
import numpy as np
from typing import Literal

from src.common.logger import get_logger

logger = get_logger(__name__)


RegimeType = Literal["bullish", "bearish", "sideways", "volatile"]


class RegimeClassifier:
    """Classify market regimes based on technical indicators."""

    @staticmethod
    def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify market regime for each timestamp.

        Uses a combination of:
        - Trend direction (EMAs)
        - Trend strength (ADX)
        - Volatility (ATR)

        Args:
            df: DataFrame with technical indicators

        Returns:
            DataFrame with regime column added
        """
        if df.empty:
            logger.warning("Empty dataframe provided to classify_regime")
            return df

        logger.info(f"Classifying market regimes for {len(df)} candles")

        result = df.copy()

        # Initialize regime column
        result["regime"] = "unknown"

        # Required indicators
        if "ema_50" not in result.columns or "ema_200" not in result.columns:
            logger.warning("Missing EMAs for regime classification, calculating them")
            import pandas_ta as ta

            if "ema_50" not in result.columns:
                result["ema_50"] = ta.ema(result["close"], length=50)
            if "ema_200" not in result.columns:
                result["ema_200"] = ta.ema(result["close"], length=200)

        if "adx" not in result.columns:
            logger.warning("Missing ADX for regime classification, calculating it")
            import pandas_ta as ta

            adx_result = ta.adx(result["high"], result["low"], result["close"], length=14)
            if adx_result is not None:
                result["adx"] = adx_result["ADX_14"]

        if "atr_14" not in result.columns:
            logger.warning("Missing ATR for regime classification, calculating it")
            import pandas_ta as ta

            result["atr_14"] = ta.atr(result["high"], result["low"], result["close"], length=14)

        # Calculate trend direction
        result["uptrend"] = result["ema_50"] > result["ema_200"]
        result["downtrend"] = result["ema_50"] < result["ema_200"]

        # Calculate volatility level
        if "atr_14" in result.columns:
            atr_percentile = result["atr_14"].rolling(100).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0.5
            )
            result["high_volatility"] = atr_percentile > 0.75
        else:
            result["high_volatility"] = False

        # Calculate trend strength
        if "adx" in result.columns:
            result["strong_trend"] = result["adx"] > 25
            result["weak_trend"] = result["adx"] < 20
        else:
            result["strong_trend"] = False
            result["weak_trend"] = True

        # Classify regimes
        for idx in result.index:
            uptrend = result.loc[idx, "uptrend"]
            downtrend = result.loc[idx, "downtrend"]
            strong_trend = result.loc[idx, "strong_trend"]
            weak_trend = result.loc[idx, "weak_trend"]
            high_vol = result.loc[idx, "high_volatility"]

            # Volatile regime (high volatility regardless of trend)
            if high_vol:
                result.loc[idx, "regime"] = "volatile"

            # Sideways regime (weak trend)
            elif weak_trend:
                result.loc[idx, "regime"] = "sideways"

            # Bullish regime (uptrend + strong trend)
            elif uptrend and strong_trend:
                result.loc[idx, "regime"] = "bullish"

            # Bearish regime (downtrend + strong trend)
            elif downtrend and strong_trend:
                result.loc[idx, "regime"] = "bearish"

            # Default to sideways
            else:
                result.loc[idx, "regime"] = "sideways"

        # Clean up temporary columns
        result = result.drop(columns=["uptrend", "downtrend", "high_volatility", "strong_trend", "weak_trend"])

        # Log regime distribution
        regime_counts = result["regime"].value_counts()
        logger.info(f"Regime distribution: {regime_counts.to_dict()}")

        return result

    @staticmethod
    def get_regime_metrics(df: pd.DataFrame) -> dict:
        """
        Get statistics about regime distribution.

        Args:
            df: DataFrame with regime column

        Returns:
            Dictionary with regime statistics
        """
        if "regime" not in df.columns:
            return {}

        total = len(df)
        regime_counts = df["regime"].value_counts()

        metrics = {
            "total_periods": total,
            "bullish_count": regime_counts.get("bullish", 0),
            "bearish_count": regime_counts.get("bearish", 0),
            "sideways_count": regime_counts.get("sideways", 0),
            "volatile_count": regime_counts.get("volatile", 0),
            "bullish_pct": regime_counts.get("bullish", 0) / total * 100 if total > 0 else 0,
            "bearish_pct": regime_counts.get("bearish", 0) / total * 100 if total > 0 else 0,
            "sideways_pct": regime_counts.get("sideways", 0) / total * 100 if total > 0 else 0,
            "volatile_pct": regime_counts.get("volatile", 0) / total * 100 if total > 0 else 0,
        }

        return metrics
