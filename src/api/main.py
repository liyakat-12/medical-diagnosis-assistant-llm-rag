"""
FastAPI backend exposing the RAG pipeline over HTTP.

Website (Express + Tailwind): http://localhost:3000
API:
    uvicorn src.api.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src import config
from src.api.auth import (
    LoginIn,
    RegisterIn,
    TokenOut,
    UserOut,
    authenticate,
    create_session,
    drop_session,
    register_user,
    require_user,
    seed_demo_user,
)
from src.pipeline.rag_pipeline import run_pipeline

app = FastAPI(
    title="Medical Diagnosis Assistant API",
    description="LLM + RAG pipeline for symptom-based condition suggestions with triage and safety guardrails.",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_optional_bearer = HTTPBearer(auto_error=False)


@app.on_event("startup")
def _startup() -> None:
    seed_demo_user()


class DiagnoseRequest(BaseModel):
    query: str
    top_k: int | None = None


class CitationOut(BaseModel):
    title: str
    source: str
    url: str
    condition: str
    relevance_score: float


class ConditionOut(BaseModel):
    condition: str
    title: str
    source: str
    url: str
    relevance_score: float


class TriageOut(BaseModel):
    level: str
    label: str
    guidance: str
    reason: str


class ClaimAuditOut(BaseModel):
    text: str
    cited_source: str | None
    status: str
    matched_title: str | None = None


class FaithfulnessOut(BaseModel):
    coverage: float
    claim_count: int
    supported_count: int
    unsupported_count: int
    fabricated_count: int
    verdict: str
    summary: str
    claims: list[ClaimAuditOut]


class DiagnoseResponse(BaseModel):
    query: str
    refused: bool
    refusal_reason: str | None
    triage: TriageOut | None
    answer: str
    citations: list[CitationOut]
    possible_conditions: list[ConditionOut] = []
    faithfulness: FaithfulnessOut | None = None
    disclaimer: str


def _unique_conditions(citations: list[dict]) -> list[ConditionOut]:
    seen: set[str] = set()
    out: list[ConditionOut] = []
    for item in citations:
        key = (item.get("condition") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            ConditionOut(
                condition=item.get("condition") or item.get("title") or "Condition",
                title=item.get("title") or "",
                source=item.get("source") or "",
                url=item.get("url") or "",
                relevance_score=item.get("relevance_score") or 0.0,
            )
        )
    return out


@app.get("/")
def root() -> dict:
    return {
        "service": "Medical Diagnosis Assistant API",
        "website": "http://localhost:3000",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "embedding_mode": config.EMBEDDING_MODE,
        "llm_provider": config.LLM_PROVIDER,
        "effective_llm_provider": config.resolve_llm_provider(),
    }


@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn) -> TokenOut:
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return TokenOut(token=create_session(user), user=UserOut(**user))


@app.post("/auth/register", response_model=TokenOut)
def register(payload: RegisterIn) -> TokenOut:
    user = register_user(payload.name, payload.email, payload.password)
    return TokenOut(token=create_session(user), user=UserOut(**user))


@app.get("/auth/me", response_model=UserOut)
def me(user: dict = Depends(require_user)) -> UserOut:
    return UserOut(**user)


@app.post("/auth/logout")
def logout(creds: HTTPAuthorizationCredentials | None = Depends(_optional_bearer)) -> dict:
    if creds:
        drop_session(creds.credentials)
    return {"ok": True}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest, user: dict = Depends(require_user)) -> DiagnoseResponse:
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
    faithfulness_out = None
    if result.faithfulness is not None:
        faithfulness_out = FaithfulnessOut(**result.faithfulness.to_dict())

    return DiagnoseResponse(
        query=result.query,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        triage=triage_out,
        answer=result.answer,
        citations=[CitationOut(**c) for c in result.citations],
        possible_conditions=_unique_conditions(result.citations),
        faithfulness=faithfulness_out,
        disclaimer=result.disclaimer,
    )
