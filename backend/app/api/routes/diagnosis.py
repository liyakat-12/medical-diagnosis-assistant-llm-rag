from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.diagnosis import DiagnoseRequest
from app.services import message_service

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.post("")
async def diagnose(payload: DiagnoseRequest, user: dict = Depends(get_current_user)) -> dict:
    del user
    return await asyncio.to_thread(message_service.diagnose_sync, payload.query.strip(), payload.top_k)
