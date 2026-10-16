import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import {
  BODY_MAP_DISCLAIMER,
  buildBodyMapQuery,
  formatReviewLine,
  suggestedSymptoms,
  summarizeSelection,
  toggleItem,
} from "../src/utils/bodyMap.ts";
import { looksEmergency } from "../src/utils/emergency.ts";

const bodyMapSource = readFileSync(new URL("../src/components/chat/BodyMap.tsx", import.meta.url), "utf8");
const chatInputSource = readFileSync(new URL("../src/components/chat/ChatInput.tsx", import.meta.url), "utf8");

describe("toggleItem", () => {
  it("adds a missing region and removes a selected one", () => {
    assert.deepEqual(toggleItem(["head"], "chest"), ["head", "chest"]);
    assert.deepEqual(toggleItem(["head", "chest"], "head"), ["chest"]);
  });
});

describe("suggestedSymptoms", () => {
  it("shows general suggestions until a region is selected", () => {
    assert.deepEqual(suggestedSymptoms([]), ["Fever", "Tiredness", "Body ache"]);
  });

  it("returns head suggestions when the head is selected", () => {
    const suggestions = suggestedSymptoms(["head"]);
    assert.ok(suggestions.includes("Headache"));
    assert.ok(suggestions.includes("Dizziness"));
    assert.ok(suggestions.includes("Scalp pain"));
  });

  it("unions symptoms for multiple regions without duplicates", () => {
    const suggestions = suggestedSymptoms(["chest", "abdomen"]);
    assert.ok(suggestions.includes("Chest pain"));
    assert.ok(suggestions.includes("Nausea"));
    assert.equal(suggestions.length, new Set(suggestions).size);
  });
});

describe("buildBodyMapQuery", () => {
  it("keeps typed text and appends structured context once", () => {
    const query = buildBodyMapQuery("worse after walking", ["chest"], ["Cough", "Cough"]);
    assert.ok(query.startsWith("worse after walking"));
    assert.equal((query.match(/locations = Chest/g) || []).length, 1);
    assert.equal((query.match(/symptoms = Cough/g) || []).length, 1);
    assert.ok(query.includes("not a diagnosis"));
  });

  it("replaces location context instead of appending duplicates", () => {
    const first = buildBodyMapQuery("hello", ["head"], []);
    const second = buildBodyMapQuery("hello", ["chest"], []);
    assert.ok(first.includes("Head"));
    assert.equal(second.includes("Head"), false);
    assert.ok(second.includes("Chest"));
    assert.ok(second.startsWith("hello"));
  });

  it("can send map context without typed text", () => {
    const query = buildBodyMapQuery("  ", ["leg"], ["Swelling"]);
    assert.ok(query.includes("locations = Leg"));
    assert.ok(query.includes("symptoms = Swelling"));
    assert.equal(query.includes("\n\n\n"), false);
  });

  it("does not invent a disease from a body part", () => {
    const query = buildBodyMapQuery("", ["head"], []);
    assert.equal(/migraine|stroke|tumou?r/i.test(query), false);
    assert.ok(query.includes("Head"));
  });
});

describe("summarizeSelection", () => {
  it("summarizes collapsed selections", () => {
    assert.equal(summarizeSelection(["head", "arm"], ["Headache"]), "Head, Arm · Headache");
    assert.equal(summarizeSelection([], []), "No body regions or symptoms selected");
  });
});

describe("formatReviewLine", () => {
  it("reviews typed text without a no-selection message", () => {
    assert.equal(formatReviewLine("worse at night", [], []), "worse at night");
  });

  it("reviews map selections with typed text", () => {
    assert.equal(formatReviewLine("worse at night", ["chest"], ["Cough"]), "Chest · Cough · worse at night");
  });
});

describe("disclaimer", () => {
  it("states the map is not a diagnosis", () => {
    assert.ok(BODY_MAP_DISCLAIMER.toLowerCase().includes("not a diagnosis"));
  });
});

describe("emergency handling", () => {
  it("does not treat a body region alone as an emergency", () => {
    assert.equal(looksEmergency(buildBodyMapQuery("", ["chest"], ["Cough"])), false);
    assert.equal(looksEmergency(buildBodyMapQuery("", ["head"], [])), false);
  });

  it("still flags emergency wording in the composed query", () => {
    const query = buildBodyMapQuery("crushing chest pain", ["chest"], []);
    assert.equal(looksEmergency(query), true);
  });
});

describe("accessibility and collapse markup", () => {
  it("keeps SVG regions keyboard-operable and labeled", () => {
    assert.match(bodyMapSource, /tabIndex=\{disabled \? -1 : 0\}/);
    assert.match(bodyMapSource, /aria-pressed=\{selected\}/);
    assert.match(bodyMapSource, /Or choose with buttons/);
    assert.match(bodyMapSource, /aria-expanded=\{open\}/);
  });

  it("keeps selection state in ChatInput instead of duplicating it", () => {
    assert.match(chatInputSource, /const \[regions, setRegions\]/);
    assert.match(chatInputSource, /const \[symptoms, setSymptoms\]/);
    assert.match(chatInputSource, /onSend\(preview\)/);
    assert.equal(bodyMapSource.includes("useState"), false);
  });
});
