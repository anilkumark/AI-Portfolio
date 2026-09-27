"""
Loads the MedDRA terminology corpus into coding.meddra_terms — run once
at setup, and again whenever MedDRA releases a new version (twice yearly).

Input format: a CSV with columns term_id, term_text, soc — export this
from your MedDRA license delivery. The exact export format varies by
license tier, so this expects a normalized CSV rather than parsing any
specific MedDRA distribution format directly; add a conversion step
before this if your delivery format differs.
"""

import csv
from pathlib import Path

from src.coding.meddra_search import embed_text
from src.common.db import get_connection

BATCH_COMMIT_SIZE = 200


def load_meddra_corpus(csv_path: Path, kb_version: str) -> dict:
    inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            for row in reader:
                embedding = embed_text(row["term_text"])
                conn.execute(
                    """INSERT INTO coding.meddra_terms (term_id, term_text, soc, embedding, kb_version)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (term_id) DO UPDATE
                       SET term_text = EXCLUDED.term_text, soc = EXCLUDED.soc,
                           embedding = EXCLUDED.embedding, kb_version = EXCLUDED.kb_version""",
                    (row["term_id"], row["term_text"], row.get("soc"), embedding, kb_version),
                )
                inserted += 1
                if inserted % BATCH_COMMIT_SIZE == 0:
                    conn.commit()
                    print(f"[meddra load] {inserted} terms embedded and inserted...")
            conn.commit()

    return {"kb_version": kb_version, "terms_loaded": inserted}


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: python embed_meddra_corpus.py <csv_path> <kb_version>")
        raise SystemExit(1)
    result = load_meddra_corpus(Path(sys.argv[1]), sys.argv[2])
    print(f"[meddra load] done: {result}")
