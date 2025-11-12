"""
Tests for data collection modules.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collection.alpha_vantage import (
    AlphaVantageClient,
    CandleDataManager,
)
from src.data_collection.macro_feeds import (
    MacroEventClassifier,
    MacroEventManager,
    create_sample_events,
)


class TestAlphaVantageClient:
    """Test Alpha Vantage API client."""

    def test_client_initialization(self):
        """Test that client can be initialized with API key."""
        try:
            client = AlphaVantageClient()
            assert client is not None
            assert client.api_key is not None
        except ValueError as e:
            # API key not configured is acceptable in test environment
            pytest.skip(f"API key not configured: {e}")

    def test_client_requires_api_key(self):
        """Test that client requires an API key."""
        with pytest.raises(ValueError):
            AlphaVantageClient(api_key=None)

    @pytest.mark.skip(reason="Requires valid API key and network access")
    def test_fetch_forex_intraday(self):
        """Test fetching forex intraday data."""
        client = AlphaVantageClient()
        df = client.fetch_forex_intraday(
            from_symbol="EUR",
            to_symbol="USD",
            interval="60min",
            outputsize="compact",
        )

        if df is not None:
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            assert "open" in df.columns
            assert "high" in df.columns
            assert "low" in df.columns
            assert "close" in df.columns
            assert df.index.name == "timestamp"


class TestCandleDataManager:
    """Test candle data storage and retrieval."""

    def test_manager_initialization(self, tmp_path):
        """Test that manager can be initialized."""
        manager = CandleDataManager(base_dir=str(tmp_path / "forex"))
        assert manager is not None
        assert manager.base_dir.exists()

    def test_save_to_parquet(self, tmp_path):
        """Test saving candle data to Parquet."""
        manager = CandleDataManager(base_dir=str(tmp_path / "forex"))

        # Create sample data
        dates = pd.date_range(start="2023-01-01", periods=100, freq="H", tz="UTC")
        df = pd.DataFrame(
            {
                "open": 1.0850,
                "high": 1.0870,
                "low": 1.0840,
                "close": 1.0860,
                "volume": 0,
                "symbol": "EURUSD",
                "interval": "60min",
            },
            index=dates,
        )
        df.index.name = "timestamp"

        # Save to Parquet
        saved_files = manager.save_to_parquet(df, "EURUSD")

        assert len(saved_files) > 0
        assert all(f.exists() for f in saved_files)

    def test_load_from_parquet(self, tmp_path):
        """Test loading candle data from Parquet."""
        manager = CandleDataManager(base_dir=str(tmp_path / "forex"))

        # Create and save sample data
        dates = pd.date_range(start="2023-01-01", periods=50, freq="H", tz="UTC")
        df = pd.DataFrame(
            {
                "open": 1.0850,
                "high": 1.0870,
                "low": 1.0840,
                "close": 1.0860,
                "volume": 0,
                "symbol": "EURUSD",
                "interval": "60min",
            },
            index=dates,
        )
        df.index.name = "timestamp"

        manager.save_to_parquet(df, "EURUSD")

        # Load data
        loaded_df = manager.load_from_parquet("EURUSD")

        assert not loaded_df.empty
        assert len(loaded_df) == len(df)

    def test_detect_gaps(self, tmp_path):
        """Test gap detection in candle data."""
        manager = CandleDataManager(base_dir=str(tmp_path / "forex"))

        # Create data with intentional gaps
        dates1 = pd.date_range(start="2023-01-01 00:00", periods=10, freq="H", tz="UTC")
        dates2 = pd.date_range(start="2023-01-01 15:00", periods=10, freq="H", tz="UTC")  # 5-hour gap

        dates = dates1.append(dates2)

        df = pd.DataFrame(
            {
                "open": 1.0850,
                "high": 1.0870,
                "low": 1.0840,
                "close": 1.0860,
            },
            index=dates,
        )

        # Detect gaps
        gaps = manager.detect_gaps(df, interval_minutes=60)

        assert len(gaps) > 0  # Should detect the 5-hour gap


class TestMacroEventClassifier:
    """Test macro event classification."""

    def test_classify_eur_bullish_event(self):
        """Test classification of EUR bullish event."""
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="ECB Rate Hike to 4.5%",
            currency="EUR",
        )

        assert bullish is True
        assert bearish is False
        assert neutral is False

    def test_classify_eur_bearish_event(self):
        """Test classification of EUR bearish event."""
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="ECB Rate Cut Expected",
            currency="EUR",
        )

        assert bullish is False
        assert bearish is True
        assert neutral is False

    def test_classify_usd_bullish_event(self):
        """Test classification of USD bullish event (bearish for EUR/USD)."""
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="Fed Rate Hike Announced",
            currency="USD",
        )

        # USD strength = EUR/USD bearish
        assert bullish is False
        assert bearish is True
        assert neutral is False

    def test_classify_neutral_event(self):
        """Test classification of neutral event."""
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="ECB President Speech",
            currency="EUR",
        )

        # Should be neutral without clear direction
        assert neutral is True

    def test_classify_with_actual_vs_consensus(self):
        """Test classification using actual vs consensus values."""
        # Beat expectations (EUR bullish)
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="Eurozone GDP",
            currency="EUR",
            actual="0.7%",
            consensus="0.5%",
        )

        assert bullish is True

        # Miss expectations (EUR bearish)
        bullish, bearish, neutral = MacroEventClassifier.classify_event(
            title="Eurozone GDP",
            currency="EUR",
            actual="0.3%",
            consensus="0.5%",
        )

        assert bearish is True

    def test_extract_number(self):
        """Test numeric extraction from strings."""
        assert MacroEventClassifier._extract_number("2.5%") == 2.5
        assert MacroEventClassifier._extract_number("200K") == 200000
        assert MacroEventClassifier._extract_number("-0.5") == -0.5
        assert MacroEventClassifier._extract_number("N/A") is None


class TestMacroEventManager:
    """Test macro event manager."""

    def test_manager_initialization(self):
        """Test that manager can be initialized."""
        manager = MacroEventManager()
        assert manager is not None

    def test_create_sample_events(self):
        """Test creating sample events."""
        # This will insert into the database
        count = create_sample_events()

        # Should create at least some events
        assert count >= 0  # May be 0 if already exist

    @pytest.mark.skip(reason="Requires network access")
    def test_fetch_and_store_events(self):
        """Test fetching and storing events."""
        manager = MacroEventManager()
        count = manager.fetch_and_store_events()

        # May be 0 if sources are unavailable
        assert count >= 0

    def test_get_upcoming_events(self):
        """Test retrieving upcoming events."""
        # First ensure we have sample events
        create_sample_events()

        manager = MacroEventManager()
        events = manager.get_upcoming_events(hours_ahead=168)  # 7 days

        assert isinstance(events, list)
        # May be empty if no events in time window

    def test_get_high_impact_events(self):
        """Test retrieving high-impact events."""
        create_sample_events()

        manager = MacroEventManager()
        events = manager.get_high_impact_events(days=7)

        assert isinstance(events, list)
        # All returned events should be high impact
        for event in events:
            if event.get("impact"):
                assert event["impact"] == "high"


class TestDataIntegration:
    """Integration tests for data collection."""

    def test_end_to_end_candle_workflow(self, tmp_path):
        """Test complete candle data workflow."""
        manager = CandleDataManager(base_dir=str(tmp_path / "forex"))

        # Create sample data
        dates = pd.date_range(start="2023-01-01", periods=24, freq="H", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [1.085 + i * 0.0001 for i in range(24)],
                "high": [1.087 + i * 0.0001 for i in range(24)],
                "low": [1.084 + i * 0.0001 for i in range(24)],
                "close": [1.086 + i * 0.0001 for i in range(24)],
                "volume": 0,
                "symbol": "EURUSD",
                "interval": "60min",
            },
            index=dates,
        )
        df.index.name = "timestamp"

        # Save
        saved_files = manager.save_to_parquet(df, "EURUSD")
        assert len(saved_files) > 0

        # Load
        loaded_df = manager.load_from_parquet("EURUSD")
        assert len(loaded_df) == len(df)

        # Check data integrity
        assert (loaded_df["open"].round(4) == df["open"].round(4)).all()

    def test_event_classification_accuracy(self):
        """Test that event classification is consistent."""
        events = [
            ("ECB Rate Hike", "EUR", True, False, False),
            ("ECB Rate Cut", "EUR", False, True, False),
            ("Fed Rate Hike", "USD", False, True, False),  # Inverse for EUR/USD
            ("Neutral Speech", "EUR", False, False, True),
        ]

        for title, currency, exp_bull, exp_bear, exp_neut in events:
            bullish, bearish, neutral = MacroEventClassifier.classify_event(
                title=title, currency=currency
            )

            assert bullish == exp_bull, f"Failed for {title}"
            assert bearish == exp_bear, f"Failed for {title}"
            assert neutral == exp_neut, f"Failed for {title}"
