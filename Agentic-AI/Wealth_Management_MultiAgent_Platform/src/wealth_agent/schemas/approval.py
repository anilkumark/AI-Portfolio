"""Typed models for the compliance-approval flow."""

from datetime import datetime

from pydantic import BaseModel


class ApprovalStatus(BaseModel):
    thread_id: str
    portfolio_id: int
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
