import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.deadline_monitor import days_remaining, needs_deadline_alert, REGULATORY_DEADLINE_DAYS


def test_days_remaining_at_receipt_is_full_window():
    now = datetime(2026, 3, 1, 12, 0)
    assert days_remaining(now, now) == REGULATORY_DEADLINE_DAYS


def test_days_remaining_counts_down_correctly():
    received = datetime(2026, 3, 1, 12, 0)
    now = received + timedelta(days=10)
    assert days_remaining(received, now) == 5


def test_no_alert_when_plenty_of_time_remains():
    received = datetime(2026, 3, 1, 12, 0)
    now = received + timedelta(days=2)
    assert needs_deadline_alert(received, now, "not_submitted") is False


def test_alert_fires_at_threshold():
    received = datetime(2026, 3, 1, 12, 0)
    now = received + timedelta(days=12)  # 3 days remaining
    assert needs_deadline_alert(received, now, "not_submitted") is True


def test_alert_fires_past_threshold_too():
    received = datetime(2026, 3, 1, 12, 0)
    now = received + timedelta(days=16)  # already breached
    assert needs_deadline_alert(received, now, "not_submitted") is True


def test_no_alert_once_submitted_regardless_of_time():
    """A submitted case should never fire a deadline alert, even if it
    was submitted close to the wire."""
    received = datetime(2026, 3, 1, 12, 0)
    now = received + timedelta(days=14, hours=23)
    assert needs_deadline_alert(received, now, "submitted") is False
