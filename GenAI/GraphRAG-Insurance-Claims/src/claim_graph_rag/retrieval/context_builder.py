"""Combines graph facts and vector-retrieved text chunks into one context
for the LLM to reason over."""

from claim_graph_rag.retrieval.graph_retrieval import get_connected_facts
from claim_graph_rag.retrieval.query_processing import process_query
from claim_graph_rag.retrieval.vector_retrieval import search_chunks


def build_context(question: str) -> dict:
    query_info = process_query(question)
    graph_facts = get_connected_facts(query_info["entity_names"])
    text_chunks = search_chunks(question)

    return {
        "question": question,
        "graph_facts": graph_facts,
        "text_chunks": text_chunks,
    }


if __name__ == "__main__":
    context = build_context(
        "Why was my claim rejected even though the policy covers sewer backup?"
    )
    print(f"Graph facts: {len(context['graph_facts'])}")
    print(f"Text chunks: {len(context['text_chunks'])}")
