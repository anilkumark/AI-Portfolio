from datetime import datetime
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from search_records import search_claim

DIAGNOSIS_MATCH_THRESHOLD = 0.5
DATE_GAP_THRESHOLD_DAYS = 2


class ClaimState(TypedDict):
    patient_name: str
    claimed_injury: str
    accident_date: str
    found_diagnosis: Optional[str]
    found_treatment_date: Optional[str]
    distance: Optional[float]
    diagnosis_match: Optional[bool]
    date_match: Optional[bool]
    confidence: Optional[float]
    decision: Optional[str]


def search_node(state: ClaimState) -> ClaimState:
    result = search_claim(state["claimed_injury"], state["patient_name"], top_k=1)

    if not result["metadatas"][0]:
        # no record at all for this patient - can't be verified
        state["found_diagnosis"] = None
        state["found_treatment_date"] = None
        state["distance"] = None
        return state

    metadata = result["metadatas"][0][0]
    state["found_diagnosis"] = metadata["diagnosis"]
    state["found_treatment_date"] = metadata["treatment_date"]
    state["distance"] = result["distances"][0][0]
    return state


def diagnosis_check_node(state: ClaimState) -> ClaimState:
    if state["distance"] is None:
        state["diagnosis_match"] = False
        return state
    state["diagnosis_match"] = state["distance"] <= DIAGNOSIS_MATCH_THRESHOLD
    return state


def date_check_node(state: ClaimState) -> ClaimState:
    if state["found_treatment_date"] is None:
        state["date_match"] = False
        return state
    accident_date = datetime.strptime(state["accident_date"], "%Y-%m-%d")
    treatment_date = datetime.strptime(state["found_treatment_date"], "%Y-%m-%d")
    gap_days = abs((treatment_date - accident_date).days)
    state["date_match"] = gap_days <= DATE_GAP_THRESHOLD_DAYS
    return state


def confidence_node(state: ClaimState) -> ClaimState:
    if state["distance"] is None:
        state["confidence"] = 0.0
        state["decision"] = "no_record_found"
    elif not state["diagnosis_match"]:
        state["confidence"] = 0.0
        state["decision"] = "no_match"
    elif not state["date_match"]:
        state["confidence"] = max(0.0, round(1 - state["distance"] - 0.3, 2))
        state["decision"] = "needs_review"
    else:
        state["confidence"] = round(1 - state["distance"], 2)
        state["decision"] = "match"
    return state


graph = StateGraph(ClaimState)
graph.add_node("search", search_node)
graph.add_node("check_diagnosis", diagnosis_check_node)
graph.add_node("check_date", date_check_node)
graph.add_node("compute_confidence", confidence_node)

graph.set_entry_point("search")
graph.add_edge("search", "check_diagnosis")
graph.add_edge("check_diagnosis", "check_date")
graph.add_edge("check_date", "compute_confidence")
graph.add_edge("compute_confidence", END)

verification_app = graph.compile()


if __name__ == "__main__":
    result = verification_app.invoke(
        {
            "patient_name": "John Doe",
            "claimed_injury": "patient reported neck pain after being rear-ended",
            "accident_date": "2026-01-15",
        }
    )
    print(result)
