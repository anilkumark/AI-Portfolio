"""Typed result for a guardrail check."""

from pydantic import BaseModel


class GuardrailResult(BaseModel):
    flagged: bool
    reasons: list[str]
