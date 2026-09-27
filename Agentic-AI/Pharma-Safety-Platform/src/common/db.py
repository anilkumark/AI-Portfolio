"""
Pooled Postgres connection. REQUIRES a live Aurora PostgreSQL instance —
set DATABASE_URL in your environment before using any module that imports
this.
"""

import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        db_url = os.environ["DATABASE_URL"]  # deliberately no default — fail loudly, not silently
        _pool = ConnectionPool(db_url, min_size=2, max_size=10,
                                kwargs={"row_factory": dict_row})
    return _pool


def get_connection():
    """Use as: with get_connection() as conn: ..."""
    conn_ctx = get_pool().connection()
    return conn_ctx
