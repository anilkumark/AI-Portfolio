import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from wealth_agent.agents.data_query_agent import build_data_query_agent_mcp


async def main():
    mcp_client = MultiServerMCPClient(
        {
            "data_tools": {
                "url": "http://localhost:9000/mcp",
                "transport": "streamable_http",
            }
        }
    )
    mcp_tools = await mcp_client.get_tools()
    print(f"Tools fetched over MCP: {[t.name for t in mcp_tools]}")

    agent = build_data_query_agent_mcp(mcp_tools)
    result = await agent.ainvoke(
        {"messages": [("user", "List all accounts for client 1.")]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
