"""Embed chunk text into vectors using OpenAI."""

from openai import OpenAI

from wealth_agent.core.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using OpenAI, return one vector per input text."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
