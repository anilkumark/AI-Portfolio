"""Typed request/response models for the chat API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    thread_id: str
    customer_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    interrupted: bool
