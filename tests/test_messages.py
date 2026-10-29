from __future__ import annotations


def test_message_persistence_and_ownership(client, monkeypatch):
    fake = {
        "query": "headache",
        "refused": False,
        "answer": "One possible match is a tension headache (Source: Tension Headache).",
        "citations": [{"title": "Tension Headache", "source": "Sample", "url": "", "condition": "tension_headache", "relevance_score": 0.9}],
        "recommendations": ["Rest in a quiet room."],
        "disclaimer": "Not a diagnosis.",
        "possible_conditions": [{"condition": "Tension Headache", "relevance_score": 0.9}],
        "triage": {"level": "self_care", "label": "Self care", "guidance": "Monitor your symptoms."},
        "faithfulness": {"supported": ["tension headache"], "uncited": [], "not_retrieved": []},
        "provider": "mock",
    }
    monkeypatch.setattr("app.services.message_service.diagnose_sync", lambda *args, **kwargs: fake)

    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    chat = client.post("/api/v1/chats", json={}).json()
    sent = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": "I have a headache behind my eyes"})
    assert sent.status_code == 200, sent.text
    payload = sent.json()
    assert payload[0]["role"] == "user"
    assert payload[1]["role"] == "assistant"
    assert "Tension Headache" in payload[1]["content"]
    listed = client.get(f"/api/v1/chats/{chat['id']}/messages")
    assert len(listed.json()) == 2
    renamed = client.get(f"/api/v1/chats/{chat['id']}")
    assert "Headache" in renamed.json()["title"]

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json={"name": "Ben", "email": "ben@test.local", "password": "securepass"})
    forbidden = client.get(f"/api/v1/chats/{chat['id']}/messages")
    assert forbidden.status_code == 404


def test_stream_saves_assistant_message(client, monkeypatch):
    def fake_stream(*args, **kwargs):
        query = args[0] if args else kwargs.get("query", "")
        yield {"type": "token", "content": "Possible sinus issue. "}
        yield {
            "type": "done",
            "result": {
                "query": query,
                "refused": False,
                "answer": "Possible sinus issue.",
                "citations": [],
                "recommendations": [],
                "disclaimer": "Not a diagnosis.",
                "possible_conditions": [],
                "triage": {"level": "consult_doctor", "label": "Consult a doctor", "guidance": "See a clinician."},
                "faithfulness": None,
                "provider": "mock",
            },
        }

    monkeypatch.setattr("app.services.message_service.stream_events", fake_stream)
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    chat = client.post("/api/v1/chats", json={}).json()
    with client.stream("POST", f"/api/v1/chats/{chat['id']}/messages/stream", json={"content": "sinus pressure"}) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "token" in body
    assert "done" in body
    messages = client.get(f"/api/v1/chats/{chat['id']}/messages").json()
    assert messages[-1]["role"] == "assistant"
    assert "sinus" in messages[-1]["content"].lower()
