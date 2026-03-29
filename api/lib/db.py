"""
Database connection for Neon Postgres (Vercel-native).
Uses psycopg2 with connection pooling via DATABASE_URL env var.
"""
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Generator

# Neon provides a connection string as DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_connection():
    """Get a raw psycopg2 connection."""
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
        options="-c statement_timeout=30000",
    )


@contextmanager
def get_db() -> Generator:
    """Context manager for DB connection with auto-commit on success."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query: str, params=None) -> list[dict]:
    """Execute a SELECT query and return list of dicts."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute_one(query: str, params=None) -> dict | None:
    """Execute a query and return one row."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute_write(query: str, params=None) -> dict | None:
    """Execute an INSERT/UPDATE/DELETE with optional RETURNING."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            try:
                row = cur.fetchone()
                return dict(row) if row else None
            except psycopg2.ProgrammingError:
                return None
