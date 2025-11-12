"""
Pytest configuration and fixtures for testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_settings


@pytest.fixture(scope="session")
def settings():
    """Provide settings for tests."""
    return get_settings()


@pytest.fixture(scope="session")
def api_base_url(settings):
    """Provide API base URL for tests."""
    return settings.api_base_url
