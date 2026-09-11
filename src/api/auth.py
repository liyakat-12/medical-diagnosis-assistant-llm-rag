"""
Simple demo authentication for the full-stack website.

Accounts are stored as salted password hashes in data/users.json.
Sessions are in-memory tokens (fine for a local academic demo).
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src import config

_LOCK = threading.Lock()
_SESSIONS: dict[str, dict] = {}
_BEARER = HTTPBearer(auto_error=False)

SESSION_SECONDS = 8 * 60 * 60
DEMO_EMAIL = "demo@clinic.local"
DEMO_PASSWORD = "demo123"
DEMO_NAME = "Demo Patient"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=4, max_length=80)


class UserOut(BaseModel):
    name: str
    email: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


def _users_path() -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.USERS_PATH


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _load_users() -> dict:
    path = _users_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict) -> None:
    path = _users_path()
    path.write_text(json.dumps(users, indent=2), encoding="utf-8")


def seed_demo_user() -> None:
    with _LOCK:
        users = _load_users()
        if DEMO_EMAIL in users:
            return
        salt = secrets.token_hex(16)
        users[DEMO_EMAIL] = {
            "name": DEMO_NAME,
            "email": DEMO_EMAIL,
            "salt": salt,
            "password_hash": _hash_password(DEMO_PASSWORD, salt),
        }
        _save_users(users)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def authenticate(email: str, password: str) -> dict | None:
    email = _normalize_email(email)
    with _LOCK:
        user = _load_users().get(email)
    if not user:
        return None
    digest = _hash_password(password, user["salt"])
    if not secrets.compare_digest(digest, user["password_hash"]):
        return None
    return {"name": user["name"], "email": user["email"]}


def register_user(name: str, email: str, password: str) -> dict:
    email = _normalize_email(email)
    if not EMAIL_RE.match(email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter a valid email address.")
    with _LOCK:
        users = _load_users()
        if email in users:
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
        salt = secrets.token_hex(16)
        users[email] = {
            "name": name.strip(),
            "email": email,
            "salt": salt,
            "password_hash": _hash_password(password, salt),
        }
        _save_users(users)
    return {"name": name.strip(), "email": email}


def create_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "user": user,
        "expires": time.time() + SESSION_SECONDS,
    }
    return token


def drop_session(token: str) -> None:
    _SESSIONS.pop(token, None)


def user_from_token(token: str | None) -> dict | None:
    if not token:
        return None
    session = _SESSIONS.get(token)
    if not session:
        return None
    if session["expires"] < time.time():
        _SESSIONS.pop(token, None)
        return None
    return session["user"]


def require_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> dict:
    user = user_from_token(creds.credentials if creds else None)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Please sign in to use the assistant.",
        )
    return user
