from __future__ import annotations

from src.ai.registry import available_providers, get_provider


def test_registry_includes_core_providers():
    names = available_providers()
    for name in ("mock", "openai", "groq", "ollama"):
        assert name in names


def test_mock_provider_grounded_answer():
    provider = get_provider("mock")
    text = provider.generate(
        "system",
        "[1] Source: Common Cold (CDC)\nRest and fluids help.\nSee a doctor if symptoms last longer than ten days.",
        grounded=True,
    )
    assert "Common Cold" in text
    assert "Not a diagnosis" in text
