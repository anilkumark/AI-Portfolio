import sys
from pathlib import Path
from datetime import date
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.submission.e2b import ConfirmedCase, generate_e2b_xml, is_well_formed, E2BGenerationError


def _valid_serious_case(**overrides):
    defaults = dict(
        case_id="case-001", patient_age=45, patient_sex="F",
        suspect_product="Drugamab", adverse_event_meddra_code="10019211",
        seriousness_result="serious", seriousness_criteria=["hospitalization"],
        reported_date=date(2026, 3, 10), reviewer_id="reviewer-42",
    )
    defaults.update(overrides)
    return ConfirmedCase(**defaults)


def test_valid_serious_case_produces_well_formed_xml():
    xml = generate_e2b_xml(_valid_serious_case())
    assert is_well_formed(xml)
    assert "case-001" in xml
    assert "hospitalization" in xml


def test_serious_flag_is_1_non_serious_is_2():
    serious_xml = generate_e2b_xml(_valid_serious_case())
    assert "<serious>1</serious>" in serious_xml

    non_serious = _valid_serious_case(
        seriousness_result="non_serious", seriousness_criteria=[], reviewer_id=None,
    )
    non_serious_xml = generate_e2b_xml(non_serious)
    assert "<serious>2</serious>" in non_serious_xml


def test_missing_required_field_refuses_generation():
    incomplete = _valid_serious_case(suspect_product="")
    with pytest.raises(E2BGenerationError, match="suspect_product"):
        generate_e2b_xml(incomplete)


def test_serious_case_without_criteria_refuses_generation():
    bad_case = _valid_serious_case(seriousness_criteria=[])
    with pytest.raises(E2BGenerationError, match="no stated basis"):
        generate_e2b_xml(bad_case)


def test_serious_case_without_reviewer_refuses_generation():
    bad_case = _valid_serious_case(reviewer_id=None)
    with pytest.raises(E2BGenerationError, match="no reviewer_id"):
        generate_e2b_xml(bad_case)


def test_non_serious_case_does_not_require_reviewer():
    case = _valid_serious_case(
        seriousness_result="non_serious", seriousness_criteria=[], reviewer_id=None,
    )
    xml = generate_e2b_xml(case)
    assert is_well_formed(xml)


def test_optional_patient_fields_can_be_absent():
    case = _valid_serious_case(patient_age=None, patient_sex=None)
    xml = generate_e2b_xml(case)
    assert is_well_formed(xml)
    assert "<patientonsetage>" not in xml


def test_malformed_xml_string_detected():
    assert is_well_formed("<ichicsr><unclosed>") is False
    assert is_well_formed("<ichicsr></ichicsr>") is True
