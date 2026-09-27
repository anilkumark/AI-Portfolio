"""Tools for the Policy Agent: semantic search over embedded SOP policy chunks."""

from langchain_core.runnables import RunnableConfig
from openai import OpenAI
from pgvector.psycopg import register_vector

from refund_system.db.connection import get_pg_connection
from refund_system.observability.cost_tracking import record_usage

EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI()


def search_policy(query: str, config: RunnableConfig, top_k: int = 3) -> list[dict]:
    """Find the most relevant policy chunks for a natural-language query."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    query_embedding = response.data[0].embedding

    thread_id = config["configurable"]["thread_id"]
    record_usage(thread_id, EMBEDDING_MODEL, response.usage.prompt_tokens, 0)

    conn = get_pg_connection()
    register_vector(conn)
    try:
        rows = conn.execute(
            """SELECT document_title, section, chunk_type, content,
                      embedding <=> %s::vector AS distance
               FROM policy_chunks
               ORDER BY distance
               LIMIT %s""",
            (query_embedding, top_k),
        ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()
