"""
Event-based features derived from macro economic calendar.
Creates features from upcoming and past macro events.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

from src.common.db import get_db
from src.common.logger import get_logger

logger = get_logger(__name__)


class EventFeatures:
    """Generate features from macro economic events."""

    def __init__(self):
        self.db = get_db()

    def get_events_dataframe(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch macro events from database as DataFrame.

        Args:
            start_date: Start date filter
            end_date: End date filter

        Returns:
            DataFrame with macro events
        """
        query = """
            SELECT
                timestamp,
                currency,
                impact,
                title,
                bullish,
                bearish,
                neutral
            FROM macro_events
            WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        query += " ORDER BY timestamp ASC"

        try:
            events = self.db.execute_query(query, tuple(params) if params else None, fetch=True)

            if not events:
                logger.warning("No events found in database")
                return pd.DataFrame()

            df = pd.DataFrame(events)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")

            logger.info(f"Loaded {len(df)} macro events from database")

            return df

        except Exception as e:
            logger.error(f"Failed to load events: {e}")
            return pd.DataFrame()

    def calculate_event_features(
        self,
        candles_df: pd.DataFrame,
        lookback_hours: int = 24,
        lookahead_hours: int = 6,
    ) -> pd.DataFrame:
        """
        Calculate event-based features for each candle timestamp.

        Args:
            candles_df: DataFrame with candle data (indexed by timestamp)
            lookback_hours: Hours to look back for recent events
            lookahead_hours: Hours to look ahead for upcoming events

        Returns:
            DataFrame with event features
        """
        if candles_df.empty:
            logger.warning("Empty candles dataframe provided")
            return candles_df

        logger.info("Calculating event-based features")

        # Get events within relevant time range
        start_date = candles_df.index.min() - timedelta(hours=lookback_hours)
        end_date = candles_df.index.max() + timedelta(hours=lookahead_hours)

        events_df = self.get_events_dataframe(start_date, end_date)

        if events_df.empty:
            logger.warning("No events available for feature calculation")
            # Return candles with zero event features
            return self._add_zero_event_features(candles_df)

        result = candles_df.copy()

        # Initialize event feature columns
        result["has_event_last_1h"] = 0
        result["has_event_last_3h"] = 0
        result["has_event_last_6h"] = 0
        result["has_event_last_24h"] = 0

        result["has_event_next_1h"] = 0
        result["has_event_next_3h"] = 0
        result["has_event_next_6h"] = 0

        result["high_impact_event_last_24h"] = 0
        result["high_impact_event_next_6h"] = 0

        result["eur_bullish_event_last_24h"] = 0
        result["eur_bearish_event_last_24h"] = 0
        result["usd_bullish_event_last_24h"] = 0
        result["usd_bearish_event_last_24h"] = 0

        result["eur_bullish_event_next_6h"] = 0
        result["eur_bearish_event_next_6h"] = 0

        result["event_count_last_24h"] = 0
        result["event_count_next_6h"] = 0

        result["days_to_next_ecb_event"] = np.nan
        result["days_to_next_fed_event"] = np.nan

        # For each candle, calculate event features
        for timestamp in result.index:
            # Past events (lookback)
            past_1h = events_df[
                (events_df.index < timestamp) &
                (events_df.index >= timestamp - timedelta(hours=1))
            ]
            past_3h = events_df[
                (events_df.index < timestamp) &
                (events_df.index >= timestamp - timedelta(hours=3))
            ]
            past_6h = events_df[
                (events_df.index < timestamp) &
                (events_df.index >= timestamp - timedelta(hours=6))
            ]
            past_24h = events_df[
                (events_df.index < timestamp) &
                (events_df.index >= timestamp - timedelta(hours=24))
            ]

            # Future events (lookahead)
            next_1h = events_df[
                (events_df.index >= timestamp) &
                (events_df.index < timestamp + timedelta(hours=1))
            ]
            next_3h = events_df[
                (events_df.index >= timestamp) &
                (events_df.index < timestamp + timedelta(hours=3))
            ]
            next_6h = events_df[
                (events_df.index >= timestamp) &
                (events_df.index < timestamp + timedelta(hours=6))
            ]

            # Event presence features
            result.loc[timestamp, "has_event_last_1h"] = int(len(past_1h) > 0)
            result.loc[timestamp, "has_event_last_3h"] = int(len(past_3h) > 0)
            result.loc[timestamp, "has_event_last_6h"] = int(len(past_6h) > 0)
            result.loc[timestamp, "has_event_last_24h"] = int(len(past_24h) > 0)

            result.loc[timestamp, "has_event_next_1h"] = int(len(next_1h) > 0)
            result.loc[timestamp, "has_event_next_3h"] = int(len(next_3h) > 0)
            result.loc[timestamp, "has_event_next_6h"] = int(len(next_6h) > 0)

            # High-impact event features
            result.loc[timestamp, "high_impact_event_last_24h"] = int(
                len(past_24h[past_24h["impact"] == "high"]) > 0
            )
            result.loc[timestamp, "high_impact_event_next_6h"] = int(
                len(next_6h[next_6h["impact"] == "high"]) > 0
            )

            # Currency-specific directional features (EUR/USD)
            # EUR events
            eur_past_24h = past_24h[past_24h["currency"] == "EUR"]
            result.loc[timestamp, "eur_bullish_event_last_24h"] = int(
                len(eur_past_24h[eur_past_24h["bullish"] == True]) > 0
            )
            result.loc[timestamp, "eur_bearish_event_last_24h"] = int(
                len(eur_past_24h[eur_past_24h["bearish"] == True]) > 0
            )

            # USD events (inverse for EUR/USD)
            usd_past_24h = past_24h[past_24h["currency"] == "USD"]
            result.loc[timestamp, "usd_bullish_event_last_24h"] = int(
                len(usd_past_24h[usd_past_24h["bullish"] == True]) > 0
            )
            result.loc[timestamp, "usd_bearish_event_last_24h"] = int(
                len(usd_past_24h[usd_past_24h["bearish"] == True]) > 0
            )

            # Future directional events
            eur_next_6h = next_6h[next_6h["currency"] == "EUR"]
            result.loc[timestamp, "eur_bullish_event_next_6h"] = int(
                len(eur_next_6h[eur_next_6h["bullish"] == True]) > 0
            )
            result.loc[timestamp, "eur_bearish_event_next_6h"] = int(
                len(eur_next_6h[eur_next_6h["bearish"] == True]) > 0
            )

            # Event counts
            result.loc[timestamp, "event_count_last_24h"] = len(past_24h)
            result.loc[timestamp, "event_count_next_6h"] = len(next_6h)

            # Days to next major central bank event
            ecb_events = events_df[
                (events_df.index >= timestamp) &
                (events_df["title"].str.contains("ECB", case=False, na=False))
            ]
            if len(ecb_events) > 0:
                next_ecb = ecb_events.index[0]
                result.loc[timestamp, "days_to_next_ecb_event"] = (
                    next_ecb - timestamp
                ).total_seconds() / 86400

            fed_events = events_df[
                (events_df.index >= timestamp) &
                (events_df["title"].str.contains("Fed|FOMC", case=False, na=False))
            ]
            if len(fed_events) > 0:
                next_fed = fed_events.index[0]
                result.loc[timestamp, "days_to_next_fed_event"] = (
                    next_fed - timestamp
                ).total_seconds() / 86400

        # Forward fill NaN values for countdown features
        result["days_to_next_ecb_event"] = result["days_to_next_ecb_event"].fillna(30)
        result["days_to_next_fed_event"] = result["days_to_next_fed_event"].fillna(30)

        logger.info(f"✅ Calculated {len([c for c in result.columns if 'event' in c or 'days_to' in c])} event features")

        return result

    def _add_zero_event_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add event feature columns with zero values when no events available."""
        result = df.copy()

        event_features = [
            "has_event_last_1h",
            "has_event_last_3h",
            "has_event_last_6h",
            "has_event_last_24h",
            "has_event_next_1h",
            "has_event_next_3h",
            "has_event_next_6h",
            "high_impact_event_last_24h",
            "high_impact_event_next_6h",
            "eur_bullish_event_last_24h",
            "eur_bearish_event_last_24h",
            "usd_bullish_event_last_24h",
            "usd_bearish_event_last_24h",
            "eur_bullish_event_next_6h",
            "eur_bearish_event_next_6h",
            "event_count_last_24h",
            "event_count_next_6h",
            "days_to_next_ecb_event",
            "days_to_next_fed_event",
        ]

        for feature in event_features:
            if "days_to" in feature:
                result[feature] = 30.0  # Default 30 days
            else:
                result[feature] = 0

        return result
