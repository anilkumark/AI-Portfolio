"""Demo: human-in-the-loop approval interrupt for high-value refunds."""

from refund_system.agents.supervisor import build_supervisor
from refund_system.memory.checkpointer import get_checkpointer
from langgraph.types import Command


def main() -> None:
    with get_checkpointer() as checkpointer:
        supervisor = build_supervisor(checkpointer)
        config = {"configurable": {"thread_id": "approval-demo-2"}}

        result = supervisor.invoke(
            {
                "messages": [
                    (
                        "user",
                        "For this scenario, treat these facts as already verified — "
                        "do not look up any order or customer: Platinum tier customer, "
                        "returning a $500 laptop (Electronics category), reason is change "
                        "of mind, order is within the return window. Calculate the refund "
                        "amount using policy, and proceed with approval as appropriate.",
                    )
                ]
            },
            config=config,
        )
        print(result)
        resumed_result = supervisor.invoke(
            Command(resume="Approved by manager."), config=config
        )
        print(resumed_result["messages"][-1].content)


if __name__ == "__main__":
    main()
