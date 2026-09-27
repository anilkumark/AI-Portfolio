"""
MedDRA coding suggestion: hybrid retrieval (pgvector + tsvector) fused
with RRF, then reranked with a cross-encoder before presenting the top
candidates to a reviewer.

REQUIRES: a live Postgres connection with the coding.meddra_terms table
populated (see src/coding/embed_meddra_corpus.py, run once at setup).
The RRF fusion math itself is tested independently in
tests/test_rrf_fusion.py without needing this database connection.
"""

import boto3
import json
from sentence_transformers import CrossEncoder

from src.coding.rrf_fusion import reciprocal_rank_fusion
from src.common.db import get_connection

TITAN_EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # runs locally, no API call

_reranker = None  # loaded lazily — avoid the model load cost on import


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(CROSS_ENCODER_MODEL)
    return _reranker


def embed_text(text: str) -> list[float]:
    client = boto3.client("bedrock-runtime")
    body = json.dumps({"inputText": text})
    response = client.invoke_model(modelId=TITAN_EMBED_MODEL_ID, body=body)
    result = json.loads(response["body"].read())
    return result["embedding"]


def vector_candidates(query_embedding: list[float], top_k: int = 20) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT term_id FROM coding.meddra_terms
               ORDER BY embedding <=> %s::vector LIMIT %s""",
            (query_embedding, top_k),
        ).fetchall()
    return [r["term_id"] for r in rows]


def keyword_candidates(query_text: str, top_k: int = 20) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT term_id FROM coding.meddra_terms
               WHERE term_tsv @@ plainto_tsquery('english', %s)
               ORDER BY ts_rank(term_tsv, plainto_tsquery('english', %s)) DESC
               LIMIT %s""",
            (query_text, query_text, top_k),
        ).fetchall()
    return [r["term_id"] for r in rows]


def _fetch_term_texts(term_ids: list[str]) -> dict[str, str]:
    if not term_ids:
        return {}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT term_id, term_text FROM coding.meddra_terms WHERE term_id = ANY(%s)",
            (term_ids,),
        ).fetchall()
    return {r["term_id"]: r["term_text"] for r in rows}


def suggest_meddra_codes(adverse_event_text: str, top_n: int = 5) -> list[dict]:
    """
    Returns the top_n MedDRA term suggestions, ranked, for a reviewer to
    choose from. Never returns a single auto-selected code — suggestion
    only, per the design's suggest-and-confirm requirement.
    """
    query_embedding = embed_text(adverse_event_text)

    vec_ranked = vector_candidates(query_embedding, top_k=20)
    kw_ranked = keyword_candidates(adverse_event_text, top_k=20)

    fused_scores = reciprocal_rank_fusion(vec_ranked, kw_ranked)
    top_fused_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:20]

    term_texts = _fetch_term_texts(top_fused_ids)

    reranker = _get_reranker()
    pairs = [(adverse_event_text, term_texts[tid]) for tid in top_fused_ids if tid in term_texts]
    rerank_scores = reranker.predict(pairs)

    scored = list(zip(top_fused_ids, rerank_scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        {"term_id": tid, "term_text": term_texts[tid], "rerank_score": float(score)}
        for tid, score in scored[:top_n]
    ]
