"""
The case-processing workflow. One LangGraph state machine, not multiple
agents — every step here depends on the one before it, so there is
nothing to parallelize with independent agents. See the design document,
Section 6, for the full reasoning.

REQUIRES: a live Postgres instance for the LangGraph checkpointer (so the
human-review pause is genuinely durable across process restarts), plus
everything extract.py and meddra_search.py require. Cannot be executed
in this environment.
"""

from typing import TypedDict, Optional
from datetime import date, datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command

from src.ingestion.extract import extract_case
from src.coding.meddra_search import suggest_meddra_codes
from src.gate.seriousness_gate import GateInput, evaluate_seriousness, determine_review_priority
from src.dedup.dedup import CandidateRecord, find_duplicate
from src.submission.e2b import ConfirmedCase, generate_e2b_xml
from src.omop.loader import CaseForLoad, omop_load
from src.common.db import get_connection


class CaseState(TypedDict):
    case_id: str
    s3_bucket: str
    s3_key: str
    local_file_path: str
    source_channel: str  # 'email' | 'upload_portal' | 'partner_api'
    source_type: str  # 'case_report' | 'ehr_extract'

    extraction: Optional[dict]
    meddra_suggestions: Optional[list[dict]]
    confirmed_meddra_code: Optional[str]
    seriousness_result: Optional[str]
    seriousness_criteria: Optional[list[str]]
    review_required: Optional[bool]
    review_priority: Optional[str]
    reviewer_id: Optional[str]
    review_decision: Optional[str]  # 'approve' | 'reject'
    duplicate_of: Optional[str]
    e2b_xml: Optional[str]


def extract_node(state: CaseState) -> CaseState:
    extraction = extract_case(
        state["s3_bucket"], state["s3_key"],
        state["local_file_path"], state["source_channel"],
    )
    state["extraction"] = extraction
    return state


def ehr_extract_exit_node(state: CaseState) -> CaseState:
    """EHR extracts stop here — no coding or seriousness decision needed."""
    return state


def meddra_coding_node(state: CaseState) -> CaseState:
    extraction = state["extraction"]
    suggestions = suggest_meddra_codes(extraction["adverse_event_text"], top_n=5)
    state["meddra_suggestions"] = suggestions
    return state


def seriousness_gate_node(state: CaseState) -> CaseState:
    extraction = state["extraction"]
    gate_input = GateInput(
        outcome=extraction.get("outcome"),
        life_threatening_flag=extraction.get("life_threatening_flag"),
        hospitalized=extraction.get("hospitalized"),
        hospitalization_prolonged=extraction.get("hospitalization_prolonged"),
        disability_flag=extraction.get("disability_flag"),
        congenital_anomaly_flag=extraction.get("congenital_anomaly_flag"),
        adverse_event_text=extraction.get("adverse_event_text", ""),
    )
    result = evaluate_seriousness(gate_input)

    confidences = extraction.get("field_confidence", {})
    min_confidence = min(confidences.values()) if confidences else 0.0

    review_required, priority = determine_review_priority(result, min_confidence)

    state["seriousness_result"] = result.seriousness_result
    state["seriousness_criteria"] = result.criteria_met
    state["review_required"] = review_required
    state["review_priority"] = priority
    return state


def human_review_node(state: CaseState) -> CaseState:
    """The durable pause. interrupt() suspends this execution — the
    LangGraph checkpointer persists the full state to Postgres, and this
    function does not resume until a POST to /cases/{case_id}/review
    calls Command(resume=...) against this exact thread_id, potentially
    hours later."""
    review_payload = interrupt({
        "case_id": state["case_id"],
        "extraction": state["extraction"],
        "meddra_suggestions": state["meddra_suggestions"],
        "seriousness_result": state["seriousness_result"],
        "seriousness_criteria": state["seriousness_criteria"],
    })
    state["reviewer_id"] = review_payload["reviewer_id"]
    state["review_decision"] = review_payload["decision"]
    state["confirmed_meddra_code"] = review_payload.get("confirmed_meddra_code")
    return state


