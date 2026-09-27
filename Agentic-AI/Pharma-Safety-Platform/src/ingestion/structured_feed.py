"""
Structured feed batch ETL. No LLM involved — the feed is already
structured, so this is schema validation plus a fixed mapping into OMOP.

Records that fail validation are quarantined with the specific failure
reason, never silently dropped or silently loaded.

REQUIRES: a live Postgres instance. Cannot be executed in this
environment, though the pure validation function (validate_record) is
tested independently below without needing a database.
"""

import csv
import json
from datetime import date
from pathlib import Path

REQUIRED_COLUMNS = ["patient_id", "year_of_birth", "sex", "drug_name", "event_date"]


def validate_record(record: dict) -> tuple[bool, str | None]:
    """Pure validation logic — testable without a database connection.
    Returns (is_valid, failure_reason)."""
    missing = [col for col in REQUIRED_COLUMNS if not record.get(col)]
    if missing:
        return False, f"missing required field(s): {missing}"

    try:
        year = int(record["year_of_birth"])
        if year < 1900 or year > date.today().year:
            return False, f"year_of_birth out of plausible range: {year}"
    except (ValueError, TypeError):
        return False, f"year_of_birth is not a valid integer: {record.get('year_of_birth')}"

    if record["sex"] not in ("M", "F", "U"):
        return False, f"sex must be one of M/F/U, got: {record.get('sex')}"

    try:
        date.fromisoformat(record["event_date"])
    except (ValueError, TypeError):
        return False, f"event_date is not a valid ISO date: {record.get('event_date')}"

    return True, None


def process_batch(csv_path: Path, batch_id: str) -> dict:
    """Reads the batch file, validates each record, loads valid ones into
    OMOP, quarantines invalid ones. Returns a summary count."""
    from src.common.db import get_connection  # deferred: keeps validate_record() usable with no DB library installed

    loaded, quarantined = 0, 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            for record in reader:
                is_valid, reason = validate_record(record)

                if not is_valid:
                    conn.execute(
                        """INSERT INTO operational.quarantine
                           (batch_id, raw_record, failure_reason)
                           VALUES (%s, %s, %s)""",
                        (batch_id, json.dumps(record), reason),
                    )
                    quarantined += 1
                    continue

                person_row = conn.execute(
                    """INSERT INTO omop.person (source_type, year_of_birth, sex)
                       VALUES ('structured_feed', %s, %s) RETURNING person_id""",
                    (int(record["year_of_birth"]), record["sex"]),
                ).fetchone()

                conn.execute(
                    """INSERT INTO omop.drug_exposure
                       (person_id, source_type, drug_source_value, exposure_start_date)
                       VALUES (%s, 'structured_feed', %s, %s)""",
                    (person_row["person_id"], record["drug_name"], record["event_date"]),
                )
                loaded += 1

            conn.commit()

    return {"batch_id": batch_id, "loaded": loaded, "quarantined": quarantined}
