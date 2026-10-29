import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import type { ChatMessage } from "../src/types/index.ts";
import { formatAssistantCopy, isSymptomCardMessage } from "../src/utils/report.ts";

const bubbleSource = readFileSync(new URL("../src/components/chat/MessageBubble.tsx", import.meta.url), "utf8");
const chatSource = readFileSync(new URL("../src/context/ChatContext.tsx", import.meta.url), "utf8");
const sessionSource = readFileSync(new URL("../src/utils/chatSession.ts", import.meta.url), "utf8");

function message(partial: Partial<ChatMessage>): ChatMessage {
  return {
    id: "1",
    chat_id: "c",
    user_id: "u",
    role: "assistant",
    content: "",
    citations: [],
    possible_conditions: [],
    recommendations: [],
    refused: false,
    ...partial,
  };
}

describe("informational knowledge-base miss copy", () => {
  it("keeps the explanation and citations, not symptom placeholders", () => {
    const item = message({
      content:
        "I did not find a close match in the local notes, so this uses general medical knowledge.\n\nDiseases can arise in several broad ways.\n\nThis is general information, not a diagnosis.",
      citations: [
        { title: "No matching sources were found in the MediAssist knowledge base" },
        { title: "General medical knowledge was used and was not verified against the knowledge base" },
      ],
      disclaimer: "This is general information, not a diagnosis.",
    });
    assert.equal(isSymptomCardMessage(item), false);
    const copy = formatAssistantCopy(item);
    assert.match(copy, /Diseases can arise in several broad ways/);
    assert.match(copy, /Evidence status/);
    assert.match(copy, /No matching sources were found in the MediAssist knowledge base/);
    assert.match(copy, /General medical knowledge was used and was not verified against the knowledge base/);
    assert.equal((copy.match(/not verified against the knowledge base/gi) || []).length, 1);
    assert.equal((copy.match(/This is general information, not a diagnosis/g) || []).length, 1);
    assert.equal(copy.includes("This explanation is general medical information"), false);
    assert.equal(copy.includes("Try adding more symptom detail"), false);
    assert.equal(copy.includes("Urgency will appear after the notes are checked"), false);
    assert.equal(/groq|openai|chatgpt|chroma/i.test(copy), false);
  });

  it("still copies urgency for emergency symptom replies", () => {
    const item = message({
      // On-screen answer omits the Call-112 banner; triage.guidance still carries it for copy.
      content: "Follow the urgency instructions shown with this reply.",
      triage: {
        level: "emergency",
        label: "Emergency",
        guidance: "Call 112 now.",
      },
      possible_conditions: [{ condition: "Heart attack", match_percent: 100, evidence_match_label: "Closest evidence match" }],
    });
    assert.equal(isSymptomCardMessage(item), true);
    const copy = formatAssistantCopy(item);
    assert.match(copy, /Follow the urgency instructions/);
    assert.equal(/call 112/i.test(item.content), false);
    assert.match(copy, /Call 112 now/);
    assert.match(copy, /Emergency/);
    assert.match(copy, /Heart attack/);
    assert.match(copy, /Closest evidence match/);
    assert.equal(copy.includes("%"), false);
    assert.match(copy, /Possible explanations/);
  });
});

describe("chat bubble rendering", () => {
  it("shows markdown answers for citation-only replies and keeps streamed content", () => {
    assert.match(bubbleSource, /isSymptomCardMessage/);
    assert.match(bubbleSource, /<MarkdownBody>\{message\.content/);
    assert.match(bubbleSource, /Evidence status/);
    assert.match(bubbleSource, /evidenceStatusItems\(message\)\.length\) return null/);
    assert.equal(bubbleSource.includes("Urgency will appear after the notes are checked"), false);
    assert.match(chatSource, /assistantFromEvent/);
    assert.match(sessionSource, /result\.answer \|\| fallback\.content/);
    assert.equal(/groq|openai|chatgpt/i.test(bubbleSource), false);
  });
});
