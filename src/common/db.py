"""
Database connection and management utilities.
Provides connection pooling and helper functions for database operations.
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import time

from src.common.config import get_settings
from src.common.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(self):
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None
        self._initialize_pool()

    def _initialize_pool(self, max_retries: int = 5, retry_delay: int = 2):
        """Initialize connection pool with retry logic."""
        for attempt in range(max_retries):
            try:
                self.connection_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    database=settings.postgres_db,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                )
                logger.info("Database connection pool initialized successfully")
                return
            except Exception as e:
                logger.error(
                    f"Failed to initialize connection pool (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def execute_query(
        self, query: str, params: Optional[tuple] = None, fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query and optionally fetch results.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch and return results

        Returns:
            List of dictionaries if fetch=True, None otherwise
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return [dict(row) for row in cursor.fetchall()]
                return None

    def health_check(self) -> bool:
        """
        Perform a simple health check on the database connection.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            result = self.execute_query("SELECT 1 as health", fetch=True)
            return result[0]["health"] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def insert_one(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a single row into a table.

        Args:
            table: Table name
            data: Dictionary of column names and values

        Returns:
            ID of inserted row if available
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["%s"] * len(values))

        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({placeholders})
            RETURNING id
        """

        try:
            result = self.execute_query(query, tuple(values), fetch=True)
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Failed to insert into {table}: {e}")
            raise

    def insert_many(self, table: str, data: List[Dict[str, Any]]) -> int:
        """
        Insert multiple rows into a table.

        Args:
            table: Table name
            data: List of dictionaries with column names and values

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        columns = list(data[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))

        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                rows_inserted = 0
                for row in data:
                    values = tuple(row[col] for col in columns)
                    cursor.execute(query, values)
                    rows_inserted += cursor.rowcount

                logger.info(f"Inserted {rows_inserted} rows into {table}")
                return rows_inserted

    def close(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def close_db():
    """Close the global database manager instance."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
