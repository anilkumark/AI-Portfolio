"""Communication Agent: sends refund decision emails to customers."""

from pathlib import Path

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from refund_system.communication import gmail_client
from dotenv import load_dotenv

load_dotenv()


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email to a customer about their refund decision."""
    return gmail_client.send_email(to, subject, body)


model = ChatOpenAI(model="gpt-4o-mini")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "communication_agent.md"
COMMUNICATION_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

TOOLS = [send_email]

communication_agent = create_react_agent(
    model, TOOLS, prompt=COMMUNICATION_SYSTEM_PROMPT, name="communication_agent"
)
