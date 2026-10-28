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

            # Pull the user line from the prompt when present so follow-ups stay relevant.
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
        titles: list[str] = []
        title_re = re.compile(r"Source:\s*(.+?)(?:\s*\(|$)", re.IGNORECASE)
        for block in user_prompt.split("\n\n"):
            if "Source:" in block:
                match = title_re.search(block)
                title = match.group(1).strip() if match else "Retrieved medical document"
                if title not in titles:
                    titles.append(title)
        if not titles:
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
        if educational or treatment or causes or symptom_edu:
            lines = []
            for title in titles[:3]:
                lines.append(f"{title} (Source: {title}).")
            lines.append("Not a diagnosis — this is general information from reference notes.")
            return "\n".join(lines)
        lines = ["Possible matches:"]
        for i, title in enumerate(titles[:3], start=1):
            lines.append(f"{i}. {title} (Source: {title}).")
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
        if recs:
            lines.append("Recommendations:")
            lines.extend(f"- {rec}" for rec in recs)
        lines.append("Not a diagnosis — see a clinician if needed.")
        return "\n".join(lines)

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
