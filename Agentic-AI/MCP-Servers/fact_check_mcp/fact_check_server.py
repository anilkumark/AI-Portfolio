from mcp.server.fastmcp import FastMCP
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")

mcp = FastMCP("fact-check-tools", stateless_http=True, port=9100)


@mcp.tool()
def check_groundedness(answer: str, evidence: str) -> dict:
    """Check whether an answer is actually supported by the given evidence."""
    prompt = f"""You are a fact-checker. Given the evidence and an answer, determine
if every claim in the answer is directly supported by the evidence.

Evidence:
{evidence}

Answer:
{answer}

Respond with exactly one word first — SUPPORTED or UNSUPPORTED — then a short
reason on the next line."""

    response = model.invoke(prompt)
    lines = response.content.strip().split("\n", 1)
    verdict = lines[0].strip()
    reason = lines[1].strip() if len(lines) > 1 else ""

    return {"grounded": verdict == "SUPPORTED", "reason": reason}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
