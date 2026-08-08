"""
FastAPI backend exposing the RAG pipeline over HTTP.

Run with:
    uvicorn src.api.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import config
from src.pipeline.rag_pipeline import run_pipeline

app = FastAPI(
    title="Medical Diagnosis Assistant API",
    description="LLM + RAG pipeline for symptom-based condition suggestions with triage and safety guardrails.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DiagnoseRequest(BaseModel):
    query: str
    top_k: int | None = None


class CitationOut(BaseModel):
    title: str
    source: str
    url: str
    condition: str
    relevance_score: float


class TriageOut(BaseModel):
    level: str
    label: str
    guidance: str
    reason: str


class DiagnoseResponse(BaseModel):
    query: str
    refused: bool
    refusal_reason: str | None
    triage: TriageOut | None
    answer: str
    citations: list[CitationOut]
    disclaimer: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "embedding_mode": config.EMBEDDING_MODE, "llm_provider": config.LLM_PROVIDER}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    result = run_pipeline(request.query, top_k=request.top_k)
    triage_out = (
        TriageOut(
            level=result.triage.level,
            label=result.triage.label,
            guidance=result.triage.guidance,
            reason=result.triage.reason,
        )
        if result.triage
        else None
    )
    return DiagnoseResponse(
        query=result.query,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        triage=triage_out,
        answer=result.answer,
        citations=[CitationOut(**c) for c in result.citations],
        disclaimer=result.disclaimer,
    )
