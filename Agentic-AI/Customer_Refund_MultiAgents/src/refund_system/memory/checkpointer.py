"""Postgres-backed checkpointer for persisting LangGraph agent state."""

import os

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

DB_URI = (
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)


def get_checkpointer():
    """Context manager yielding a PostgresSaver connected to our database."""
    return PostgresSaver.from_conn_string(DB_URI)


def main() -> None:
    with get_checkpointer() as checkpointer:
        checkpointer.setup()
        print("Checkpoint tables ready.")


if __name__ == "__main__":
    main()
