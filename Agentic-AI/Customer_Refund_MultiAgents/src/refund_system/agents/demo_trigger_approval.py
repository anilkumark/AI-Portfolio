"""Trigger a refund request that needs human approval, sent via email."""

from refund_system.agents.supervisor import build_supervisor
from refund_system.memory.checkpointer import get_checkpointer


def main() -> None:
    with get_checkpointer() as checkpointer:
        supervisor = build_supervisor(checkpointer)
        config = {"configurable": {"thread_id": "email-approval-demo-3"}}

        result = supervisor.invoke(
            {
                "messages": [
                    (
                        "user",
                        "Customer ID MARWIL0205 wants to return order ORD-TEST-003, "
                        "a $500 laptop (Electronics category), reason is change of mind. "
                        "Treat the order as already verified and within the return window "
                        "— do not look up the order, product, or customer email. Use "
                        "anilkumark0204@gmail.com as the customer's email for the "
                        "notification. Calculate the refund, get approval if needed, "
                        "and email the customer with the outcome.",
                    )
                ]
            },
            config=config,
        )
        print(result.get("__interrupt__", "No interrupt — check the full result below"))
        print(result)


if __name__ == "__main__":
    main()
