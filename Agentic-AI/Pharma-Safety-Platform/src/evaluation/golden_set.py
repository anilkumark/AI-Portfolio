"""
Golden set structure for Phase 1: extraction and coding accuracy proof.
The design calls for ~50 real, de-identified cases across the three
hardest source types. This file defines the structure; the actual 50
cases must be sourced from your real (de-identified) case archive — they
cannot be fabricated, since the entire point is measuring extraction
against real, hard, expert-confirmed ground truth.
"""

from dataclasses import dataclass


@dataclass
class GoldenCase:
    case_id: str
    source_type: str          # 'digital_pdf' | 'scanned_fax' | 'email_narrative'
    document_path: str
    expected_fields: dict     # expert-confirmed correct values for every extracted field
    expected_meddra_code: str
    expected_seriousness: str  # 'serious' | 'non_serious'


# Populate this from your real de-identified case archive before running
# evaluate.py. Left empty here — this sandbox has no case data, and
# fabricating example cases would defeat the purpose of this file.
GOLDEN_SET: list[GoldenCase] = []


def validate_golden_set_composition(cases: list[GoldenCase]) -> dict:
    """Checks the golden set actually covers what Phase 1 requires before
    evaluation is trusted — the design specifically calls for coverage
    across the three hardest source types, not just 50 easy cases."""
    by_type: dict[str, int] = {}
    for case in cases:
        by_type[case.source_type] = by_type.get(case.source_type, 0) + 1

    required_types = {"digital_pdf", "scanned_fax", "email_narrative"}
    missing_types = required_types - set(by_type.keys())

    return {
        "total_cases": len(cases),
        "by_source_type": by_type,
        "missing_source_types": list(missing_types),
        "meets_minimum_coverage": len(missing_types) == 0 and len(cases) >= 30,
    }
