"""Supervisor Agent: routes refund requests between Validation and Policy agents."""

from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from pathlib import Path
from refund_system.agents.communication_agent import communication_agent
from refund_system.agents.policy_agent import policy_agent
from refund_system.agents.validation_agent import validation_agent
from langgraph.types import interrupt
from langchain_core.tools import tool
import os
import secrets
from langchain_core.runnables import RunnableConfig
from refund_system.communication import gmail_client
from refund_system.db.connection import get_pg_connection

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

model = ChatOpenAI(model="gpt-4o-mini")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "supervisor.md"
SUPERVISOR_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


@tool
def request_human_approval(
    order_id: str, refund_amount: float, reason: str, config: RunnableConfig
) -> str:
    """Pause and request human approval before finalizing a refund above the auto-approval threshold."""
    thread_id = config["configurable"]["thread_id"]

    conn = get_pg_connection()
    try:
        existing = conn.execute(
            "SELECT token FROM pending_approvals WHERE thread_id = %s", (thread_id,)
        ).fetchone()

        if existing is None:
            token = secrets.token_urlsafe(24)
            conn.execute(
                """INSERT INTO pending_approvals (thread_id, token, order_id, refund_amount, reason)
                   VALUES (%s, %s, %s, %s, %s)""",
                (thread_id, token, order_id, refund_amount, reason),
            )
            conn.commit()

            approve_link = (
                f"{API_BASE_URL}/decide/{thread_id}?token={token}&decision=approve"
            )
            deny_link = f"{API_BASE_URL}/decide/{thread_id}?token={token}&decision=deny"
            gmail_client.send_email(
                to=os.environ["REVIEWER_EMAIL"],
                subject=f"Refund approval needed: order {order_id}",
                body=(
                    f"A refund requires your approval.\n\n"
                    f"Order ID: {order_id}\n"
                    f"Refund amount: ${refund_amount:.2f}\n"
                    f"Reason: {reason}\n\n"
                    f"Approve: {approve_link}\n"
                    f"Deny: {deny_link}\n"
                ),
            )
    finally:
        conn.close()

    decision = interrupt(
        {
            "order_id": order_id,
            "refund_amount": refund_amount,
            "reason": reason,
            "message": "Human approval required for this refund.",
        }
    )
    return decision


def build_supervisor(checkpointer=None):
    return create_supervisor(
        agents=[validation_agent, policy_agent, communication_agent],
        model=model,
        tools=[request_human_approval],
        prompt=SUPERVISOR_PROMPT,
    ).compile(checkpointer=checkpointer)


supervisor = build_supervisor()
