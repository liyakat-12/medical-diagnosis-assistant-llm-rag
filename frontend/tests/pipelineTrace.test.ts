import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { PipelineRun, RetrievalCase } from "../src/types/evaluation.ts";
import { pickDemoCases, SAFETY_PROBES } from "../src/utils/demoCases.ts";
import { tracePipeline } from "../src/utils/pipelineTrace.ts";

function pipeline(overrides: Partial<PipelineRun> = {}): PipelineRun {
  return {
    query: "q",
    refused: false,
    refusal_reason: null,
    answer: "",
    citations: [],
    triage: null,
    faithfulness: null,
    evidence_origin: "none",
    timings: {},
    question_type: "",
    ...overrides,
  };
}

function statuses(run: PipelineRun) {
  return Object.fromEntries(tracePipeline(run).map((item) => [item.stage.id, item.status]));
}

describe("tracePipeline", () => {
  it("marks every stage as run for a grounded answer, with server timings", () => {
    const run = pipeline({
      citations: [{ title: "Dehydration" }],
      evidence_origin: "knowledge_base",
      faithfulness: { verdict: "pass" },
      timings: { classify_ms: 5, retrieve_ms: 120, generate_ms: 900, total_ms: 1030 },
    });
    assert.deepEqual(statuses(run), { safety: "ran", prepare: "ran", retrieve: "ran", select: "ran", generate: "ran", verify: "ran" });
    const trace = tracePipeline(run);
    assert.equal(trace.find((item) => item.stage.id === "retrieve")?.ms, 120);
    assert.equal(trace.find((item) => item.stage.id === "safety")?.ms, null);
  });

  it("stops at the safety stage for a refused request", () => {
    const result = statuses(pipeline({ refused: true }));
    assert.equal(result.safety, "stopped");
    for (const stage of ["prepare", "retrieve", "select", "generate", "verify"]) assert.equal(result[stage], "skipped", stage);
  });

  it("does not claim retrieval or verification ran for a non-medical message", () => {
    const result = statuses(pipeline({ timings: { classify_ms: 2 } }));
    assert.equal(result.prepare, "ran");
    assert.equal(result.retrieve, "skipped");
    assert.equal(result.select, "skipped");
    assert.equal(result.generate, "skipped");
    assert.equal(result.verify, "skipped");
  });

  it("treats zero timings as not run", () => {
    assert.equal(statuses(pipeline({ timings: { classify_ms: 0, retrieve_ms: 0, generate_ms: 0 } })).retrieve, "skipped");
  });
});

describe("pickDemoCases", () => {
  const make = (id: string, rank: number | null, category: string): RetrievalCase => ({
    id,
    category,
    query: `query ${id}`,
    expected_doc_ids: [`doc_${id}`],
    retrieved_doc_ids: [],
    rank,
    reciprocal_rank: rank ? 1 / rank : 0,
  });

  it("mixes outcomes and categories, and labels safety probes separately", () => {
    const cases = [make("a", 1, "x"), make("b", 1, "x"), make("c", 1, "y"), make("d", 1, "z"), make("e", 2, "y"), make("f", null, "x")];
    const demo = pickDemoCases(cases, 4);
    const fromDataset = demo.filter((item) => item.source === "evaluation_dataset");
    assert.deepEqual(fromDataset.filter((item) => item.stored_outcome === "top1").map((item) => item.key), ["case-a", "case-c", "case-d"]);
    assert.deepEqual(fromDataset.filter((item) => item.stored_outcome === "lower").map((item) => item.stored_rank), [2]);
    assert.deepEqual(fromDataset.filter((item) => item.stored_outcome === "miss").map((item) => item.key), ["case-f"]);
    assert.deepEqual(demo.slice(-SAFETY_PROBES.length), SAFETY_PROBES);
  });

  it("returns only the labelled safety probes when there is no stored run", () => {
    const demo = pickDemoCases([], 4);
    assert.ok(demo.every((item) => item.source === "safety_probe" && item.expected_doc_ids.length === 0));
  });
});
