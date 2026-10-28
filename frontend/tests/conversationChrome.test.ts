import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import type { ChatMessage } from "../src/types/index.ts";
import { conversationChrome } from "../src/utils/conversationChrome.ts";
import { evidenceStatusItems, formatAssistantCopy, retrievedCitations } from "../src/utils/report.ts";

const chatPageSource = readFileSync(new URL("../src/pages/Chat.tsx", import.meta.url), "utf8");
const bubbleSource = readFileSync(new URL("../src/components/chat/MessageBubble.tsx", import.meta.url), "utf8");
const emergencySource = readFileSync(new URL("../src/components/chat/EmergencyCallButton.tsx", import.meta.url), "utf8");

function message(partial: Partial<ChatMessage>): ChatMessage {
  return {
    id: "1",
    chat_id: "c",
    user_id: "u",
    role: "user",
    content: "",
    citations: [],
    possible_conditions: [],
    recommendations: [],
    refused: false,
    ...partial,
  };
}

describe("conversationChrome", () => {
  it("uses Health information for a general medical question with no symptoms", () => {
    const chrome = conversationChrome([
      message({ content: "What causes a rare disease that is not in my knowledge base?" }),
      message({
        id: "2",
        role: "assistant",
        content: "Diseases can arise in several broad ways.",
        citations: [
          { title: "No matching sources were found in the MediAssist knowledge base" },
          { title: "General medical knowledge was used and was not verified against the knowledge base" },
        ],
      }),
    ]);
    assert.equal(chrome.title, "Health information");
    assert.equal(chrome.emphasizeEmergency, false);
    assert.match(chrome.subtitle, /Not a diagnosis/);
  });

  it("uses Health information for educational paraphrases with no personal symptoms", () => {
    for (const query of ["What is asthma?", "What asthma is", "Tell me about asthma", "Explain asthma in simple words", "I want to understand asthma"]) {
      const chrome = conversationChrome([
        message({ content: query }),
        message({
          id: "2",
          role: "assistant",
          content: "Asthma tightens the airways.",
          metadata: { question_type: "MEDICAL_EDUCATION", personal_context: false, evidence_origin: "knowledge_base" },
          citations: [{ title: "What Asthma Can Feel Like", source: "CDC" }],
        }),
      ]);
      assert.equal(chrome.title, "Health information", query);
      assert.equal(chrome.emphasizeEmergency, false, query);
    }
  });

  it("keeps Symptom conversation for a personal symptom thread", () => {
    const chrome = conversationChrome([
      message({ content: "I have a cough" }),
      message({
        id: "2",
        role: "assistant",
        content: "This may be a leftover cold.",
        possible_conditions: [{ condition: "Common cold", match_percent: 60 }],
        triage: { level: "self_care", label: "Self-care", guidance: "Rest." },
        citations: [{ title: "Dry Cough at Night", source: "Sample KB" }],
      }),
    ]);
    assert.equal(chrome.title, "Symptom conversation");
    assert.equal(chrome.emphasizeEmergency, false);
  });

  it("emphasizes emergency help for red-flag symptoms", () => {
    const chrome = conversationChrome([
      message({ content: "crushing chest pain spreading to my jaw" }),
      message({
        id: "2",
        role: "assistant",
        content: "This may be urgent.",
        triage: { level: "emergency", label: "Emergency", guidance: "Call 112 now." },
      }),
    ]);
    assert.equal(chrome.title, "Emergency help");
    assert.equal(chrome.emphasizeEmergency, true);
  });

  it("drops emergency chrome after a later non-emergency turn", () => {
    const chrome = conversationChrome([
      message({ content: "crushing chest pain spreading to my jaw" }),
      message({
        id: "2",
        role: "assistant",
        content: "This may be urgent.",
        triage: { level: "emergency", label: "Emergency", guidance: "Call 112 now." },
      }),
      message({ id: "3", content: "Which is better, a car or a bike?" }),
    ]);
    assert.equal(chrome.emphasizeEmergency, false);
    assert.notEqual(chrome.title, "Emergency help");
  });
});

describe("evidence status versus sources", () => {
  it("treats knowledge-base-miss labels as evidence status, not retrieved sources", () => {
    const item = message({
      role: "assistant",
      content: "Diseases can arise in several broad ways.",
      citations: [
        { title: "No matching sources were found in the MediAssist knowledge base" },
        { title: "General medical knowledge was used and was not verified against the knowledge base" },
      ],
    });
    assert.equal(retrievedCitations(item).length, 0);
    assert.equal(evidenceStatusItems(item).length, 2);
    const copy = formatAssistantCopy(item);
    assert.match(copy, /Evidence status/);
    assert.equal(copy.includes("\nSources\n"), false);
    assert.match(copy, /No matching sources were found in the MediAssist knowledge base/);
    assert.match(copy, /General medical knowledge was used and was not verified against the knowledge base/);
    assert.equal((copy.match(/not verified against the knowledge base/gi) || []).length, 1);
    assert.equal(copy.includes("This explanation is general medical information"), false);
  });

  it("keeps genuine retrieved notes under Sources", () => {
    const item = message({
      role: "assistant",
      content: "A dry cough at night may follow a leftover cold.",
      possible_conditions: [{ condition: "Dry Cough", match_percent: 100 }],
      triage: { level: "self_care", label: "Self-care", guidance: "Rest and fluids." },
      citations: [{ title: "Dry Cough at Night", source: "Sample KB", url: "https://example.test/cough" }],
    });
    assert.equal(retrievedCitations(item).length, 1);
    assert.equal(evidenceStatusItems(item).length, 0);
    const copy = formatAssistantCopy(item);
    assert.match(copy, /Sources/);
    assert.match(copy, /Dry Cough at Night/);
    assert.equal(copy.includes("Evidence status"), false);
  });
});

describe("chat chrome markup", () => {
  it("wires a context-aware header, quieter 112 control, and a non-overlapping Latest button", () => {
    assert.match(chatPageSource, /conversationChrome/);
    assert.match(chatPageSource, /chrome\.title/);
    assert.match(chatPageSource, /pb-28/);
    assert.match(chatPageSource, /right-4/);
    assert.equal(chatPageSource.includes("left-1/2"), false);
    assert.match(bubbleSource, /Evidence status/);
    assert.match(bubbleSource, /retrievedCitations/);
    assert.match(emergencySource, /EMERGENCY_TEL/);
    assert.match(emergencySource, /urgent \? `Call \$\{EMERGENCY_NUMBER\}` : `112`/);
  });
});
