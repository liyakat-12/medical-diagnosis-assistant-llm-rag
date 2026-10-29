import { useEffect, useMemo, useState } from "react";
import { Loader2, RotateCw, Search } from "lucide-react";
import { cn } from "../../lib/cn";
import { runLiveRetrieval } from "../../services/evaluation";
import type { LiveRetrieval, RetrievalCase } from "../../types/evaluation";
import type { AsyncState } from "../../utils/dashboardStats";
import {
  caseCategories,
  filterCases,
  firstExpectedRank,
  formatCategory,
  formatPercent,
  formatScore,
  OUTCOME_LABELS,
  summarizeCases,
  type OutcomeFilter,
} from "../../utils/evaluationMetrics";
import { publicError } from "../../utils/publicText";
import { EmptyState, ErrorState } from "../insights/States";
import { LiveResultsTable, OutcomeBadge, RankLadder } from "./RankLadder";

const PAGE = 20;
const LIVE_ERROR = "Live retrieval failed. Check that the API and retrieval index are available.";

export function CaseExplorer({ cases, depth }: { cases: RetrievalCase[]; depth: number }) {
  const [outcome, setOutcome] = useState<OutcomeFilter>("all");
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const categories = useMemo(() => caseCategories(cases), [cases]);
  const visible = useMemo(() => filterCases(cases, depth, { outcome, category, search }), [cases, depth, outcome, category, search]);
  const subset = useMemo(() => summarizeCases(visible, depth), [visible, depth]);
  const selected = visible.find((item) => item.id === selectedId) ?? visible[0] ?? null;

  useEffect(() => setLimit(PAGE), [outcome, category, search]);

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3" role="search" aria-label="Filter evaluation cases">
        <label className="min-w-[14rem] flex-1 text-xs font-bold text-slate-600">
          Search
          <span className="mt-1 flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 focus-within:border-teal-700 focus-within:ring-2 focus-within:ring-teal-700/20">
            <Search size={14} className="text-slate-400" aria-hidden />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Query text or document id" className="min-h-10 w-full bg-transparent text-sm font-normal text-slate-900 outline-none" />
          </span>
        </label>
        <label className="text-xs font-bold text-slate-600">
          Outcome
          <select value={outcome} onChange={(event) => setOutcome(event.target.value as OutcomeFilter)} className="mt-1 block min-h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900">
            <option value="all">All outcomes</option>
            {(Object.keys(OUTCOME_LABELS) as (keyof typeof OUTCOME_LABELS)[]).map((key) => (
              <option key={key} value={key}>
                {OUTCOME_LABELS[key]}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-bold text-slate-600">
          Category
          <select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1 block min-h-10 max-w-[14rem] rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900">
            <option value="all">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {formatCategory(item)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="mt-3 text-xs text-slate-600" aria-live="polite">
        <span className="font-bold text-slate-800">{visible.length}</span> of {cases.length} cases · Recall@1 <span className="font-bold tabular-nums">{formatPercent(subset.recallAt1)}</span> · Recall@3{" "}
        <span className="font-bold tabular-nums">{formatPercent(subset.recallAt3)}</span> · MRR <span className="font-bold tabular-nums">{formatScore(subset.mrr)}</span>
        <span className="text-slate-400"> (computed for this filtered subset)</span>
      </p>

      {!visible.length ? (
        <div className="mt-4">
          <EmptyState title="No cases match these filters">Clear the search or choose another outcome or category.</EmptyState>
        </div>
      ) : (
        <div className="mt-4 grid gap-6 lg:grid-cols-[1.25fr_1fr]">
          <div className="min-w-0">
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
              <table className="w-full min-w-[34rem] text-left text-xs">
                <caption className="sr-only">Evaluation cases. Select a row to see its details.</caption>
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th scope="col" className="px-3 py-2 font-bold">Query</th>
                    <th scope="col" className="px-3 py-2 font-bold">Category</th>
                    <th scope="col" className="px-3 py-2 text-right font-bold">Rank</th>
                    <th scope="col" className="px-3 py-2 text-right font-bold" title="Reciprocal rank: 1 / rank, or 0 if missed">RR</th>
                    <th scope="col" className="px-3 py-2 font-bold">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.slice(0, limit).map((item) => {
                    const active = selected?.id === item.id;
                    return (
                      <tr key={item.id} className={cn("border-b border-slate-100 last:border-0", active ? "bg-teal-50" : "hover:bg-slate-50")}>
                        <td className="max-w-[18rem] px-3 py-2">
                          <button
                            type="button"
                            onClick={() => setSelectedId(item.id)}
                            aria-pressed={active}
                            className="block w-full truncate text-left font-bold text-[#0b1f33] outline-none hover:text-teal-800 focus-visible:underline"
                            title={item.query}
                          >
                            {item.query}
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatCategory(item.category)}</td>
                        <td className="px-3 py-2 text-right font-bold tabular-nums">{item.rank ?? "—"}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{formatScore(item.reciprocal_rank, 2)}</td>
                        <td className="px-3 py-2">
                          <OutcomeBadge rank={item.rank} depth={depth} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {visible.length > limit ? (
              <button type="button" onClick={() => setLimit((value) => value + PAGE)} className="mt-3 text-sm font-bold text-teal-800 hover:underline">
                Show {Math.min(PAGE, visible.length - limit)} more ({visible.length - limit} hidden)
              </button>
            ) : null}
          </div>
          {selected ? <CaseDetail key={selected.id} item={selected} depth={depth} /> : null}
        </div>
      )}
    </div>
  );
}

function Flag({ label, value }: { label: string; value: string; }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-bold tabular-nums text-[#0b1f33]">{value}</dd>
    </div>
  );
}

function CaseDetail({ item, depth }: { item: RetrievalCase; depth: number }) {
  const [live, setLive] = useState<AsyncState<LiveRetrieval> | null>(null);

  const rerun = async () => {
    setLive({ status: "loading" });
    try {
      setLive({ status: "ready", data: await runLiveRetrieval(item.query, depth) });
    } catch (error) {
      setLive({ status: "error", message: publicError(error instanceof Error ? error.message : "", LIVE_ERROR) });
    }
  };

  const liveRank = live?.status === "ready" ? firstExpectedRank(live.data.results.map((result) => result.doc_id), item.expected_doc_ids) : null;

  return (
    <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 lg:sticky lg:top-20 lg:self-start" aria-labelledby={`case-${item.id}`}>
      <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
        Case <span className="font-mono normal-case">{item.id}</span> · {formatCategory(item.category)}
      </p>
      <h3 id={`case-${item.id}`} className="mt-1 text-base font-extrabold leading-snug text-[#0b1f33]">
        “{item.query}”
      </h3>
      <dl className="mt-3 grid grid-cols-4 gap-2 text-xs">
        <Flag label="Rank" value={item.rank ? `#${item.rank}` : "Missed"} />
        <Flag label="Top-1" value={item.rank === 1 ? "Yes" : "No"} />
        <Flag label="Top-3" value={item.rank !== null && item.rank <= 3 ? "Yes" : "No"} />
        <Flag label="RR" value={formatScore(item.reciprocal_rank, 2)} />
      </dl>
      <div className="mt-4">
        <RankLadder label={`Stored run: top ${depth} retrieved`} retrieved={item.retrieved_doc_ids} expected={item.expected_doc_ids} />
      </div>

      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-bold text-slate-600">Live result against the current index</p>
          <button
            type="button"
            onClick={() => void rerun()}
            disabled={live?.status === "loading"}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 text-xs font-bold text-[#0b1f33] hover:border-teal-700 hover:text-teal-800 disabled:opacity-60"
          >
            {live?.status === "loading" ? <Loader2 size={13} className="animate-spin motion-reduce:animate-none" aria-hidden /> : <RotateCw size={13} aria-hidden />}
            {live ? "Run again" : "Re-run live"}
          </button>
        </div>
        <div className="mt-3" aria-live="polite">
          {!live ? <p className="text-xs text-slate-500">Runs this query through retrieval now, showing titles and scores. Nothing is saved.</p> : null}
          {live?.status === "loading" ? <p className="text-xs text-slate-500">Searching the index…</p> : null}
          {live?.status === "error" ? <ErrorState title="Live retrieval failed" message={live.message} onRetry={() => void rerun()} /> : null}
          {live?.status === "ready" ? (
            <div className="space-y-2">
              <p className="text-xs text-slate-600">
                Expected note now at: <span className="font-bold">{liveRank ? `#${liveRank}` : `not in top ${live.data.results.length}`}</span> · retrieval took{" "}
                <span className="font-bold tabular-nums">{Math.round(live.data.timings.retrieve_ms)} ms</span>
                {live.data.search_query !== item.query ? (
                  <>
                    {" "}· searched as “<span className="italic">{live.data.search_query}</span>”
                  </>
                ) : null}
              </p>
              {!live.data.pipeline_retrieves && live.data.pipeline_skip_reason ? (
                <p className="rounded-lg bg-amber-50 px-2 py-1.5 text-xs text-amber-900">{live.data.pipeline_skip_reason} These results show what retrieval alone would return.</p>
              ) : null}
              <LiveResultsTable results={live.data.results} expected={item.expected_doc_ids} />
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
