import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { quickActions, RecentChats, RetrievalGlance } from "../src/pages/Dashboard.tsx";
import type { Chat } from "../src/types/index.ts";
import type { EvaluationOverview, RetrievalRun } from "../src/types/evaluation.ts";
import type { AsyncState } from "../src/utils/dashboardStats.ts";

function render(node: ReturnType<typeof createElement>): string {
  return renderToStaticMarkup(createElement(MemoryRouter, null, node));
}

function chat(id: string, title: string, count: number): Chat {
  return { id, user_id: "u1", title, message_count: count, archived: false, last_message_at: "2026-10-16T00:00:00Z" };
}

function run(): RetrievalRun {
  return {
    id: "batch4",
    label: "Batch4",
    description: "",
    file: "kb_phase2_batch4.json",
    generated_at: "2026-10-20T00:00:00Z",
    corpus_docs: 1017,
    query_count: 103,
    depth: 4,
    metrics: { n: 103, found: 103, missed: 0, recall_at_1: 0.835, recall_at_3: 0.99, recall_at_4: 1, mrr: 0.91 },
    stored_metrics: { recall_at_1: 0.835, recall_at_4: 1, mrr: 0.91 },
    rank_distribution: {},
    categories: {},
    safety: { emergency: { n: 4, passed: 4, failed: [] } },
  };
}

function overview(retrieval: RetrievalRun | null): EvaluationOverview {
  return {
    knowledge_base: { documents: 1, chunks_indexed: 1, index_ready: true, embedding_mode: "general", rerank_enabled: true, top_k: 4, rerank_candidates: 12, error: null },
    retrieval_runs: retrieval ? [retrieval] : [],
    embedding_comparison: [],
    quality_reports: [],
    grounding: null,
    test_suite: null,
    definitions: { recall_at_k: "", mrr: "" },
  };
}

describe("dashboard navigation", () => {
  it("keeps the conversation button and the three existing quick actions", () => {
    const source = readFileSync(new URL("../src/pages/Dashboard.tsx", import.meta.url), "utf8");
    assert.match(source, /Start a conversation/);
    assert.match(source, /to="\/chat"/);
    assert.match(source, /It does not diagnose/);
    assert.deepEqual(quickActions.map((item) => item.to), ["/chat?map=1", "/history", "/evaluation"]);
    assert.deepEqual(quickActions.map((item) => item.title), ["Symptom body map", "Previous conversations", "Evaluation dashboard"]);
  });

  it("opens the saved conversation and does not render a message body", () => {
    const title = "Persistent calf pain after a long flight";
    const html = render(createElement(RecentChats, { state: { status: "ready", data: [chat("chat-42", title, 2), chat("other", "Second chat", 1)] } }));
    assert.match(html, /href="\/chat\/chat-42"/);
    assert.match(html, /href="\/chat\/other"/);
    assert.match(html, new RegExp(title));
    assert.match(html, /truncate/);
    assert.match(html, />2 </);
    assert.match(html, /messages/);
    assert.doesNotMatch(html, /swelling|shortness of breath|assistant/i);
  });

  it("shows an empty state and a loading state without invented chats", () => {
    const empty = render(createElement(RecentChats, { state: { status: "ready", data: [] } }));
    assert.match(empty, /No conversations yet/);
    assert.match(empty, /href="\/chat"/);
    assert.match(empty, /Only you can see them/);
    const loading = render(createElement(RecentChats, { state: { status: "loading" } }));
    assert.match(loading, /aria-busy="true"/);
    assert.doesNotMatch(loading, /href="\/chat\//);
  });
});

describe("retrieval glance", () => {
  it("shows the latest run with recall percentages and MRR as a rank score", () => {
    const html = render(createElement(RetrievalGlance, { state: { status: "ready", data: overview(run()) } as AsyncState<EvaluationOverview> }));
    assert.match(html, /Batch4/);
    assert.match(html, /103 labelled queries/);
    assert.match(html, /83\.5%/);
    assert.match(html, /99\.0%/);
    assert.match(html, /100\.0%/);
    assert.match(html, /0\.910/);
    assert.match(html, /Rank score/);
    assert.match(html, /not a recall percentage/);
    assert.doesNotMatch(html, /91\.0%/);
  });

  it("marks a missing score unavailable and explains a missing run", () => {
    const stored = run();
    stored.metrics.mrr = null;
    stored.metrics.recall_at_4 = null;
    const html = render(createElement(RetrievalGlance, { state: { status: "ready", data: overview(stored) } }));
    assert.match(html, /Recall@4[\s\S]*?—[\s\S]*unavailable/);
    assert.match(html, /MRR[\s\S]*?—[\s\S]*unavailable/);
    const missing = render(createElement(RetrievalGlance, { state: { status: "ready", data: overview(null) } }));
    assert.match(missing, /No stored evaluation run/);
    assert.doesNotMatch(missing, /83\.5%|0\.910/);
  });
});
