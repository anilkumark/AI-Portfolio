"""
Phase 6 (optional) -- natural-language query over the unified store. A
plain-English question in, a plain-English answer out, with the generated
SQL always returned alongside the answer so the answer can be checked
against what was actually asked, not taken on faith.

Two layers of read-only enforcement, per the design: the database
credential this connects with should have no write grant at all (a
deployment/IAM concern, not something Python can guarantee on its own) --
and, defense in depth, every generated query is validated here before
execution, rejecting anything that isn't a single SELECT confined to the
omop schema. A flawed generated query should fail the validator, not reach
the database at all.

The validator is pure and tested without a database or Bedrock call. The
end-to-end ask() function needs both.
"""

import re
from dataclasses import dataclass

ALLOWED_SCHEMA_PREFIX = "omop."

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "grant", "revoke", "exec", "execute", "call", "merge", "copy",
    "into", "vacuum", "reindex",
]

NL_TO_SQL_SYSTEM_PROMPT = """You translate a plain-English drug-safety question into a single read-only
PostgreSQL SELECT statement against the omop schema (omop.person, omop.condition_occurrence,
omop.drug_exposure, omop.observation). Only reference tables in the omop schema. Never write more
than one statement. Never use INSERT, UPDATE, DELETE, or any DDL. Return only the SQL, nothing else."""

NL_SUMMARY_SYSTEM_PROMPT = """You explain a SQL query result in plain English for a medical affairs
or epidemiology reviewer. State only what the data shows. Do not add clinical interpretation,
causal claims, or recommendations beyond what the numbers themselves state."""


class UnsafeQueryError(Exception):
    """Raised when a generated query fails the read-only / schema-scope
    check. This must never be caught and silently retried with a looser
    check -- an unsafe query is refused, not worked around."""


@dataclass
class NLQueryResult:
    question: str
    generated_sql: str
    row_count: int
    answer: str


def validate_query_is_safe(sql: str) -> None:
    """Raises UnsafeQueryError if the query isn't a single, schema-scoped
    SELECT. Pure, deterministic, no database or network call."""
    normalized = sql.strip().rstrip(";").strip()

    if not normalized:
        raise UnsafeQueryError("Empty query.")

    statements = [s for s in normalized.split(";") if s.strip()]
    if len(statements) != 1:
        raise UnsafeQueryError(
            f"Expected exactly one statement, found {len(statements)} -- "
            "statement chaining is not permitted."
        )

    lowered = normalized.lower()
    if not lowered.lstrip().startswith("select"):
        raise UnsafeQueryError("Query must be a SELECT statement.")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeQueryError(f"Query contains a forbidden keyword: '{keyword}'.")

    table_refs = re.findall(r"\bfrom\s+([a-zA-Z0-9_.]+)|\bjoin\s+([a-zA-Z0-9_.]+)", lowered)
    referenced_tables = [t for pair in table_refs for t in pair if t]

    if not referenced_tables:
        raise UnsafeQueryError("Query does not reference any table.")

    out_of_scope = [t for t in referenced_tables if not t.startswith(ALLOWED_SCHEMA_PREFIX)]
    if out_of_scope:
        raise UnsafeQueryError(
            f"Query references table(s) outside the omop schema: {out_of_scope}. "
            "The NL query layer is scoped to omop.* only."
        )


def generate_sql(question: str) -> str:
    """Single Bedrock call: NL question -> SQL. REQUIRES AWS credentials."""
    import boto3

    client = boto3.client("bedrock-runtime")
    response = client.converse(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        system=[{"text": NL_TO_SQL_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": question}]}],
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def summarize_result(question: str, sql: str, rows: list[dict]) -> str:
    """Single Bedrock call: SQL result -> plain-English summary. REQUIRES
    AWS credentials."""
    import boto3

    client = boto3.client("bedrock-runtime")
    user_message = f"Question: {question}\n\nSQL run: {sql}\n\nResult rows: {rows}"
    response = client.converse(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        system=[{"text": NL_SUMMARY_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def ask(question: str) -> NLQueryResult:
    """Full NL -> SQL -> execute -> summarize round trip. REQUIRES AWS
    credentials and a live, read-only-scoped Postgres connection. The
    generated SQL is always carried through to the final result, whether
    execution succeeds or the query gets rejected by validate_query_is_safe."""
    from src.common.db import get_connection

    sql = generate_sql(question)
    validate_query_is_safe(sql)  # raises UnsafeQueryError, uncaught -- a rejected query never runs

    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()

    answer = summarize_result(question, sql, rows)

    return NLQueryResult(question=question, generated_sql=sql, row_count=len(rows), answer=answer)
