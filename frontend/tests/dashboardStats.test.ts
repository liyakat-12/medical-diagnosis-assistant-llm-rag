import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { Chat } from "../src/types/index.ts";
import type { EvaluationOverview, RetrievalRun } from "../src/types/evaluation.ts";
import { buildDashboardStats, glanceMetrics, latestRun, type AsyncState, type LatestReply } from "../src/utils/dashboardStats.ts";

const LOADING = { status: "loading" } as const;

function run(id: string, recall1: number | null, mrr: number | null, n = 10): RetrievalRun {
  return {
    id,
    label: id,
    description: "",
    file: `kb_phase2_${id}.json`,
    generated_at: "2026-10-01T00:00:00Z",
    corpus_docs: 100,
    query_count: n,
    depth: 4,
    metrics: { n, found: n, missed: 0, recall_at_1: recall1, recall_at_3: recall1, recall_at_4: recall1, mrr },
    stored_metrics: { recall_at_1: recall1, recall_at_4: recall1, mrr },
    rank_distribution: {},
    categories: {},
    safety: {},
  };
}

function overview(runs: RetrievalRun[], kb: Partial<EvaluationOverview["knowledge_base"]> = {}): EvaluationOverview {
  return {
    knowledge_base: { documents: 1017, chunks_indexed: 1035, index_ready: true, embedding_mode: "general", rerank_enabled: true, top_k: 4, rerank_candidates: 12, error: null, ...kb },
    retrieval_runs: runs,
    embedding_comparison: [],
    quality_reports: [],
    grounding: null,
    test_suite: null,
    definitions: { recall_at_k: "", mrr: "" },
  };
}

const chat: Chat = { id: "c1", user_id: "u1", title: "Knee pain", message_count: 2, archived: false };

function byId(stats: ReturnType<typeof buildDashboardStats>) {
  return Object.fromEntries(stats.map((stat) => [stat.id, stat.display]));
}

describe("buildDashboardStats", () => {
  it("shows loading for every card while data loads", () => {
    const stats = buildDashboardStats(LOADING, LOADING, LOADING);
    assert.equal(stats.length, 6);
    assert.ok(stats.every((stat) => stat.display.kind === "loading"));
  });

  it("shows errors per source without inventing values", () => {
    const failed: AsyncState<never> = { status: "error", message: "down" };
    const stats = byId(buildDashboardStats(failed, { status: "ready", data: [chat] }, failed));
    assert.equal(stats.documents.kind, "error");
    assert.equal(stats.recall1.kind, "error");
    assert.deepEqual(stats.conversations, { kind: "value", value: "1" });
    assert.equal(stats.latest_sources.kind, "error");
  });

  it("marks evaluation metrics unavailable when no run is stored", () => {
    const stats = byId(buildDashboardStats({ status: "ready", data: overview([]) }, { status: "ready", data: [] }, { status: "ready", data: null }));
    assert.equal(stats.recall1.kind, "unavailable");
    assert.equal(stats.mrr.kind, "unavailable");
    assert.equal(stats.latest_sources.kind, "unavailable");
    assert.deepEqual(stats.conversations, { kind: "value", value: "0" });
  });

  it("marks the index unavailable when it is not ready", () => {
    const stats = byId(buildDashboardStats({ status: "ready", data: overview([], { index_ready: false, chunks_indexed: null, error: "Index missing" }) }, LOADING, LOADING));
    assert.deepEqual(stats.chunks, { kind: "unavailable", reason: "Index missing" });
    assert.equal(stats.documents.kind, "value");
  });

  it("uses the most recent run and real counts", () => {
    const data = overview([run("baseline", 0.5, 0.6), run("batch4", 0.835, 0.91, 103)]);
    assert.equal(latestRun(data)?.id, "batch4");
    const latest: AsyncState<LatestReply> = { status: "ready", data: { chatId: "c1", chatTitle: "Knee pain", citations: 3 } };
    const cards = buildDashboardStats({ status: "ready", data }, { status: "ready", data: [chat] }, latest);
    const stats = byId(cards);
    assert.deepEqual(stats.recall1, { kind: "value", value: "83.5%", detail: "batch4 · 103 labelled queries" });
    assert.deepEqual(stats.mrr, { kind: "value", value: "0.910", detail: "Rank score · batch4" });
    assert.deepEqual(stats.latest_sources, { kind: "value", value: "3", detail: "Knee pain" });
    assert.equal((stats.documents as { value: string }).value, (1017).toLocaleString());
    assert.equal(cards.find((item) => item.id === "recall1")?.href, "/evaluation");
    assert.equal(cards.find((item) => item.id === "mrr")?.href, "/evaluation");
    assert.equal(cards.find((item) => item.id === "conversations")?.href, "/history");
    assert.equal(cards.find((item) => item.id === "latest_sources")?.href, "/chat/c1");
    assert.equal(cards.find((item) => item.id === "documents")?.href, undefined);
    assert.equal(cards.find((item) => item.id === "chunks")?.href, undefined);
  });

  it("does not link metrics when the source failed or the reply is missing", () => {
    const failed: AsyncState<never> = { status: "error", message: "down" };
    const emptyLatest: AsyncState<LatestReply> = { status: "ready", data: null };
    const cards = buildDashboardStats(failed, { status: "ready", data: [] }, emptyLatest);
    assert.equal(cards.find((item) => item.id === "recall1")?.href, undefined);
    assert.equal(cards.find((item) => item.id === "latest_sources")?.href, undefined);
    assert.equal(cards.find((item) => item.id === "conversations")?.href, "/history");
  });
});

describe("glanceMetrics", () => {
  it("keeps recall percentages separate from the MRR rank score", () => {
    const metrics = glanceMetrics(run("batch4", 0.835, null, 103));
    assert.deepEqual(metrics.map((item) => item.label), ["Recall@1", "Recall@3", "Recall@4", "MRR"]);
    assert.equal(metrics.find((item) => item.id === "r4")?.kind, "recall");
    assert.equal(metrics.find((item) => item.id === "r4")?.value, 0.835);
    assert.equal(metrics.find((item) => item.id === "mrr")?.kind, "rank");
    assert.equal(metrics.find((item) => item.id === "mrr")?.value, null);
  });

  it("leaves a missing Recall@4 empty instead of inventing zero", () => {
    const stored = run("baseline", 0.5, 0.4);
    stored.metrics.recall_at_4 = null;
    const recall4 = glanceMetrics(stored).find((item) => item.id === "r4");
    assert.equal(recall4?.value, null);
  });
});
