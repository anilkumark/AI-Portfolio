"""Extracts structured entities from each document chunk using the LLM."""

import json

from openai import OpenAI

from claim_graph_rag.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)

ENTITY_TYPES = [
    "Coverage",
    "Peril",
    "Exclusion",
    "Condition",
    "PolicySection",
    "Procedure",
]

SYSTEM_PROMPT = f"""You extract structured entities from flood insurance text —
either policy/claims documents, or a customer's question about their claim.

Only extract entities that are explicitly named in the text — never invent one.
Valid entity types: {", ".join(ENTITY_TYPES)}.

IMPORTANT: entity names must be short, canonical concept names, not copied
sentence fragments. Example: if the text says "backs up through sewers or
drains" or "sewer backup", the entity name is "Sewer Backup" either way —
the same real-world concept should always get the same name, whether it
appears in formal document text or a casual question.

If a passage describes a rule that denies or limits coverage under certain
conditions, extract that rule itself as an Exclusion entity, in addition to
the perils and conditions mentioned within it.

Return a JSON object: {{"entities": [{{"name": "...", "type": "..."}}]}}.
If no entities are found, return {{"entities": []}}."""


def extract_entities(chunk_text: str) -> list[dict]:
    response = client.chat.completions.create(
        model=settings.llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk_text},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    return result.get("entities", [])
