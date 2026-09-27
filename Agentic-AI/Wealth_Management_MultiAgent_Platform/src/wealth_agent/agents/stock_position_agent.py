"""Stock Position Analysis Agent: real portfolio concentration metrics only."""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from wealth_agent.analysis.stock_position import analyze_portfolio_composition
from wealth_agent.core.llm import get_model

model = get_model()


@tool
def analyze_portfolio(portfolio_id: int) -> dict:
    """Analyze a portfolio's composition — allocation by asset type and largest single holding."""
    return analyze_portfolio_composition(portfolio_id)


PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "stock_position_agent.md"
)
STOCK_POSITION_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

TOOLS = [analyze_portfolio]

stock_position_agent = create_react_agent(
    model, TOOLS, prompt=STOCK_POSITION_SYSTEM_PROMPT, name="stock_position_agent"
)
