import asyncio
from uuid import uuid4

import httpx
from crewai.tools import tool

from a2a.client import A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    TextPart,
)

HOSPITAL_AGENT_URL = "http://localhost:8080"

# Captured after every tool call so claims_agent.py can read the exact
# machine-parseable string, instead of relying on the LLM's paraphrased
# final answer to decide the claim status.
last_raw_response: str | None = None


async def _call_hospital_agent(
    patient_name: str, claimed_injury: str, accident_date: str
) -> str:
    query_text = f"{patient_name}|{claimed_injury}|{accident_date}"
    print(f"[hospital_tool] STEP 1 - outgoing A2A query text: {query_text!r}")

    async with httpx.AsyncClient() as httpx_client:
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, HOSPITAL_AGENT_URL
        )
        print(f"[hospital_tool] STEP 2 - fetched Agent Card from {HOSPITAL_AGENT_URL}")

        message = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=query_text))],
        )
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=message),
        )

        print("[hospital_tool] STEP 3 - sending JSON-RPC message/send request")
        response = await client.send_message(request)

        root = response.root
        if hasattr(root, "error"):
            raise RuntimeError(f"Hospital agent returned an error: {root.error}")

        text = root.result.parts[0].root.text
        print(f"[hospital_tool] STEP 4 - raw response from Hospital Agent: {text!r}")
        return text


@tool("Verify claim with hospital")
def verify_claim_with_hospital(
    patient_name: str, claimed_injury: str, accident_date: str
) -> str:
    """Calls the Hospital's A2A agent to verify whether a claimed injury matches
    their medical records for the given patient and accident date. Returns a
    text result containing decision, confidence, found_diagnosis, and
    found_treatment_date."""
    global last_raw_response
    try:
        result = asyncio.run(
            _call_hospital_agent(patient_name, claimed_injury, accident_date)
        )
        last_raw_response = result
        return result
    except httpx.ConnectError as e:
        error_text = (
            "error=connection_failed, message=Could not reach the Hospital Agent "
            f"at {HOSPITAL_AGENT_URL}. Is a2a_server.py running? ({e})"
        )
        print(f"[hospital_tool] STEP 4 - EXCEPTION: {error_text}")
        last_raw_response = error_text
        return error_text
    except Exception as e:
        error_text = f"error=tool_failure, message={e}"
        print(f"[hospital_tool] STEP 4 - EXCEPTION: {error_text}")
        last_raw_response = error_text
        return error_text
