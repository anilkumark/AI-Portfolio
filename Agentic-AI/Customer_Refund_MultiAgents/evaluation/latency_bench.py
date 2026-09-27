"""One-off latency benchmark: time real end-to-end Policy Agent calls
(retrieval + generation) against the live system, using the real eval questions.
Not part of the regular test suite -- ad hoc measurement script.
"""

import time

from evaluation.questions import EVAL_QUESTIONS
from refund_system.agents.policy_agent import policy_agent

RUNS_PER_QUESTION = 3


def main() -> None:
    timings = []
    for item in EVAL_QUESTIONS:
        question = item["question"]
        for i in range(RUNS_PER_QUESTION):
            start = time.perf_counter()
            policy_agent.invoke({"messages": [("user", question)]})
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            print(f"[{elapsed:6.2f}s] run {i + 1}/{RUNS_PER_QUESTION} -- {question[:55]}")

    timings.sort()
    n = len(timings)

    def percentile(p: float) -> float:
        idx = min(n - 1, int(round(p * (n - 1))))
        return timings[idx]

    print("\n=== Latency results (end-to-end Policy Agent: retrieval + generation) ===")
    print(f"n = {n} real requests")
    print(f"min    = {timings[0]:.2f}s")
    print(f"P50    = {percentile(0.50):.2f}s")
    print(f"P90    = {percentile(0.90):.2f}s")
    print(f"max    = {timings[-1]:.2f}s")


if __name__ == "__main__":
    main()
