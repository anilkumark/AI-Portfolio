import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient


def check_groundedness(answer: str, evidence: str) -> dict:
    return asyncio.run(_check_groundedness_async(answer, evidence))


async def _check_groundedness_async(answer: str, evidence: str) -> dict:
    mcp_client = MultiServerMCPClient(
        {
            "fact_check": {
                "url": "http://localhost:9100/mcp",
                "transport": "streamable_http",
            }
        }
    )
    tools = await mcp_client.get_tools()
    check_groundedness_tool = tools[0]
    raw_result = await check_groundedness_tool.ainvoke(
        {"answer": answer, "evidence": evidence}
    )
    return json.loads(raw_result[0]["text"])
