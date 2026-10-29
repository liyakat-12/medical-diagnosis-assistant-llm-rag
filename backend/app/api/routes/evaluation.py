from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.schemas.evaluation import LiveRetrievalRequest
from app.services import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/overview")
async def evaluation_overview(user: dict = Depends(get_current_user)) -> dict:
    del user
    return await asyncio.to_thread(evaluation_service.overview)


@router.get("/retrieval/cases")
async def retrieval_cases(run: str | None = None, user: dict = Depends(get_current_user)) -> dict:
    del user
    result = await asyncio.to_thread(evaluation_service.retrieval_cases, run)
    if result is None:
        raise HTTPException(status_code=404, detail="No stored retrieval evaluation run was found.")
    return result


@router.post("/retrieve")
async def live_retrieval(payload: LiveRetrievalRequest, user: dict = Depends(get_current_user)) -> dict:
    del user
    return await asyncio.to_thread(evaluation_service.live_retrieval, payload.query.strip(), payload.top_k)
