"""
Generates E2B(R3)-shaped XML from a confirmed, reviewer-approved case
record. Only called after review sign-off — never on raw extraction
output.

This is a simplified subset of the real E2B(R3) ICH ICSR schema, covering
the fields this platform actually populates. A production deployment
validates the generated document against the full ICH E2B(R3) XSD before
submission; that XSD is a large, externally-maintained specification not
reproduced here. What this module guarantees on its own is internal
consistency — every required field present, correctly typed, and
well-formed XML — which is exactly what is testable without the
official schema in hand.
"""

from dataclasses import dataclass
from datetime import date
from lxml import etree


class E2BGenerationError(Exception):
    """Raised when a case record is missing a field required for
    submission. Generation must fail loudly here — a case with a gap
    must never produce a technically-valid-looking XML document that is
    actually incomplete."""


@dataclass
class ConfirmedCase:
    case_id: str
    patient_age: int | None
    patient_sex: str | None
    suspect_product: str
    adverse_event_meddra_code: str          # must be reviewer-confirmed, never a raw suggestion
    seriousness_result: str                  # 'serious' | 'non_serious'
    seriousness_criteria: list[str]
    reported_date: date
    reviewer_id: str | None                  # None only if the case never required review


REQUIRED_FIELDS = [
    "case_id", "suspect_product", "adverse_event_meddra_code",
    "seriousness_result", "reported_date",
]


def _validate(case: ConfirmedCase) -> None:
    missing = []
    for field_name in REQUIRED_FIELDS:
        if getattr(case, field_name) in (None, ""):
            missing.append(field_name)
    if missing:
        raise E2BGenerationError(
            f"Case {case.case_id} is missing required field(s) for E2B submission: {missing}. "
            "Generation refused rather than producing an incomplete document."
        )
    if case.seriousness_result == "serious" and not case.seriousness_criteria:
        raise E2BGenerationError(
            f"Case {case.case_id} is marked serious but carries no seriousness_criteria — "
            "refusing to submit a serious case with no stated basis."
        )
    if case.seriousness_result == "serious" and case.reviewer_id is None:
        raise E2BGenerationError(
            f"Case {case.case_id} is serious and has no reviewer_id — a serious case must "
            "have gone through human review before submission."
        )


def generate_e2b_xml(case: ConfirmedCase) -> str:
    _validate(case)

    root = etree.Element("ichicsr")
    safetyreport = etree.SubElement(root, "safetyreport")

    etree.SubElement(safetyreport, "safetyreportid").text = case.case_id
    etree.SubElement(safetyreport, "serious").text = "1" if case.seriousness_result == "serious" else "2"

    for criterion in case.seriousness_criteria:
        etree.SubElement(safetyreport, "seriousnesscriterion").text = criterion

    patient = etree.SubElement(safetyreport, "patient")
    if case.patient_age is not None:
        etree.SubElement(patient, "patientonsetage").text = str(case.patient_age)
    if case.patient_sex is not None:
        etree.SubElement(patient, "patientsex").text = case.patient_sex

    drug = etree.SubElement(patient, "drug")
    etree.SubElement(drug, "medicinalproduct").text = case.suspect_product
    etree.SubElement(drug, "drugcharacterization").text = "1"  # suspect

    reaction = etree.SubElement(patient, "reaction")
    etree.SubElement(reaction, "reactionmeddrapt").text = case.adverse_event_meddra_code

    etree.SubElement(safetyreport, "receivedate").text = case.reported_date.isoformat()
    if case.reviewer_id:
        etree.SubElement(safetyreport, "reviewerid").text = case.reviewer_id

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


def is_well_formed(xml_string: str) -> bool:
    try:
        etree.fromstring(xml_string.encode())
        return True
    except etree.XMLSyntaxError:
        return False
