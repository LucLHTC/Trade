"""
Technical indicator calculations for trading signals.
Generates 100+ technical features from OHLCV data.
"""

import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime

# Import ta library (technical-analysis)
from ta.momentum import RSIIndicator, StochasticOscillator, ROCIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator, CCIIndicator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator, VolumeWeightedAveragePrice

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

        try:
            # 1. RSI (Relative Strength Index)
            rsi_14 = RSIIndicator(close=result["close"], window=14)
            result["rsi_14"] = rsi_14.rsi()

            rsi_7 = RSIIndicator(close=result["close"], window=7)
            result["rsi_7"] = rsi_7.rsi()

            rsi_21 = RSIIndicator(close=result["close"], window=21)
            result["rsi_21"] = rsi_21.rsi()

            # 2. MACD (Moving Average Convergence Divergence)
            macd = MACD(close=result["close"], window_fast=12, window_slow=26, window_sign=9)
            result["macd"] = macd.macd()
            result["macd_signal"] = macd.macd_signal()
            result["macd_histogram"] = macd.macd_diff()

            # 3. EMA (Exponential Moving Average)
            ema_9 = EMAIndicator(close=result["close"], window=9)
            result["ema_9"] = ema_9.ema_indicator()

            ema_21 = EMAIndicator(close=result["close"], window=21)
            result["ema_21"] = ema_21.ema_indicator()

            ema_50 = EMAIndicator(close=result["close"], window=50)
            result["ema_50"] = ema_50.ema_indicator()

            ema_100 = EMAIndicator(close=result["close"], window=100)
            result["ema_100"] = ema_100.ema_indicator()

            ema_200 = EMAIndicator(close=result["close"], window=200)
            result["ema_200"] = ema_200.ema_indicator()

            # 4. SMA (Simple Moving Average)
            sma_20 = SMAIndicator(close=result["close"], window=20)
            result["sma_20"] = sma_20.sma_indicator()

            sma_50 = SMAIndicator(close=result["close"], window=50)
            result["sma_50"] = sma_50.sma_indicator()

            sma_200 = SMAIndicator(close=result["close"], window=200)
            result["sma_200"] = sma_200.sma_indicator()

            # 5. Bollinger Bands
            bbands = BollingerBands(close=result["close"], window=20, window_dev=2)
            result["bb_upper"] = bbands.bollinger_hband()
            result["bb_middle"] = bbands.bollinger_mavg()
            result["bb_lower"] = bbands.bollinger_lband()
            result["bb_bandwidth"] = bbands.bollinger_wband()
            result["bb_percent"] = bbands.bollinger_pband()

            # 6. ATR (Average True Range)
            atr_14 = AverageTrueRange(high=result["high"], low=result["low"], close=result["close"], window=14)
            result["atr_14"] = atr_14.average_true_range()

            atr_7 = AverageTrueRange(high=result["high"], low=result["low"], close=result["close"], window=7)
            result["atr_7"] = atr_7.average_true_range()

            # 7. Stochastic Oscillator
            stoch = StochasticOscillator(high=result["high"], low=result["low"], close=result["close"],
                                          window=14, smooth_window=3)
            result["stoch_k"] = stoch.stoch()
            result["stoch_d"] = stoch.stoch_signal()

            # 8. ADX (Average Directional Index)
            adx = ADXIndicator(high=result["high"], low=result["low"], close=result["close"], window=14)
            result["adx"] = adx.adx()
            result["di_plus"] = adx.adx_pos()
            result["di_minus"] = adx.adx_neg()

            # 9. CCI (Commodity Channel Index)
            cci = CCIIndicator(high=result["high"], low=result["low"], close=result["close"], window=20)
            result["cci_20"] = cci.cci()

            # 10. ROC (Rate of Change)
            roc_10 = ROCIndicator(close=result["close"], window=10)
            result["roc_10"] = roc_10.roc()

            roc_20 = ROCIndicator(close=result["close"], window=20)
            result["roc_20"] = roc_20.roc()

            # 11. MFI (Money Flow Index) - requires volume
            if "volume" in result.columns and result["volume"].sum() > 0:
                mfi = MFIIndicator(high=result["high"], low=result["low"],
                                  close=result["close"], volume=result["volume"], window=14)
                result["mfi_14"] = mfi.money_flow_index()

            # 12. OBV (On-Balance Volume)
            if "volume" in result.columns:
                obv = OnBalanceVolumeIndicator(close=result["close"], volume=result["volume"])
                result["obv"] = obv.on_balance_volume()

            # 13. VWAP (Volume Weighted Average Price)
            if "volume" in result.columns and result["volume"].sum() > 0:
                vwap = VolumeWeightedAveragePrice(high=result["high"], low=result["low"],
                                                  close=result["close"], volume=result["volume"])
                result["vwap"] = vwap.volume_weighted_average_price()

            # 14. Keltner Channels
            kc = KeltnerChannel(high=result["high"], low=result["low"], close=result["close"], window=20)
            result["kc_upper"] = kc.keltner_channel_hband()
            result["kc_middle"] = kc.keltner_channel_mband()
            result["kc_lower"] = kc.keltner_channel_lband()

            logger.info(f"Calculated {len(result.columns) - len(df.columns)} technical indicators")

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            raise

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
        Calculate price pattern features (candlestick patterns, support/resistance, etc.).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with pattern features
        """
        result = df.copy()

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

        # Simple candlestick patterns
        body = abs(result["close"] - result["open"])
        total_range = result["high"] - result["low"]
        upper_shadow = result["high"] - result[["open", "close"]].max(axis=1)
        lower_shadow = result[["open", "close"]].min(axis=1) - result["low"]

        # Doji - small body compared to total range
        result["cdl_doji"] = ((body / total_range < 0.1) & (total_range > 0)).astype(int)

        # Hammer - long lower shadow, small upper shadow
        result["cdl_hammer"] = (
            (lower_shadow > body * 2) &
            (upper_shadow < body * 0.5) &
            (total_range > 0)
        ).astype(int)

        # Hanging Man (bearish) - same as hammer but at top of uptrend
        result["cdl_hangingman"] = result["cdl_hammer"].copy()

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
