"""Risk Calculation & Mitigation Agent: real risk scores + grounded suggestions.
Never authorized to finalize anything — the Supervisor gates its output."""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from wealth_agent.analysis.risk import calculate_risk
from wealth_agent.core.llm import get_model

model = get_model()


@tool
def get_portfolio_risk(portfolio_id: int) -> dict:
    """Calculate a portfolio's risk score and concentration flag."""
    return calculate_risk(portfolio_id)


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "risk_agent.md"
RISK_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

risk_agent = create_react_agent(
    model, [get_portfolio_risk], prompt=RISK_SYSTEM_PROMPT, name="risk_agent"
)
