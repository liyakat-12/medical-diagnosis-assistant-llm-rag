from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response

from app.core import config
from app.core.dependencies import get_current_user
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest, response: Response) -> UserResponse:
    user = await auth_service.register_user(payload.name, str(payload.email), payload.password)
    auth_service.set_auth_cookies(response, user["id"])
    return UserResponse(**user)


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, response: Response) -> UserResponse:
    user = await auth_service.login_user(str(payload.email), payload.password)
    auth_service.set_auth_cookies(response, user["id"])
    return UserResponse(**user)


@router.post("/logout")
async def logout(response: Response) -> dict:
    auth_service.clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**user)


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=config.REFRESH_COOKIE),
) -> UserResponse:
    user_id = await auth_service.refresh_user(refresh_token)
    user = await user_repository.find_by_id(user_id)
    serialized = user_repository.serialize_user(user)
    auth_service.set_auth_cookies(response, serialized["id"])
    return UserResponse(**serialized)
