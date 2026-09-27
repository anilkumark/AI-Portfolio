"""Policy Agent: interprets company refund/return policy documents."""

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pathlib import Path
from refund_system.retrieval import search


@tool
def search_policy(query: str, config: RunnableConfig) -> list[dict]:
    """Search company refund/return policy documents for rules relevant to a natural-language question."""
    return search.search_policy(query, config=config)


model = ChatOpenAI(model="gpt-4o-mini")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "policy_agent.md"
POLICY_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


TOOLS = [search_policy]

policy_agent = create_react_agent(
    model, TOOLS, prompt=POLICY_SYSTEM_PROMPT, name="policy_agent"
)
