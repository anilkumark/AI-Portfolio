"""
Runs every locally-executable pipeline step against the 8 real sample PDFs:
classify -> extract text -> [SIMULATED Bedrock extraction, clearly labeled] ->
seriousness gate -> dedup -> OMOP load -> E2B generation (serious cases) ->
real signal detection against the accumulated data.

The only step not real here is the Bedrock extraction call itself -- there
are no AWS credentials in this environment. Its output is hand-written to
match exactly what the real document says (the documents were authored
for this test, so the "ground truth" is simply what's in them), in the
same shape extract.py's EXTRACTION_SCHEMA expects. Everything after that
point -- gate, dedup, OMOP, E2B, signal detection -- is 100% real code
running against a real local Postgres instance.
"""

import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")

from src.ingestion.classify import classify_document
from src.ingestion.pdf_extract import extract_text_from_pdf
from src.gate.seriousness_gate import GateInput, evaluate_seriousness, determine_review_priority
from src.dedup.dedup import CandidateRecord, find_duplicate
from src.omop.loader import CaseForLoad, omop_load
from src.submission.e2b import ConfirmedCase, generate_e2b_xml
from src.analytics.signal_detection import run_signal_detection
from src.common.db import get_connection

# SIMULATED Bedrock output -- what a real extraction call would return for
# each document, hand-matched to the real text each PDF actually contains.
SIMULATED_EXTRACTIONS = {
    "case_001_drugx_cardiac_arrest_a.pdf": {
        "label": "DEMO-CASE-001", "patient_id": "PT-JD-001", "patient_age": 54, "patient_sex": "male",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "cardiac arrest",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": True,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.95, "suspect_product": 0.98, "hospitalized": 0.9},
        "meddra_code": "10007515",
    },
    "case_002_drugx_cardiac_arrest_b.pdf": {
        "label": "DEMO-CASE-002", "patient_id": "PT-MS-002", "patient_age": 61, "patient_sex": "female",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "cardiac arrest",
        "outcome": "recovered", "life_threatening_flag": True, "hospitalized": True,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.96, "suspect_product": 0.97, "hospitalized": 0.92},
        "meddra_code": "10007515",
    },
    "case_003_drugx_cardiac_arrest_c.pdf": {
        "label": "DEMO-CASE-003", "patient_id": "PT-TK-003", "patient_age": 48, "patient_sex": "male",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "cardiac arrest",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": True,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.94, "suspect_product": 0.96, "hospitalized": 0.91},
        "meddra_code": "10007515",
    },
    "case_009_drugx_cardiac_arrest_d.pdf": {
        "label": "DEMO-CASE-009", "patient_id": "PT-FW-009", "patient_age": 59, "patient_sex": "male",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "cardiac arrest",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": True,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.95, "suspect_product": 0.97, "hospitalized": 0.92},
        "meddra_code": "10007515",
    },
    "case_010_drugx_cardiac_arrest_e.pdf": {
        "label": "DEMO-CASE-010", "patient_id": "PT-SO-010", "patient_age": 52, "patient_sex": "female",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "cardiac arrest",
        "outcome": "recovered", "life_threatening_flag": True, "hospitalized": True,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.96, "suspect_product": 0.98, "hospitalized": 0.93},
        "meddra_code": "10007515",
    },
    "case_004_drugx_mild_nausea.pdf": {
        "label": "DEMO-CASE-004", "patient_id": "PT-AK-004", "patient_age": 31, "patient_sex": "female",
        "suspect_product": "ExampleDrugX", "adverse_event_text": "nausea",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": False,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.9, "suspect_product": 0.97, "hospitalized": 0.95},
        "meddra_code": "10028813",
    },
    "case_005_drugz_severe_skin_reaction.pdf": {
        "label": "DEMO-CASE-005", "patient_id": "PT-RM-005", "patient_age": 67, "patient_sex": "male",
        "suspect_product": "ExampleDrugZ", "adverse_event_text": "toxic epidermal necrolysis",
        "outcome": "ongoing", "life_threatening_flag": True, "hospitalized": True,
        "hospitalization_prolonged": True, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.88, "suspect_product": 0.95, "hospitalized": 0.9},
        "meddra_code": "10044223",
    },
    "case_006_drugy_headache.pdf": {
        "label": "DEMO-CASE-006", "patient_id": "PT-LP-006", "patient_age": 42, "patient_sex": "female",
        "suspect_product": "ExampleDrugY", "adverse_event_text": "headache",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": False,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.93, "suspect_product": 0.97, "hospitalized": 0.96},
        "meddra_code": "10019211",
    },
    "case_007_drugy_nausea.pdf": {
        "label": "DEMO-CASE-007", "patient_id": "PT-GH-007", "patient_age": 55, "patient_sex": "male",
        "suspect_product": "ExampleDrugY", "adverse_event_text": "nausea",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": False,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.91, "suspect_product": 0.96, "hospitalized": 0.94},
        "meddra_code": "10028813",
    },
    "case_008_drugz_nausea.pdf": {
        "label": "DEMO-CASE-008", "patient_id": "PT-NB-008", "patient_age": 38, "patient_sex": "female",
        "suspect_product": "ExampleDrugZ", "adverse_event_text": "nausea",
        "outcome": "recovered", "life_threatening_flag": False, "hospitalized": False,
        "hospitalization_prolonged": False, "disability_flag": False, "congenital_anomaly_flag": False,
        "field_confidence": {"adverse_event_text": 0.92, "suspect_product": 0.95, "hospitalized": 0.93},
        "meddra_code": "10028813",
    },
}


