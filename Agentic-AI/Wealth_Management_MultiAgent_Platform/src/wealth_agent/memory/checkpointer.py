"""Postgres-backed checkpointer for persisting Supervisor state across pauses."""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from wealth_agent.core.config import settings

DB_URI = (
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)


def get_checkpointer():
    """Sync checkpointer — for direct scripts/tests using build_supervisor()."""
    return PostgresSaver.from_conn_string(DB_URI)


def get_async_checkpointer():
    """Async checkpointer — required by ainvoke(), which the live FastAPI app
    uses so MCP's async-only tools can run."""
    return AsyncPostgresSaver.from_conn_string(DB_URI)


def main() -> None:
    with get_checkpointer() as checkpointer:
        checkpointer.setup()
        print("Checkpoint tables ready.")


if __name__ == "__main__":
    main()
