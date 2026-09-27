"""Typed models for the human-approval flow."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ApprovalStatus(BaseModel):
    thread_id: str
    order_id: str
    refund_amount: Decimal
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
