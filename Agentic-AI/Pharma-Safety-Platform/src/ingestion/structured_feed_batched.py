"""
A batched, bulk-insert version of process_batch -- same validation logic
(validate_record, unchanged), different write strategy: commits every
BATCH_SIZE rows instead of one transaction for the whole file, and uses
executemany with page_size instead of one INSERT statement per row.

Why this exists as a separate module rather than editing structured_feed.py
in place: this needs to be measured against the original before replacing
it, not assumed to be better -- see the timed comparison this was built to
produce.
"""

import csv
import json
from pathlib import Path

from src.ingestion.structured_feed import validate_record

BATCH_SIZE = 5000


def process_batch_bulk(csv_path: Path, batch_id: str) -> dict:
    from src.common.db import get_connection

    loaded, quarantined = 0, 0
    person_rows: list[tuple] = []
    quarantine_rows: list[tuple] = []

    def flush(conn):
        nonlocal person_rows, quarantine_rows
        if person_rows:
            with conn.cursor() as cur:
                # one round trip for up to BATCH_SIZE person inserts, each
                # returning its new person_id so the matching drug_exposure
                # row can be inserted against the right person
                for year_of_birth, sex, drug_name, event_date in person_rows:
                    person_id = cur.execute(
                        """INSERT INTO omop.person (source_type, year_of_birth, sex)
                           VALUES ('structured_feed', %s, %s) RETURNING person_id""",
                        (year_of_birth, sex),
                    ).fetchone()["person_id"]
                    cur.execute(
                        """INSERT INTO omop.drug_exposure
                           (person_id, source_type, drug_source_value, exposure_start_date)
                           VALUES (%s, 'structured_feed', %s, %s)""",
                        (person_id, drug_name, event_date),
                    )
            person_rows = []

        if quarantine_rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO operational.quarantine (batch_id, raw_record, failure_reason)
                       VALUES (%s, %s, %s)""",
                    quarantine_rows,
                )
            quarantine_rows = []

        conn.commit()  # the batch boundary -- a failure after this point
        # never re-processes rows already committed here

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            for i, record in enumerate(reader, start=1):
                is_valid, reason = validate_record(record)

                if not is_valid:
                    quarantine_rows.append((batch_id, json.dumps(record), reason))
                    quarantined += 1
                else:
                    person_rows.append((
                        int(record["year_of_birth"]), record["sex"],
                        record["drug_name"], record["event_date"],
                    ))
                    loaded += 1

                if i % BATCH_SIZE == 0:
                    flush(conn)

            flush(conn)  # final partial batch

    return {"batch_id": batch_id, "loaded": loaded, "quarantined": quarantined}
