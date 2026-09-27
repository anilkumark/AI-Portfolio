import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient


def unwrap(raw):
    """MCP tool results come back as a list of content blocks, e.g.
    [{'type': 'text', 'text': '{"tables": [...]}' }]. This pulls out the
    real JSON and parses it back into a plain Python dict."""
    return json.loads(raw[0]["text"])


async def main():
    mcp_client = MultiServerMCPClient(
        {"db_query": {"url": "http://localhost:9200/mcp", "transport": "streamable_http"}}
    )
    tools = await mcp_client.get_tools()
    print(f"Tools fetched over MCP: {[t.name for t in tools]}\n")

    tool_map = {t.name: t for t in tools}

    tables_raw = await tool_map["list_tables"].ainvoke({})
    tables = unwrap(tables_raw)["tables"]
    print("Tables:", tables)

    first_table = tables[0]
    columns_raw = await tool_map["describe_table"].ainvoke({"table_name": first_table})
    columns = unwrap(columns_raw)["columns"]
    print(f"\nColumns in '{first_table}':", columns)

    result_raw = await tool_map["run_query"].ainvoke({"sql": f"SELECT * FROM {first_table} LIMIT 3"})
    result = unwrap(result_raw)
    print(f"\nSample rows from '{first_table}':", result)

    blocked_raw = await tool_map["run_query"].ainvoke({"sql": f"DROP TABLE {first_table}"})
    blocked = unwrap(blocked_raw)
    print("\nAttempted DROP TABLE (should be blocked):", blocked)


if __name__ == "__main__":
    asyncio.run(main())
