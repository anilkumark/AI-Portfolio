"""Shared chat model factory — every agent uses this instead of repeating the setup."""

from langchain_openai import ChatOpenAI

from wealth_agent.core.config import settings


def get_model(name: str = "gpt-4o-mini") -> ChatOpenAI:
    return ChatOpenAI(model=name, api_key=settings.openai_api_key)
