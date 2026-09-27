"""
Notifications: reviewer alerts when a case enters the review queue, and
data-source contact alerts when a structured-feed batch is quarantined.
Both are SNS topic publishes — actual email/SMS delivery is configured on
the SNS topic subscriptions, not in this code.
"""

import json
import boto3

REVIEWER_ALERT_TOPIC_ARN_ENV = "REVIEWER_ALERT_TOPIC_ARN"
QUARANTINE_ALERT_TOPIC_ARN_ENV = "QUARANTINE_ALERT_TOPIC_ARN"


def _publish(topic_arn: str, subject: str, message: dict) -> None:
    client = boto3.client("sns")
    client.publish(
        TopicArn=topic_arn,
        Subject=subject[:100],  # SNS subject length limit
        Message=json.dumps(message, default=str),
    )


def notify_reviewer(case_id: str, priority: str, seriousness_result: str) -> None:
    import os
    topic_arn = os.environ[REVIEWER_ALERT_TOPIC_ARN_ENV]
    _publish(
        topic_arn,
        subject=f"[{priority.upper()}] Case {case_id} awaiting review",
        message={
            "case_id": case_id,
            "priority": priority,
            "seriousness_result": seriousness_result,
            "action": "Review required in the reviewer workbench",
        },
    )


def notify_quarantine(batch_id: str, quarantined_count: int, sample_reasons: list[str]) -> None:
    import os
    topic_arn = os.environ[QUARANTINE_ALERT_TOPIC_ARN_ENV]
    _publish(
        topic_arn,
        subject=f"Structured feed batch {batch_id}: {quarantined_count} records quarantined",
        message={
            "batch_id": batch_id,
            "quarantined_count": quarantined_count,
            "sample_failure_reasons": sample_reasons[:5],
        },
    )


def notify_deadline_approaching(case_id: str, days_remaining: int) -> None:
    """Called by the scheduled deadline-monitoring job — see
    src/evaluation/deadline_monitor.py."""
    import os
    topic_arn = os.environ[REVIEWER_ALERT_TOPIC_ARN_ENV]
    _publish(
        topic_arn,
        subject=f"[URGENT] Case {case_id} — {days_remaining} day(s) to regulatory deadline",
        message={
            "case_id": case_id,
            "days_remaining": days_remaining,
            "action": "Escalate to team lead if not resolved within 24 hours",
        },
    )
