"""FastAPI app: exposes the human-approval decision endpoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from refund_system.agents.supervisor import build_supervisor
from refund_system.memory.checkpointer import get_checkpointer
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from langgraph.types import Command

from refund_system.db.connection import get_pg_connection
import logging

from refund_system.core.logging_config import setup_logging
from refund_system.observability.cost_tracking import UsageTracker
from refund_system.schemas.chat import ChatRequest, ChatResponse
from refund_system.schemas.approval import ApprovalStatus
from refund_system.schemas.cost import ThreadCost

setup_logging()
logger = logging.getLogger("refund_system.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_checkpointer() as checkpointer:
        app.state.supervisor = build_supervisor(checkpointer)
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/decide/{thread_id}", response_class=HTMLResponse)
def decide(thread_id: str, token: str, decision: str):
    logger.info(
        "API /decide received | thread_id=%s | decision=%s", thread_id, decision
    )

    if decision not in ("approve", "deny"):
        raise HTTPException(400, "Invalid decision")

    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pending_approvals WHERE thread_id = %s", (thread_id,)
        ).fetchone()
        if row is None or row["token"] != token:
            logger.warning(
                "API /decide token mismatch or not found | thread_id=%s", thread_id
            )
            raise HTTPException(404, "Approval request not found")
        if row["status"] != "pending":
            logger.info(
                "API /decide already resolved | thread_id=%s | status=%s",
                thread_id,
                row["status"],
            )
            return f"<h2>This request was already {row['status']}.</h2>"

        new_status = "approved" if decision == "approve" else "denied"
        conn.execute(
            "UPDATE pending_approvals SET status = %s, resolved_at = now() WHERE thread_id = %s",
            (new_status, thread_id),
        )
        conn.commit()
        logger.info(
            "API /decide updated status | thread_id=%s | status=%s",
            thread_id,
            new_status,
        )
    finally:
        conn.close()

    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [UsageTracker(thread_id)],
    }
    resume_message = (
        "Approved by reviewer." if decision == "approve" else "Denied by reviewer."
    )
    logger.info("API /decide resuming supervisor graph | thread_id=%s", thread_id)
    app.state.supervisor.invoke(Command(resume=resume_message), config=config)
    logger.info("API /decide resume complete | thread_id=%s", thread_id)

    return (
        f"<h2>Refund request has been {new_status}. The customer will be notified.</h2>"
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(
        "API /chat received message | thread_id=%s | message=%r",
        request.thread_id,
        request.message,
    )

    config = {
        "configurable": {"thread_id": request.thread_id},
        "callbacks": [UsageTracker(request.thread_id)],
    }
    logger.info("API /chat invoking supervisor graph | thread_id=%s", request.thread_id)
    tagged_message = (
        f"[Authenticated Customer ID: {request.customer_id}] {request.message}"
    )
    result = app.state.supervisor.invoke(
        {"messages": [("user", tagged_message)]}, config=config
    )

    if "__interrupt__" in result:
        logger.info(
            "API /chat supervisor PAUSED (human approval required) | thread_id=%s",
            request.thread_id,
        )
        return ChatResponse(
            reply=(
                "This refund needs manager approval before I can finalize it. "
                "I'll follow up here once it's been reviewed."
            ),
            interrupted=True,
        )

    logger.info("API /chat supervisor completed | thread_id=%s", request.thread_id)
    return ChatResponse(reply=result["messages"][-1].content, interrupted=False)


@app.get("/status/{thread_id}", response_model=ApprovalStatus | None)
def status(thread_id: str):
    """Used by the UI to poll whether a pending approval has been resolved yet."""
    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pending_approvals WHERE thread_id = %s", (thread_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return ApprovalStatus(**row)


@app.get("/cost/{thread_id}", response_model=ThreadCost)
def cost(thread_id: str):
    """Real token usage and spend for one conversation thread, summed from every
    recorded LLM call across the supervisor and all three sub-agents."""
    conn = get_pg_connection()
    try:
        row = conn.execute(
            """SELECT
                   COUNT(*) AS call_count,
                   COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                   COALESCE(SUM(cost_usd), 0) AS cost_usd
               FROM llm_usage
               WHERE thread_id = %s""",
            (thread_id,),
        ).fetchone()
    finally:
        conn.close()

    return ThreadCost(thread_id=thread_id, **row)
