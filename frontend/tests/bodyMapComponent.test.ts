import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { BodyFigure, BodyMapCard, BodyViewTabs } from "../src/components/bodymap/BodyMap.tsx";
import { DETAIL_LINES, FIGURE_VIEWBOX, MIRROR, REGION_LAYERS } from "../src/components/bodymap/bodyShapes.ts";
import { buildMessagePayload, REGION_LABELS, REGION_ORDER, toggleItem, viewForRegion, type BodyRegion, type BodyView } from "../src/utils/bodyMap.ts";

const noop = () => {};

function figure(view: BodyView, selected: BodyRegion[] = [], disabled = false) {
  return renderToStaticMarkup(createElement(BodyFigure, { view, selected, focused: null, onToggle: noop, disabled }));
}

function card(view: BodyView, selectedRegions: BodyRegion[]) {
  return renderToStaticMarkup(
    createElement(BodyMapCard, { view, onViewChange: noop, selectedRegions, onToggleRegion: noop, onClear: noop, onDescribe: noop }),
  );
}

function clearButton(html: string): string {
  const buttons = html.match(/<button\b[^>]*>(?:(?!<\/button>).)*<\/button>/g) ?? [];
  const found = buttons.find((button) => button.includes("Clear selection"));
  assert.ok(found, "Clear selection button not rendered");
  return found.slice(0, found.indexOf(">") + 1);
}

function regionButtons(html: string): Map<string, string> {
  const found = new Map<string, string>();
  for (const match of html.matchAll(/<g[^>]*role="button"[^>]*>/g)) {
    const label = match[0].match(/aria-label="([^",]+)/)?.[1] ?? "";
    found.set(label, match[0]);
  }
  return found;
}

