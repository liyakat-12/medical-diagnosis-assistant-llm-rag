from __future__ import annotations

from src.api.chats import append_turn, create_chat, get_chat, list_chats


def test_create_and_list_chats(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.CHATS_PATH", tmp_path / "chats.json")
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    email = "asha@test.local"
    created = create_chat(email)
    listed = list_chats(email)
    assert listed[0]["id"] == created["id"]
    assert listed[0]["title"] == "New chat"


def test_append_turn_sets_title(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.CHATS_PATH", tmp_path / "chats.json")
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    email = "asha@test.local"
    chat = create_chat(email)
    updated = append_turn(
        email,
        chat["id"],
        "I have a runny nose and sore throat",
        {"answer": "Likely a cold.", "query": "I have a runny nose and sore throat"},
    )
    assert updated["title"].startswith("I have a runny nose")
    loaded = get_chat(email, chat["id"])
    assert len(loaded["messages"]) == 2
    assert loaded["messages"][0]["role"] == "user"
    assert loaded["messages"][1]["result"]["answer"] == "Likely a cold."
