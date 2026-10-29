"""Health/readiness must not treat an empty Chroma collection as healthy in production."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_retrieval_fields(client: TestClient):
    body = client.get("/api/v1/health").json()
    assert "retrieval_ready" in body
    assert "retrieval_documents" in body
    assert "retrieval_mode" in body
    assert "status" in body


def test_production_health_is_unavailable_when_index_empty(monkeypatch, client: TestClient):
    import app.api.routes.health as health_route
    import app.core.config as app_config

    monkeypatch.setattr(app_config, "APP_ENV", "production")
    monkeypatch.setattr(app_config, "is_production", lambda: True)
    monkeypatch.setattr(
        health_route,
        "_retrieval_status",
        lambda: {
            "retrieval_ready": False,
            "retrieval_mode": "general",
            "retrieval_documents": 0,
            "retrieval_error": "Knowledge-base index is empty or unavailable.",
        },
    )
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["retrieval_ready"] is False
    assert body["retrieval_documents"] == 0
