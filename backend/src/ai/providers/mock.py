from __future__ import annotations

import re
from collections.abc import Iterator

from src.ai.base import BaseAIProvider


class MockProvider:
    name = "mock"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
    ) -> str:
        del model
        if "[CONVERSATIONAL]" in user_prompt or "friendly medical information helper" in (system_prompt or "").lower():
            return (
                "Hello — I'm MediAssist, a medical information helper. "
                "Describe symptoms in your own words, or tap the body map, whenever you want to look something up. "
                "I'm not a doctor and this is not a diagnosis."
            )
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
    ) -> Iterator[str]:
        text = self.generate(system_prompt, user_prompt, grounded=grounded, model=model)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else f" {word}"
