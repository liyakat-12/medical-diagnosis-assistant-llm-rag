import type { Chat } from "../types";
import type { EvaluationOverview, RetrievalRun } from "../types/evaluation";
import { formatPercent, formatScore } from "./evaluationMetrics";

export type AsyncState<T> = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: T };

export type StatDisplay =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "unavailable"; reason: string }
  | { kind: "value"; value: string; detail?: string };

export type StatCard = { id: string; label: string; hint: string; href?: string; linkLabel?: string; display: StatDisplay };

export type LatestReply = { chatId: string; chatTitle: string; citations: number } | null;

export type GlanceMetric = { id: string; label: string; kind: "recall" | "rank"; value: number | null };

export function latestRun(overview: EvaluationOverview): RetrievalRun | null {
  return overview.retrieval_runs.at(-1) ?? null;
}

export function glanceMetrics(run: RetrievalRun): GlanceMetric[] {
  return [
    { id: "r1", label: "Recall@1", kind: "recall", value: run.metrics.recall_at_1 },
    { id: "r3", label: "Recall@3", kind: "recall", value: run.metrics.recall_at_3 },
    { id: "r4", label: "Recall@4", kind: "recall", value: run.metrics.recall_at_4 ?? null },
    { id: "mrr", label: "MRR", kind: "rank", value: run.metrics.mrr },
  ];
}

function fromState<T>(state: AsyncState<T>, read: (data: T) => StatDisplay): StatDisplay {
  if (state.status === "loading") return { kind: "loading" };
  if (state.status === "error") return { kind: "error", message: state.message };
  return read(state.data);
}

const NO_RUN = "No stored evaluation run. Run evaluation/evaluate_kb_phase2.py to create one.";

export function buildDashboardStats(
  overview: AsyncState<EvaluationOverview>,
  chats: AsyncState<Chat[]>,
  latest: AsyncState<LatestReply>,
): StatCard[] {
  const evaluationHref = overview.status === "ready" ? "/evaluation" : undefined;
  const historyHref = chats.status === "ready" ? "/history" : undefined;
  const latestHref = latest.status === "ready" && latest.data ? `/chat/${latest.data.chatId}` : undefined;
  return [
    {
      id: "documents",
      label: "Knowledge-base notes",
      hint: "Markdown reference notes available for retrieval.",
      display: fromState(overview, (data) =>
        data.knowledge_base.documents === null
          ? { kind: "unavailable", reason: "The knowledge-base folder was not found." }
          : { kind: "value", value: data.knowledge_base.documents.toLocaleString() },
      ),
    },
    {
      id: "chunks",
      label: "Indexed chunks",
      hint: "Passages stored in the vector index.",
      display: fromState(overview, (data) =>
        data.knowledge_base.index_ready && data.knowledge_base.chunks_indexed !== null
          ? { kind: "value", value: data.knowledge_base.chunks_indexed.toLocaleString(), detail: data.knowledge_base.rerank_enabled ? "Re-ranking on" : "Re-ranking off" }
          : { kind: "unavailable", reason: data.knowledge_base.error || "The retrieval index is not ready." },
      ),
    },
    {
      id: "recall1",
      label: "Recall@1",
      hint: "Share of labelled queries whose expected note ranked first. This is not diagnostic accuracy.",
      href: evaluationHref,
      linkLabel: "Open the evaluation dashboard",
      display: fromState(overview, (data) => {
        const run = latestRun(data);
        return run && run.metrics.recall_at_1 !== null
          ? { kind: "value", value: formatPercent(run.metrics.recall_at_1), detail: `${run.label} · ${run.metrics.n} labelled queries` }
          : { kind: "unavailable", reason: NO_RUN };
      }),
    },
    {
      id: "mrr",
      label: "MRR",
      hint: "Mean reciprocal rank of the expected note. A ranking score from 0 to 1, not a recall percentage.",
      href: evaluationHref,
      linkLabel: "Open the evaluation dashboard",
      display: fromState(overview, (data) => {
        const run = latestRun(data);
        return run && run.metrics.mrr !== null ? { kind: "value", value: formatScore(run.metrics.mrr), detail: `Rank score · ${run.label}` } : { kind: "unavailable", reason: NO_RUN };
      }),
    },
    {
      id: "conversations",
      label: "Your conversations",
      hint: "Chats saved in your account.",
      href: historyHref,
      linkLabel: "Open conversation history",
      display: fromState(chats, (data) => ({ kind: "value", value: data.length.toLocaleString() })),
    },
    {
      id: "latest_sources",
      label: "Sources in latest reply",
      hint: "Cited notes in your most recent assistant reply.",
      href: latestHref,
      linkLabel: "Open this conversation",
      display: fromState(latest, (data) =>
        data ? { kind: "value", value: data.citations.toLocaleString(), detail: data.chatTitle } : { kind: "unavailable", reason: "No assistant replies yet." },
      ),
    },
  ];
}
