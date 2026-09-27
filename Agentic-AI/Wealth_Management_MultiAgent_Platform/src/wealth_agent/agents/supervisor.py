"""Supervisor Agent: routes client questions between specialist agents and
gates any risk-based advice behind human compliance approval."""

import secrets
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import interrupt
from langgraph_supervisor import create_supervisor

from wealth_agent.agents.data_query_agent import build_data_query_agent_mcp, data_query_agent
from wealth_agent.agents.insights_agent import insights_agent
from wealth_agent.agents.reporting_agent import reporting_agent
from wealth_agent.agents.risk_agent import risk_agent
from wealth_agent.agents.stock_position_agent import stock_position_agent
from wealth_agent.communication import gmail_client
from wealth_agent.core.config import settings
from wealth_agent.core.llm import get_model
from wealth_agent.db.connection import get_pg_connection

model = get_model()

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "supervisor.md"
SUPERVISOR_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


@tool
def request_compliance_approval(
    portfolio_id: int, reason: str, config: RunnableConfig
) -> str:
    """Pause and request compliance approval before sharing risk-based advice."""
    thread_id = config["configurable"]["thread_id"]

    conn = get_pg_connection()
    try:
        existing = conn.execute(
            "SELECT token FROM pending_approvals WHERE thread_id = %s", (thread_id,)
        ).fetchone()

        if existing is None:
            token = secrets.token_urlsafe(24)
            conn.execute(
                """INSERT INTO pending_approvals (thread_id, token, portfolio_id, reason)
                   VALUES (%s, %s, %s, %s)""",
                (thread_id, token, portfolio_id, reason),
            )
            conn.commit()

            approve_link = (
                f"{settings.api_base_url}/decide/{thread_id}?token={token}&decision=approve"
            )
            deny_link = (
                f"{settings.api_base_url}/decide/{thread_id}?token={token}&decision=deny"
            )
            gmail_client.send_email(
                to=settings.reviewer_email,
                subject=f"Compliance approval needed: portfolio {portfolio_id}",
                body=(
                    f"Risk-based advice requires your approval.\n\n"
                    f"Portfolio ID: {portfolio_id}\n"
                    f"Reason: {reason}\n\n"
                    f"Approve: {approve_link}\n"
                    f"Deny: {deny_link}\n"
                ),
            )
    finally:
        conn.close()

    decision = interrupt(
        {
            "portfolio_id": portfolio_id,
            "reason": reason,
            "message": "Compliance approval required before sharing this advice.",
        }
    )
    return decision


def _build(agents: list, checkpointer=None):
    return create_supervisor(
        agents=agents,
        model=model,
        tools=[request_compliance_approval],
        prompt=SUPERVISOR_PROMPT,
    ).compile(checkpointer=checkpointer)


def build_supervisor(checkpointer=None):
    """Sync build using local, in-process tools — for direct testing/scripts."""
    return _build(
        [data_query_agent, stock_position_agent, risk_agent, insights_agent, reporting_agent],
        checkpointer,
    )


async def build_supervisor_async(checkpointer=None):
    """Async build for the live app: Data Query Agent sources its tools over
    MCP from the standalone data_tools_server, proving tools work as a
    reusable networked service rather than only local Python imports."""
    mcp_client = MultiServerMCPClient(
        {"data_tools": {"url": "http://localhost:9000/mcp", "transport": "streamable_http"}}
    )
    mcp_tools = await mcp_client.get_tools()
    data_query_agent_mcp = build_data_query_agent_mcp(mcp_tools)
    return _build(
        [data_query_agent_mcp, stock_position_agent, risk_agent, insights_agent, reporting_agent],
        checkpointer,
    )
