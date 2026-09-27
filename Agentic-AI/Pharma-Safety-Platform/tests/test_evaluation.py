import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.evaluate import compare_fields, summarize_field_accuracy
from src.evaluation.golden_set import GoldenCase, validate_golden_set_composition


def test_compare_fields_flags_correct_and_incorrect():
    extracted = {"suspect_product": "Drugamab", "outcome": "recovered"}
    expected = {"suspect_product": "Drugamab", "outcome": "death"}
    result = compare_fields(extracted, expected)
    assert result["suspect_product"]["correct"] is True
    assert result["outcome"]["correct"] is False


def test_compare_fields_missing_extracted_field_counts_incorrect():
    extracted = {"suspect_product": "Drugamab"}
    expected = {"suspect_product": "Drugamab", "outcome": "death"}
    result = compare_fields(extracted, expected)
    assert result["outcome"]["correct"] is False
    assert result["outcome"]["actual"] is None


def test_summarize_field_accuracy_computes_per_field_rate():
    case1 = {"outcome": {"correct": True}, "suspect_product": {"correct": True}}
    case2 = {"outcome": {"correct": False}, "suspect_product": {"correct": True}}
    summary = summarize_field_accuracy([case1, case2])
    assert summary["outcome"]["accuracy"] == 0.5
    assert summary["suspect_product"]["accuracy"] == 1.0


def test_summarize_field_accuracy_never_blends_fields_together():
    """The design's core evaluation principle: one weak field must stay
    visible, not get averaged away by strong fields."""
    case = {
        "outcome": {"correct": True}, "suspect_product": {"correct": True},
        "hospitalized": {"correct": True}, "seriousness_relevant_field": {"correct": False},
    }
    summary = summarize_field_accuracy([case])
    assert summary["seriousness_relevant_field"]["accuracy"] == 0.0
    assert summary["outcome"]["accuracy"] == 1.0
    # each field has its own independent number — none of them is 0.75 (blended)


def test_golden_set_composition_flags_missing_source_types():
    cases = [
        GoldenCase("c1", "digital_pdf", "", {}, "T1", "serious"),
        GoldenCase("c2", "digital_pdf", "", {}, "T1", "serious"),
    ]
    result = validate_golden_set_composition(cases)
    assert "scanned_fax" in result["missing_source_types"]
    assert "email_narrative" in result["missing_source_types"]
    assert result["meets_minimum_coverage"] is False


def test_golden_set_composition_passes_with_full_coverage():
    cases = (
        [GoldenCase(f"d{i}", "digital_pdf", "", {}, "T1", "serious") for i in range(10)]
        + [GoldenCase(f"s{i}", "scanned_fax", "", {}, "T1", "serious") for i in range(10)]
        + [GoldenCase(f"e{i}", "email_narrative", "", {}, "T1", "serious") for i in range(10)]
    )
    result = validate_golden_set_composition(cases)
    assert result["missing_source_types"] == []
    assert result["meets_minimum_coverage"] is True
