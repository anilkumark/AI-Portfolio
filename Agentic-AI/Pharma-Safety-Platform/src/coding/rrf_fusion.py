"""
Reciprocal Rank Fusion for combining vector-similarity and keyword-search
rankings when suggesting MedDRA codes.

The fusion function itself is pure — it takes two ranked ID lists and
returns fused scores. The database queries that PRODUCE those ranked
lists (pgvector cosine distance, tsvector full-text search) need a real
Postgres instance with the MedDRA corpus loaded, which this sandbox
cannot provide. That boundary is deliberate: the algorithm is fully
testable now; the retrieval integration is tested once you have a
database to point it at.
"""

RRF_K = 60  # standard constant — large enough to avoid over-weighting rank 1


def reciprocal_rank_fusion(*ranked_lists: list[str]) -> dict[str, float]:
    """
    Each argument is a list of term_ids in rank order (best first).
    Returns {term_id: fused_score}, higher is better. A term appearing in
    more than one list accumulates score from each — this is what lets a
    term that's merely good on both signals outrank one that's excellent
    on only one.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, term_id in enumerate(ranked_list):
            scores[term_id] = scores.get(term_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return scores


def top_n_fused(*ranked_lists: list[str], n: int = 5) -> list[str]:
    scores = reciprocal_rank_fusion(*ranked_lists)
    return sorted(scores, key=scores.get, reverse=True)[:n]
