"""Governance: attribute token usage to the specific agent that generated
each message, not just the conversation as a whole."""

from wealth_agent.db.connection import get_pg_connection


def log_usage(thread_id: str, agent_name: str, usage: dict) -> None:
    """Record one agent call's token usage."""
    conn = get_pg_connection()
    try:
        conn.execute(
            """INSERT INTO agent_usage (thread_id, agent_name, input_tokens, output_tokens, total_tokens)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                thread_id,
                agent_name,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def log_run_usage(thread_id: str, messages: list) -> None:
    """Walk a Supervisor run's messages and log usage for every agent that responded."""
    for message in messages:
        usage = getattr(message, "usage_metadata", None)
        if usage:
            agent_name = getattr(message, "name", None) or "supervisor"
            log_usage(thread_id, agent_name, usage)
