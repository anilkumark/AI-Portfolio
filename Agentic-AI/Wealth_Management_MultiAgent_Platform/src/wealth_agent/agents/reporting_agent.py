"""Reporting Agent: formats gathered facts and approved findings into a
final client-ready report. No lookups or calculations of its own."""

from pathlib import Path

from langgraph.prebuilt import create_react_agent

from wealth_agent.core.llm import get_model

model = get_model()

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "reporting_agent.md"
REPORTING_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

reporting_agent = create_react_agent(
    model, [], prompt=REPORTING_SYSTEM_PROMPT, name="reporting_agent"
)
