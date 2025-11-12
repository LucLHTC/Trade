"""
Technical indicator calculations for trading signals.
Generates 100+ technical features from OHLCV data.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional
from datetime import datetime

from src.common.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data."""

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for a given OHLCV dataframe.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index must be datetime

        Returns:
            DataFrame with original data plus all technical indicators
        """
        if df.empty:
            logger.warning("Empty dataframe provided to calculate_all")
            return df

        logger.info(f"Calculating technical indicators for {len(df)} candles")

        # Create a copy to avoid modifying original
        result = df.copy()

        # Ensure required columns exist
        required_cols = ["open", "high", "low", "close"]
        missing = [col for col in required_cols if col not in result.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # 1. RSI (Relative Strength Index)
        result["rsi_14"] = ta.rsi(result["close"], length=14)
        result["rsi_7"] = ta.rsi(result["close"], length=7)
        result["rsi_21"] = ta.rsi(result["close"], length=21)

        # 2. MACD (Moving Average Convergence Divergence)
        macd = ta.macd(result["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            result["macd"] = macd[f"MACD_12_26_9"]
            result["macd_signal"] = macd[f"MACDs_12_26_9"]
            result["macd_histogram"] = macd[f"MACDh_12_26_9"]

        # 3. EMA (Exponential Moving Average)
        result["ema_9"] = ta.ema(result["close"], length=9)
        result["ema_21"] = ta.ema(result["close"], length=21)
        result["ema_50"] = ta.ema(result["close"], length=50)
        result["ema_100"] = ta.ema(result["close"], length=100)
        result["ema_200"] = ta.ema(result["close"], length=200)

        # 4. SMA (Simple Moving Average)
        result["sma_20"] = ta.sma(result["close"], length=20)
        result["sma_50"] = ta.sma(result["close"], length=50)
        result["sma_200"] = ta.sma(result["close"], length=200)

        # 5. Bollinger Bands
        bbands = ta.bbands(result["close"], length=20, std=2)
        if bbands is not None:
            result["bb_upper"] = bbands[f"BBU_20_2.0"]
            result["bb_middle"] = bbands[f"BBM_20_2.0"]
            result["bb_lower"] = bbands[f"BBL_20_2.0"]
            result["bb_bandwidth"] = bbands[f"BBB_20_2.0"]
            result["bb_percent"] = bbands[f"BBP_20_2.0"]

        # 6. ATR (Average True Range)
        result["atr_14"] = ta.atr(result["high"], result["low"], result["close"], length=14)
        result["atr_7"] = ta.atr(result["high"], result["low"], result["close"], length=7)

        # 7. Stochastic Oscillator
        stoch = ta.stoch(result["high"], result["low"], result["close"], k=14, d=3, smooth_k=3)
        if stoch is not None:
            result["stoch_k"] = stoch[f"STOCHk_14_3_3"]
            result["stoch_d"] = stoch[f"STOCHd_14_3_3"]

        # 8. ADX (Average Directional Index)
        adx = ta.adx(result["high"], result["low"], result["close"], length=14)
        if adx is not None:
            result["adx"] = adx[f"ADX_14"]
            result["di_plus"] = adx[f"DMP_14"]
            result["di_minus"] = adx[f"DMN_14"]

        # 9. CCI (Commodity Channel Index)
        result["cci_20"] = ta.cci(result["high"], result["low"], result["close"], length=20)

        # 10. ROC (Rate of Change)
        result["roc_10"] = ta.roc(result["close"], length=10)
        result["roc_20"] = ta.roc(result["close"], length=20)

        # 11. MFI (Money Flow Index) - requires volume
        if "volume" in result.columns and result["volume"].sum() > 0:
            result["mfi_14"] = ta.mfi(
                result["high"], result["low"], result["close"], result["volume"], length=14
            )

        # 12. OBV (On-Balance Volume)
        if "volume" in result.columns:
            result["obv"] = ta.obv(result["close"], result["volume"])

        # 13. VWAP (Volume Weighted Average Price)
        if "volume" in result.columns and result["volume"].sum() > 0:
            result["vwap"] = ta.vwap(
                result["high"], result["low"], result["close"], result["volume"]
            )

        # 14. Donchian Channels
        donchian = ta.donchian(result["high"], result["low"], lower_length=20, upper_length=20)
        if donchian is not None:
            result["donchian_upper"] = donchian[f"DCU_20_20"]
            result["donchian_middle"] = donchian[f"DCM_20_20"]
            result["donchian_lower"] = donchian[f"DCL_20_20"]

        # 15. Keltner Channels
        kc = ta.kc(result["high"], result["low"], result["close"], length=20, scalar=2)
        if kc is not None:
            result["kc_upper"] = kc[f"KCUe_20_2"]
            result["kc_middle"] = kc[f"KCBe_20_2"]
            result["kc_lower"] = kc[f"KCLe_20_2"]

        # 16. Parabolic SAR
        result["psar"] = ta.psar(result["high"], result["low"], result["close"])["PSARl_0.02_0.2"]

        # 17. Ichimoku Cloud
        ichimoku = ta.ichimoku(result["high"], result["low"], result["close"])
        if ichimoku is not None and len(ichimoku) > 0:
            result["ichimoku_conv"] = ichimoku[0][f"ICS_9"]
            result["ichimoku_base"] = ichimoku[0][f"IKS_26"]
            result["ichimoku_span_a"] = ichimoku[0][f"ISA_9"]
            result["ichimoku_span_b"] = ichimoku[0][f"ISB_26"]

        logger.info(f"Calculated {len(result.columns) - len(df.columns)} technical indicators")

        return result

    @staticmethod
    def calculate_derived_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate derived features from technical indicators.

        These are engineered features based on relationships between indicators.

        Args:
            df: DataFrame with technical indicators already calculated

        Returns:
            DataFrame with additional derived features
        """
        result = df.copy()

        # EMA crossovers
        if "ema_9" in result.columns and "ema_21" in result.columns:
            result["ema_cross_9_21"] = (result["ema_9"] > result["ema_21"]).astype(int)
            result["ema_distance_9_21"] = (result["ema_9"] - result["ema_21"]) / result["close"]

        if "ema_21" in result.columns and "ema_50" in result.columns:
            result["ema_cross_21_50"] = (result["ema_21"] > result["ema_50"]).astype(int)

        if "ema_50" in result.columns and "ema_200" in result.columns:
            result["ema_cross_50_200"] = (result["ema_50"] > result["ema_200"]).astype(int)

        # MACD signals
        if "macd" in result.columns and "macd_signal" in result.columns:
            result["macd_above_signal"] = (result["macd"] > result["macd_signal"]).astype(int)
            result["macd_signal_distance"] = result["macd"] - result["macd_signal"]

        # Price vs EMAs
        if "ema_21" in result.columns:
            result["price_vs_ema21"] = (result["close"] - result["ema_21"]) / result["close"]

        if "ema_50" in result.columns:
            result["price_vs_ema50"] = (result["close"] - result["ema_50"]) / result["close"]

        if "ema_200" in result.columns:
            result["price_vs_ema200"] = (result["close"] - result["ema_200"]) / result["close"]

        # Price vs Bollinger Bands
        if all(col in result.columns for col in ["bb_upper", "bb_lower", "close"]):
            bb_range = result["bb_upper"] - result["bb_lower"]
            result["price_bb_position"] = np.where(
                bb_range > 0,
                (result["close"] - result["bb_lower"]) / bb_range,
                0.5,
            )

        # RSI conditions
        if "rsi_14" in result.columns:
            result["rsi_oversold"] = (result["rsi_14"] < 30).astype(int)
            result["rsi_overbought"] = (result["rsi_14"] > 70).astype(int)
            result["rsi_neutral"] = (
                (result["rsi_14"] >= 40) & (result["rsi_14"] <= 60)
            ).astype(int)

        # Stochastic conditions
        if "stoch_k" in result.columns:
            result["stoch_oversold"] = (result["stoch_k"] < 20).astype(int)
            result["stoch_overbought"] = (result["stoch_k"] > 80).astype(int)

        # ATR spike detection
        if "atr_14" in result.columns:
            atr_mean = result["atr_14"].rolling(50).mean()
            atr_std = result["atr_14"].rolling(50).std()
            result["atr_spike"] = (result["atr_14"] > atr_mean + 2 * atr_std).astype(int)

        # Volatility metrics
        result["returns"] = result["close"].pct_change()
        result["log_returns"] = np.log(result["close"] / result["close"].shift(1))
        result["volatility_10"] = result["returns"].rolling(10).std()
        result["volatility_20"] = result["returns"].rolling(20).std()
        result["volatility_50"] = result["returns"].rolling(50).std()

        # Candle size metrics
        result["candle_size"] = abs(result["close"] - result["open"]) / result["open"]
        result["candle_range"] = (result["high"] - result["low"]) / result["open"]
        result["upper_wick"] = (result["high"] - result[["open", "close"]].max(axis=1)) / result["open"]
        result["lower_wick"] = (result[["open", "close"]].min(axis=1) - result["low"]) / result["open"]

        # Z-score of candle size
        candle_size_mean = result["candle_size"].rolling(50).mean()
        candle_size_std = result["candle_size"].rolling(50).std()
        result["candle_size_zscore"] = np.where(
            candle_size_std > 0,
            (result["candle_size"] - candle_size_mean) / candle_size_std,
            0,
        )

        # Momentum indicators
        result["momentum_10"] = result["close"] - result["close"].shift(10)
        result["momentum_20"] = result["close"] - result["close"].shift(20)

        # Price acceleration
        result["price_accel"] = result["returns"] - result["returns"].shift(1)

        # Trend strength (ADX-based)
        if "adx" in result.columns:
            result["strong_trend"] = (result["adx"] > 25).astype(int)
            result["weak_trend"] = (result["adx"] < 20).astype(int)

        # DI cross
        if "di_plus" in result.columns and "di_minus" in result.columns:
            result["di_cross"] = (result["di_plus"] > result["di_minus"]).astype(int)

        # Volume features (if available)
        if "volume" in result.columns and result["volume"].sum() > 0:
            result["volume_sma_20"] = result["volume"].rolling(20).mean()
            result["volume_ratio"] = result["volume"] / result["volume_sma_20"]
            result["volume_spike"] = (result["volume"] > result["volume_sma_20"] * 2).astype(int)

        logger.info(f"Calculated {len(result.columns) - len(df.columns)} derived features")

        return result

    @staticmethod
    def calculate_price_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate price pattern features (candlestick patterns, etc.).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with pattern features
        """
        result = df.copy()

        # Basic candlestick patterns using pandas-ta
        patterns = ta.cdl_pattern(
            result["open"], result["high"], result["low"], result["close"]
        )

        if patterns is not None:
            # Select most important patterns
            pattern_cols = [
                "CDL_DOJI",
                "CDL_ENGULFING",
                "CDL_HAMMER",
                "CDL_HANGINGMAN",
                "CDL_MORNINGSTAR",
                "CDL_EVENINGSTAR",
            ]

            for col in pattern_cols:
                if col in patterns.columns:
                    result[col.lower()] = patterns[col]

        # Higher highs and lower lows
        result["higher_high"] = (
            result["high"] > result["high"].shift(1)
        ).astype(int)
        result["lower_low"] = (
            result["low"] < result["low"].shift(1)
        ).astype(int)

        # Support/Resistance touches
        rolling_high = result["high"].rolling(50).max()
        rolling_low = result["low"].rolling(50).min()

        result["near_resistance"] = (
            (result["close"] > rolling_high * 0.995)
        ).astype(int)
        result["near_support"] = (
            (result["close"] < rolling_low * 1.005)
        ).astype(int)

        logger.info(f"Calculated {len(result.columns) - len(df.columns)} price pattern features")

        return result


def calculate_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical features for given OHLCV data.

    This is the main entry point for feature calculation.

    Args:
        df: DataFrame with OHLCV data (index = timestamp)

    Returns:
        DataFrame with all technical features
    """
    logger.info("Starting complete feature calculation pipeline")

    # Step 1: Technical indicators
    df = TechnicalIndicators.calculate_all(df)

    # Step 2: Derived features
    df = TechnicalIndicators.calculate_derived_features(df)

    # Step 3: Price patterns
    df = TechnicalIndicators.calculate_price_patterns(df)

    total_features = len([col for col in df.columns if col not in ["open", "high", "low", "close", "volume", "symbol", "interval"]])

    logger.info(f"✅ Feature calculation complete: {total_features} total features")

    return df
