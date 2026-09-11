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
        del system_prompt, model
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
