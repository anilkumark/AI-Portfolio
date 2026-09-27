CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document      TEXT NOT NULL,
    page_number   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    embedding     VECTOR(1536),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
