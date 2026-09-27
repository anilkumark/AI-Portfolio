import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    mcp_client = MultiServerMCPClient(
        {
            "fact_check": {
                "url": "http://localhost:9100/mcp",
                "transport": "streamable_http",
            }
        }
    )
    tools = await mcp_client.get_tools()
    print(f"Tools fetched over MCP: {[t.name for t in tools]}")

    check_groundedness = tools[0]

    evidence = "The restocking fee for electronics is 15%, with a minimum of $25 and a maximum of $200."

    grounded_answer = "The restocking fee for electronics is 15%, capped at $200."
    result1 = await check_groundedness.ainvoke(
        {"answer": grounded_answer, "evidence": evidence}
    )
    print("\nGrounded answer test:")
    print(result1)

    ungrounded_answer = "The restocking fee for electronics is 50%, with no maximum."
    result2 = await check_groundedness.ainvoke(
        {"answer": ungrounded_answer, "evidence": evidence}
    )
    print("\nUngrounded answer test:")
    print(result2)


if __name__ == "__main__":
    asyncio.run(main())
