"""Input guardrails: block prompt-injection attempts and unsolicited PII
before a message ever reaches an agent. Rule-based on purpose — a lightweight
in-house module rather than a third-party framework, per the project design."""

import re

from wealth_agent.schemas.guardrail import GuardrailResult

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all|any|the) (previous|above|prior) instructions",
        r"disregard (the|your) (system prompt|instructions)",
        r"reveal (your|the) (system prompt|instructions)",
        r"you are now",
        r"act as (?!.*(a\s+)?(financial|wealth)\b)",
        r"jailbreak",
        r"developer mode",
    )
]

PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


def screen_input(text: str) -> GuardrailResult:
    """Flag prompt-injection attempts or unsolicited PII in a user message."""
    reasons = [
        f"possible prompt injection: {p.pattern}"
        for p in INJECTION_PATTERNS
        if p.search(text)
    ] + [f"possible {label} detected" for label, p in PII_PATTERNS.items() if p.search(text)]

    return GuardrailResult(flagged=bool(reasons), reasons=reasons)
