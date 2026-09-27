from src.omop.loader import CaseForLoad, build_omop_rows


def test_case_report_produces_person_drug_condition_and_observation_rows():
    case = CaseForLoad(
        case_id="CASE-001",
        source_type="case_report",
        patient_age=54,
        patient_sex="male",
        suspect_product="ExampleDrugX",
        concomitant_drugs=["ExampleDrugY"],
        adverse_event_text="cardiac arrest",
        adverse_event_meddra_code="10007515",
        event_date="2026-09-10",
        seriousness_result="serious",
    )
    rows = build_omop_rows(case)

    assert rows["person"]["sex"] == "male"
    assert len(rows["drugs"]) == 2
    assert rows["drugs"][0]["is_suspect_product"] is True
    assert rows["drugs"][0]["drug_source_value"] == "ExampleDrugX"
    assert rows["drugs"][1]["is_suspect_product"] is False
    assert rows["condition"]["condition_source_value"] == "cardiac arrest"
    assert rows["observation"]["value_as_string"] == "serious"


def test_ehr_extract_has_no_observation_row():
    case = CaseForLoad(
        case_id="CASE-002",
        source_type="ehr_extract",
        patient_age=40,
        patient_sex="female",
        suspect_product="ExampleDrugZ",
        adverse_event_text=None,
        event_date="2026-09-10",
        seriousness_result=None,  # EHR extracts never go through the seriousness gate
    )
    rows = build_omop_rows(case)

    assert rows["observation"] is None
    assert rows["condition"] is None
    assert len(rows["drugs"]) == 1


def test_no_concomitant_drugs_still_produces_suspect_drug_row():
    case = CaseForLoad(
        case_id="CASE-003",
        source_type="case_report",
        patient_age=None,
        patient_sex=None,
        suspect_product="ExampleDrugX",
    )
    rows = build_omop_rows(case)
    assert len(rows["drugs"]) == 1
    assert rows["drugs"][0]["is_suspect_product"] is True
