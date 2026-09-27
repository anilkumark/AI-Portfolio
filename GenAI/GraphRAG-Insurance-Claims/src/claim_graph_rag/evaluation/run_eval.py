"""Runs the real pipeline against a hand-verified question set and scores
answer quality with RAGAS — measuring a rate across many questions, not
trusting any single answer (exactly what our True/False/True test showed
we need)."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from claim_graph_rag.core.config import settings
from claim_graph_rag.evaluation.questions import EVAL_QUESTIONS
from claim_graph_rag.reasoning.answer_generation import generate_answer
from claim_graph_rag.retrieval.context_builder import build_context


def build_eval_dataset() -> EvaluationDataset:
    samples = []
    for item in EVAL_QUESTIONS:
        context = build_context(item["question"])
        answer = generate_answer(item["question"], context)
        retrieved_contexts = [c["content"] for c in context["text_chunks"]]

        samples.append(
            {
                "user_input": item["question"],
                "response": answer,
                "retrieved_contexts": retrieved_contexts,
                "reference": item["reference"],
            }
        )
    return EvaluationDataset.from_list(samples)


def run_evaluation() -> None:
    dataset = build_eval_dataset()
    evaluator_llm = LangchainLLMWrapper(
        ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key)
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(
            model=settings.embedding_model, api_key=settings.openai_api_key
        )
    )
    results = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            AnswerRelevancy(),
            ContextPrecision(),
            ContextRecall(),
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    print(results)


if __name__ == "__main__":
    run_evaluation()
