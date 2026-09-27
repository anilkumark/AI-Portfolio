import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from agent_card import AGENT_CARD
from verification_flow import verification_app


class HospitalVerificationExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        patient_name, claimed_injury, accident_date = [
            p.strip() for p in user_input.split("|")
        ]

        result = verification_app.invoke(
            {
                "patient_name": patient_name,
                "claimed_injury": claimed_injury,
                "accident_date": accident_date,
            }
        )

        response_text = (
            f"decision={result['decision']}, confidence={result['confidence']}, "
            f"found_diagnosis={result['found_diagnosis']}, found_treatment_date={result['found_treatment_date']}"
        )
        await event_queue.enqueue_event(new_agent_text_message(response_text))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")


request_handler = DefaultRequestHandler(
    agent_executor=HospitalVerificationExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(agent_card=AGENT_CARD, http_handler=request_handler)

if __name__ == "__main__":
    uvicorn.run(app.build(), host="0.0.0.0", port=8080)
