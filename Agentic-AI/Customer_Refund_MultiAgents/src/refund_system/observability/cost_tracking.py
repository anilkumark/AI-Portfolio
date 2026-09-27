"""Per-thread OpenAI token usage and cost, recorded from real API responses."""

from langchain_core.callbacks import BaseCallbackHandler

from refund_system.db.connection import get_pg_connection

# Published OpenAI per-1M-token rates (USD) for the models this system calls.
PRICING = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "text-embedding-3-small": {"prompt": 0.02, "completion": 0.0},
}


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING.get(model, PRICING["gpt-4o-mini"])
    return (prompt_tokens / 1_000_000) * rates["prompt"] + (
        completion_tokens / 1_000_000
    ) * rates["completion"]


def record_usage(
    thread_id: str, model: str, prompt_tokens: int, completion_tokens: int
) -> None:
    cost = compute_cost(model, prompt_tokens, completion_tokens)
    conn = get_pg_connection()
    try:
        conn.execute(
            """INSERT INTO llm_usage (thread_id, model, prompt_tokens, completion_tokens, cost_usd)
               VALUES (%s, %s, %s, %s, %s)""",
            (thread_id, model, prompt_tokens, completion_tokens, cost),
        )
        conn.commit()
    finally:
        conn.close()


class UsageTracker(BaseCallbackHandler):
    """LangChain callback: records real token usage for every chat-model call
    made anywhere inside one supervisor.invoke() — routing, validation, policy,
    and communication all propagate through the same config, so one tracker
    per request captures the full graph run."""

    def __init__(self, thread_id: str):
        self.thread_id = thread_id

    def on_llm_end(self, response, **kwargs) -> None:
        llm_output = response.llm_output or {}
        usage = llm_output.get("token_usage")
        if not usage:
            return
        record_usage(
            self.thread_id,
            llm_output.get("model_name", "gpt-4o-mini"),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )
