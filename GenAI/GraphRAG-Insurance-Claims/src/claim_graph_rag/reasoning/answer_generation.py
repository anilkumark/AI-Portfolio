"""Generates the final answer using graph facts + retrieved text, grounded
only in what was actually found — not the model's own memory."""

from openai import OpenAI

from langsmith.wrappers import wrap_openai
from openai import OpenAI

from claim_graph_rag.core.config import settings

client = wrap_openai(OpenAI(api_key=settings.openai_api_key))


SYSTEM_PROMPT = """You are an insurance claims assistant. Answer the customer's
question using ONLY the graph facts and document excerpts provided below —
never from your own general knowledge. If the provided information doesn't
fully answer the question, say so honestly rather than guessing.

IMPORTANT — pay careful attention to "excluded unless" logic, which is easy
to get backwards: when a rule says "X is excluded unless Y is true," it means
X is NOT covered by default, and Y is the exception that RESTORES coverage.
So if Y is true, the claim IS covered — not rejected.

Example: "Sewer backup is excluded unless a flood is the proximate cause."
- If a flood WAS the proximate cause -> the exclusion does NOT apply -> COVERED.
- If a flood was NOT the proximate cause -> the exclusion DOES apply -> NOT covered.
Do not reverse this logic.

Cite specific facts and page numbers where relevant."""


def generate_answer(question: str, context: dict) -> str:
    facts_text = "\n".join(
        f"- {f['entity']} --{f['relationship']}--> {f['related_entity']} ({f['related_type']})"
        for f in context["graph_facts"]
    )
    chunks_text = "\n\n".join(
        f"[{c['document']} p.{c['page_number']}]\n{c['content']}"
        for c in context["text_chunks"]
    )

    user_content = f"""Question: {question}

Graph facts:
{facts_text}

Document excerpts:
{chunks_text}"""

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    answer = generate_answer(
        "Why was my claim rejected even though the policy covers sewer backup?"
    )
    print(answer)
