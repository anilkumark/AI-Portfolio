"""
True bulk-load version of process_batch. The batched-commit version
(structured_feed_batched.py) turned out to barely help -- the real cost
is the round trip on every 'INSERT ... RETURNING person_id' needed to link
each drug_exposure row to its person. This version removes that
dependency entirely: person_id is generated client-side (uuid4, matching
the column's own default generator), so both tables can be bulk-loaded
independently with executemany and no row-by-row round trip at all.
"""

import csv
import json
import uuid
from pathlib import Path

BATCH_SIZE = 5000


def process_batch_true_bulk(csv_path: Path, batch_id: str) -> dict:
    from src.common.db import get_connection

    loaded, quarantined = 0, 0
    person_rows: list[tuple] = []
    drug_rows: list[tuple] = []
    quarantine_rows: list[tuple] = []

    def flush(conn):
        nonlocal person_rows, drug_rows, quarantine_rows
        with conn.cursor() as cur:
            if person_rows:
                cur.executemany(
                    """INSERT INTO omop.person (person_id, source_type, year_of_birth, sex)
                       VALUES (%s, 'structured_feed', %s, %s)""",
                    person_rows,
                )
            if drug_rows:
                cur.executemany(
                    """INSERT INTO omop.drug_exposure
                       (person_id, source_type, drug_source_value, exposure_start_date)
                       VALUES (%s, 'structured_feed', %s, %s)""",
                    drug_rows,
                )
            if quarantine_rows:
                cur.executemany(
                    """INSERT INTO operational.quarantine (batch_id, raw_record, failure_reason)
                       VALUES (%s, %s, %s)""",
                    quarantine_rows,
                )
        conn.commit()
        person_rows, drug_rows, quarantine_rows = [], [], []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            from src.ingestion.structured_feed import validate_record

            for i, record in enumerate(reader, start=1):
                is_valid, reason = validate_record(record)

                if not is_valid:
                    quarantine_rows.append((batch_id, json.dumps(record), reason))
                    quarantined += 1
                else:
                    person_id = str(uuid.uuid4())
                    person_rows.append((person_id, int(record["year_of_birth"]), record["sex"]))
                    drug_rows.append((person_id, record["drug_name"], record["event_date"]))
                    loaded += 1

                if i % BATCH_SIZE == 0:
                    flush(conn)

            flush(conn)

    return {"batch_id": batch_id, "loaded": loaded, "quarantined": quarantined}
