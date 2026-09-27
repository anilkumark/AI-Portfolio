"""
The seriousness gate has no acceptable error rate per the design. Every
ICH criterion gets its own test, plus the fail-safe-on-missing-data
behaviour gets tested explicitly, because that is the property the whole
gate depends on.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gate.seriousness_gate import (
    GateInput, evaluate_seriousness, determine_review_priority
)


def test_death_triggers_serious():
    result = evaluate_seriousness(GateInput(
        outcome="death", life_threatening_flag=False, hospitalized=False,
        disability_flag=False, congenital_anomaly_flag=False,
    ))
    assert result.seriousness_result == "serious"
    assert "death" in result.criteria_met


def test_fully_non_serious_case():
    result = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=False,
        hospitalization_prolonged=False, disability_flag=False,
        congenital_anomaly_flag=False, adverse_event_text="mild headache",
    ))
    assert result.seriousness_result == "non_serious"
    assert result.criteria_met == []
    assert result.indeterminate_criteria == []


def test_hospitalization_triggers_serious():
    result = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=True,
        disability_flag=False, congenital_anomaly_flag=False,
    ))
    assert result.seriousness_result == "serious"
    assert "hospitalization" in result.criteria_met


def test_missing_field_is_indeterminate_not_false():
    """The core fail-safe property. A field that was never extracted must
    not be silently treated as 'this criterion was not met'."""
    result = evaluate_seriousness(GateInput(outcome=None))
    assert "death" in result.indeterminate_criteria
    assert result.seriousness_result == "serious"


def test_all_fields_missing_is_serious():
    result = evaluate_seriousness(GateInput())
    assert result.seriousness_result == "serious"
    assert len(result.indeterminate_criteria) == 5  # all but the free-text check


def test_other_medically_important_keyword_match():
    result = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=False,
        hospitalization_prolonged=False, disability_flag=False,
        congenital_anomaly_flag=False,
        adverse_event_text="Patient experienced anaphylactic reaction after dosing.",
    ))
    assert result.seriousness_result == "serious"
    assert "other_medically_important" in result.criteria_met


def test_routing_serious_case_is_priority():
    gate = evaluate_seriousness(GateInput(outcome="death"))
    review_required, priority = determine_review_priority(gate, min_confidence=0.99)
    assert review_required is True
    assert priority == "priority"


def test_routing_indeterminate_case_is_priority_even_if_confidence_high():
    """An indeterminate case must route to priority review regardless of
    how confident the extraction was on the fields it DID get — confidence
    on present fields says nothing about the missing one."""
    gate = evaluate_seriousness(GateInput(outcome=None))
    review_required, priority = determine_review_priority(gate, min_confidence=0.99)
    assert review_required is True
    assert priority == "priority"


def test_routing_low_confidence_non_serious_case_is_standard_review():
    gate = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=False,
        hospitalization_prolonged=False, disability_flag=False,
        congenital_anomaly_flag=False, adverse_event_text="mild rash",
    ))
    review_required, priority = determine_review_priority(gate, min_confidence=0.5)
    assert review_required is True
    assert priority == "standard"


def test_routing_clean_confident_non_serious_case_needs_no_review():
    gate = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=False,
        hospitalization_prolonged=False, disability_flag=False,
        congenital_anomaly_flag=False, adverse_event_text="mild rash",
    ))
    review_required, priority = determine_review_priority(gate, min_confidence=0.95)
    assert review_required is False
    assert priority is None


def test_novel_product_event_pair_forces_priority_review():
    gate = evaluate_seriousness(GateInput(
        outcome="recovered", life_threatening_flag=False, hospitalized=False,
        hospitalization_prolonged=False, disability_flag=False,
        congenital_anomaly_flag=False, adverse_event_text="mild rash",
    ))
    review_required, priority = determine_review_priority(
        gate, min_confidence=0.99, is_novel_product_event_pair=True
    )
    assert review_required is True
    assert priority == "priority"
