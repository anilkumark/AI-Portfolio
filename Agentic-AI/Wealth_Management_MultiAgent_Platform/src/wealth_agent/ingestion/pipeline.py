"""Ingestion pipeline: read market-insights documents, chunk, embed, store in Postgres."""

import logging
from pathlib import Path

from pgvector.psycopg import register_vector

from wealth_agent.db.connection import get_pg_connection
from wealth_agent.ingestion.chunking import chunk_document
from wealth_agent.ingestion.embedding import embed_texts
from wealth_agent.ingestion.parsers import extract_doc_metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MARKET_INSIGHTS_DIR = Path(__file__).resolve().parents[3] / "market_insights_documents"


def insert_chunks(pg_conn, chunks: list[dict], embeddings: list[list[float]]) -> None:
    with pg_conn.cursor() as cur:
        for chunk, embedding in zip(chunks, embeddings):
            cur.execute(
                """INSERT INTO market_insights_chunks
                   (document_id, document_title, section, chunk_type, content, embedding)
                   VALUES (%(document_id)s, %(document_title)s, %(section)s, %(chunk_type)s, %(content)s, %(embedding)s)""",
                {**chunk, "embedding": embedding},
            )
    pg_conn.commit()


def main() -> None:
    pg_conn = get_pg_connection()
    register_vector(pg_conn)
    try:
        for md_file in sorted(MARKET_INSIGHTS_DIR.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            doc_id, doc_title = extract_doc_metadata(text)
            chunks = chunk_document(text, doc_id, doc_title)
            embeddings = embed_texts([c["content"] for c in chunks])
            insert_chunks(pg_conn, chunks, embeddings)
            logger.info("Embedded %d chunks from %s", len(chunks), md_file.name)
        logger.info("All market-insights documents embedded.")
    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
