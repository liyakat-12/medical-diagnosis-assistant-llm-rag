import type { ChatMessage, PossibleCondition } from "../types";

export function formatConditionName(value?: string): string {
  const text = (value || "").trim();
  if (!text) return "Possible match";
  if (text.includes("_") && !text.includes(" ")) {
    return text.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
  return text;
}

export function withPercents(items: PossibleCondition[], limit = 4): PossibleCondition[] {
  const rows = items.slice(0, limit);
  if (!rows.length) return [];
  if (rows.every((item) => typeof item.match_percent === "number")) {
    return rows;
  }
  const scores = rows.map((item) => Math.max(0, item.relevance_score || 0));
  const total = scores.reduce((sum, score) => sum + score, 0);
  if (total <= 0) {
    const share = Math.floor(100 / rows.length);
    return rows.map((item, index) => ({
      ...item,
      match_percent: share + (index < 100 % rows.length ? 1 : 0),
    }));
  }
  const raw = scores.map((score) => (score / total) * 100);
  const floors = raw.map((value) => Math.floor(value));
  let leftover = 100 - floors.reduce((sum, value) => sum + value, 0);
  const order = raw
    .map((value, index) => ({ index, frac: value - floors[index] }))
    .sort((a, b) => b.frac - a.frac);
  const percents = [...floors];
  for (const item of order) {
    if (leftover <= 0) break;
    percents[item.index] += 1;
    leftover -= 1;
  }
  return rows.map((item, index) => ({ ...item, match_percent: percents[index] }));
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

export function formatAssistantCopy(message: ChatMessage): string {
  if (message.refused) return message.content;
  const outcomes = withPercents(message.possible_conditions);
  const citations = uniqueCitations(message);
  const lines: string[] = [];

  lines.push("1. Possible outcomes");
  if (outcomes.length) {
    for (const item of outcomes) {
      lines.push(`• ${formatConditionName(item.condition)} — ${item.match_percent}%`);
    }
  } else {
    lines.push("• No close matches yet. Try adding more symptom detail.");
  }

  lines.push("", "2. Urgency");
  if (message.triage) {
    lines.push(`• ${message.triage.label}`);
    if (message.triage.guidance) lines.push(`• ${message.triage.guidance}`);
  } else {
    lines.push("• Urgency will appear after the notes are checked.");
  }

  lines.push("", "3. Citations");
  if (citations.length) {
    for (const item of citations) {
      const title = item.title || formatConditionName(item.condition);
      lines.push(`• ${title}${item.source ? ` — ${item.source}` : ""}`);
    }
  } else {
    lines.push("• No sources retrieved for this reply.");
  }

  if (message.disclaimer) {
    lines.push("", message.disclaimer);
  }
  return lines.join("\n");
}
