"""Builds the knowledge graph: reads chunks from Postgres, extracts entities
and relationships from each, and writes them into Neo4j."""

from claim_graph_rag.core.postgres import get_pg_connection
from claim_graph_rag.graph.entity_extraction import extract_entities
from claim_graph_rag.graph.neo4j_writer import save_to_graph
from claim_graph_rag.graph.relationship_extraction import extract_relationships


def fetch_chunks() -> list[dict]:
    conn = get_pg_connection()
    try:
        return conn.execute("SELECT chunk_id, content FROM document_chunks").fetchall()
    finally:
        conn.close()


def process_chunk(chunk: dict) -> tuple[int, int]:
    text = chunk["content"]
    entities = extract_entities(text)
    relationships = extract_relationships(text, entities)
    save_to_graph(entities, relationships)
    return len(entities), len(relationships)


def build_graph() -> None:
    chunks = fetch_chunks()
    for i, chunk in enumerate(chunks, 1):
        try:
            entity_count, rel_count = process_chunk(chunk)
            print(
                f"[{i}/{len(chunks)}] chunk {chunk['chunk_id']}: {entity_count} entities, {rel_count} relationships"
            )
        except Exception as e:
            print(f"[{i}/{len(chunks)}] chunk {chunk['chunk_id']} FAILED: {e}")


if __name__ == "__main__":
    build_graph()
