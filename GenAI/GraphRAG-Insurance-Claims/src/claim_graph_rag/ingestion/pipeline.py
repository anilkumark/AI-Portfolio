"""Ingestion pipeline: chunk the processed documents, embed each chunk,
and store them in Postgres."""

from pgvector.psycopg import register_vector

from claim_graph_rag.core.embeddings import embed_texts
from claim_graph_rag.core.postgres import get_pg_connection
from claim_graph_rag.ingestion.chunking import PROCESSED_DIR, chunk_document

BATCH_SIZE = 100


def insert_chunks(conn, chunks: list[dict], embeddings: list[list[float]]) -> None:
    for chunk, embedding in zip(chunks, embeddings):
        conn.execute(
            """INSERT INTO document_chunks (document, page_number, content, embedding)
               VALUES (%(document)s, %(page_number)s, %(content)s, %(embedding)s)""",
            {**chunk, "embedding": embedding},
        )


def run() -> None:
    conn = get_pg_connection()
    register_vector(conn)
    try:
        for json_file in PROCESSED_DIR.glob("*.json"):
            chunks = chunk_document(json_file)

            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                embeddings = embed_texts([c["content"] for c in batch])
                insert_chunks(conn, batch, embeddings)

            print(f"{json_file.name}: embedded and stored {len(chunks)} chunks")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
