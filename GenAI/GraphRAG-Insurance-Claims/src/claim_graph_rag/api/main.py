"""FastAPI app: exposes the claim question-answering endpoint."""

from fastapi import FastAPI
from pydantic import BaseModel

from claim_graph_rag.reasoning.answer_generation import generate_answer
from claim_graph_rag.reasoning.answer_validation import validate_answer
from claim_graph_rag.retrieval.context_builder import build_context

app = FastAPI()


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    valid: bool
    issues: list[str]


@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest):
    context = build_context(request.question)
    answer = generate_answer(request.question, context)
    validation = validate_answer(request.question, answer, context)
    return AnswerResponse(
        answer=answer, valid=validation["valid"], issues=validation["issues"]
    )
