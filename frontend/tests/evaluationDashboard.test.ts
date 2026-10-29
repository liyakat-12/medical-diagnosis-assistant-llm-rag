import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DistributionBars, GroupedBarChart } from "../src/components/insights/Charts.tsx";
import { MetricCards } from "../src/components/evaluation/MetricCards.tsx";
import { RagPipelineDiagram } from "../src/components/evaluation/RagPipelineDiagram.tsx";
import type { EmbeddingRun, RetrievalRun } from "../src/types/evaluation.ts";
import { categoryRows, embeddingGroups, embeddingNote, rankDistribution, retrievalMetricCards, retrievalRunGroups, retrievalRunsNote, scoreLabel, selectedRun } from "../src/utils/evaluationCharts.ts";

function run(overrides: Partial<RetrievalRun> = {}): RetrievalRun {
  return {
    id: "batch4",
    label: "Batch4",
    description: "Stored run",
    file: "kb_phase2_batch4.json",
    generated_at: "2026-01-01T00:00:00Z",
    corpus_docs: 120,
    query_count: 20,
    depth: 4,
    metrics: { n: 20, found: 18, missed: 2, recall_at_1: 0.5, recall_at_3: 0.75, recall_at_4: 0.9, mrr: 0.62 },
    stored_metrics: { recall_at_1: 0.5, recall_at_4: 0.9, mrr: 0.62 },
    rank_distribution: { "1": 10, "2": 3, "3": 2, "4": 3, miss: 2 },
    categories: {
      symptoms: { n: 12, found: 11, missed: 1, recall_at_1: 0.4, recall_at_3: 0.6, recall_at_4: 0.8, mrr: 0.55 },
    },
    safety: {},
    ...overrides,
  };
}

describe("evaluation run selection", () => {
  const runs = [run({ id: "baseline", label: "Baseline" }), run({ id: "batch4", label: "Batch4" })];

  it("uses the requested run, otherwise the latest stored run", () => {
    assert.equal(selectedRun(runs, "baseline")?.id, "baseline");
    assert.equal(selectedRun(runs, null)?.id, "batch4");
    assert.equal(selectedRun(runs, "missing")?.id, "batch4");
    assert.equal(selectedRun([], "batch4"), null);
  });

  it("changes the metric cards when the selected run changes", () => {
    const first = retrievalMetricCards(run({ metrics: { n: 10, found: 8, missed: 2, recall_at_1: 0.2, recall_at_3: 0.4, recall_at_4: 0.5, mrr: 0.3 } }));
    const second = retrievalMetricCards(run());
    assert.notEqual(first.find((item) => item.label === "Recall@1")?.value, second.find((item) => item.label === "Recall@1")?.value);
    assert.equal(second.find((item) => item.label === "Recall@1")?.value, "50.0%");
    assert.equal(second.find((item) => item.label === "Total test queries")?.value, "20");
    assert.equal(second.find((item) => item.label === "Found / missed")?.value, "18 / 2");
  });
});

describe("metric rendering", () => {
  it("renders the six cards from the run and marks a missing score unavailable", () => {
    const html = renderToStaticMarkup(createElement(MetricCards, { run: run() }));
    for (const label of ["Recall@1", "Recall@3", "Recall@4", "MRR", "Total test queries", "Found / missed"]) {
      assert.match(html, new RegExp(`data-metric="${label}"`));
    }
    assert.match(html, /50\.0%/);
    assert.match(html, /0\.620/);
    assert.doesNotMatch(html, /diagnostic accuracy|heart attack|you have/i);

    const missing = run({ metrics: { n: 4, found: 0, missed: 4, recall_at_1: null, recall_at_3: null, recall_at_4: null, mrr: null } });
    const emptyHtml = renderToStaticMarkup(createElement(MetricCards, { run: missing }));
    assert.match(emptyHtml, /data-metric="Recall@4"[\s\S]*?—[\s\S]*unavailable/);
    assert.match(emptyHtml, /data-metric="MRR"[\s\S]*?—[\s\S]*unavailable/);
    assert.match(emptyHtml, />4</);
  });
});

