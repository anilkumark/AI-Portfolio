"""Demo: multi-turn conversation memory using the Postgres checkpointer."""

from refund_system.agents.supervisor import build_supervisor
from refund_system.memory.checkpointer import get_checkpointer


def main() -> None:
    with get_checkpointer() as checkpointer:
        supervisor = build_supervisor(checkpointer)
        config = {"configurable": {"thread_id": "demo-thread-1"}}

        result1 = supervisor.invoke(
            {"messages": [("user", "What tier is customer MARWIL0205?")]}, config=config
        )
        print("Turn 1:", result1["messages"][-1].content)
        result2 = supervisor.invoke(
            {"messages": [("user", "What was the customer ID I just asked about?")]},
            config=config,
        )
        print("Turn 2:", result2["messages"][-1].content)


if __name__ == "__main__":
    main()
