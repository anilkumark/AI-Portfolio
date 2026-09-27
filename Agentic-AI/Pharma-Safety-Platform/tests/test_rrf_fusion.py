import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coding.rrf_fusion import reciprocal_rank_fusion, top_n_fused


def test_term_appearing_in_both_lists_outranks_top_of_one_list():
    """The core reason RRF is used: a term that's good on BOTH vector and
    keyword signals should beat a term that's merely #1 on one signal
    alone."""
    vector_ranked = ["T2", "T1", "T3"]     # T1 is #2 here
    keyword_ranked = ["T1", "T4", "T5"]    # T1 is #1 here
    scores = reciprocal_rank_fusion(vector_ranked, keyword_ranked)
    # T1 appears in both -> should outrank T2, which only appears once (at #1)
    assert scores["T1"] > scores["T2"]


def test_single_list_preserves_original_order():
    ranked = ["A", "B", "C"]
    scores = reciprocal_rank_fusion(ranked)
    assert scores["A"] > scores["B"] > scores["C"]


def test_empty_lists_produce_empty_scores():
    assert reciprocal_rank_fusion([], []) == {}


def test_top_n_returns_correct_count():
    vector_ranked = ["T1", "T2", "T3", "T4", "T5", "T6"]
    keyword_ranked = ["T3", "T1", "T6"]
    result = top_n_fused(vector_ranked, keyword_ranked, n=3)
    assert len(result) == 3


def test_top_n_ranks_dual_appearance_first():
    vector_ranked = ["T5", "T1", "T2"]
    keyword_ranked = ["T1", "T5", "T3"]
    result = top_n_fused(vector_ranked, keyword_ranked, n=2)
    assert set(result) == {"T1", "T5"}  # both appear in both lists, both should be top-2
