import type { ChatMessage, Citation } from "../types";

const EVIDENCE_STATUS =
  /not verified|General AI medical knowledge|No matching sources|not retrieved from the (MediAssist )?knowledge base/i;

export function formatConditionName(value?: string): string {
  const text = (value || "").trim();
  if (!text) return "Possible match";
  if (text.includes("_") && !text.includes(" ")) {
    return text.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
  return text;
}

export function uniqueCitations(message: ChatMessage) {
  const seen = new Set<string>();
  return message.citations.filter((item) => {
    const key = (item.title || item.condition || item.source || "").trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function isEvidenceStatusCitation(item: Citation): boolean {
  return EVIDENCE_STATUS.test(`${item.title || ""} ${item.source || ""} ${item.condition || ""}`);
}

export function retrievedCitations(message: ChatMessage): Citation[] {
  return uniqueCitations(message).filter((item) => !isEvidenceStatusCitation(item));
}

export function evidenceStatusItems(message: ChatMessage): Citation[] {
  return uniqueCitations(message).filter((item) => isEvidenceStatusCitation(item));
}

export function isSymptomCardMessage(message: ChatMessage): boolean {
  const level = message.triage?.level;
  return Boolean(message.possible_conditions.length || (level && level !== "none"));
}

export function formatAssistantCopy(message: ChatMessage): string {
  if (message.refused) return message.content;
  const outcomes = message.possible_conditions.slice(0, 4);
  const citations = retrievedCitations(message);
  const statusItems = evidenceStatusItems(message);
  const lines: string[] = [];
  const explanation = (message.content || "").trim();
  const symptomLayout = isSymptomCardMessage(message);

  if (explanation) {
    lines.push(explanation);
  }

  if (symptomLayout) {
    if (lines.length) lines.push("");
    lines.push("Possible explanations");
    if (outcomes.length) {
      for (const item of outcomes) {
        const label = item.evidence_match_label ? ` — ${item.evidence_match_label}` : "";
        lines.push(`• ${formatConditionName(item.condition)}${label}`);
      }
    }
    if (message.triage && message.triage.level !== "none") {
      lines.push("", "Urgency");
      lines.push(`• ${message.triage.label}`);
      if (message.triage.guidance) lines.push(`• ${message.triage.guidance}`);
    }
  }

  if (citations.length) {
    if (lines.length) lines.push("");
    lines.push("Sources");
    for (const item of citations) {
      const title = item.title || formatConditionName(item.condition);
      lines.push(`• ${title}${item.source ? ` — ${item.source}` : ""}`);
    }
  }

  if (statusItems.length) {
    if (lines.length) lines.push("");
    lines.push("Evidence status");
    for (const item of statusItems) {
      const title = item.title || formatConditionName(item.condition);
      lines.push(`• ${title}${item.source ? ` — ${item.source}` : ""}`);
    }
  }

  const disclaimer = (message.disclaimer || "").trim();
  const combined = lines.join("\n").toLowerCase();
  if (
    disclaimer &&
    !combined.includes(disclaimer.toLowerCase()) &&
    !(statusItems.length && /not verified against the .*knowledge base/i.test(disclaimer))
  ) {
    lines.push("", disclaimer);
  }
  return lines.join("\n");
}
