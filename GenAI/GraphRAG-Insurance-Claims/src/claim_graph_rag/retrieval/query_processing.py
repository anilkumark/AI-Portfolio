"""Processes a raw user question into entities we can search the graph and
vector store with — reuses the same entity extractor built for documents."""

from claim_graph_rag.graph.entity_extraction import extract_entities


def process_query(question: str) -> dict:
    entities = extract_entities(question)
    return {
        "question": question,
        "entity_names": [e["name"] for e in entities],
    }


if __name__ == "__main__":
    result = process_query(
        "Why was my claim rejected even though the policy covers sewer backup?"
    )
    print(result)
