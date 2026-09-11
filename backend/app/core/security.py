from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core import config

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _encode(subject: str, expires: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _encode(user_id, timedelta(minutes=config.JWT_ACCESS_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: str) -> str:
    return _encode(user_id, timedelta(days=config.JWT_REFRESH_EXPIRE_DAYS), "refresh")


def decode_token(token: str, expected_type: str) -> str | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None
