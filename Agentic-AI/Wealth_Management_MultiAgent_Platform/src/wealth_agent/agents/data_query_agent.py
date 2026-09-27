"""Data Query Agent: looks up real client/account/portfolio facts. No LLM-generated SQL."""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from wealth_agent.core.llm import get_model
from wealth_agent.data_query import queries
from wealth_agent.memory.client_profile import get_notes


@tool
def get_client(client_id: int) -> dict | None:
    """Look up a client's basic info by ID, including their risk profile."""
    return queries.get_client(client_id)


@tool
def get_client_accounts(client_id: int) -> list[dict]:
    """List all accounts belonging to a client."""
    return queries.get_client_accounts(client_id)


@tool
def get_client_portfolios(client_id: int) -> list[dict]:
    """List all portfolios belonging to a client."""
    return queries.get_client_portfolios(client_id)


@tool
def get_portfolio_holdings(portfolio_id: int) -> list[dict]:
    """List a portfolio's actual holdings — asset name, type, value, and allocation percentage."""
    return queries.get_portfolio_holdings(portfolio_id)


@tool
def get_client_transactions(client_id: int) -> list[dict]:
    """List a client's recent transactions across all their accounts, most recent first."""
    return queries.get_client_transactions(client_id)


@tool
def get_client_history(client_id: int) -> list[dict]:
    """Look up durable notes about a client from past conversations (e.g. prior risk reviews)."""
    return get_notes(client_id)


# create_react_agent is the LangGraph function that actually builds the agent.
#  It takes a model (gpt-4o-mini),
# a list of tools, and a system prompt, and returns a working agent
# that can read a message, decide which tool(s) to call, execute them, and respond — the same "ReAct" tool-calling loop we used for every agent in the refund project (Validation, Policy, Communication). This is the standard building block for any single scoped agent in LangGraph.

model = get_model()

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "data_query_agent.md"
DATA_QUERY_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

TOOLS = [
    get_client,
    get_client_accounts,
    get_client_portfolios,
    get_portfolio_holdings,
    get_client_transactions,
    get_client_history,
]

data_query_agent = create_react_agent(
    model, TOOLS, prompt=DATA_QUERY_SYSTEM_PROMPT, name="data_query_agent"
)


def build_data_query_agent_mcp(mcp_tools: list):
    """Build the same agent, but sourcing its tools over MCP instead of local
    Python imports — proves data_query's tools work as a reusable, networked
    service, not just functions bundled into this one app."""
    return create_react_agent(
        model, mcp_tools, prompt=DATA_QUERY_SYSTEM_PROMPT, name="data_query_agent"
    )
