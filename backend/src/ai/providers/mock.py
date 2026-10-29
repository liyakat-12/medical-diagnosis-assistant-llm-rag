from __future__ import annotations

import re
from collections.abc import Iterator

from src.ai.base import BaseAIProvider


def _conversational_mock(user_prompt: str) -> str:
    query = ""
    for line in (user_prompt or "").splitlines():
        if line.lower().startswith("user message:"):
            query = line.split(":", 1)[-1].strip()
            break
    lowered = (query or user_prompt or "").lower()
    if "print(" in lowered or "python" in lowered or "javascript" in lowered or ("write" in lowered and "code" in lowered):
        return (
            "That looks like a programming question. Example:\n\n"
            "```python\nprint(\"my name is abd\")\n```\n\n"
            "This prints the text in parentheses. I can also help debug or explain other code."
        )
    if ("car" in lowered and "bike" in lowered) or "versus" in lowered or " vs" in lowered:
        return (
            "A car is usually better for long trips, weather protection, and carrying people or luggage. "
            "A bike is cheaper, easier to park, and better for short urban trips. "
            "Choose based on distance, budget, weather, and whether you need to carry passengers."
        )
    if "travel" in lowered or "distance" in lowered or "hotel" in lowered or "flight" in lowered:
        return (
            "I can help with travel planning. Share the cities, dates, and budget, "
            "and I will compare options such as train, bus, or flight for that route."
        )
    if "weather" in lowered:
        return (
            "I do not have a live weather feed here. Check a local forecast for your city. "
            "If you share the place and date, I can still help you plan around typical conditions."
        )
    if "laptop" in lowered or "iphone" in lowered or "android" in lowered or "tablet" in lowered or "phone" in lowered:
        return (
            "I can compare laptops, phones, and other consumer products. Tell me which features matter most "
            "(price, battery, screen, storage) and I will outline trade-offs."
        )
    topic = query or "your question"
    return (
        f"Here is a general answer to: {topic}. Ask a follow-up if you want more detail, "
        "examples, or a comparison. If this is actually a health symptom, describe it and "
        "I will look it up in the medical notes."
    )


def _extract_query(user_prompt: str) -> str:
    for line in (user_prompt or "").splitlines():
        lowered = line.lower()
        if lowered.startswith("user symptom description:") or lowered.startswith("user question:"):
            return line.split(":", 1)[-1].strip()
    return ""


def _context_blocks(user_prompt: str) -> list[str]:
    marker = "Reference context (each block is a passage from a cited medical document):"
    if marker not in (user_prompt or ""):
        return []
    after = user_prompt.split(marker, 1)[1]
    for stop in ("\n\nUser symptom description:", "\n\nUser question:"):
        if stop in after:
            after = after.split(stop, 1)[0]
            break
    blocks = [part.strip() for part in after.split("\n\n") if part.strip() and "Source:" in part]
    return blocks


class MockProvider:
    name = "mock"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        del model, max_tokens
        if "[CONVERSATIONAL]" in user_prompt or "helpful conversational assistant" in (system_prompt or "").lower():
            return _conversational_mock(user_prompt)
        if "Do not name specific diseases" in (system_prompt or ""):
            from src.safety.followups import weak_match_answer

            query = ""
            for line in (user_prompt or "").splitlines():
                if line.lower().startswith("user symptom description:"):
                    query = line.split(":", 1)[-1].strip()
                    break
            return weak_match_answer(query or user_prompt or "")
        if not grounded:
            return (
                "No documents were retrieved, so this answer cannot be cited.\n"
                "Not a diagnosis — see a clinician if needed."
            )

        from src.llm.notes_answer import synthesize_notes_answer

        blocks = _context_blocks(user_prompt)
        query = _extract_query(user_prompt) or "these symptoms"
        if not blocks:
            return (
                "Not enough matching documents for a confident answer. "
                "Please rephrase, or see a doctor.\n"
                "Not a diagnosis — see a clinician if needed."
            )
        educational = "general educational question" in (system_prompt or "").lower() or (
            "do not assume they have the condition" in (system_prompt or "").lower()
        )
        treatment = "general treatment and management" in (system_prompt or "").lower()
        causes = "plausible causes supported" in (system_prompt or "").lower()
        symptom_edu = "what symptoms a named condition can cause" in (system_prompt or "").lower()
        mode = "symptom"
        if educational:
            mode = "education"
        elif treatment:
            mode = "treatment"
        elif causes:
            mode = "causes"
        elif symptom_edu:
            mode = "symptom_education"
        answer = synthesize_notes_answer(query, blocks, mode=mode)
        if mode == "symptom":
            recs: list[str] = []
            for sent in re.split(r"(?<=[.!?])\s+", user_prompt):
                text = sent.strip()
                if len(text) < 35 or len(text) > 220:
                    continue
                if not re.search(r"\b(self-care|rest|fluid|see a doctor|seek|consult|monitor)\b", text, re.I):
                    continue
                if text not in recs:
                    recs.append(text)
                if len(recs) == 2:
                    break
            if recs and "Recommendations:" not in answer:
                lines = [answer.rstrip()]
                # Keep recommendations before the closing disclaimer line.
                disclaimer = "Not a diagnosis — see a clinician if needed."
                if lines[-1].endswith(disclaimer):
                    body = lines[-1][: -len(disclaimer)].rstrip()
                    lines = [body, "Recommendations:", *[f"- {rec}" for rec in recs], disclaimer]
                    return "\n".join(line for line in lines if line)
                lines.append("Recommendations:")
                lines.extend(f"- {rec}" for rec in recs)
                return "\n".join(lines)
        return answer

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        text = self.generate(
            system_prompt, user_prompt, grounded=grounded, model=model, max_tokens=max_tokens
        )
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else f" {word}"
