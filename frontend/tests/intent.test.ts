import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
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
  });

  it("accepts symptom and disease questions", () => {
    assert.equal(looksMedical("I have a cough and mild fever"), true);
    assert.equal(looksMedical("What is diverticulitis?"), true);
  });

  it("treats follow-ups as medical once a symptom thread exists", () => {
    const history = [message({ content: "I have a cough", possible_conditions: [{ condition: "Cold" }] })];
    assert.equal(looksMedical("I also have a mild fever with that", history), true);
  });
});

describe("needsSymptomIntake", () => {
  it("opens intake only for a first symptom query", () => {
    assert.equal(needsSymptomIntake("I have a cough", []), true);
    assert.equal(needsSymptomIntake("hello", []), false);
    assert.equal(needsSymptomIntake("crushing chest pain", []), false);
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
  });

  it("uses Analyze Symptoms and Skip & Send Now on the intake card", () => {
    assert.match(followUpSource, /Analyze Symptoms/);
    assert.match(followUpSource, /Skip & Send Now/);
  });
});