describe("body figure views", () => {
  it("front view has chest and abdomen, not the back regions", () => {
    const labels = [...regionButtons(figure("front")).keys()];
    assert.ok(labels.includes("Chest") && labels.includes("Abdomen"));
    assert.ok(!labels.includes("Upper back") && !labels.includes("Lower back"));
    assert.match(figure("front"), /aria-label="Front View of the body/);
  });

  it("back view has upper and lower back, not chest or abdomen", () => {
    const labels = [...regionButtons(figure("back")).keys()];
    assert.ok(labels.includes("Upper back") && labels.includes("Lower back"));
    assert.ok(!labels.includes("Chest") && !labels.includes("Abdomen"));
    assert.match(figure("back"), /aria-label="Back View of the body/);
  });

  it("offers every required region across the two views, once per view", () => {
    const front = [...regionButtons(figure("front")).keys()];
    const back = [...regionButtons(figure("back")).keys()];
    assert.equal(new Set(front).size, front.length);
    assert.equal(new Set(back).size, back.length);
    const all = new Set([...front, ...back]);
    for (const region of REGION_ORDER) assert.ok(all.has(REGION_LABELS[region]), region);
  });

  it("labels the person's left and right correctly for each view", () => {
    assert.match(figure("front"), /x="22"[^>]*>Right</);
    assert.match(figure("back"), /x="22"[^>]*>Left</);
  });

  it("draws visibly different front and back anatomy", () => {
    assert.notDeepEqual(DETAIL_LINES.front, DETAIL_LINES.back);
    const foot = (view: BodyView) => REGION_LAYERS[view].find((layer) => layer.region === "ankle_foot")?.shapes[0].d;
    assert.notEqual(foot("front"), foot("back"));
  });

  it("draws both sides of every paired limb, including both forearms and hands", () => {
    for (const view of ["front", "back"] as BodyView[]) {
      const html = figure(view);
      for (const region of ["shoulder", "arm", "elbow", "wrist_hand", "thigh", "knee", "lower_leg", "ankle_foot"] as BodyRegion[]) {
        const layer = REGION_LAYERS[view].find((item) => item.region === region);
        assert.ok(layer, `${region} missing on ${view}`);
        for (const shape of layer.shapes) {
          assert.equal(shape.mirror, true, `${region} is not mirrored`);
          assert.match(html, new RegExp(`<path d="${shape.d.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}" fill-rule="nonzero"`));
          assert.match(html, new RegExp(`<path d="${shape.d.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}" transform="${MIRROR.replace(/[()]/g, "\\$&")}"`));
        }
      }
    }
  });

  it("joins limb segments edge to edge so no part floats", () => {
    const start = (d: string) => d.match(/^M([\d.]+) ([\d.]+) L([\d.]+) ([\d.]+)/)!.slice(1).map(Number);
    const shape = (region: BodyRegion, index = 0) => REGION_LAYERS.front.find((layer) => layer.region === region)!.shapes[index].d;
    const chain: [string, string][] = [
      [shape("arm", 0), shape("elbow")],
      [shape("elbow"), shape("arm", 1)],
      [shape("arm", 1), shape("wrist_hand")],
      [shape("thigh"), shape("knee")],
      [shape("knee"), shape("lower_leg")],
      [shape("lower_leg"), shape("ankle_foot")],
    ];
    for (const [upper, lower] of chain) {
      const [x1, y1, x2, y2] = start(lower);
      assert.ok(upper.includes(`${x1} ${y1}`) && upper.includes(`${x2} ${y2}`), `${lower.slice(0, 20)} does not meet ${upper.slice(0, 20)}`);
    }
  });

  it("keeps every shape inside the drawing area", () => {
    const [minX, minY, width, height] = FIGURE_VIEWBOX.split(" ").map(Number);
    for (const view of ["front", "back"] as BodyView[]) {
      for (const layer of REGION_LAYERS[view]) {
        for (const shape of layer.shapes) {
          const numbers = shape.d.match(/-?[\d.]+/g)!.map(Number);
          for (let i = 0; i + 1 < numbers.length; i += 2) {
            assert.ok(numbers[i] >= minX && numbers[i] <= minX + width, `${layer.region} x ${numbers[i]}`);
            assert.ok(numbers[i + 1] >= 0 && numbers[i + 1] <= minY + height, `${layer.region} y ${numbers[i + 1]}`);
          }
        }
      }
    }
  });

  it("shows a hover and focus label for each region and marks selection with a pattern, not only colour", () => {
    const html = figure("front", ["knee"]);
    assert.match(html, /group-hover:opacity-100 group-focus-visible:opacity-100/);
    assert.match(html, />Knee<\/text>/);
    for (const match of html.matchAll(/<rect x="([\d.-]+)" y="-29" width="([\d.]+)"/g)) {
      assert.ok(Number(match[1]) >= 0 && Number(match[1]) + Number(match[2]) <= 240, "hover label overflows the figure");
    }
    assert.match(html, /data-selected-overlay=""[^>]*>(<path[^>]*>)+/);
    assert.match(html, /fill="url\(#hatch-/);
    assert.doesNotMatch(figure("front"), /data-selected-overlay=""[^>]*><path/);
  });
});

describe("selection and keyboard access", () => {
  it("marks selected regions as pressed and keeps them when the view changes", () => {
    const selected: BodyRegion[] = ["knee", "lower_back", "chest"];
    const front = regionButtons(figure("front", selected));
    const back = regionButtons(figure("back", selected));
    assert.match(front.get("Knee") ?? "", /aria-pressed="true"/);
    assert.match(front.get("Chest") ?? "", /aria-pressed="true"/);
    assert.match(back.get("Knee") ?? "", /aria-pressed="true"/);
    assert.match(back.get("Lower back") ?? "", /aria-pressed="true"/);
    assert.match(front.get("Head") ?? "", /aria-pressed="false"/);
  });

  it("makes every region focusable, and none when disabled", () => {
    for (const tag of regionButtons(figure("front")).values()) assert.match(tag, /tabindex="0"/);
    for (const tag of regionButtons(figure("front", [], true)).values()) assert.match(tag, /tabindex="-1"/);
  });

  it("view tabs show Front View and Back View with one active tab", () => {
    const html = renderToStaticMarkup(createElement(BodyViewTabs, { view: "back", onChange: noop }));
    assert.match(html, /role="tablist"/);
    assert.match(html, /aria-selected="false"[^>]*>Front View</);
    assert.match(html, /aria-selected="true"[^>]*>Back View</);
    assert.equal((html.match(/tabindex="0"/g) || []).length, 1);
  });

  it("switches to the side where a list-picked region is drawn", () => {
    assert.equal(viewForRegion("upper_back", "front"), "back");
    assert.equal(viewForRegion("chest", "back"), "front");
    assert.equal(viewForRegion("knee", "back"), "back");
  });
});

describe("body map card", () => {
  it("shows selected labels, a clear button, and an accessible region list", () => {
    const html = card("front", ["knee", "lower_back"]);
    assert.match(html, /Front View/);
    assert.match(html, /Back View/);
    assert.match(html, /aria-label="Remove Knee"/);
    assert.match(html, /aria-label="Remove Lower back"/);
    assert.match(html, /Also selected on the Back View/);
    assert.doesNotMatch(clearButton(html), /disabled=""/);
    for (const region of REGION_ORDER) assert.match(html, new RegExp(`>(✓ )?${REGION_LABELS[region]}<`));
    assert.match(html, /not a diagnosis/);
  });

  it("disables clearing when nothing is selected", () => {
    const html = card("front", []);
    assert.match(html, /None yet\./);
    assert.match(clearButton(html), /disabled=""/);
  });

  it("does not suggest any condition from the selected areas alone", () => {
    const visibleText = card("front", ["chest", "head"]).replace(/<[^>]+>/g, " ");
    assert.doesNotMatch(visibleText, /migraine|heart attack|angina|stroke|you (may )?have/i);
  });
});

describe("selection survives view switching and clearing", () => {
  it("sends regions picked on both views, and nothing after clearing", () => {
    let regions: BodyRegion[] = [];
    regions = toggleItem(regions, "chest");
    regions = toggleItem(regions, "lower_back");
    regions = toggleItem(regions, "knee");
    assert.deepEqual(buildMessagePayload("aching", regions, []).body_regions, ["chest", "lower_back", "knee"]);
    regions = [];
    assert.deepEqual(buildMessagePayload("aching", regions, []).body_regions, []);
  });
});

describe("chat and presentation wiring", () => {
  const chatInput = readFileSync(new URL("../src/components/chat/ChatInput.tsx", import.meta.url), "utf8");
  const chatPage = readFileSync(new URL("../src/pages/Chat.tsx", import.meta.url), "utf8");
  const evaluation = readFileSync(new URL("../src/pages/Evaluation.tsx", import.meta.url), "utf8");

  it("drives the inline card from the composer's single selection state", () => {
    assert.match(chatPage, /<BodyMapCard/);
    assert.match(chatPage, /onSelectionChange=\{setBodySelection\}/);
    assert.match(chatPage, /composerRef\.current\?\.toggleRegion\(region\)/);
    assert.match(chatPage, /composerRef\.current\?\.clearRegions\(\)/);
    assert.match(chatInput, /onSelectionChange\?\.\(\{ regions, view \}\)/);
  });

  it("labels the toggle Presentation Mode and keeps its toggle behaviour", () => {
    assert.match(evaluation, />\s*Presentation Mode\s*</);
    assert.match(evaluation, /aria-pressed=\{demo\}/);
    assert.match(evaluation, /setParam\("demo", demo \? null : "1"\)/);
    assert.match(evaluation, /Exit Presentation Mode/);
    assert.doesNotMatch(evaluation, /Faculty demo/i);
  });
});
