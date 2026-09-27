"""Evaluate the Policy Agent's RAG quality using RAGAS.

For each question: retrieve context via search_policy(), generate an answer via
the real policy_agent, then score faithfulness/relevancy/precision/recall
against the known ground-truth answer.
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from evaluation.questions import EVAL_QUESTIONS
from refund_system.agents.policy_agent import policy_agent
from refund_system.retrieval.search import search_policy


def build_dataset() -> EvaluationDataset:
    samples = []
    for item in EVAL_QUESTIONS:
        question = item["question"]

        retrieved = search_policy(question, top_k=3)
        contexts = [chunk["content"] for chunk in retrieved]

        result = policy_agent.invoke({"messages": [("user", question)]})
        answer = result["messages"][-1].content

        samples.append(
            {
                "user_input": question,
                "response": answer,
                "retrieved_contexts": contexts,
                "reference": item["ground_truth"],
            }
        )
        print(f"Generated answer for: {question[:60]}...")

    return EvaluationDataset.from_list(samples)


def main() -> None:
    dataset = build_dataset()

    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-3-small")
    )

    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    print("\n=== RAGAS Evaluation Results ===")
    print(result)

    df = result.to_pandas()
    df.to_csv("evaluation/last_run_results.csv", index=False)
    print("\nDetailed per-question results saved to evaluation/last_run_results.csv")


if __name__ == "__main__":
    main()
