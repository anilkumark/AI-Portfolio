"""
Dedup matching. Runs before any record joins the OMOP unified store,
because a duplicated event corrupts every signal-detection number built
on top of it.

Two matching strategies, tried in order:
  1. Exact match on patient identifier, when one is reliably present and
     consistent across sources (rare in practice, but the strongest
     signal when available).
  2. Fuzzy match on suspect product + adverse event + event date within
     a configurable window, when patient identifiers are absent or
     unreliable — which is the common case across case reports, EHR
     extracts, and structured feed data that were never designed to
     share a common patient key.

A match above the similarity threshold links the new record to the
existing one rather than inserting a duplicate. Both source record IDs
are retained on the link, so the link itself is auditable — nothing is
silently discarded.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from difflib import SequenceMatcher


DEFAULT_DATE_WINDOW_DAYS = 7
DEFAULT_SIMILARITY_THRESHOLD = 0.82


@dataclass
class CandidateRecord:
    record_id: str
    patient_id: str | None
    suspect_product: str
    adverse_event_text: str
    event_date: date | None


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _dates_within_window(d1: date | None, d2: date | None, window_days: int) -> bool:
    if d1 is None or d2 is None:
        return False
    return abs((d1 - d2).days) <= window_days


def find_duplicate(
    new_record: CandidateRecord,
    existing_records: list[CandidateRecord],
    date_window_days: int = DEFAULT_DATE_WINDOW_DAYS,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> CandidateRecord | None:
    """Returns the matching existing record if new_record is a likely
    duplicate, else None. Checks patient-ID match first (strongest
    signal); falls back to fuzzy matching only when no reliable patient
    ID is available on either side."""

    # Strategy 1: patient ID match, when both sides have one
    if new_record.patient_id:
        for existing in existing_records:
            if existing.patient_id and existing.patient_id == new_record.patient_id:
                if _text_similarity(new_record.adverse_event_text, existing.adverse_event_text) > 0.5:
                    return existing

    # Strategy 2: fuzzy match on product + event + date window -- only when
    # a reliable patient ID isn't available on BOTH sides. Two records that
    # each carry a known, distinct patient ID are two different people by
    # definition; the fuzzy path must never override that, or a real safety
    # signal (multiple different patients, same product+event, close in
    # time) gets misread as one duplicated report and silently undercounted.
    best_match = None
    best_score = 0.0
    for existing in existing_records:
        if new_record.patient_id and existing.patient_id and new_record.patient_id != existing.patient_id:
            continue  # both sides have a known identity, and they differ -- not a duplicate, full stop
        if existing.suspect_product.lower().strip() != new_record.suspect_product.lower().strip():
            continue
        if not _dates_within_window(new_record.event_date, existing.event_date, date_window_days):
            continue
        score = _text_similarity(new_record.adverse_event_text, existing.adverse_event_text)
        if score > best_score:
            best_score = score
            best_match = existing

    if best_match and best_score >= similarity_threshold:
        return best_match
    return None
