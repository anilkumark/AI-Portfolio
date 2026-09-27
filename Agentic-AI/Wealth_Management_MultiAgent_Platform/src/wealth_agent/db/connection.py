"""Shared Postgres connection helper for the wealth management platform."""

import psycopg
from psycopg.rows import dict_row

from wealth_agent.core.config import settings


def get_pg_connection() -> psycopg.Connection:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        row_factory=dict_row,
    )
