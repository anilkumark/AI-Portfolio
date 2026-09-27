"""FastAPI app: exposes the chat and compliance-decision endpoints.

Run via `python -m wealth_agent.api.run_server`, not `uvicorn ...` directly —
the Windows event-loop policy fix (needed for the async Postgres checkpointer)
has to happen before uvicorn starts, which run_server.py handles."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from langgraph.types import Command

from wealth_agent.agents.supervisor import build_supervisor_async
from wealth_agent.core.logging_config import setup_logging
from wealth_agent.db.connection import get_pg_connection
from wealth_agent.governance.usage_tracking import log_run_usage
from wealth_agent.guardrails.input_guardrails import screen_input
from wealth_agent.guardrails.output_guardrails import apply_disclaimer, screen_output
from wealth_agent.memory.checkpointer import get_async_checkpointer
from wealth_agent.memory.client_profile import add_note
from wealth_agent.schemas.approval import ApprovalStatus
from wealth_agent.schemas.chat import ChatRequest, ChatResponse

setup_logging()
logger = logging.getLogger("wealth_agent.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with get_async_checkpointer() as checkpointer:
        app.state.supervisor = await build_supervisor_async(checkpointer)
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    logger.info("API /chat received | thread_id=%s", request.thread_id)

    input_check = screen_input(request.message)
    if input_check.flagged:
        logger.warning(
            "API /chat input guardrail BLOCKED | thread_id=%s | reasons=%s",
            request.thread_id,
            input_check.reasons,
        )
        return ChatResponse(
            reply="I can't process that message. Please rephrase without sensitive personal details or attempts to override my instructions.",
            interrupted=False,
        )

    config = {"configurable": {"thread_id": request.thread_id}}
    result = await app.state.supervisor.ainvoke(
        {"messages": [("user", request.message)]}, config=config
    )
    log_run_usage(request.thread_id, result["messages"])

    if "__interrupt__" in result:
        logger.info(
            "API /chat PAUSED (compliance approval required) | thread_id=%s",
            request.thread_id,
        )
        return ChatResponse(
            reply=(
                "This advice needs compliance approval before I can share it. "
                "I'll follow up here once it's been reviewed."
            ),
            interrupted=True,
        )

    reply = result["messages"][-1].content
    output_check = screen_output(reply)
    if output_check.flagged:
        logger.warning(
            "API /chat output guardrail auto-corrected | thread_id=%s | reasons=%s",
            request.thread_id,
            output_check.reasons,
        )
        reply = apply_disclaimer(reply)

    logger.info("API /chat completed | thread_id=%s", request.thread_id)
    return ChatResponse(reply=reply, interrupted=False)


@app.get("/decide/{thread_id}", response_class=HTMLResponse)
async def decide(thread_id: str, token: str, decision: str):
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
            raise HTTPException(404, "Approval request not found")
        if row["status"] != "pending":
            return f"<h2>This request was already {row['status']}.</h2>"

        new_status = "approved" if decision == "approve" else "denied"
        conn.execute(
            "UPDATE pending_approvals SET status = %s, resolved_at = now() WHERE thread_id = %s",
            (new_status, thread_id),
        )
        conn.commit()

        client_row = conn.execute(
            "SELECT client_id FROM portfolios WHERE portfolio_id = %s", (row["portfolio_id"],)
        ).fetchone()
    finally:
        conn.close()

    if client_row is not None:
        add_note(
            client_row["client_id"],
            f"Risk advice for portfolio {row['portfolio_id']} was {new_status}. Reason: {row['reason']}",
        )

    config = {"configurable": {"thread_id": thread_id}}
    resume_message = (
        "Approved by reviewer." if decision == "approve" else "Denied by reviewer."
    )
    await app.state.supervisor.ainvoke(Command(resume=resume_message), config=config)

    return f"<h2>Request has been {new_status}. The client will be notified.</h2>"


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
