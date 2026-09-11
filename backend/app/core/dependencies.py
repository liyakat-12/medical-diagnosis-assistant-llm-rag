from __future__ import annotations

from fastapi import Cookie, Depends, Header

from app.core import config
from app.core.exceptions import unauthorized
from app.core.security import decode_token
from app.repositories import user_repository


async def get_current_user(
    access_token: str | None = Cookie(default=None, alias=config.ACCESS_COOKIE),
    authorization: str | None = Header(default=None),
) -> dict:
    token = access_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise unauthorized()
    user_id = decode_token(token, "access")
    if not user_id:
        raise unauthorized("Your session has expired. Please sign in again.")
    user = await user_repository.find_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise unauthorized()
    return user_repository.serialize_user(user)
