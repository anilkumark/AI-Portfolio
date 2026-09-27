"""
Reviewer workbench API. Per the design document, Section 7: this is the
one interface people interact with directly. Reviewer identity comes from
the authenticated session (a verified Cognito ID token), never from the
request body.

REQUIRES: a live Postgres instance, a provisioned Cognito User Pool
(COGNITO_REGION / COGNITO_USER_POOL_ID / COGNITO_APP_CLIENT_ID set), and a
compiled LangGraph graph (src/workflow/graph.py). Cannot be executed in
this environment.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from langgraph.types import Command

from src.workflow.graph import build_graph
from src.common.auth import verify_reviewer_token, TokenVerificationError
from src.common.db import get_connection

app = FastAPI(title="Post-Market Safety Platform — Reviewer Workbench")

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def get_authenticated_reviewer_id(authorization: str = Header(...)) -> str:
    """The ONE place reviewer identity comes from — never from the request
    body, so a decision can never be misattributed even if a request were
    altered in transit. Verifies a real Cognito ID token; any failure
    (missing header, bad signature, expired token, wrong audience) is a
    401, not a fallback identity."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header (expected 'Bearer <token>').")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_reviewer_token(token)
    except TokenVerificationError as e:
        raise HTTPException(401, f"Token verification failed: {e}") from e


class FieldCorrection(BaseModel):
    field: str
    corrected_value: str


class ReviewDecision(BaseModel):
    field_corrections: list[FieldCorrection] = []
    confirmed_meddra_code: str
    decision: str  # 'approve' | 'reject'
    notes: str = ""


@app.get("/cases/pending")
def list_pending_cases(queue: str = "priority"):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.case_id, c.received_at, c.seriousness_result, c.field_confidence
               FROM operational.case_records c
               JOIN operational.pending_reviews p ON p.case_id = c.case_id
               WHERE p.priority = %s
               ORDER BY c.received_at ASC""",
            (queue,),
        ).fetchall()
    return rows


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM operational.case_records WHERE case_id = %s", (case_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "case not found")
    return row


@app.post("/cases/{case_id}/review")
def submit_review(
    case_id: str,
    decision: ReviewDecision,
    reviewer_id: str = Depends(get_authenticated_reviewer_id),
):
    with get_connection() as conn:
        thread_row = conn.execute(
            "SELECT thread_id FROM operational.pending_reviews WHERE case_id = %s",
            (case_id,),
        ).fetchone()
    if not thread_row:
        raise HTTPException(404, "no pending review for this case")

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_row["thread_id"]}}

    result = graph.invoke(
        Command(resume={
            "reviewer_id": reviewer_id,
            "decision": decision.decision,
            "confirmed_meddra_code": decision.confirmed_meddra_code,
        }),
        config=config,
    )

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO operational.audit_log (case_id, event_type, actor, after_value)
               VALUES (%s, 'review_decided', %s, %s)""",
            (case_id, reviewer_id, decision.decision),
        )
        conn.execute(
            "DELETE FROM operational.pending_reviews WHERE case_id = %s", (case_id,)
        )
        conn.commit()

    return {"case_id": case_id, "status": "resumed", "final_state": result}


@app.get("/health")
def health():
    return {"status": "ok"}
