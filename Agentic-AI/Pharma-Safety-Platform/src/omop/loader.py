"""
Loads deduped, quality-gated case records (case_report and ehr_extract
sources) into the OMOP unified store. The structured-feed path already has
its own loader (src/ingestion/structured_feed.py); this is the missing
counterpart for the other two sources -- without it, case reports and EHR
extracts are processed and reviewed but never actually reach the unified
view signal detection and dashboards read from.

Runs only after the dedup gate (see workflow/graph.py) -- a record found
to be a duplicate is linked, not separately loaded here.

REQUIRES a live Postgres instance for omop_load(); the field-mapping
function itself (build_omop_rows) is pure and tested without a database.
"""

from dataclasses import dataclass, field


@dataclass
class CaseForLoad:
    """The minimal shape needed to load one case into the unified store --
    deliberately narrower than the full case record, so this module can't
    accidentally depend on fields the seriousness gate or E2B step own."""
    case_id: str
    source_type: str  # 'case_report' | 'ehr_extract'
    patient_age: int | None
    patient_sex: str | None
    suspect_product: str
    concomitant_drugs: list[str] = field(default_factory=list)
    adverse_event_text: str | None = None
    adverse_event_meddra_code: str | None = None
    event_date: str | None = None  # ISO date string
    seriousness_result: str | None = None  # only present for case_report


def build_omop_rows(case: CaseForLoad) -> dict:
    """
    Pure mapping from a case record to the rows that need inserting --
    one person row, one or more drug_exposure rows (suspect + concomitant,
    each tagged), an optional condition_occurrence row (only if there's an
    adverse event to record -- EHR extracts without one just get the
    person + drug rows), and an optional observation row for seriousness
    (case_report only -- EHR extracts never have a seriousness result).

    Returns a dict shaped for the DB layer to insert directly, with no
    database touched here -- this is what makes the mapping testable.
    """
    person_row = {
        "source_record_id": case.case_id,
        "source_type": case.source_type,
        "year_of_birth": None,  # only age is known post-extraction, not birth year
        "sex": case.patient_sex,
    }

    drug_rows = [{
        "source_record_id": case.case_id,
        "source_type": case.source_type,
        "drug_source_value": case.suspect_product,
        "is_suspect_product": True,
        "exposure_start_date": case.event_date,
    }]
    for concomitant in case.concomitant_drugs:
        drug_rows.append({
            "source_record_id": case.case_id,
            "source_type": case.source_type,
            "drug_source_value": concomitant,
            "is_suspect_product": False,
            "exposure_start_date": case.event_date,
        })

    condition_row = None
    if case.adverse_event_text:
        condition_row = {
            "source_record_id": case.case_id,
            "condition_source_value": case.adverse_event_text,
            "condition_meddra_code": case.adverse_event_meddra_code,
            "condition_start_date": case.event_date,
        }

    observation_row = None
    if case.seriousness_result is not None:
        observation_row = {
            "source_record_id": case.case_id,
            "observation_type": "seriousness_result",
            "value_as_string": case.seriousness_result,
            "observation_date": case.event_date,
        }

    return {
        "person": person_row,
        "drugs": drug_rows,
        "condition": condition_row,
        "observation": observation_row,
    }


def omop_load(case: CaseForLoad) -> str:
    """Writes the mapped rows to Postgres inside one transaction -- a
    partially-loaded case (person row with no drug rows, say) would corrupt
    signal-detection counts, so this is all-or-nothing.
    Returns the new omop.person.person_id."""
    from src.common.db import get_connection

    rows = build_omop_rows(case)

    with get_connection() as conn:
        person = conn.execute(
            """INSERT INTO omop.person (source_record_id, source_type, year_of_birth, sex)
               VALUES (%(source_record_id)s, %(source_type)s, %(year_of_birth)s, %(sex)s)
               RETURNING person_id""",
            rows["person"],
        ).fetchone()
        person_id = person["person_id"]

        for drug in rows["drugs"]:
            conn.execute(
                """INSERT INTO omop.drug_exposure
                   (person_id, source_record_id, source_type, drug_source_value,
                    is_suspect_product, exposure_start_date)
                   VALUES (%(person_id)s, %(source_record_id)s, %(source_type)s,
                           %(drug_source_value)s, %(is_suspect_product)s, %(exposure_start_date)s)""",
                {**drug, "person_id": person_id},
            )

        if rows["condition"]:
            conn.execute(
                """INSERT INTO omop.condition_occurrence
                   (person_id, source_record_id, condition_source_value,
                    condition_meddra_code, condition_start_date)
                   VALUES (%(person_id)s, %(source_record_id)s, %(condition_source_value)s,
                           %(condition_meddra_code)s, %(condition_start_date)s)""",
                {**rows["condition"], "person_id": person_id},
            )

        if rows["observation"]:
            conn.execute(
                """INSERT INTO omop.observation
                   (person_id, source_record_id, observation_type, value_as_string, observation_date)
                   VALUES (%(person_id)s, %(source_record_id)s, %(observation_type)s,
                           %(value_as_string)s, %(observation_date)s)""",
                {**rows["observation"], "person_id": person_id},
            )

        conn.commit()

    return str(person_id)
