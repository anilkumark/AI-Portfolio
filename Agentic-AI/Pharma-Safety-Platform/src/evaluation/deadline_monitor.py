"""
The regulatory-clock check. Per the design: cases approaching the 15-day
deadline must be visible before they breach, not after. Run as a
scheduled job (e.g. every hour) against the operational case records.

The date-math logic is pure and tested without a database below.
"""

from datetime import datetime, timedelta

REGULATORY_DEADLINE_DAYS = 15
WARNING_THRESHOLD_DAYS_REMAINING = 3  # alert once 3 days or fewer remain


def days_remaining(received_at: datetime, now: datetime) -> int:
    deadline = received_at + timedelta(days=REGULATORY_DEADLINE_DAYS)
    remaining = (deadline - now).days
    return remaining


def needs_deadline_alert(received_at: datetime, now: datetime, submission_status: str) -> bool:
    if submission_status == "submitted":
        return False
    return days_remaining(received_at, now) <= WARNING_THRESHOLD_DAYS_REMAINING


def run_deadline_check() -> list[dict]:
    """Queries all unsubmitted cases and returns those needing an alert.
    REQUIRES a live database connection."""
    from src.common.db import get_connection
    from src.common.notifications import notify_deadline_approaching

    now = datetime.utcnow()
    alerts_sent = []

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT case_id, received_at FROM operational.case_records
               WHERE submission_status != 'submitted'"""
        ).fetchall()

    for row in rows:
        remaining = days_remaining(row["received_at"], now)
        if needs_deadline_alert(row["received_at"], now, "not_submitted"):
            notify_deadline_approaching(str(row["case_id"]), remaining)
            alerts_sent.append({"case_id": str(row["case_id"]), "days_remaining": remaining})

    return alerts_sent


if __name__ == "__main__":
    result = run_deadline_check()
    print(f"[deadline check] {len(result)} alert(s) sent")
