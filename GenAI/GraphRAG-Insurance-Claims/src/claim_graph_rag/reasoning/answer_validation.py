"""Validates a generated answer against the source facts it was built from —
catches contradictions or reversed logic before an answer reaches a customer."""

import json

from openai import OpenAI

from claim_graph_rag.core.config import settings
from claim_graph_rag.retrieval.context_builder import build_context

client = OpenAI(api_key=settings.openai_api_key)

VALIDATION_PROMPT = """You are a fact-checker. Given source facts and a generated
answer, check whether the answer is fully consistent with the facts — no
contradictions, no reversed logic, no claims the facts don't support.

Respond with JSON: {"valid": true/false, "issues": ["..."]}
If fully consistent, return {"valid": true, "issues": []}."""


def validate_answer(question: str, answer: str, context: dict) -> dict:
    facts_text = "\n".join(
        f"- {f['entity']} --{f['relationship']}--> {f['related_entity']}"
        for f in context["graph_facts"]
    )
    chunks_text = "\n\n".join(c["content"] for c in context["text_chunks"])

    user_content = f"""Source facts:
{facts_text}

Source excerpts:
{chunks_text}

Generated answer:
{answer}"""

    response = client.chat.completions.create(
        model=settings.llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": VALIDATION_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    question = "Why was my claim rejected even though the policy covers sewer backup?"
    bad_answer = (
        "Your claim was likely rejected because the sewer backup was deemed to be "
        "caused by a flood, which is an exclusion under your policy."
    )
    result = validate_answer(question, bad_answer)
    print(result)
