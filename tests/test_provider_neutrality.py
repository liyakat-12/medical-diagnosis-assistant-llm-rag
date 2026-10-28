from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.rag_pipeline import iter_pipeline_stream, result_to_dict, run_pipeline
from src.safety.public_text import contains_provider_leak, public_chat_payload, sanitize_error, sanitize_status

ROOT = Path(__file__).resolve().parent.parent
VENDOR_MARKERS = ("groq", "openai", "ollama", "chatgpt", "gpt-oss", "gpt-4o")


def _blob(value) -> str:
    return json.dumps(value, default=str).lower()


def test_sanitize_status_and_errors_drop_vendor_names():
    assert "groq" not in sanitize_status("Local notes had no close match. Asking Groq...").lower()
    assert "openai" not in sanitize_error("OpenAI RateLimitError: 429 from https://api.openai.com").lower()
    assert contains_provider_leak("GROQ_API_KEY is not set")
    assert not contains_provider_leak("I could not finish this lookup. Please try again.")


def test_public_payload_strips_provider_fields():
    cleaned = public_chat_payload(
        {
            "answer": "A bike is cheaper for short city trips.",
            "provider": "groq",
            "model": "openai/gpt-oss-20b",
            "llm_provider": "groq",
        }
    )
    assert "provider" not in cleaned
    assert "llm_provider" not in cleaned
    assert cleaned.get("model") is None
    blob = _blob(cleaned)
    for marker in VENDOR_MARKERS:
        assert marker not in blob


def test_result_to_dict_is_provider_neutral():
    payload = result_to_dict(run_pipeline("Which is better, a car or a bike?"))
    assert "provider" not in payload
    blob = _blob(payload)
    for marker in VENDOR_MARKERS:
        assert marker not in blob


def test_health_does_not_name_providers(client):
    body = client.get("/api/v1/health").json()
    blob = _blob(body)
    for marker in VENDOR_MARKERS:
        assert marker not in blob
    assert "llm_provider" not in body
    assert "providers" not in body


def test_stream_status_and_errors_do_not_name_providers(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.retriever import Evidence

    weak = [
        Evidence(
            text="unrelated furniture notes",
            title="Table Care",
            source="Sample",
            url="",
            condition="table",
            triage_level="self_care",
            relevance_score=0.01,
            doc_id="table",
            vector_score=0.1,
        )
    ]

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (weak, weak))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(
        kb,
        "_call_llm",
        lambda *_a, **_k: json.dumps(
            {
                "answer": "This may be dust irritation.",
                "triage": "self_care",
                "recommendations": ["Rinse the nose with saline.", "See a doctor if it lasts."],
                "matches": [
                    {"condition": "Dust irritation", "weight": 3},
                    {"condition": "Allergic rhinitis", "weight": 2},
                ],
            }
        ),
    )
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)
    events = list(iter_pipeline_stream("itchy nose after dusting"))
    blob = _blob(events)
    for marker in VENDOR_MARKERS:
        assert marker not in blob


def test_stream_failure_event_is_provider_neutral(client, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("Groq RateLimitError 429 openai/gpt-oss-20b https://api.groq.com")

    monkeypatch.setattr("app.services.message_service.stream_events", boom)
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    chat = client.post("/api/v1/chats", json={}).json()
    with client.stream("POST", f"/api/v1/chats/{chat['id']}/messages/stream", json={"content": "hello there friend"}) as response:
        body = "".join(response.iter_text()).lower()
    for marker in VENDOR_MARKERS:
        assert marker not in body
    assert "traceback" not in body
    assert "i could not finish this lookup" in body


def test_saved_messages_do_not_expose_model_vendor(client, monkeypatch):
    fake = {
        "query": "headache",
        "refused": False,
        "answer": "One possible match is a tension headache (Source: Tension Headache).",
        "citations": [{"title": "Tension Headache", "source": "Sample", "url": "", "condition": "tension_headache"}],
        "recommendations": ["Rest in a quiet room."],
        "disclaimer": "Not a diagnosis.",
        "possible_conditions": [{"condition": "Tension Headache"}],
        "triage": {"level": "self_care", "label": "Self care", "guidance": "Monitor."},
        "provider": "groq",
        "model": "openai/gpt-oss-20b",
    }
    monkeypatch.setattr("app.services.message_service.diagnose_sync", lambda *_a, **_k: fake)
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    chat = client.post("/api/v1/chats", json={}).json()
    sent = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": "I have a headache behind my eyes"})
    assert sent.status_code == 200, sent.text
    assistant = sent.json()[1]
    blob = _blob(assistant)
    for marker in VENDOR_MARKERS:
        assert marker not in blob
    assert assistant.get("model") in {None, ""}


def test_pipeline_still_works_when_backend_provider_is_mock(monkeypatch):
    monkeypatch.setattr("src.config.LLM_PROVIDER", "mock")
    result = run_pipeline("Which is better, a car or a bike?")
    assert result.possible_conditions == []
    assert result.triage is None
    assert "car" in result.answer.lower()
    assert "provider" not in result_to_dict(result)


def test_frontend_source_has_no_vendor_or_secret_config():
    frontend_src = ROOT / "frontend" / "src"
    forbidden = (
        "groq",
        "openai",
        "ollama",
        "chatgpt",
        "gpt-oss",
        "gsk_",
        "sk-proj",
        "VITE_GROQ",
        "VITE_OPENAI",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
    )
    for path in frontend_src.rglob("*"):
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for marker in forbidden:
            assert marker.lower() not in text, f"{path} contains {marker}"
