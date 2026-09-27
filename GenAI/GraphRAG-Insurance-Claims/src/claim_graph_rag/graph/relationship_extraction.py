"""Extracts relationships between already-extracted entities."""

import json

from openai import OpenAI

from claim_graph_rag.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)

RELATIONSHIP_TYPES = ["COVERS", "EXCLUDES", "APPLIES_TO", "UNLESS", "REQUIRES"]

SYSTEM_PROMPT = f"""You extract relationships between entities already found in flood insurance text.
You will be given the source text and a list of entities found in it.
Connect entities using only these relationship types: {", ".join(RELATIONSHIP_TYPES)}.
Only use entities from the provided list — never invent a new entity.
Return JSON: {{"relationships": [{{"source": "...", "relationship": "...", "target": "..."}}]}}.
If no relationships are found, return {{"relationships": []}}."""


def extract_relationships(chunk_text: str, entities: list[dict]) -> list[dict]:
    entity_names = [e["name"] for e in entities]
    user_content = f"Text:\n{chunk_text}\n\nEntities found: {entity_names}"

    response = client.chat.completions.create(
        model=settings.llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    return result.get("relationships", [])