function embedding(overrides: Partial<EmbeddingRun> = {}): EmbeddingRun {
  return {
    id: "general",
    label: "General embeddings (MiniLM)",
    description: "Dense vector search only.",
    file: "embedding_eval_general.csv",
    generated_at: "2026-01-02T00:00:00Z",
    depth: 5,
    metrics: { n: 40, found: 30, missed: 10, recall_at_1: 0.4, recall_at_3: 0.6, recall_at_5: 0.7, mrr: 0.5 },
    ...overrides,
  };
}

const RUN_SERIES = [
  { key: "r1", label: "Recall@1", color: "#0f766e" },
  { key: "r3", label: "Recall@3", color: "#5eead4" },
  { key: "r4", label: "Recall@4", color: "#94a3b8" },
  { key: "mrr", label: "MRR", color: "#0b1f33" },
];

describe("chart data", () => {
  it("plots every stored run with recall and MRR distinguished on one axis", () => {
    const runs = [run({ id: "baseline", label: "Baseline", metrics: { n: 87, found: 80, missed: 7, recall_at_1: 0.2, recall_at_3: 0.4, recall_at_4: 0.5, mrr: 0.3 }, corpus_docs: 40 }), run()];
    const groups = retrievalRunGroups(runs, "batch4");
    assert.deepEqual(groups.map((item) => item.label), ["Baseline", "Batch4"]);
    assert.equal(groups[1].values.r1, 0.5);
    assert.equal(groups[1].values.mrr, 0.62);
    assert.match(groups[1].sublabel ?? "", /Selected/);
    assert.match(retrievalRunsNote(runs), /query counts differ/);
    assert.match(retrievalRunsNote(runs), /corpus size differs/);
    assert.doesNotMatch(retrievalRunsNote(runs), /not recorded/);
    assert.match(retrievalRunsNote(runs), /not a recall rate/);
    assert.match(retrievalRunsNote([run({ corpus_docs: null }), run({ id: "after", label: "After", corpus_docs: null })]), /corpus size was not recorded/);
    assert.doesNotMatch(retrievalRunsNote([run(), run({ id: "after", label: "After" })]), /query counts differ/);

    const html = renderToStaticMarkup(
      createElement(GroupedBarChart, {
        title: "Retrieval runs over time",
        description: "Stored runs",
        yLabel: "Score (0 to 1)",
        series: RUN_SERIES,
        format: scoreLabel,
        groups,
      }),
    );
    assert.match(html, /Retrieval runs over time/);
    assert.match(html, /Recall@1/);
    assert.match(html, /Recall@4/);
    assert.match(html, />MRR</);
    assert.match(html, /Batch4 · Recall@1: 0\.50/);
    assert.match(html, />Baseline</);
  });

  it("counts rank 1, 2, 3, 4, and not in the top four without dropping queries", () => {
    const buckets = rankDistribution(run());
    assert.ok(buckets);
    assert.deepEqual(buckets.map((item) => [item.label, item.value]), [
      ["Rank 1", 10],
      ["Rank 2", 3],
      ["Rank 3", 2],
      ["Rank 4", 3],
      ["Not in the top four", 2],
    ]);
    assert.equal(buckets.reduce((sum, item) => sum + item.value, 0), 20);
    const switched = rankDistribution(run({ rank_distribution: { "1": 1, "2": 0, "3": 0, "4": 0, miss: 4 } }));
    assert.equal(switched?.[0].value, 1);
    assert.notEqual(switched?.[0].value, buckets[0].value);
    const html = renderToStaticMarkup(
      createElement(DistributionBars, {
        title: "Where the expected note ranked (Batch4)",
        description: "Ranks for Batch4",
        total: 20,
        items: buckets,
      }),
    );
    assert.match(html, /Not in the top four/);
    assert.match(html, /Rank 2/);
    assert.match(html, /Rank 3/);
  });

  it("omits category and rank charts when that data is absent", () => {
    assert.equal(categoryRows(run({ categories: {} })), null);
    assert.equal(rankDistribution(run({ rank_distribution: {} })), null);
    const rows = categoryRows(run());
    assert.equal(rows?.[0].category, "Symptoms");
    assert.equal(rows?.[0].queries, 12);
    assert.equal(rows?.[0].recallAt1, "40%");
    assert.equal(rows?.[0].mrr, "0.55");
  });

  it("shows a missing score as n/a instead of inventing one", () => {
    const groups = retrievalRunGroups([run({ metrics: { n: 3, found: 0, missed: 3, recall_at_1: null, recall_at_3: null, mrr: null } })], "batch4");
    assert.equal(groups[0].values.r1, null);
    assert.equal(groups[0].values.r4, null);
    const html = renderToStaticMarkup(
      createElement(GroupedBarChart, {
        title: "Retrieval runs over time",
        description: "Missing scores",
        yLabel: "Score (0 to 1)",
        series: RUN_SERIES,
        format: scoreLabel,
        groups,
      }),
    );
    assert.match(html, />n\/a</);
  });

  it("keeps the embedding comparison on its own experiment data", () => {
    const runs = [
      embedding(),
      embedding({ id: "medical", label: "Biomedical embeddings (PubMedBERT)", file: "embedding_eval_medical.csv", metrics: { n: 40, found: 32, missed: 8, recall_at_1: 0.45, recall_at_3: 0.7, recall_at_5: null, mrr: 0.55 } }),
      embedding({ id: "general_rerank", label: "General embeddings + cross-encoder re-rank", file: "embedding_eval_general_rerank.csv" }),
    ];
    const groups = embeddingGroups(runs);
    assert.deepEqual(groups.map((item) => item.label), ["General (MiniLM)", "Biomedical (PubMedBERT)", "General + re-rank"]);
    assert.equal(groups[1].values.r5, null);
    assert.equal(groups[0].values.r5, 0.7);
    assert.match(groups[0].sublabel ?? "", /n=40/);
    assert.match(embeddingNote(runs) ?? "", /different question set/);
    assert.match(embeddingNote(runs) ?? "", /embedding_eval_general.csv/);
    assert.equal(embeddingNote([]), null);
  });
});

