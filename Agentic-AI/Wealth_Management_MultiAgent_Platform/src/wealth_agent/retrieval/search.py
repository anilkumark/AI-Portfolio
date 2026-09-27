"""Tools for the Insights Agent: semantic search over embedded market-insights chunks."""

from openai import OpenAI
from pgvector.psycopg import register_vector

from wealth_agent.core.config import settings
from wealth_agent.db.connection import get_pg_connection

EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI(api_key=settings.openai_api_key)


def search_market_insights(query: str, top_k: int = 3) -> list[dict]:
    """Find the most relevant market-insights chunks for a natural-language query."""
    query_embedding = (
        client.embeddings.create(model=EMBEDDING_MODEL, input=[query]).data[0].embedding
    )

    conn = get_pg_connection()
    register_vector(conn)
    try:
        rows = conn.execute(
            """SELECT document_title, section, chunk_type, content,
                      embedding <=> %s::vector AS distance
               FROM market_insights_chunks
               ORDER BY distance
               LIMIT %s""",
            (query_embedding, top_k),
        ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()
