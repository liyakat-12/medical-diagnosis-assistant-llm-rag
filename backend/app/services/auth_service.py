from __future__ import annotations

import logging

from fastapi import Response

from app.core import config
from app.core.exceptions import bad_request, conflict, unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories import user_repository

logger = logging.getLogger("mediassist.auth")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def set_auth_cookies(response: Response, user_id: str) -> None:
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    cookie_kw = {
        "httponly": True,
        "secure": config.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(
        config.ACCESS_COOKIE,
        access,
        max_age=config.JWT_ACCESS_EXPIRE_MINUTES * 60,
        **cookie_kw,
    )
    response.set_cookie(
        config.REFRESH_COOKIE,
        refresh,
        max_age=config.JWT_REFRESH_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_kw,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(config.ACCESS_COOKIE, path="/")
    response.delete_cookie(config.REFRESH_COOKIE, path="/")


async def register_user(name: str, email: str, password: str) -> dict:
    email = _normalize_email(email)
    if await user_repository.find_by_email(email):
        raise conflict("An account with this email already exists.")
    user = await user_repository.create_user(name.strip(), email, hash_password(password))
    serialized = user_repository.serialize_user(user)
    logger.info("Registered user_id=%s", serialized["id"])
    return serialized


async def login_user(email: str, password: str) -> dict:
    email = _normalize_email(email)
    user = await user_repository.find_by_email(email)
    if not user or not verify_password(password, user.get("password_hash") or ""):
        raise unauthorized("Incorrect email or password.")
    if not user.get("is_active", True):
        raise unauthorized("This account is inactive.")
    await user_repository.touch_login(str(user["_id"]))
    user = await user_repository.find_by_id(str(user["_id"])) or user
    serialized = user_repository.serialize_user(user)
    logger.info("Login succeeded user_id=%s", serialized["id"])
    return serialized


async def refresh_user(refresh_token: str | None) -> str:
    if not refresh_token:
        raise unauthorized("Your session has expired. Please sign in again.")
    user_id = decode_token(refresh_token, "refresh")
    if not user_id:
        raise unauthorized("Your session has expired. Please sign in again.")
    user = await user_repository.find_by_id(user_id)
    if not user:
        raise unauthorized("Please sign in to use the assistant.")
    return str(user["_id"])


async def seed_demo_user() -> None:
    """Ensure the advertised demo login works in every environment.

    The sign-in page always offers demo@clinic.local / demo123. Production used
    to skip seeding, so that button failed with "Incorrect email or password."
    Seed (or repair) the account whenever DEMO_EMAIL and DEMO_PASSWORD are set.
    """
    email = _normalize_email(config.DEMO_EMAIL or "")
    password = config.DEMO_PASSWORD or ""
    if not email or not password:
        logger.info("Skipping demo user seed (DEMO_EMAIL/DEMO_PASSWORD unset)")
        return
    existing = await user_repository.find_by_email(email)
    digest = hash_password(password)
    if existing:
        if not verify_password(password, existing.get("password_hash") or ""):
            await user_repository.update_user(str(existing["_id"]), {"password_hash": digest})
            logger.info("Repaired demo user password email=%s", email)
        return
    await user_repository.create_user(config.DEMO_NAME, email, digest)
    logger.info("Seeded demo user email=%s", email)
