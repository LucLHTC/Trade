"""
Macro economic events scraper from RSS feeds and APIs.
Parses events, classifies them, and stores in database.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pytz
import re

from src.common.config import get_settings
from src.common.logger import get_logger
from src.common.db import get_db

settings = get_settings()
logger = get_logger(__name__)


class MacroEventClassifier:
    """Classifies macro events as bullish/bearish/neutral for EUR/USD."""

    # Events that are typically EUR bullish (bearish for USD)
    EUR_BULLISH_KEYWORDS = [
        "ecb rate", "rate hike", "rate increase",
        "gdp growth", "gdp beats", "gdp higher",
        "employment rises", "employment up", "jobs beat",
        "inflation rises", "cpi up", "ppi up",
        "pmi beats", "manufacturing up", "services up",
        "retail sales beat", "consumer confidence up",
        "trade surplus", "export growth"
    ]

    # Events that are typically EUR bearish (bullish for USD)
    EUR_BEARISH_KEYWORDS = [
        "rate cut", "rate decrease", "dovish",
        "gdp miss", "gdp lower", "recession",
        "employment falls", "unemployment up", "jobs miss",
        "inflation falls", "deflation",
        "pmi miss", "manufacturing down", "contraction",
        "retail sales miss", "consumer confidence down",
        "trade deficit"
    ]

    # USD-specific events (inverse relationship with EUR/USD)
    USD_BULLISH_KEYWORDS = [
        "fed rate hike", "hawkish fed", "dollar strength",
        "us jobs beat", "nonfarm payrolls beat", "unemployment down",
        "us gdp beat", "us inflation up"
    ]

    USD_BEARISH_KEYWORDS = [
        "fed rate cut", "dovish fed", "dollar weakness",
        "us jobs miss", "nonfarm payrolls miss",
        "us gdp miss", "us recession"
    ]

    @classmethod
    def classify_event(
        cls,
        title: str,
        currency: str,
        actual: Optional[str] = None,
        consensus: Optional[str] = None,
        previous: Optional[str] = None,
    ) -> Tuple[bool, bool, bool]:
        """
        Classify an event as bullish/bearish/neutral for EUR/USD.

        Args:
            title: Event title/description
            currency: Currency code (EUR, USD, etc.)
            actual: Actual value reported
            consensus: Consensus forecast
            previous: Previous value

        Returns:
            Tuple of (bullish, bearish, neutral) booleans
        """
        title_lower = title.lower()

        # Start as neutral
        bullish = False
        bearish = False
        neutral = True

        # EUR events
        if currency == "EUR":
            # Check bullish keywords
            if any(keyword in title_lower for keyword in cls.EUR_BULLISH_KEYWORDS):
                bullish = True
                neutral = False

            # Check bearish keywords
            elif any(keyword in title_lower for keyword in cls.EUR_BEARISH_KEYWORDS):
                bearish = True
                neutral = False

        # USD events (inverse for EUR/USD)
        elif currency == "USD":
            # USD strength = EUR/USD bearish
            if any(keyword in title_lower for keyword in cls.USD_BULLISH_KEYWORDS):
                bearish = True  # Inverse!
                neutral = False

            # USD weakness = EUR/USD bullish
            elif any(keyword in title_lower for keyword in cls.USD_BEARISH_KEYWORDS):
                bullish = True  # Inverse!
                neutral = False

        # Try to infer from actual vs consensus
        if actual and consensus and not bullish and not bearish:
            try:
                # Extract numeric values
                actual_val = cls._extract_number(actual)
                consensus_val = cls._extract_number(consensus)

                if actual_val is not None and consensus_val is not None:
                    # Beat expectations
                    if actual_val > consensus_val:
                        if currency == "EUR":
                            bullish = True
                            neutral = False
                        elif currency == "USD":
                            bearish = True  # Inverse
                            neutral = False

                    # Miss expectations
                    elif actual_val < consensus_val:
                        if currency == "EUR":
                            bearish = True
                            neutral = False
                        elif currency == "USD":
                            bullish = True  # Inverse
                            neutral = False

            except Exception as e:
                logger.debug(f"Could not compare actual vs consensus: {e}")

        return bullish, bearish, neutral

    @staticmethod
    def _extract_number(value: str) -> Optional[float]:
        """Extract numeric value from string (e.g., '2.5%' -> 2.5)."""
        if not value:
            return None

        # Remove common suffixes
        value = value.replace("%", "").replace("K", "000").replace("M", "000000")
        value = re.sub(r"[^\d.-]", "", value)

        try:
            return float(value)
        except ValueError:
            return None


class ForexFactoryScraper:
    """Scraper for ForexFactory economic calendar."""

    BASE_URL = "https://www.forexfactory.com"
    CALENDAR_URL = f"{BASE_URL}/calendar"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        })

    def fetch_events(self, days_ahead: int = 7) -> List[Dict]:
        """
        Fetch economic events from ForexFactory.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of event dictionaries
        """
        logger.info(f"Fetching ForexFactory events for next {days_ahead} days")

        try:
            # ForexFactory calendar
            response = self.session.get(self.CALENDAR_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Parse calendar table
            # Note: This is a simplified parser. ForexFactory structure may change.
            events = []

            # Find all event rows
            rows = soup.find_all("tr", class_=re.compile("calendar__row"))

            for row in rows[:20]:  # Limit to 20 events for MVP
                try:
                    # Extract event details
                    title_elem = row.find("td", class_="calendar__event")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # Extract currency
                    currency_elem = row.find("td", class_="calendar__currency")
                    currency = currency_elem.get_text(strip=True) if currency_elem else "N/A"

                    # Extract impact
                    impact_elem = row.find("td", class_="calendar__impact")
                    impact = "medium"  # Default
                    if impact_elem:
                        impact_spans = impact_elem.find_all("span", class_="calendar__impact-icon")
                        if len(impact_spans) == 3:
                            impact = "high"
                        elif len(impact_spans) == 2:
                            impact = "medium"
                        else:
                            impact = "low"

                    # Extract actual, forecast, previous
                    actual_elem = row.find("td", class_="calendar__actual")
                    forecast_elem = row.find("td", class_="calendar__forecast")
                    previous_elem = row.find("td", class_="calendar__previous")

                    actual = actual_elem.get_text(strip=True) if actual_elem else None
                    consensus = forecast_elem.get_text(strip=True) if forecast_elem else None
                    previous = previous_elem.get_text(strip=True) if previous_elem else None

                    # For MVP, use current time + offset as timestamp
                    # In production, parse actual date/time from ForexFactory
                    timestamp = datetime.utcnow() + timedelta(hours=len(events))

                    event = {
                        "title": title,
                        "currency": currency,
                        "impact": impact,
                        "actual": actual,
                        "consensus": consensus,
                        "previous": previous,
                        "timestamp": timestamp,
                        "source": "ForexFactory",
                    }

                    events.append(event)

                except Exception as e:
                    logger.debug(f"Failed to parse event row: {e}")
                    continue

            logger.info(f"Parsed {len(events)} events from ForexFactory")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch ForexFactory events: {e}")
            return []


class TradingEconomicsScraper:
    """Scraper for TradingEconomics RSS feed."""

    RSS_URL = "https://tradingeconomics.com/rss/calendar.aspx"

    def fetch_events(self) -> List[Dict]:
        """
        Fetch events from TradingEconomics RSS feed.

        Returns:
            List of event dictionaries
        """
        logger.info("Fetching TradingEconomics RSS feed")

        try:
            feed = feedparser.parse(self.RSS_URL)

            events = []

            for entry in feed.entries[:30]:  # Limit to 30 events
                try:
                    title = entry.get("title", "")
                    description = entry.get("description", "")
                    published = entry.get("published_parsed")

                    # Parse timestamp
                    if published:
                        timestamp = datetime(*published[:6], tzinfo=pytz.UTC)
                    else:
                        timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC)

                    # Extract currency from title or description
                    # Simple heuristic: look for currency codes
                    currency = "N/A"
                    for curr in ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD"]:
                        if curr in title.upper() or curr in description.upper():
                            currency = curr
                            break

                    # Determine impact (simplified)
                    impact = "medium"
                    if any(word in title.lower() for word in ["gdp", "employment", "rate", "cpi", "ppi", "nfp"]):
                        impact = "high"
                    elif any(word in title.lower() for word in ["minutes", "speech", "testimony"]):
                        impact = "medium"
                    else:
                        impact = "low"

                    event = {
                        "title": title,
                        "currency": currency,
                        "impact": impact,
                        "actual": None,
                        "consensus": None,
                        "previous": None,
                        "timestamp": timestamp,
                        "source": "TradingEconomics",
                    }

                    events.append(event)

                except Exception as e:
                    logger.debug(f"Failed to parse RSS entry: {e}")
                    continue

            logger.info(f"Parsed {len(events)} events from TradingEconomics")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch TradingEconomics RSS: {e}")
            return []


class MacroEventManager:
    """Manages macro economic events storage and retrieval."""

    def __init__(self):
        self.db = get_db()
        self.classifier = MacroEventClassifier()
        logger.info("Macro event manager initialized")

    def fetch_and_store_events(self) -> int:
        """
        Fetch events from all sources and store in database.

        Returns:
            Number of events stored
        """
        logger.info("Fetching macro events from all sources")

        all_events = []

        # Fetch from ForexFactory
        try:
            ff_scraper = ForexFactoryScraper()
            ff_events = ff_scraper.fetch_events()
            all_events.extend(ff_events)
        except Exception as e:
            logger.error(f"ForexFactory fetch failed: {e}")

        # Fetch from TradingEconomics
        try:
            te_scraper = TradingEconomicsScraper()
            te_events = te_scraper.fetch_events()
            all_events.extend(te_events)
        except Exception as e:
            logger.error(f"TradingEconomics fetch failed: {e}")

        if not all_events:
            logger.warning("No events fetched from any source")
            return 0

        # Classify and store events
        stored_count = 0

        for event in all_events:
            try:
                # Classify event
                bullish, bearish, neutral = self.classifier.classify_event(
                    title=event["title"],
                    currency=event["currency"],
                    actual=event.get("actual"),
                    consensus=event.get("consensus"),
                    previous=event.get("previous"),
                )

                # Prepare record
                record = {
                    "timestamp": event["timestamp"],
                    "currency": event["currency"],
                    "impact": event["impact"],
                    "title": event["title"],
                    "previous_value": event.get("previous"),
                    "consensus_value": event.get("consensus"),
                    "actual_value": event.get("actual"),
                    "bullish": bullish,
                    "bearish": bearish,
                    "neutral": neutral,
                    "source": event.get("source", "Unknown"),
                }

                # Insert into database (with conflict handling)
                try:
                    self.db.insert_one("macro_events", record)
                    stored_count += 1
                except Exception as e:
                    # Duplicate key error is expected
                    logger.debug(f"Event already exists or insert failed: {e}")

            except Exception as e:
                logger.error(f"Failed to store event: {e}")
                continue

        logger.info(f"✅ Stored {stored_count} macro events")
        return stored_count

    def get_upcoming_events(self, hours_ahead: int = 24) -> List[Dict]:
        """
        Get upcoming macro events within specified time window.

        Args:
            hours_ahead: Number of hours to look ahead

        Returns:
            List of upcoming events
        """
        query = """
            SELECT *
            FROM macro_events
            WHERE timestamp >= NOW()
            AND timestamp <= NOW() + INTERVAL '%s hours'
            ORDER BY timestamp ASC
        """

        try:
            events = self.db.execute_query(query, (hours_ahead,), fetch=True)
            logger.info(f"Found {len(events)} upcoming events in next {hours_ahead}h")
            return events
        except Exception as e:
            logger.error(f"Failed to query upcoming events: {e}")
            return []

    def get_high_impact_events(self, days: int = 7) -> List[Dict]:
        """
        Get high-impact events for the next N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of high-impact events
        """
        query = """
            SELECT *
            FROM macro_events
            WHERE impact = 'high'
            AND timestamp >= NOW()
            AND timestamp <= NOW() + INTERVAL '%s days'
            ORDER BY timestamp ASC
        """

        try:
            events = self.db.execute_query(query, (days,), fetch=True)
            logger.info(f"Found {len(events)} high-impact events in next {days} days")
            return events
        except Exception as e:
            logger.error(f"Failed to query high-impact events: {e}")
            return []


def create_sample_events():
    """Create sample macro events for testing (MVP)."""
    logger.info("Creating sample macro events for testing")

    db = get_db()
    classifier = MacroEventClassifier()

    sample_events = [
        {
            "title": "ECB Interest Rate Decision",
            "currency": "EUR",
            "impact": "high",
            "previous": "4.50%",
            "consensus": "4.50%",
            "actual": "4.75%",
            "timestamp": datetime.utcnow() + timedelta(days=1),
        },
        {
            "title": "US Non-Farm Payrolls",
            "currency": "USD",
            "impact": "high",
            "previous": "200K",
            "consensus": "210K",
            "actual": "225K",
            "timestamp": datetime.utcnow() + timedelta(days=2),
        },
        {
            "title": "Eurozone GDP Growth Rate",
            "currency": "EUR",
            "impact": "high",
            "previous": "0.5%",
            "consensus": "0.6%",
            "actual": "0.7%",
            "timestamp": datetime.utcnow() + timedelta(days=3),
        },
        {
            "title": "US CPI Inflation Rate",
            "currency": "USD",
            "impact": "high",
            "previous": "3.2%",
            "consensus": "3.1%",
            "actual": "3.4%",
            "timestamp": datetime.utcnow() + timedelta(days=4),
        },
        {
            "title": "ECB President Lagarde Speech",
            "currency": "EUR",
            "impact": "medium",
            "previous": None,
            "consensus": None,
            "actual": None,
            "timestamp": datetime.utcnow() + timedelta(days=5),
        },
    ]

    stored = 0
    for event in sample_events:
        bullish, bearish, neutral = classifier.classify_event(
            title=event["title"],
            currency=event["currency"],
            actual=event.get("actual"),
            consensus=event.get("consensus"),
            previous=event.get("previous"),
        )

        record = {
            "timestamp": event["timestamp"],
            "currency": event["currency"],
            "impact": event["impact"],
            "title": event["title"],
            "previous_value": event.get("previous"),
            "consensus_value": event.get("consensus"),
            "actual_value": event.get("actual"),
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "source": "Sample",
        }

        try:
            db.insert_one("macro_events", record)
            stored += 1
            logger.info(f"  ✓ {event['title']} - Bull:{bullish} Bear:{bearish} Neut:{neutral}")
        except Exception as e:
            logger.debug(f"Sample event insert failed (may already exist): {e}")

    logger.info(f"✅ Created {stored} sample events")
    return stored
