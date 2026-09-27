"""Read-only database MCP tool.

Works against any SQL database SQLAlchemy supports (Postgres, MySQL, SQLite, ...)
by changing only the connection string. Exposes schema discovery and safe,
SELECT-only query execution as MCP tools -- no writes, no destructive statements.
"""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, inspect, text

DB_URL = "postgresql+psycopg://refund_admin:changeme_dev_password@localhost:5432/refund_system"
MAX_ROWS = 100

engine = create_engine(DB_URL)

mcp = FastMCP("db-query-tools", stateless_http=True, port=9200)


@mcp.tool()
def list_tables() -> dict:
    """List all tables available in the connected database."""
    inspector = inspect(engine)
    return {"tables": inspector.get_table_names()}


@mcp.tool()
def describe_table(table_name: str) -> dict:
    """Describe a table's columns: name, type, and whether it's nullable."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {
        "columns": [
            {"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]}
            for col in columns
        ]
    }


@mcp.tool()
def run_query(sql: str) -> dict:
    """Run a read-only SELECT query against the database.

    Rejects anything that isn't a single SELECT statement, and caps
    results at MAX_ROWS so a broad query can't return an unbounded result set.
    """
    cleaned = sql.strip()

    if not cleaned.lower().startswith("select"):
        return {"error": "Only SELECT statements are allowed."}

    if ";" in cleaned.rstrip(";"):
        return {"error": "Multiple statements are not allowed."}

    with engine.connect() as conn:
        result = conn.execute(text(cleaned))
        rows = result.mappings().fetchmany(MAX_ROWS)
        return {"rows": [dict(row) for row in rows], "row_count": len(rows)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
