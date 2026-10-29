import { Info } from "lucide-react";
import { cn } from "../../lib/cn";
import type { GroundingSummary, PipelineRun } from "../../types/evaluation";
import { formatCategory, formatPercent } from "../../utils/evaluationMetrics";
import { DistributionBars } from "../insights/Charts";

const ORIGIN_SHORT: Record<string, string> = {
  knowledge_base: "Knowledge base",
  mixed: "KB + general",
  general: "General only",
  none: "No evidence used",
};

export const ORIGIN_LABELS: Record<string, string> = {
  knowledge_base: "Knowledge-base evidence",
  mixed: "Knowledge base plus general knowledge",
  general: "General knowledge only",
  none: "No evidence used",
};

const VERDICT: Record<string, { label: string; className: string }> = {
  pass: { label: "All factual sentences cited", className: "text-emerald-800 bg-emerald-50 ring-emerald-200" },
  partial: { label: "Some sentences uncited", className: "text-amber-800 bg-amber-50 ring-amber-200" },
  fail: { label: "Citation problems found", className: "text-rose-800 bg-rose-50 ring-rose-200" },
  n_a: { label: "No factual claims to audit", className: "text-slate-700 bg-slate-50 ring-slate-200" },
};

export function CitationCaveat() {
  return (
    <p className="flex items-start gap-2 rounded-xl bg-slate-100 px-3 py-2 text-xs leading-5 text-slate-700">
      <Info size={14} className="mt-0.5 shrink-0 text-slate-500" aria-hidden />
      A citation shows which reference note a sentence was drawn from. It does not prove the statement is medically correct or that it applies to a particular person.
    </p>
  );
}

export function AnswerGrounding({ run }: { run: PipelineRun }) {
  const audit = run.faithfulness;
  const verdict = audit?.verdict ? VERDICT[audit.verdict] : null;
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Evidence source</dt>
          <dd className="font-bold text-[#0b1f33]">{ORIGIN_LABELS[run.evidence_origin] ?? formatCategory(run.evidence_origin || "none")}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Cited notes</dt>
          <dd className="font-bold tabular-nums text-[#0b1f33]">{run.citations.length}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Cited sentences</dt>
          <dd className="font-bold tabular-nums text-[#0b1f33]">
            {audit && typeof audit.supported_count === "number" && audit.claim_count ? `${audit.supported_count} of ${audit.claim_count}` : "Not audited"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Triage</dt>
          <dd className="font-bold text-[#0b1f33]">{run.triage?.label || (run.refused ? "Refused" : "None")}</dd>
        </div>
      </dl>
      {verdict ? (
        <p className={cn("inline-flex rounded-full px-2.5 py-1 text-[11px] font-bold ring-1 ring-inset", verdict.className)}>
          Citation audit: {verdict.label}
          {typeof audit?.coverage === "number" && audit.verdict !== "n_a" ? ` · coverage ${formatPercent(audit.coverage, 0)}` : ""}
        </p>
      ) : null}
      {run.citations.length ? (
        <ul className="space-y-1 text-xs">
          {run.citations.map((citation, index) => (
            <li key={`${citation.title}-${index}`} className="flex gap-2">
              <span className="font-bold tabular-nums text-slate-500">[{index + 1}]</span>
              <span className="min-w-0">
                <span className="font-bold text-[#0b1f33]">{citation.title || citation.condition || "Reference note"}</span>
                {citation.source ? <span className="text-slate-500"> · {citation.source}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <CitationCaveat />
    </div>
  );
}

export function GroundingSummaryPanel({ summary }: { summary: GroundingSummary }) {
  const origins = Object.entries(summary.origin_counts).sort((a, b) => b[1] - a[1]);
  const checks = Object.entries(summary.checks);
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div>
        <DistributionBars
          title="Where answers drew their evidence"
          description={`Evidence source across ${summary.cases} stored answer-quality cases.`}
          total={summary.cases}
          items={origins.map(([origin, count]) => ({
            label: ORIGIN_SHORT[origin] ?? formatCategory(origin),
            value: count,
            tone: origin === "knowledge_base" ? "good" : origin === "none" ? "bad" : "warn",
          }))}
        />
        <p className="mt-3 text-xs leading-5 text-slate-500">
          “No evidence used” is expected for refusals, greetings and emergencies. {summary.cases_with_citations} of {summary.cases} answers carried citations ({summary.citations_total} in total).
        </p>
      </div>
      <div>
        <p className="text-sm font-extrabold text-[#0b1f33]">Automated answer checks</p>
        <table className="mt-3 w-full text-left text-xs">
          <caption className="sr-only">Automated grounding checks from the stored answer-quality report</caption>
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th scope="col" className="py-1.5 font-bold">Check</th>
              <th scope="col" className="py-1.5 text-right font-bold">Applied to</th>
              <th scope="col" className="py-1.5 text-right font-bold">Failed</th>
            </tr>
          </thead>
          <tbody>
            {checks.map(([name, check]) => (
              <tr key={name} className="border-b border-slate-100">
                <th scope="row" className="py-1.5 font-bold text-slate-700">{formatCategory(name)}</th>
                <td className="py-1.5 text-right tabular-nums">{check.n}</td>
                <td className={cn("py-1.5 text-right font-bold tabular-nums", check.failed ? "text-rose-700" : "text-emerald-700")}>{check.failed}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-slate-500">
          Source: <span className="font-mono">{summary.report}</span>
          {summary.method ? ` · ${summary.method}` : ""}
        </p>
      </div>
    </div>
  );
}
