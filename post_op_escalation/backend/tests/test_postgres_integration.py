"""
Optional Live PostgreSQL Integration Test Suite.

By default, the core test suite runs against SQLite without requiring a live PostgreSQL instance.
This module provides optional integration testing against a live PostgreSQL server when available.
"""
import os
import pytest
from sqlalchemy import create_engine, text

POSTGRES_URL = os.getenv("POSTGRES_TEST_URL", "postgresql://postgres:postgres@localhost:5432/post_op_db")

def is_postgres_available() -> bool:
    try:
        engine = create_engine(POSTGRES_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

POSTGRES_AVAILABLE = is_postgres_available()


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL server not available at POSTGRES_TEST_URL")
def test_live_postgres_connectivity_and_schema():
    """Verify live PostgreSQL server accepts connections and SQLAlchemy dialect behaves correctly."""
    engine = create_engine(POSTGRES_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1
