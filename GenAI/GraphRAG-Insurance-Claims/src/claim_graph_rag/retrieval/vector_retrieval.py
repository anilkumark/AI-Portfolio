"""Vector search: finds text chunks most similar to a question."""

from pgvector.psycopg import register_vector

from claim_graph_rag.core.embeddings import embed_texts
from claim_graph_rag.core.postgres import get_pg_connection


def search_chunks(question: str, top_k: int = 3) -> list[dict]:
    query_embedding = embed_texts([question])[0]

    conn = get_pg_connection()
    register_vector(conn)
    try:
        rows = conn.execute(
            """SELECT document, page_number, content, embedding <=> %s::vector AS distance
               FROM document_chunks
               ORDER BY distance
               LIMIT %s""",
            (query_embedding, top_k),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    results = search_chunks(
        "Why was my claim rejected even though the policy covers sewer backup?"
    )
    for r in results:
        print(f"[{r['document']} p.{r['page_number']}, distance={r['distance']:.4f}]")
        print(r["content"][:200])
        print("---")
