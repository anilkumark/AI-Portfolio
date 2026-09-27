import io
import contextlib

import streamlit as st
from sqlalchemy import text

import hospital_tool
from hospital_tool import verify_claim_with_hospital
from claims_agent import engine, claims_agent, get_claim, update_claim_status
from crewai import Task, Crew, Process

st.set_page_config(page_title="Insurance <-> Hospital A2A Debugger", layout="wide")
st.title("Insurance Company <-> Hospital A2A Debugger")
st.caption(
    "Insurance Agent (CrewAI, AWS side) talks to the Hospital Agent (LangGraph, "
    "GCP side) over the real A2A protocol on http://localhost:8080. "
    "Every request here is a genuine JSON-RPC message/send call, not a mock."
)

tab1, tab2 = st.tabs(
    [
        "1. Direct A2A test (no LLM, fastest)",
        "2. Full Insurance Agent flow (CrewAI + DB)",
    ]
)

with tab1:
    st.subheader("Send a raw claim straight to the Hospital Agent")
    st.write(
        "This bypasses the CrewAI LLM entirely and calls the A2A tool directly, "
        "so you can see exactly what the Hospital Agent returns for correct AND "
        "wrong/mismatched data, with zero LLM cost."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        patient_name = st.text_input("Patient name", "John Doe")
    with col2:
        claimed_injury = st.text_input(
            "Claimed injury", "patient reported neck pain after being rear-ended"
        )
    with col3:
        accident_date = st.text_input("Accident date (YYYY-MM-DD)", "2026-01-15")

    st.markdown("**Try these to see negative/edge scenarios:**")
    st.code(
        "Wrong patient name    -> patient_name = 'Nonexistent Person'\n"
        "Wrong injury          -> claimed_injury = 'broken leg from a fall'\n"
        "Date far from record  -> accident_date = '2020-01-01'\n"
        "Server not running    -> stop a2a_server.py, then click the button",
        language="text",
    )

    if st.button("Send to Hospital Agent", type="primary"):
        hospital_tool.last_raw_response = None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            raw = verify_claim_with_hospital.func(
                patient_name=patient_name,
                claimed_injury=claimed_injury,
                accident_date=accident_date,
            )

        st.markdown("**Step 1 - Outgoing query sent over A2A:**")
        st.code(f"{patient_name}|{claimed_injury}|{accident_date}", language="text")

        st.markdown("**Step 2 - Raw response from Hospital Agent:**")
        if raw.startswith("error="):
            st.error(raw)
        else:
            st.success(raw)

        st.markdown("**Step 3 - Parsed fields:**")
        if not raw.startswith("error="):
            fields = dict(part.split("=", 1) for part in raw.split(", "))
            st.json(fields)
        else:
            st.warning("No fields parsed - the call failed before a decision was made.")

        with st.expander("Full debug log (console output)"):
            st.code(buf.getvalue() or "(no console output captured)", language="text")

with tab2:
    st.subheader(
        "Run the full pipeline: DB claim -> CrewAI Insurance Agent -> A2A -> DB update"
    )

    with engine.connect() as conn:
        claim_rows = (
            conn.execute(
                text(
                    "SELECT claim_id, patient_name, claimed_injury, accident_date, status FROM claims ORDER BY claim_id"
                )
            )
            .mappings()
            .all()
        )

    if not claim_rows:
        st.warning("No rows found in the claims table.")
    else:
        options = {
            f"Claim {r['claim_id']} - {r['patient_name']} - status={r['status']}": r[
                "claim_id"
            ]
            for r in claim_rows
        }
        choice = st.selectbox("Pick a claim from the database", list(options.keys()))
        claim_id = options[choice]

        selected = next(r for r in claim_rows if r["claim_id"] == claim_id)
        st.markdown("**Current claim row:**")
        st.json(dict(selected))

        if st.button("Run full Insurance Agent verification", type="primary"):
            hospital_tool.last_raw_response = None
            buf = io.StringIO()

            with st.status(
                "Running CrewAI Insurance Agent...", expanded=True
            ) as status_box:
                claim = get_claim(claim_id)
                st.write(f"**Step A - claim fetched from DB:** `{claim}`")

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
                crew = Crew(
                    agents=[claims_agent], tasks=[task], process=Process.sequential
                )

                with contextlib.redirect_stdout(buf):
                    result = crew.kickoff()

                st.write("**Step B - LLM's final narrative answer:**")
                st.info(str(result))

                raw = hospital_tool.last_raw_response
                st.write(
                    "**Step C - raw hospital tool response (used for the actual status decision):**"
                )
                if raw and raw.startswith("error="):
                    st.error(raw)
                elif raw:
                    st.success(raw)
                else:
                    st.warning("No tool response captured.")

                if raw is None or raw.startswith("error="):
                    new_status = "pending"
                elif "decision=match" in raw:
                    new_status = "approved"
                elif "decision=needs_review" in raw:
                    new_status = "needs_review"
                else:
                    new_status = "rejected"

                update_claim_status(claim_id, new_status)
                st.write(
                    f"**Step D - claim {claim_id} updated to status:** `{new_status}`"
                )

                status_box.update(label="Done", state="complete")

            with st.expander(
                "Full debug log (console output, all framework/tool calls)"
            ):
                st.code(
                    buf.getvalue() or "(no console output captured)", language="text"
                )
