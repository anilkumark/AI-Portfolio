"""
Includes the specific scenario named as Phase 3's sign-off gate in the
design document: the same event reported through two different channels
must be linked, not double-counted.
"""

import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dedup.dedup import CandidateRecord, find_duplicate


def test_same_event_two_channels_is_linked_not_duplicated():
    """The Phase 3 sign-off scenario: a physician report and a patient
    report of the same event, no shared patient ID, arriving three days
    apart with near-identical (but not identical) wording."""
    physician_report = CandidateRecord(
        record_id="case-001", patient_id=None, suspect_product="Drugamab",
        adverse_event_text="Patient developed severe rash on arms and torso after second dose",
        event_date=date(2026, 3, 10),
    )
    patient_report = CandidateRecord(
        record_id="case-002", patient_id=None, suspect_product="Drugamab",
        adverse_event_text="I developed a severe rash on my arms and torso after the second dose",
        event_date=date(2026, 3, 13),
    )
    match = find_duplicate(patient_report, [physician_report])
    assert match is not None
    assert match.record_id == "case-001"


def test_different_product_is_not_a_duplicate():
    a = CandidateRecord("case-001", None, "Drugamab", "severe rash after second dose", date(2026, 3, 10))
    b = CandidateRecord("case-002", None, "OtherDrugX", "severe rash after second dose", date(2026, 3, 11))
    assert find_duplicate(b, [a]) is None


def test_same_product_far_outside_date_window_is_not_a_duplicate():
    a = CandidateRecord("case-001", None, "Drugamab", "severe rash after second dose", date(2026, 3, 10))
    b = CandidateRecord("case-002", None, "Drugamab", "severe rash after second dose", date(2026, 6, 1))
    assert find_duplicate(b, [a]) is None


def test_same_product_similar_date_different_event_is_not_a_duplicate():
    a = CandidateRecord("case-001", None, "Drugamab", "severe rash on arms and torso", date(2026, 3, 10))
    b = CandidateRecord("case-002", None, "Drugamab", "persistent headache and dizziness", date(2026, 3, 11))
    assert find_duplicate(b, [a]) is None


def test_matching_patient_id_with_weakly_similar_text_still_links():
    """Patient ID is the stronger signal — when it matches and the text
    is at least plausibly related, trust the ID."""
    a = CandidateRecord("case-001", "PT-5521", "Drugamab", "rash on arms", date(2026, 3, 10))
    b = CandidateRecord("case-002", "PT-5521", "Drugamab", "skin rash noted on upper limbs", date(2026, 3, 10))
    match = find_duplicate(b, [a])
    assert match is not None
    assert match.record_id == "case-001"


def test_matching_patient_id_but_completely_unrelated_text_does_not_link():
    """A shared patient ID with totally unrelated adverse event text is
    more likely a data entry issue than a genuine duplicate — do not
    link blindly on ID alone."""
    a = CandidateRecord("case-001", "PT-5521", "Drugamab", "mild nausea", date(2026, 3, 10))
    b = CandidateRecord("case-002", "PT-5521", "Drugamab", "severe cardiac arrhythmia requiring hospitalization", date(2026, 3, 10))
    assert find_duplicate(b, [a]) is None


def test_distinct_known_patient_ids_are_never_fuzzy_matched_into_a_duplicate():
    """Regression test: two records that each carry a KNOWN, DIFFERENT
    patient ID must never be linked via the fuzzy fallback, even with an
    identical product, identical event text, and the same date -- this is
    exactly the shape of a real safety signal (several different patients,
    same product+event, close in time), and treating it as one duplicated
    report would silently suppress it. Found by running 3 real, distinct
    synthetic patients through the pipeline and seeing them incorrectly
    collapse into one OMOP record."""
    a = CandidateRecord("case-001", "PT-JD-001", "ExampleDrugX", "cardiac arrest", date(2026, 3, 10))
    b = CandidateRecord("case-002", "PT-MS-002", "ExampleDrugX", "cardiac arrest", date(2026, 3, 10))
    assert find_duplicate(b, [a]) is None


def test_no_existing_records_returns_none():
    a = CandidateRecord("case-001", None, "Drugamab", "rash", date(2026, 3, 10))
    assert find_duplicate(a, []) is None


def test_picks_the_best_match_among_multiple_candidates():
    close_match = CandidateRecord("case-001", None, "Drugamab",
                                    "severe rash on arms and torso after second dose", date(2026, 3, 10))
    weak_match = CandidateRecord("case-002", None, "Drugamab",
                                   "some skin irritation", date(2026, 3, 11))
    new = CandidateRecord("case-003", None, "Drugamab",
                            "severe rash on arms and torso after the second dose", date(2026, 3, 12))
    match = find_duplicate(new, [weak_match, close_match])
    assert match is not None
    assert match.record_id == "case-001"
