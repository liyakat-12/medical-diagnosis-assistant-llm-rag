import { Check, X } from "lucide-react";
import { cn } from "../../lib/cn";
import type { LiveRetrievalResult } from "../../types/evaluation";
import { caseOutcome, formatScore, markRetrieved, OUTCOME_LABELS, type CaseOutcome } from "../../utils/evaluationMetrics";

export const OUTCOME_STYLES: Record<CaseOutcome, string> = {
  top1: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  lower: "bg-amber-50 text-amber-800 ring-amber-200",
  miss: "bg-rose-50 text-rose-800 ring-rose-200",
};

export function OutcomeBadge({ rank, depth }: { rank: number | null; depth: number }) {
  const outcome = caseOutcome(rank, depth);
  return (
    <span className={cn("inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset", OUTCOME_STYLES[outcome])}>
      {OUTCOME_LABELS[outcome]}
      {outcome === "lower" ? ` (#${rank})` : ""}
    </span>
  );
}

/** Ranked list of retrieved documents, with the expected one(s) marked and missing expected notes listed below. */
export function RankLadder({ retrieved, expected, label }: { retrieved: string[]; expected: string[]; label: string }) {
  const rows = markRetrieved(retrieved, expected);
  const missing = expected.filter((docId) => !retrieved.includes(docId));
  const hit = rows.some((row) => row.expected);
  return (
    <div>
      <p className="text-xs font-bold text-slate-600">{label}</p>
      <ol className="mt-2 space-y-1">
        {rows.map((row) => (
          <li
            key={`${row.rank}-${row.docId}`}
            className={cn(
              "flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs",
              row.expected ? (row.rank === 1 ? "bg-emerald-50 ring-1 ring-inset ring-emerald-200" : "bg-amber-50 ring-1 ring-inset ring-amber-200") : "bg-slate-50",
            )}
          >
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-white text-[10px] font-extrabold tabular-nums text-slate-600 ring-1 ring-slate-200">{row.rank}</span>
            <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-700" title={row.docId}>
              {row.docId}
            </span>
            {row.expected ? (
              <span className="inline-flex items-center gap-1 font-bold text-emerald-800">
                <Check size={12} aria-hidden /> Expected
              </span>
            ) : null}
          </li>
        ))}
        {!rows.length ? <li className="text-xs text-slate-500">Nothing was retrieved.</li> : null}
      </ol>
      {missing.length ? (
        <ul className="mt-2 space-y-1">
          {missing.map((docId) => (
            <li key={docId} className={cn("flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs ring-1 ring-inset", hit ? "bg-white ring-slate-200" : "bg-rose-50 ring-rose-200")}>
              <X size={12} className={cn("shrink-0", hit ? "text-slate-400" : "text-rose-700")} aria-hidden />
              <span className={cn("min-w-0 flex-1 truncate font-mono text-[11px]", hit ? "text-slate-600" : "text-rose-900")}>{docId}</span>
              <span className={cn("font-bold", hit ? "text-slate-500" : "text-rose-800")}>{hit ? "Also acceptable, not retrieved" : "Expected, not retrieved"}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {expected.length > 1 ? <p className="mt-2 text-[11px] text-slate-500">Any one of the {expected.length} expected notes counts as a hit.</p> : null}
    </div>
  );
}

export function LiveResultsTable({ results, expected }: { results: LiveRetrievalResult[]; expected: string[] }) {
  if (!results.length) return <p className="text-xs text-slate-500">The live search returned no passages.</p>;
  const wanted = new Set(expected);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[30rem] text-left text-xs">
        <caption className="sr-only">Live retrieval results ranked by re-ranker relevance</caption>
        <thead>
          <tr className="border-b border-slate-200 text-slate-500">
            <th scope="col" className="py-1.5 pr-2 font-bold">#</th>
            <th scope="col" className="py-1.5 pr-2 font-bold">Title and document</th>
            <th scope="col" className="py-1.5 pr-2 text-right font-bold" title="Cross-encoder relevance score used for ranking">Relevance</th>
            <th scope="col" className="py-1.5 text-right font-bold" title="Vector similarity before re-ranking">Vector</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => {
            const hit = wanted.has(result.doc_id);
            return (
              <tr key={`${result.rank}-${result.doc_id}`} className={cn("border-b border-slate-100 align-top", hit && "bg-emerald-50")}>
                <td className="py-1.5 pr-2 font-bold tabular-nums">{result.rank}</td>
                <td className="py-1.5 pr-2">
                  <span className="block font-bold text-[#0b1f33]">
                    {result.title || result.condition || "Untitled"}
                    {hit ? <span className="ml-1.5 text-[10px] font-extrabold uppercase text-emerald-800">Expected</span> : null}
                  </span>
                  <span className="block font-mono text-[10px] text-slate-500">{result.doc_id}</span>
                </td>
                <td className="py-1.5 pr-2 text-right tabular-nums">{formatScore(result.relevance_score)}</td>
                <td className="py-1.5 text-right tabular-nums">{formatScore(result.vector_score)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
