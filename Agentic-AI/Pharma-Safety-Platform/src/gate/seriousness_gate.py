"""
Deterministic seriousness gate.

This is deliberately NOT a model call. It reads structured fields already
extracted from the case (by the LLM extraction step upstream) and decides
seriousness using fixed rules that map directly to the standard ICH
seriousness criteria. Every rule states exactly which field it reads and
why, so this can be audited by a person without reading code.

Design rule enforced here: if a required field for a rule is missing, that
rule does NOT silently pass as "not met" — it is flagged as indeterminate,
and an indeterminate case is treated as serious. Fail-safe on missing
data, same principle used for allergen handling and triage escalation
elsewhere in this portfolio: when uncertain, escalate, never downgrade.
"""

from dataclasses import dataclass, field


SERIOUSNESS_CRITERIA = [
    "death",
    "life_threatening",
    "hospitalization",
    "disability",
    "congenital_anomaly",
    "other_medically_important",
]

# Terms that, if found in the free-text adverse event description, trigger
# the "other medically important" criterion. This list is maintained by
# the safety team, not by engineering — it is the one place free text is
# consulted directly by this deterministic gate, and it is a keyword match,
# not a model judgment.
OTHER_MEDICALLY_IMPORTANT_TERMS = [
    "anaphyla", "overdose", "suicide", "intentional overdose",
    "drug abuse", "drug dependence", "cancer", "carcinoma",
]


@dataclass
class GateInput:
    """The structured fields the gate reads. Anything not provided is
    treated as unknown, not as False — see module docstring."""
    outcome: str | None = None                 # 'death' | 'recovered' | 'ongoing' | None
    life_threatening_flag: bool | None = None
    hospitalized: bool | None = None
    hospitalization_prolonged: bool | None = None
    disability_flag: bool | None = None
    congenital_anomaly_flag: bool | None = None
    adverse_event_text: str = ""


@dataclass
class GateResult:
    seriousness_result: str            # 'serious' | 'non_serious'
    criteria_met: list[str] = field(default_factory=list)
    indeterminate_criteria: list[str] = field(default_factory=list)


def _check_other_medically_important(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in OTHER_MEDICALLY_IMPORTANT_TERMS)


def evaluate_seriousness(data: GateInput) -> GateResult:
    """
    Evaluate each ICH seriousness criterion independently. A case is
    serious if ANY criterion is met OR indeterminate — fail-safe direction,
    not fail-open.
    """
    criteria_met: list[str] = []
    indeterminate: list[str] = []

    # death
    if data.outcome == "death":
        criteria_met.append("death")
    elif data.outcome is None:
        indeterminate.append("death")

    # life-threatening
    if data.life_threatening_flag is True:
        criteria_met.append("life_threatening")
    elif data.life_threatening_flag is None:
        indeterminate.append("life_threatening")

    # hospitalization (initial or prolonged)
    if data.hospitalized is True or data.hospitalization_prolonged is True:
        criteria_met.append("hospitalization")
    elif data.hospitalized is None and data.hospitalization_prolonged is None:
        indeterminate.append("hospitalization")

    # disability
    if data.disability_flag is True:
        criteria_met.append("disability")
    elif data.disability_flag is None:
        indeterminate.append("disability")

    # congenital anomaly
    if data.congenital_anomaly_flag is True:
        criteria_met.append("congenital_anomaly")
    elif data.congenital_anomaly_flag is None:
        indeterminate.append("congenital_anomaly")

    # other medically important — free-text keyword check, always evaluable
    if _check_other_medically_important(data.adverse_event_text):
        criteria_met.append("other_medically_important")

    is_serious = bool(criteria_met) or bool(indeterminate)

    return GateResult(
        seriousness_result="serious" if is_serious else "non_serious",
        criteria_met=criteria_met,
        indeterminate_criteria=indeterminate,
    )


def determine_review_priority(gate_result: GateResult, min_confidence: float,
                               confidence_threshold: float = 0.75,
                               is_novel_product_event_pair: bool = False) -> tuple[bool, str | None]:
    """
    Routing decision: does this case need human review, and at what
    priority? Returns (review_required, priority).

    Deliberately separate from evaluate_seriousness() — seriousness is a
    regulatory fact about the case; routing is an operational decision
    about who needs to look at it. Keeping them apart means a change to
    routing policy (e.g. a different confidence threshold) never risks
    touching the seriousness logic itself.
    """
    if gate_result.seriousness_result == "serious":
        return True, "priority"
    if gate_result.indeterminate_criteria:
        return True, "priority"
    if is_novel_product_event_pair:
        return True, "priority"
    if min_confidence < confidence_threshold:
        return True, "standard"
    return False, None
