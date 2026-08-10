"""Demo: full refund flow — validation, policy, human approval, and email notification."""

from refund_system.agents.supervisor import build_supervisor
from refund_system.memory.checkpointer import get_checkpointer
from langgraph.types import Command


def main() -> None:
    with get_checkpointer() as checkpointer:
        supervisor = build_supervisor(checkpointer)
        config = {"configurable": {"thread_id": "full-flow-demo-1"}}

        result = supervisor.invoke(
            {
                "messages": [
                    (
                        "user",
                        "Customer ID MARWIL0205 wants to return order ORD-TEST-001, "
                        "a $500 laptop (Electronics category), reason is change of mind. "
                        "Treat the order as already verified and within the return window "
                        "— do not look up the order or product, but DO look up the "
                        "customer's email via validation_agent. Calculate the refund, "
                        "get approval if needed, and email the customer with the outcome.",
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
