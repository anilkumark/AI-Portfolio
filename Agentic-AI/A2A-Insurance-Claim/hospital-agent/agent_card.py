from a2a.types import AgentCard, AgentSkill, AgentCapabilities

AGENT_CARD = AgentCard(
    name="Hospital Verification Agent",
    description="Verifies whether a claimed injury matches this hospital's medical records for a given patient.",
    url="http://localhost:8080/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="verify_claim",
            name="Verify Injury Claim",
            description="Given a patient name, claimed injury description, and accident date, checks hospital records and returns a match confidence.",
            tags=["insurance", "medical-verification"],
        )
    ],
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
)
