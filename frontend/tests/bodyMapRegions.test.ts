import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import {
  buildMessagePayload,
  hiddenInView,
  REGION_GROUPS,
  REGION_LABELS,
  REGION_ORDER,
  regionsForView,
  regionView,
  suggestedSymptoms,
  summarizeSelection,
  toggleItem,
  type BodyRegion,
} from "../src/utils/bodyMap.ts";
import { streamRequestBody } from "../src/services/chat.ts";

const bodyMapSource = readFileSync(new URL("../src/components/bodymap/BodyMap.tsx", import.meta.url), "utf8");
const schemaSource = readFileSync(new URL("../../backend/app/schemas/message.py", import.meta.url), "utf8");

const REQUIRED: BodyRegion[] = ["head", "neck", "chest", "abdomen", "upper_back", "lower_back", "shoulder", "arm", "elbow", "wrist_hand", "hip", "thigh", "knee", "lower_leg", "ankle_foot"];

describe("body map regions", () => {
  it("covers every required anatomical region, each with a label", () => {
    assert.deepEqual([...REGION_ORDER].sort(), [...REQUIRED].sort());
    for (const region of REQUIRED) assert.ok(REGION_LABELS[region], region);
  });

  it("lists every region exactly once in the accessible grouped list", () => {
    const grouped = REGION_GROUPS.flatMap((group) => group.regions);
    assert.equal(new Set(grouped).size, grouped.length);
    assert.deepEqual([...grouped].sort(), [...REQUIRED].sort());
  });

  it("keeps region ids identical to the backend schema", () => {
    const literal = schemaSource.match(/BodyRegionId = Literal\[([^\]]+)\]/);
    assert.ok(literal, "BodyRegionId literal not found");
    const backend = literal[1].split(",").map((item) => item.trim().replace(/"/g, "")).filter(Boolean).sort();
    assert.deepEqual(backend, Object.keys(REGION_LABELS).sort());
  });
});

describe("selection", () => {
  it("supports multi-select and deselect", () => {
    let selected: BodyRegion[] = [];
    selected = toggleItem(selected, "knee");
    selected = toggleItem(selected, "ankle_foot");
    selected = toggleItem(selected, "lower_back");
    assert.deepEqual(selected, ["knee", "ankle_foot", "lower_back"]);
    selected = toggleItem(selected, "ankle_foot");
    assert.deepEqual(selected, ["knee", "lower_back"]);
  });

  it("resets to the fallback state when cleared", () => {
    assert.equal(summarizeSelection([], []), "No body regions or symptoms selected");
    assert.deepEqual(suggestedSymptoms([]), ["Fever", "Tiredness", "Body ache"]);
  });

  it("suggests symptoms for the selected areas without duplicates", () => {
    const chips = suggestedSymptoms(["knee", "ankle_foot"]);
    assert.ok(chips.includes("Knee pain"));
    assert.ok(chips.includes("Ankle pain"));
    assert.equal(chips.filter((chip) => chip === "Swelling").length, 1);
  });
});

describe("view switching", () => {
  it("shows chest and abdomen only on the front, back regions only on the back", () => {
    assert.equal(regionView("chest"), "front");
    assert.equal(regionView("lower_back"), "back");
    assert.equal(regionView("knee"), "both");
    assert.ok(regionsForView("front").includes("abdomen"));
    assert.ok(!regionsForView("front").includes("upper_back"));
    assert.ok(regionsForView("back").includes("upper_back"));
    assert.ok(!regionsForView("back").includes("chest"));
  });

  it("keeps selections from the other view and reports them as hidden", () => {
    const selected: BodyRegion[] = ["chest", "lower_back", "knee"];
    assert.deepEqual(hiddenInView(selected, "front"), ["lower_back"]);
    assert.deepEqual(hiddenInView(selected, "back"), ["chest"]);
  });

  it("renders front and back views in the component", () => {
    assert.match(bodyMapSource, /role="tablist"/);
    assert.match(bodyMapSource, /\["front", "back"\]/);
    assert.match(bodyMapSource, /aria-selected/);
  });
});

describe("message payload", () => {
  it("sends structured, de-duplicated body regions with the text", () => {
    const payload = buildMessagePayload("hurts on stairs", ["knee", "knee", "ankle_foot"], ["Knee pain"]);
    assert.deepEqual(payload.body_regions, ["knee", "ankle_foot"]);
    assert.match(payload.content, /^hurts on stairs/);
    assert.match(payload.content, /not a diagnosis/);
  });

  it("does not attach body_regions when none are selected", () => {
    assert.deepEqual(streamRequestBody("hello"), { content: "hello" });
    assert.deepEqual(streamRequestBody("hello", []), { content: "hello" });
  });

  it("adds body_regions to the stream request body when present", () => {
    assert.deepEqual(streamRequestBody("knee pain", ["knee", "knee"]), { content: "knee pain", body_regions: ["knee"] });
  });

  it("never turns a region selection into a diagnosis", () => {
    const { content } = buildMessagePayload("", ["chest"], []);
    assert.doesNotMatch(content, /you have|diagnos(is|ed) (is|with)/i);
  });
});
