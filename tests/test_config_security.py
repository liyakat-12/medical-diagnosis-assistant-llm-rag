from __future__ import annotations

import pytest

from src.config import jwt_secret_is_unsafe, mongo_uri_mode, validate_runtime_config


def test_default_jwt_secret_is_unsafe():
    assert jwt_secret_is_unsafe("dev-only-change-me")
    assert jwt_secret_is_unsafe("change-this-to-a-long-random-string")
    assert jwt_secret_is_unsafe("short")
    assert not jwt_secret_is_unsafe("a-sufficiently-long-unique-dev-secret")


def test_mongo_uri_modes():
    assert mongo_uri_mode("memory") == "memory"
    assert mongo_uri_mode("mongomock") == "memory"
    assert mongo_uri_mode("mongodb://127.0.0.1:27017") == "persistent"
    assert mongo_uri_mode("mongodb+srv://cluster.example.net") == "persistent"
    with pytest.raises(ValueError):
        mongo_uri_mode("postgres://localhost")


def test_production_rejects_default_jwt(monkeypatch):
    monkeypatch.setattr("src.config.APP_ENV", "production")
    monkeypatch.setattr("src.config.JWT_SECRET", "dev-only-change-me")
    monkeypatch.setattr("src.config.CORS_ORIGINS", ["http://localhost:5173"])
    monkeypatch.setattr("src.config.MONGODB_URI", "memory")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_runtime_config()


def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setattr("src.config.APP_ENV", "production")
    monkeypatch.setattr("src.config.JWT_SECRET", "a-sufficiently-long-unique-dev-secret")
    monkeypatch.setattr("src.config.CORS_ORIGINS", ["*"])
    monkeypatch.setattr("src.config.MONGODB_URI", "memory")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_runtime_config()


def test_development_allows_default_jwt_with_valid_mongo(monkeypatch):
    monkeypatch.setattr("src.config.APP_ENV", "development")
    monkeypatch.setattr("src.config.JWT_SECRET", "dev-only-change-me")
    monkeypatch.setattr("src.config.CORS_ORIGINS", ["http://localhost:5173"])
    monkeypatch.setattr("src.config.MONGODB_URI", "memory")
    validate_runtime_config()
