from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.repositories import user_repository
from app.schemas.auth import ProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_profile(user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
) -> UserResponse:
    updated = await user_repository.update_user(
        user["id"],
        payload.model_dump(exclude_unset=True),
    )
    return UserResponse(**user_repository.serialize_user(updated))
