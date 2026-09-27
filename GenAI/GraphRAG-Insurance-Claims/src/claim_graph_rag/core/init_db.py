"""Applies schema.sql to Postgres."""

from pathlib import Path

from claim_graph_rag.core.postgres import get_pg_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def create_schema() -> None:
    conn = get_pg_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text()
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        print("Schema created.")
    finally:
        conn.close()


if __name__ == "__main__":
    create_schema()
