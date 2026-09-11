from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core import config

logger = logging.getLogger("mediassist")

_client: AsyncIOMotorClient | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def oid(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid id")
    return ObjectId(value)


def as_id(value) -> str:
    return str(value)


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[config.MONGODB_DB_NAME]


def set_client(client: AsyncIOMotorClient | None) -> None:
    global _client
    _client = client


async def connect() -> None:
    if config.MONGODB_URI.strip().lower() in {"memory", "mongomock"}:
        from mongomock_motor import AsyncMongoMockClient

        set_client(AsyncMongoMockClient())
        logger.warning("Using in-memory MongoDB. Data will not persist across restarts.")
        return
    try:
        client = get_client()
        await client.admin.command("ping")
    except Exception:
        logger.exception("MongoDB connection failed")
        raise
    logger.info("Connected to MongoDB database=%s", config.MONGODB_DB_NAME)


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
