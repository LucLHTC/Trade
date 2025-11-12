"""
Health check tests for API and database.
"""

import pytest
from httpx import AsyncClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app
from src.common.db import get_db


class TestAPIHealth:
    """Test API health endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns correct response."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "online"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        # Accept both 200 (healthy) and 503 (degraded/unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "api" in data
        assert "database" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_ping_endpoint(self):
        """Test ping endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/ping")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_status_endpoint(self):
        """Test detailed status endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert "api" in data
        assert "database" in data
        assert "configuration" in data
        assert "timestamp" in data


class TestDatabaseHealth:
    """Test database connectivity and health."""

    def test_database_connection(self):
        """Test that database connection can be established."""
        db = get_db()
        assert db is not None
        assert db.connection_pool is not None

    def test_database_health_check(self):
        """Test database health check query."""
        db = get_db()
        result = db.health_check()
        assert isinstance(result, bool)

    def test_database_query_execution(self):
        """Test that we can execute a simple query."""
        db = get_db()
        result = db.execute_query("SELECT 1 as test", fetch=True)
        assert result is not None
        assert len(result) == 1
        assert result[0]["test"] == 1

    def test_database_tables_exist(self):
        """Test that expected tables exist in the database."""
        db = get_db()

        expected_tables = [
            "raw_candles",
            "macro_events",
            "features",
            "labels",
            "trades",
            "drift_log",
            "system_health",
        ]

        for table in expected_tables:
            query = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                );
            """
            result = db.execute_query(query, fetch=True)
            assert result[0]["exists"] is True, f"Table {table} does not exist"


class TestConfiguration:
    """Test configuration loading."""

    def test_settings_loaded(self, settings):
        """Test that settings are loaded correctly."""
        assert settings is not None
        assert settings.postgres_host is not None
        assert settings.postgres_port > 0
        assert settings.postgres_db is not None

    def test_database_url_construction(self, settings):
        """Test that database URL is constructed correctly."""
        db_url = settings.database_url
        assert "postgresql://" in db_url
        assert settings.postgres_user in db_url
        assert settings.postgres_host in db_url

    def test_trading_configuration(self, settings):
        """Test trading configuration values."""
        assert settings.initial_equity > 0
        assert 0 < settings.risk_per_trade < 1
        assert settings.max_trades_per_week > 0

    def test_model_configuration(self, settings):
        """Test model configuration values."""
        assert settings.training_window_days > 0
        assert settings.validation_window_days > 0
        assert settings.drift_psi_threshold > 0
        assert settings.drift_ks_pvalue > 0
