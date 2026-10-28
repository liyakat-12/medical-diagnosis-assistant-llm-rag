from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.connection import mongodb
from app.connection.indexes import ensure_indexes
from app.main import app
from app.services.auth_service import seed_demo_user


@pytest.fixture(autouse=True)
def safe_test_runtime(monkeypatch):
    monkeypatch.setattr("src.config.APP_ENV", "development")
    monkeypatch.setattr("app.core.config.APP_ENV", "development")
    monkeypatch.setattr("src.config.LLM_PROVIDER", "mock")
    monkeypatch.setattr("app.core.config.LLM_PROVIDER", "mock")
    from src.ai.registry import get_provider

    get_provider.cache_clear()
    yield
    get_provider.cache_clear()


@pytest.fixture
def client(monkeypatch):
    mongodb.set_client(AsyncMongoMockClient())

    async def skip_ping() -> None:
        await ensure_indexes()
        await seed_demo_user()

    async def skip_disconnect() -> None:
        mongodb.set_client(None)

    monkeypatch.setattr("app.main.connect", skip_ping)
    monkeypatch.setattr("app.main.disconnect", skip_disconnect)
    with TestClient(app) as test_client:
        yield test_client
    mongodb.set_client(None)
