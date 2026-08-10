"""Validation Agent: verifies customers, orders, products, and return eligibility."""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pathlib import Path
from refund_system.validation import queries


@tool
def get_customer(customer_id: str) -> dict | None:
    """Look up a customer by ID, including their loyalty tier (Bronze/Silver/Gold/Platinum)."""
    return queries.get_customer(customer_id)


@tool
def get_order(order_id: str) -> dict | None:
    """Look up an order by ID, including product, quantity, dates, and delivery status."""
    return queries.get_order(order_id)


@tool
def get_product(product_id: str) -> dict | None:
    """Look up a product's price, return window, and whether it's fragile or restockable."""
    return queries.get_product(product_id)


@tool
def check_return_eligibility(order_id: str) -> dict:
    """Check whether an order is still within its product's return window, given the order ID."""
    return queries.check_return_eligibility(order_id)


@tool
def get_customer_orders(customer_id: str) -> list[dict]:
    """List all orders for a customer, most recent first — use this when the customer doesn't know their order ID."""
    return queries.get_customer_orders(customer_id)


model = ChatOpenAI(model="gpt-4o-mini")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "validation_agent.md"
VALIDATION_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


TOOLS = [
    get_customer,
    get_order,
    get_product,
    check_return_eligibility,
    get_customer_orders,
]

validation_agent = create_react_agent(
    model, TOOLS, prompt=VALIDATION_SYSTEM_PROMPT, name="validation_agent"
)
