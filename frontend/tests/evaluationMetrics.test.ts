import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { RetrievalCase } from "../src/types/evaluation.ts";
import {
  caseCategories,
  caseOutcome,
  filterCases,
  firstExpectedRank,
  formatPercent,
  formatScore,
  markRetrieved,
  summarizeCases,
} from "../src/utils/evaluationMetrics.ts";

function make(id: string, rank: number | null, category = "general", query = `query ${id}`): RetrievalCase {
  return {
    id,
    category,
    query,
    expected_doc_ids: [`doc_${id}`],
    retrieved_doc_ids: ["a", "b", "c", "d"],
    rank,
    reciprocal_rank: rank ? 1 / rank : 0,
  };
}

describe("summarizeCases", () => {
  it("computes Recall@k and MRR from ranks", () => {
    const cases = [make("1", 1), make("2", 2), make("3", 4), make("4", null)];
    const summary = summarizeCases(cases, 4);
    assert.equal(summary.n, 4);
    assert.equal(summary.found, 3);
    assert.equal(summary.missed, 1);
    assert.equal(summary.recallAt1, 0.25);
    assert.equal(summary.recallAt3, 0.5);
    assert.equal(summary.recallAtDepth, 0.75);
    assert.ok(Math.abs((summary.mrr ?? 0) - (1 + 0.5 + 0.25 + 0) / 4) < 1e-12);
  });

  it("treats ranks beyond the retrieval depth as misses", () => {
    const summary = summarizeCases([make("1", 6)], 4);
    assert.equal(summary.found, 0);
    assert.equal(summary.mrr, 0);
  });

  it("returns null metrics, not zero, for an empty dataset", () => {
    const summary = summarizeCases([], 4);
    assert.deepEqual(summary, { n: 0, found: 0, missed: 0, recallAt1: null, recallAt3: null, recallAtDepth: null, mrr: null });
    assert.equal(formatPercent(summary.recallAt1), "—");
    assert.equal(formatScore(summary.mrr), "—");
  });
});

describe("case outcomes and filters", () => {
  const cases = [make("1", 1, "cardio", "chest tightness"), make("2", 3, "skin"), make("3", null, "skin")];

  it("classifies outcomes", () => {
    assert.equal(caseOutcome(1, 4), "top1");
    assert.equal(caseOutcome(3, 4), "lower");
    assert.equal(caseOutcome(null, 4), "miss");
    assert.equal(caseOutcome(5, 4), "miss");
  });

  it("filters by outcome, category and search text", () => {
    assert.deepEqual(filterCases(cases, 4, { outcome: "miss", category: "all", search: "" }).map((item) => item.id), ["3"]);
    assert.deepEqual(filterCases(cases, 4, { outcome: "all", category: "skin", search: "" }).map((item) => item.id), ["2", "3"]);
    assert.deepEqual(filterCases(cases, 4, { outcome: "all", category: "all", search: "TIGHTNESS" }).map((item) => item.id), ["1"]);
    assert.deepEqual(filterCases(cases, 4, { outcome: "all", category: "all", search: "doc_2" }).map((item) => item.id), ["2"]);
    assert.deepEqual(filterCases([], 4, { outcome: "all", category: "all", search: "" }), []);
  });

  it("lists categories once, sorted", () => {
    assert.deepEqual(caseCategories(cases), ["cardio", "skin"]);
  });
});

describe("rank ladder helpers", () => {
  it("marks expected documents in retrieved order", () => {
    assert.deepEqual(markRetrieved(["x", "doc", "y"], ["doc"]), [
      { docId: "x", rank: 1, expected: false },
      { docId: "doc", rank: 2, expected: true },
      { docId: "y", rank: 3, expected: false },
    ]);
  });

  it("finds the first expected rank or null", () => {
    assert.equal(firstExpectedRank(["x", "y", "doc"], ["doc", "other"]), 3);
    assert.equal(firstExpectedRank(["x"], ["doc"]), null);
    assert.equal(firstExpectedRank([], []), null);
  });
});
