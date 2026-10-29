import type { RetrievalCase } from "../types/evaluation";

export type CaseOutcome = "top1" | "lower" | "miss";
export type OutcomeFilter = "all" | CaseOutcome;

export const OUTCOME_LABELS: Record<CaseOutcome, string> = {
  top1: "Ranked first",
  lower: "Found lower",
  miss: "Missed",
};

export type CaseSummary = {
  n: number;
  found: number;
  missed: number;
  recallAt1: number | null;
  recallAt3: number | null;
  recallAtDepth: number | null;
  mrr: number | null;
};

export function caseOutcome(rank: number | null, depth: number): CaseOutcome {
  if (rank === 1) return "top1";
  if (rank !== null && rank > 1 && rank <= depth) return "lower";
  return "miss";
}

export function summarizeCases(cases: Pick<RetrievalCase, "rank">[], depth: number): CaseSummary {
  const n = cases.length;
  const ranks = cases.map((item) => (item.rank !== null && item.rank >= 1 && item.rank <= depth ? item.rank : null));
  const found = ranks.filter((rank): rank is number => rank !== null);
  const share = (k: number) => (n ? found.filter((rank) => rank <= k).length / n : null);
  return {
    n,
    found: found.length,
    missed: n - found.length,
    recallAt1: share(1),
    recallAt3: share(3),
    recallAtDepth: share(depth),
    mrr: n ? found.reduce((total, rank) => total + 1 / rank, 0) / n : null,
  };
}

export function filterCases(
  cases: RetrievalCase[],
  depth: number,
  filters: { outcome: OutcomeFilter; category: string; search: string },
): RetrievalCase[] {
  const needle = filters.search.trim().toLowerCase();
  return cases.filter((item) => {
    if (filters.outcome !== "all" && caseOutcome(item.rank, depth) !== filters.outcome) return false;
    if (filters.category !== "all" && item.category !== filters.category) return false;
    if (!needle) return true;
    return [item.query, item.id, ...item.expected_doc_ids, ...item.retrieved_doc_ids].some((value) => value.toLowerCase().includes(needle));
  });
}

export function caseCategories(cases: RetrievalCase[]): string[] {
  return Array.from(new Set(cases.map((item) => item.category))).sort();
}

export type RankedDoc = { docId: string; rank: number; expected: boolean };

export function markRetrieved(retrieved: string[], expected: string[]): RankedDoc[] {
  const wanted = new Set(expected);
  return retrieved.map((docId, index) => ({ docId, rank: index + 1, expected: wanted.has(docId) }));
}

export function firstExpectedRank(retrieved: string[], expected: string[]): number | null {
  const index = retrieved.findIndex((docId) => expected.includes(docId));
  return index === -1 ? null : index + 1;
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatScore(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatCategory(value: string): string {
  return value.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}
