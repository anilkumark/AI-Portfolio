"""Typed model for per-thread cost reporting."""

from decimal import Decimal

from pydantic import BaseModel


class ThreadCost(BaseModel):
    thread_id: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
