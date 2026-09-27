"""Postgres connection helper — pgvector-backed store for document chunks."""

import psycopg
from psycopg.rows import dict_row

from claim_graph_rag.core.config import settings


def get_pg_connection():
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        row_factory=dict_row,
        autocommit=True,
    )