def main():
    pdf_dir = Path("data/sample_cases")
    existing_for_dedup: list[CandidateRecord] = []
    results = []

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        doc_type = classify_document(str(pdf_path), source_channel="upload_portal")
        real_text = extract_text_from_pdf(str(pdf_path))
        extraction = SIMULATED_EXTRACTIONS[pdf_path.name]
        case_id = str(uuid.uuid4())  # a real system generates this on intake, same as operational.case_records.case_id

        gate_input = GateInput(
            outcome=extraction["outcome"],
            life_threatening_flag=extraction["life_threatening_flag"],
            hospitalized=extraction["hospitalized"],
            hospitalization_prolonged=extraction["hospitalization_prolonged"],
            disability_flag=extraction["disability_flag"],
            congenital_anomaly_flag=extraction["congenital_anomaly_flag"],
            adverse_event_text=extraction["adverse_event_text"],
        )
        gate_result = evaluate_seriousness(gate_input)
        min_conf = min(extraction["field_confidence"].values())
        review_required, priority = determine_review_priority(gate_result, min_conf)

        new_record = CandidateRecord(
            record_id=case_id, patient_id=extraction["patient_id"],
            suspect_product=extraction["suspect_product"],
            adverse_event_text=extraction["adverse_event_text"],
            event_date=date.today(),
        )
        duplicate = find_duplicate(new_record, existing_for_dedup)
        existing_for_dedup.append(new_record)

        omop_person_id = None
        if not duplicate:
            case_for_load = CaseForLoad(
                case_id=case_id, source_type="case_report",
                patient_age=extraction["patient_age"], patient_sex=extraction["patient_sex"],
                suspect_product=extraction["suspect_product"],
                adverse_event_text=extraction["adverse_event_text"],
                adverse_event_meddra_code=extraction["meddra_code"],
                event_date=date.today().isoformat(),
                seriousness_result=gate_result.seriousness_result,
            )
            omop_person_id = omop_load(case_for_load)

        e2b_xml = None
        # matches graph.py's real routing: route_after_dedup sends duplicates
        # straight to END, so a duplicate never reaches submission at all
        if not duplicate and (gate_result.seriousness_result == "serious" or not review_required):
            confirmed = ConfirmedCase(
                case_id=case_id,
                patient_age=extraction["patient_age"], patient_sex=extraction["patient_sex"],
                suspect_product=extraction["suspect_product"],
                adverse_event_meddra_code=extraction["meddra_code"],
                seriousness_result=gate_result.seriousness_result,
                seriousness_criteria=gate_result.criteria_met,
                reported_date=date.today(),
                reviewer_id="demo-reviewer-001" if gate_result.seriousness_result == "serious" else None,
            )
            e2b_xml = generate_e2b_xml(confirmed)

        results.append({
            "label": extraction["label"], "product": extraction["suspect_product"],
            "event": extraction["adverse_event_text"], "doc_type": doc_type.value,
            "text_chars": len(real_text), "seriousness": gate_result.seriousness_result,
            "criteria": gate_result.criteria_met, "review_priority": priority,
            "duplicate_of": duplicate.record_id if duplicate else None,
            "omop_person_id": omop_person_id, "e2b_generated": e2b_xml is not None,
        })

    print(f"{'label':16} {'product':14} {'event':28} {'serious':9} {'priority':9} {'omop':6} {'e2b':4}")
    for r in results:
        print(f"{r['label']:16} {r['product']:14} {r['event']:28} {r['seriousness']:9} "
              f"{str(r['review_priority']):9} {'Y' if r['omop_person_id'] else 'N':6} "
              f"{'Y' if r['e2b_generated'] else 'N':4}")

    print()
    print(f"Loaded into OMOP: {sum(1 for r in results if r['omop_person_id'])} / {len(results)}")
    print(f"E2B generated: {sum(1 for r in results if r['e2b_generated'])} / {len(results)}")
    print(f"Duplicates found: {sum(1 for r in results if r['duplicate_of'])}")

    print()
    print("=== Real signal detection against the accumulated OMOP data ===")
    signals = run_signal_detection()
    if signals:
        for s in signals:
            print(f"  SIGNAL: {s.drug} + {s.event} -- a={s.a} b={s.b} c={s.c} d={s.d} "
                  f"PRR={s.prr:.2f} ROR={s.ror:.2f} chi2={s.chi_square:.2f}")
    else:
        print("  No pairs cleared the signal threshold (a>=3, PRR>=2, chi2>=4) on this data.")


if __name__ == "__main__":
    main()
