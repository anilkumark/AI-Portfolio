"""Insights Agent: RAG over market-commentary and risk-disclosure documents."""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from wealth_agent.core.llm import get_model
from wealth_agent.retrieval.search import search_market_insights

model = get_model()


@tool
def search_insights(query: str) -> list[dict]:
    """Search market-commentary and risk-disclosure documents for relevant guidance."""
    return search_market_insights(query)


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "insights_agent.md"
INSIGHTS_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

insights_agent = create_react_agent(
    model, [search_insights], prompt=INSIGHTS_SYSTEM_PROMPT, name="insights_agent"
)
