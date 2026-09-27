"""
Runs the extraction and coding chain against the golden set and scores
accuracy field by field — never blended into one document-level score,
per the design's evaluation principle.

REQUIRES: AWS credentials (extraction chain) and a live database
(MedDRA search). The scoring logic itself (compare_fields) is pure and
tested independently below.
"""

from src.evaluation.golden_set import GoldenCase


def compare_fields(extracted: dict, expected: dict) -> dict:
    """
    Field-by-field comparison. Returns per-field correct/incorrect, plus
    an overall count — deliberately not a single blended percentage,
    since a 95%-correct case with one wrong seriousness-relevant field is
    a failure, not a near-success.
    """
    results = {}
    for field_name, expected_value in expected.items():
        actual_value = extracted.get(field_name)
        results[field_name] = {
            "expected": expected_value,
            "actual": actual_value,
            "correct": actual_value == expected_value,
        }
    return results


def summarize_field_accuracy(all_case_results: list[dict]) -> dict:
    """Aggregates per-field accuracy across every case in the run — this
    is what tells you WHICH field is weak, not just an overall score."""
    field_totals: dict[str, dict] = {}

    for case_result in all_case_results:
        for field_name, outcome in case_result.items():
            if field_name not in field_totals:
                field_totals[field_name] = {"correct": 0, "total": 0}
            field_totals[field_name]["total"] += 1
            if outcome["correct"]:
                field_totals[field_name]["correct"] += 1

    return {
        field_name: {
            **counts,
            "accuracy": counts["correct"] / counts["total"] if counts["total"] else None,
        }
        for field_name, counts in field_totals.items()
    }


def run_evaluation(golden_cases: list[GoldenCase]) -> dict:
    """Full Phase 1 evaluation run against real infrastructure. Not
    executable in this sandbox — needs AWS credentials and a populated
    MedDRA corpus."""
    from src.ingestion.extract import extract_case
    from src.coding.meddra_search import suggest_meddra_codes
    from src.gate.seriousness_gate import GateInput, evaluate_seriousness

    all_field_results = []
    coding_correct = 0
    seriousness_correct = 0

    for case in golden_cases:
        extraction = extract_case(
            s3_bucket="", s3_key="",
            local_file_path=case.document_path, source_channel="upload_portal",
        )
        field_results = compare_fields(extraction, case.expected_fields)
        all_field_results.append(field_results)

        suggestions = suggest_meddra_codes(extraction["adverse_event_text"], top_n=5)
        if any(s["term_id"] == case.expected_meddra_code for s in suggestions):
            coding_correct += 1

        gate_input = GateInput(
            outcome=extraction.get("outcome"),
            life_threatening_flag=extraction.get("life_threatening_flag"),
            hospitalized=extraction.get("hospitalized"),
            hospitalization_prolonged=extraction.get("hospitalization_prolonged"),
            disability_flag=extraction.get("disability_flag"),
            congenital_anomaly_flag=extraction.get("congenital_anomaly_flag"),
            adverse_event_text=extraction.get("adverse_event_text", ""),
        )
        gate_result = evaluate_seriousness(gate_input)
        if gate_result.seriousness_result == case.expected_seriousness:
            seriousness_correct += 1

    n = len(golden_cases)
    return {
        "n_cases": n,
        "field_accuracy": summarize_field_accuracy(all_field_results),
        "meddra_suggestion_accuracy": coding_correct / n if n else None,
        "seriousness_gate_accuracy": seriousness_correct / n if n else None,
    }