def dedup_node(state: CaseState) -> CaseState:
    """Checks the new case against existing records before it can be
    submitted or joined to the unified store."""
    extraction = state["extraction"]
    with get_connection() as conn:
        existing_rows = conn.execute(
            """SELECT case_id, suspect_product, adverse_event_text, received_at::date as event_date
               FROM operational.case_records
               WHERE suspect_product = %s AND duplicate_of_case_id IS NULL""",
            (extraction["suspect_product"],),
        ).fetchall()

    existing = [
        CandidateRecord(
            record_id=str(r["case_id"]), patient_id=None,
            suspect_product=r["suspect_product"],
            adverse_event_text=r["adverse_event_text"],
            event_date=r["event_date"],
        )
        for r in existing_rows
    ]
    new_record = CandidateRecord(
        record_id=state["case_id"], patient_id=None,
        suspect_product=extraction["suspect_product"],
        adverse_event_text=extraction["adverse_event_text"],
        event_date=date.today(),
    )
    match = find_duplicate(new_record, existing)
    state["duplicate_of"] = match.record_id if match else None
    return state


def omop_load_node(state: CaseState) -> CaseState:
    """Loads this case into the unified store -- the step that was missing
    for case_report and ehr_extract sources (the structured feed already
    has its own loader in ingestion/structured_feed.py). Runs after dedup
    confirms this isn't a duplicate, for both source types, independent of
    whether submission (case_report only) happens afterward."""
    extraction = state["extraction"]
    case_for_load = CaseForLoad(
        case_id=state["case_id"],
        source_type=state["source_type"],
        patient_age=extraction.get("patient_age"),
        patient_sex=extraction.get("patient_sex"),
        suspect_product=extraction["suspect_product"],
        concomitant_drugs=extraction.get("concomitant_drugs", []),
        adverse_event_text=extraction.get("adverse_event_text"),
        adverse_event_meddra_code=state.get("confirmed_meddra_code"),
        event_date=date.today().isoformat(),
        seriousness_result=state.get("seriousness_result"),
    )
    omop_load(case_for_load)
    return state


def submission_node(state: CaseState) -> CaseState:
    """Only reached if review_decision == 'approve' and no duplicate was
    found. Generates and stores the E2B(R3) XML."""
    extraction = state["extraction"]
    confirmed = ConfirmedCase(
        case_id=state["case_id"],
        patient_age=extraction.get("patient_age"),
        patient_sex=extraction.get("patient_sex"),
        suspect_product=extraction["suspect_product"],
        adverse_event_meddra_code=state["confirmed_meddra_code"],
        seriousness_result=state["seriousness_result"],
        seriousness_criteria=state["seriousness_criteria"],
        reported_date=date.today(),
        reviewer_id=state.get("reviewer_id"),
    )
    state["e2b_xml"] = generate_e2b_xml(confirmed)
    return state


def route_after_extraction(state: CaseState) -> str:
    return "ehr_exit" if state["source_type"] == "ehr_extract" else "meddra_coding"


def route_after_gate(state: CaseState) -> str:
    return "human_review" if state["review_required"] else "dedup"


def route_after_review(state: CaseState) -> str:
    if state["review_decision"] == "reject":
        return END
    return "dedup"


def route_after_dedup(state: CaseState) -> str:
    if state["duplicate_of"]:
        return END  # linked to an existing case, no separate load or submission
    return "omop_load"


def route_after_omop_load(state: CaseState) -> str:
    # EHR extracts stop here -- no submission, they were never bound for E2B
    return "submission" if state["source_type"] == "case_report" else END


def build_graph():
    graph = StateGraph(CaseState)

    graph.add_node("extract", extract_node)
    graph.add_node("ehr_exit", ehr_extract_exit_node)
    graph.add_node("meddra_coding", meddra_coding_node)
    graph.add_node("seriousness_gate", seriousness_gate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("dedup", dedup_node)
    graph.add_node("omop_load", omop_load_node)
    graph.add_node("submission", submission_node)

    graph.set_entry_point("extract")
    graph.add_conditional_edges("extract", route_after_extraction,
                                 {"ehr_exit": "ehr_exit", "meddra_coding": "meddra_coding"})
    graph.add_edge("ehr_exit", "dedup")
    graph.add_edge("meddra_coding", "seriousness_gate")
    graph.add_conditional_edges("seriousness_gate", route_after_gate,
                                 {"human_review": "human_review", "dedup": "dedup"})
    graph.add_conditional_edges("human_review", route_after_review,
                                 {"dedup": "dedup", END: END})
    graph.add_conditional_edges("dedup", route_after_dedup,
                                 {"omop_load": "omop_load", END: END})
    graph.add_conditional_edges("omop_load", route_after_omop_load,
                                 {"submission": "submission", END: END})
    graph.add_edge("submission", END)

    checkpointer = PostgresSaver.from_conn_string(get_conn_string_for_checkpointer())
    return graph.compile(checkpointer=checkpointer)


def get_conn_string_for_checkpointer() -> str:
    import os
    return os.environ["DATABASE_URL"]