describe("pipeline diagram", () => {
  it("shows the six design stages and does not claim a live run", () => {
    const html = renderToStaticMarkup(createElement(RagPipelineDiagram));
    for (const label of ["User Query", "Query Preparation", "Vector Retrieval", "Evidence Selection", "Answer Generation", "Citation and Safety Checks"]) {
      assert.match(html, new RegExp(label));
    }
    assert.match(html, /flex-col/);
    assert.match(html, /md:flex-row/);
    assert.match(html, /not a live run/i);
    assert.doesNotMatch(html, /Did not run|Stopped here|>Ran<|>Skipped<|\d+\s*ms/);
  });
});

describe("evaluation page surface", () => {
  const source = readFileSync(new URL("../src/pages/Evaluation.tsx", import.meta.url), "utf8");

  it("binds every section to the selected stored run", () => {
    assert.match(source, /selectedRun\(runs, params\.get\("run"\)\)/);
    assert.match(source, /<MetricCards run=\{run\}/);
    assert.match(source, /retrievalRunGroups\(runs, run\.id\)/);
    assert.match(source, /rankDistribution\(run\)/);
    assert.match(source, /categoryRows\(run\)/);
    assert.match(source, /embeddingGroups\(embeddings\)/);
  });

  it("no longer renders the detailed evaluation panels", () => {
    assert.doesNotMatch(source, /CaseExplorer|DemoMode|GroundingSummaryPanel|TraceQuery|getRetrievalCases/);
    assert.doesNotMatch(source, /Stored evaluation suites|Cases not ranked|Sample cases|Sample query|Evidence grounding|Live retrieval|Pipeline trace/i);
  });
});
