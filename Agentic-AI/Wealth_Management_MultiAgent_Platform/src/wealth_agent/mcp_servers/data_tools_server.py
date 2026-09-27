"""MCP server: exposes the data-query functions as reusable MCP tools,
callable by any MCP-compatible client (this platform's agents, or a
completely different system) over HTTP — not just as local Python imports."""

from mcp.server.fastmcp import FastMCP

from wealth_agent.data_query import queries
from wealth_agent.memory.client_profile import get_notes

mcp = FastMCP("wealth-data-tools", stateless_http=True, port=9000)


@mcp.tool()
def get_client(client_id: int) -> dict | None:
    """Look up a client's basic info by ID, including their risk profile."""
    return queries.get_client(client_id)


@mcp.tool()
def get_client_accounts(client_id: int) -> list[dict]:
    """List all accounts belonging to a client."""
    return queries.get_client_accounts(client_id)


@mcp.tool()
def get_client_portfolios(client_id: int) -> list[dict]:
    """List all portfolios belonging to a client."""
    return queries.get_client_portfolios(client_id)


@mcp.tool()
def get_portfolio_holdings(portfolio_id: int) -> list[dict]:
    """List a portfolio's actual holdings — asset name, type, value, and allocation percentage."""
    return queries.get_portfolio_holdings(portfolio_id)


@mcp.tool()
def get_client_transactions(client_id: int) -> list[dict]:
    """List a client's recent transactions across all their accounts, most recent first."""
    return queries.get_client_transactions(client_id)


@mcp.tool()
def get_client_history(client_id: int) -> list[dict]:
    """Look up durable notes about a client from past conversations (e.g. prior risk reviews)."""
    return get_notes(client_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
