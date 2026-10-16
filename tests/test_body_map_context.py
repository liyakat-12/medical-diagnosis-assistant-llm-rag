"""Body-map context is extra query text. It must not change safety rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.safety.guardrails import check_emergency, check_prescription_request

HEAD_ONLY = (
    "Body map context (user-described discomfort, not a diagnosis): locations = Head."
)
CHEST_COUGH = (
    "Body map context (user-described discomfort, not a diagnosis): "
    "locations = Chest; symptoms = Cough."
)
EMERGENCY_WITH_MAP = (
    "crushing chest pain spreading to my left arm\n\n"
    "Body map context (user-described discomfort, not a diagnosis): locations = Chest."
)
PRESCRIPTION_WITH_MAP = (
    "how many mg of ibuprofen should I take\n\n"
    "Body map context (user-described discomfort, not a diagnosis): locations = Head."
)


def test_body_region_alone_is_not_an_emergency():
    assert not check_emergency(HEAD_ONLY).triggered
    assert not check_emergency(CHEST_COUGH).triggered


def test_emergency_text_still_fires_with_body_map_context():
    assert check_emergency(EMERGENCY_WITH_MAP).triggered


def test_prescription_refusal_still_fires_with_body_map_context():
    assert check_prescription_request(PRESCRIPTION_WITH_MAP).triggered
