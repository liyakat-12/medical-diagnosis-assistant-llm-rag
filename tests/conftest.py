from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.db import mongodb
from app.db.indexes import ensure_indexes
from app.main import app
from app.services.auth_service import seed_demo_user


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
