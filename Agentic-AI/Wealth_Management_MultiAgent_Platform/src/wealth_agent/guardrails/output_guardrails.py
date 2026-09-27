"""Output guardrails: catch risk/advice content missing its required
disclaimer before it reaches a client."""

import re

from wealth_agent.schemas.guardrail import GuardrailResult

RISK_KEYWORDS = re.compile(r"\b(risk score|mitigat|concentrat)\w*", re.IGNORECASE)
DISCLAIMER_PHRASE = "not a guarantee of future performance"


def screen_output(text: str) -> GuardrailResult:
    """Flag risk-related output that's missing the mandatory disclaimer."""
    if RISK_KEYWORDS.search(text) and DISCLAIMER_PHRASE not in text.lower():
        return GuardrailResult(
            flagged=True, reasons=["risk/mitigation content missing required disclaimer"]
        )
    return GuardrailResult(flagged=False, reasons=[])


def apply_disclaimer(text: str) -> str:
    """Append the disclaimer if risk content is present but the check flagged it missing."""
    return f"{text}\n\nThis report is based on current holdings and is not a guarantee of future performance."
