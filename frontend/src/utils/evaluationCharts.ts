import type { EmbeddingRun, RetrievalRun } from "../types/evaluation";
import { formatDate } from "./dates";
import { formatCategory, formatPercent, formatScore } from "./evaluationMetrics";
import type { BarGroup } from "../components/insights/Charts";

export type MetricCardModel = {
  label: string;
  value: string;
  unavailable: boolean;
  accent: "teal" | "navy" | "slate";
};

export type RankBucket = {
  label: string;
  value: number;
  tone: "good" | "warn" | "bad";
  color: string;
};

export function selectedRun(runs: RetrievalRun[], requestedId: string | null): RetrievalRun | null {
  if (!runs.length) return null;
  return runs.find((item) => item.id === requestedId) ?? runs[runs.length - 1];
}

function missing(value: number | null | undefined): boolean {
  return value === null || value === undefined || Number.isNaN(value);
}

export function retrievalMetricCards(run: RetrievalRun): MetricCardModel[] {
  const recall4 = run.metrics.recall_at_4 ?? null;
  return [
    { label: "Recall@1", value: formatPercent(run.metrics.recall_at_1), unavailable: missing(run.metrics.recall_at_1), accent: "teal" },
    { label: "Recall@3", value: formatPercent(run.metrics.recall_at_3), unavailable: missing(run.metrics.recall_at_3), accent: "teal" },
    { label: "Recall@4", value: formatPercent(recall4), unavailable: missing(recall4), accent: "teal" },
    { label: "MRR", value: formatScore(run.metrics.mrr), unavailable: missing(run.metrics.mrr), accent: "navy" },
    { label: "Total test queries", value: run.metrics.n.toLocaleString(), unavailable: false, accent: "slate" },
    {
      label: "Found / missed",
      value: `${run.metrics.found.toLocaleString()} / ${run.metrics.missed.toLocaleString()}`,
      unavailable: false,
      accent: "slate",
    },
  ];
}

export function scoreLabel(value: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toFixed(2);
}

function countAt(distribution: Record<string, number>, key: string): number {
  return distribution[key] ?? 0;
}

/** Rank 1 through 4, then everything else as not in the top four. Null when the run has no rank counts. */
export function rankDistribution(run: RetrievalRun): RankBucket[] | null {
  const distribution = run.rank_distribution;
  if (!distribution || !Object.keys(distribution).length) return null;
  const ranked = ["1", "2", "3", "4"] as const;
  const colors = ["#0f766e", "#14b8a6", "#5eead4", "#94a3b8"];
  const buckets: RankBucket[] = ranked.map((key, index) => ({
    label: `Rank ${key}`,
    value: countAt(distribution, key),
    tone: index === 0 ? "good" : "warn",
    color: colors[index],
  }));
  const notInTopFour = Object.entries(distribution)
    .filter(([key]) => !ranked.includes(key as (typeof ranked)[number]))
    .reduce((sum, [, value]) => sum + value, 0);
  buckets.push({ label: "Not in the top four", value: notInTopFour, tone: "bad", color: "#b45309" });
  return buckets;
}

export type CategoryRow = { category: string; queries: number; recallAt1: string; mrr: string };

export function categoryRows(run: RetrievalRun): CategoryRow[] | null {
  const entries = Object.entries(run.categories);
  if (!entries.length) return null;
  return entries.map(([name, metrics]) => ({
    category: formatCategory(name),
    queries: metrics.n,
    recallAt1: formatPercent(metrics.recall_at_1, 0),
    mrr: formatScore(metrics.mrr, 2),
  }));
}

/** Every stored run, oldest first. Sublabels keep each run's own query count and corpus size. */
export function retrievalRunGroups(runs: RetrievalRun[], selectedId: string | null): BarGroup[] {
  return runs.map((item) => ({
    label: item.label,
    sublabel: `${item.id === selectedId ? "Selected · " : ""}${item.corpus_docs ?? "?"} notes · n=${item.metrics.n}`,
    values: {
      r1: item.metrics.recall_at_1,
      r3: item.metrics.recall_at_3,
      r4: item.metrics.recall_at_4 ?? null,
      mrr: item.metrics.mrr,
    },
  }));
}

export function retrievalRunsNote(runs: RetrievalRun[]): string {
  const mrr = "MRR is a rank score on the same 0–1 axis, not a recall rate.";
  if (runs.length < 2) return mrr;
  const issues: string[] = [];
  if (new Set(runs.map((item) => item.metrics.n)).size > 1) issues.push("query counts differ");
  const corpusMissing = runs.some((item) => item.corpus_docs === null);
  const corpusDiffers = new Set(runs.map((item) => item.corpus_docs)).size > 1;
  if (corpusDiffers && corpusMissing) issues.push("corpus size differs or was not recorded");
  else if (corpusDiffers) issues.push("corpus size differs");
  else if (corpusMissing) issues.push("corpus size was not recorded");
  if (new Set(runs.map((item) => item.depth)).size > 1) issues.push("retrieval depth differs");
  if (!issues.length) return mrr;
  return `Shown together even though ${issues.join(", ")}. Each bar uses that run's own queries. ${mrr}`;
}

export function embeddingLabel(label: string): string {
  return label
    .replace(" embeddings (MiniLM)", " (MiniLM)")
    .replace(" embeddings (PubMedBERT)", " (PubMedBERT)")
    .replace(" embeddings + cross-encoder re-rank", " + re-rank");
}

export function embeddingGroups(runs: EmbeddingRun[]): BarGroup[] {
  return runs.map((item) => ({
    label: embeddingLabel(item.label),
    sublabel: `n=${item.metrics.n} · ${formatDate(item.generated_at)}`,
    values: {
      r1: item.metrics.recall_at_1,
      r3: item.metrics.recall_at_3,
      r5: item.metrics.recall_at_5 ?? null,
      mrr: item.metrics.mrr,
    },
  }));
}

export function embeddingNote(runs: EmbeddingRun[]): string | null {
  if (!runs.length) return null;
  const counts = [...new Set(runs.map((item) => item.metrics.n))].join(", ");
  return `Earlier experiment, ${counts} questions (${runs.map((item) => item.file).join(", ")}). It used a different question set and an earlier knowledge base, so it is not directly comparable with the runs above.`;
}
