from sqlalchemy import create_engine, text

from crewai import Agent, Task, Crew, Process

import hospital_tool
from hospital_tool import verify_claim_with_hospital

engine = create_engine(
    "postgresql+psycopg2://postgres:truckdelay_pg@localhost:5432/truck_eta"
)

claims_agent = Agent(
    role="Claims Verification Specialist",
    goal="Verify submitted insurance claims by checking with the relevant hospital, then report a clear decision.",
    backstory=(
        "You work for an insurance company, verifying accident claims before "
        "they are approved. You never approve a claim without checking with "
        "the hospital first."
    ),
    tools=[verify_claim_with_hospital],
    llm="claude-sonnet-5",
    verbose=True,
)


def get_claim(claim_id: int):
    with engine.connect() as conn:
        row = (
            conn.execute(
                text("SELECT * FROM claims WHERE claim_id = :id"), {"id": claim_id}
            )
            .mappings()
            .first()
        )
        return dict(row)


def update_claim_status(claim_id: int, status: str):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE claims SET status = :status WHERE claim_id = :id"),
            {"status": status, "id": claim_id},
        )


def verify_claim(claim_id: int):
    claim = get_claim(claim_id)
    print(f"[claims_agent] STEP A - claim fetched from DB: {claim}")

    hospital_tool.last_raw_response = None

    task = Task(
        description=(
            f"Verify this insurance claim using the hospital verification tool.\n"
            f"Patient name: {claim['patient_name']}\n"
            f"Claimed injury: {claim['claimed_injury']}\n"
            f"Accident date: {claim['accident_date']}\n"
            "Call the tool with these exact values, then report the decision and confidence."
        ),
        expected_output="The hospital's decision (match/needs_review/no_match) and confidence score.",
        agent=claims_agent,
    )

    crew = Crew(agents=[claims_agent], tasks=[task], process=Process.sequential)
    result = crew.kickoff()
    print(f"[claims_agent] STEP B - LLM's final narrative answer: {result}")

    raw = hospital_tool.last_raw_response
    print(f"[claims_agent] STEP C - raw hospital tool response used for status logic: {raw!r}")

    if raw is None:
        new_status = "pending"
    elif raw.startswith("error="):
        new_status = "pending"
    elif "decision=match" in raw:
        new_status = "approved"
    elif "decision=needs_review" in raw:
        new_status = "needs_review"
    else:
        new_status = "rejected"

    update_claim_status(claim_id, new_status)
    print(f"[claims_agent] STEP D - claim {claim_id} updated to status: {new_status}")


if __name__ == "__main__":
    verify_claim(1)
