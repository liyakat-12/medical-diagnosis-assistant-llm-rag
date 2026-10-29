import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { looksEmergency, needsPromptAssessment } from "../src/utils/emergency.ts";
import { looksMedical, needsSymptomIntake } from "../src/utils/intent.ts";
import type { ChatMessage } from "../src/types/index.ts";

const chatPageSource = readFileSync(new URL("../src/pages/Chat.tsx", import.meta.url), "utf8");
const bubbleSource = readFileSync(new URL("../src/components/chat/MessageBubble.tsx", import.meta.url), "utf8");
const followUpSource = readFileSync(new URL("../src/components/chat/FollowUpCard.tsx", import.meta.url), "utf8");

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

describe("looksMedical", () => {
  it("rejects greetings and off-topic text", () => {
    assert.equal(looksMedical("hello"), false);
    assert.equal(looksMedical("I am good"), false);
    assert.equal(looksMedical("this is a table"), false);
    assert.equal(looksMedical("what can you do?"), false);
    assert.equal(looksMedical("What is the distance from Bengaluru to Delhi?"), false);
    assert.equal(looksMedical("Which is better, a car or a bike?"), false);
    assert.equal(looksMedical("What's better, an iPhone or Android?"), false);
    assert.equal(looksMedical("Car vs bike?"), false);
    assert.equal(looksMedical("Should I buy a car or a bike?"), false);
    assert.equal(looksMedical("Write Python code"), false);
    assert.equal(looksMedical('print("my name is abd")'), false);
  });

  it("accepts symptom and disease questions", () => {
    assert.equal(looksMedical("I have a cough and mild fever"), true);
    assert.equal(looksMedical("What is diverticulitis?"), true);
    assert.equal(looksMedical("I have pain when riding my bike"), true);
    assert.equal(looksMedical("I feel dizzy while travelling"), true);
    assert.equal(looksMedical("Can you explain diabetes?"), true);
    assert.equal(looksMedical("Tell me about asthma"), true);
    assert.equal(looksMedical("What asthma is"), true);
    assert.equal(looksMedical("I want to understand asthma"), true);
    assert.equal(looksMedical("What causes headaches?"), true);
    assert.equal(looksMedical("What is paracetamol used for?"), true);
    assert.equal(looksMedical("I have diarrhoea after a meal out"), true);
    assert.equal(looksMedical("How can I quit smoking?"), true);
    assert.equal(looksMedical("What is dementia, and is it a normal part of ageing?"), true);
    assert.equal(looksMedical("What causes a rare disease that is not in my knowledge base?"), true);
  });

  it("treats follow-ups as medical once a symptom thread exists", () => {
    const history = [message({ content: "I have a cough", possible_conditions: [{ condition: "Cold" }] })];
    assert.equal(looksMedical("I also have a mild fever with that", history), true);
    assert.equal(looksMedical("What should I do?", history), true);
    assert.equal(looksMedical("What could cause this?", history), true);
    assert.equal(looksMedical("miss you", history), false);
    assert.equal(looksMedical("Which is better, a car or a bike?", history), false);
  });
});

describe("looksEmergency", () => {
  it("catches paraphrases and skips negated or quoted wording", () => {
    assert.equal(looksEmergency("I have chest pain"), false);
    assert.equal(looksEmergency("I have shortness of breath"), true);
    assert.equal(looksEmergency("chest pain spreading to my jaw"), true);
    assert.equal(looksEmergency("I have a sudden, extremely severe headache"), true);
    assert.equal(looksEmergency("I am coughing up blood"), true);
    assert.equal(
      looksEmergency("I am coughing up a large amount of blood and struggling to breathe"),
      true,
    );
    assert.equal(looksEmergency("I have a persistent cough with blood"), false);
    assert.equal(needsPromptAssessment("I have a persistent cough with blood"), true);
    assert.equal(needsPromptAssessment("I am coughing up blood"), false);
    assert.equal(needsSymptomIntake("I have chest pain", []), true);
    assert.equal(needsSymptomIntake("I have a sudden, extremely severe headache", []), false);
    assert.equal(looksEmergency("I don't have chest pain"), false);
    assert.equal(looksEmergency('What does "chest pain" mean?'), false);
  });
});

describe("needsSymptomIntake", () => {
  it("opens intake only for a first symptom query", () => {
    assert.equal(needsSymptomIntake("I have a cough", []), true);
    assert.equal(needsSymptomIntake("hello", []), false);
    assert.equal(needsSymptomIntake("What is asthma?", []), false);
    assert.equal(needsSymptomIntake("Tell me about asthma", []), false);
    assert.equal(needsSymptomIntake("What asthma is", []), false);
    assert.equal(needsSymptomIntake("I want to understand asthma", []), false);
    assert.equal(needsSymptomIntake("crushing chest pain", []), false);
    assert.equal(
      needsSymptomIntake("What causes a rare disease that is not in my knowledge base?", []),
      false,
    );
  });

  it("does not reopen intake after a medical thread has started", () => {
    const history = [message({ content: "I have a cough" })];
    assert.equal(needsSymptomIntake("I also have a fever", history), false);
  });
});

describe("chat chrome", () => {
  it("keeps hospitals in the header modal, not every bubble", () => {
    assert.match(chatPageSource, /Nearby hospitals/);
    assert.match(chatPageSource, /HospitalFinderModal/);
    assert.equal(chatPageSource.includes("<NearbyHospitals"), false);
    assert.match(bubbleSource, /Emergency — View Nearby Hospitals/);
    assert.match(chatPageSource, /conversationChrome/);
  });

  it("uses Analyze Symptoms and Skip & Send Now on the intake card", () => {
    assert.match(followUpSource, /Analyze Symptoms/);
    assert.match(followUpSource, /Skip & Send Now/);
  });

  it("renders GitHub-flavored tables and labels general knowledge after the explanation", () => {
    assert.match(bubbleSource, /remarkGfm/);
    assert.match(bubbleSource, /remarkPlugins=\{\[remarkGfm\]\}/);
    assert.match(bubbleSource, /EvidenceNote/);
    assert.match(bubbleSource, /was not retrieved from the MediAssist knowledge base/);
    const explanationIdx = bubbleSource.indexOf("<MarkdownBody>{explanation}</MarkdownBody>");
    const fallbackIdx = bubbleSource.indexOf("<MarkdownBody>{message.content");
    const evidenceIdx = bubbleSource.indexOf("<EvidenceNote message={message} />", Math.max(explanationIdx, fallbackIdx));
    assert.ok(fallbackIdx >= 0 || explanationIdx >= 0);
    assert.ok(evidenceIdx > 0);
  });
});
