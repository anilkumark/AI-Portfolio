"""Long-term client memory: durable notes that persist across conversation
threads, distinct from the thread-scoped LangGraph checkpointer."""

from wealth_agent.db.connection import get_pg_connection


def add_note(client_id: int, note: str) -> None:
    """Record a durable observation about a client, outside any one conversation."""
    conn = get_pg_connection()
    try:
        conn.execute(
            "INSERT INTO client_profile_notes (client_id, note) VALUES (%s, %s)",
            (client_id, note),
        )
        conn.commit()
    finally:
        conn.close()


def get_notes(client_id: int, limit: int = 5) -> list[dict]:
    """Fetch a client's most recent durable notes, newest first."""
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            """SELECT note, created_at FROM client_profile_notes
               WHERE client_id = %s ORDER BY created_at DESC LIMIT %s""",
            (client_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
