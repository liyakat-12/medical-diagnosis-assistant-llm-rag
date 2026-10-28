import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { looksLikeGfmTable, normalizeMarkdownTables } from "../src/utils/markdown.ts";

const bubbleSource = readFileSync(new URL("../src/components/chat/MessageBubble.tsx", import.meta.url), "utf8");
const chatSource = readFileSync(new URL("../src/context/ChatContext.tsx", import.meta.url), "utf8");

describe("normalizeMarkdownTables", () => {
  it("keeps a valid GitHub-flavored table", () => {
    const input = [
      "Broad causes:",
      "",
      "| Mechanism | Meaning |",
      "| --- | --- |",
      "| Genetic | A gene change may affect a protein |",
    ].join("\n");
    const output = normalizeMarkdownTables(input);
    assert.match(output, /\| Mechanism \| Meaning \|/);
    assert.match(output, /\| --- \| --- \|/);
    assert.match(output, /\| Genetic \|/);
    assert.equal(looksLikeGfmTable(output), true);
  });

  it("repairs a concatenated one-line table", () => {
    const input =
      "Overview: | Mechanism | Meaning | | --- | --- | | Genetic | A gene change | | Infection | Tissue injury |";
    const output = normalizeMarkdownTables(input);
    assert.match(output, /\| Mechanism \| Meaning \|/);
    assert.match(output, /\| --- \| --- \|/);
    assert.equal(output.includes("| Genetic |"), true);
    assert.equal(output.split("\n").some((line) => line.startsWith("| Genetic |")), true);
    assert.equal(looksLikeGfmTable(output), true);
  });

  it("turns a malformed pipe row into a readable list", () => {
    const output = normalizeMarkdownTables("Causes: | Genetic changes | Infections |");
    assert.equal(output.includes("| Genetic"), false);
    assert.match(output, /^- \*\*Genetic changes\*\*: Infections/m);
  });
});

describe("medical evidence labeling", () => {
  it("labels general knowledge after the explanation and hides backend providers", () => {
    assert.match(bubbleSource, /remarkPlugins=\{\[remarkGfm\]\}/);
    assert.match(bubbleSource, /normalizeMarkdownTables/);
    assert.match(
      bubbleSource,
      /It was not retrieved from the MediAssist knowledge base and has not been verified against those notes/,
    );
    assert.equal(/groq|openai|chatgpt|chroma/i.test(bubbleSource), false);
    assert.equal(/groq|openai|chatgpt|chroma/i.test(chatSource), false);
  });
});
