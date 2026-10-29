import { useEffect, useRef, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Presentation, X } from "lucide-react";
import { PageShell } from "../components/common/PageShell";
import { MetricCards } from "../components/evaluation/MetricCards";
import { RagPipelineDiagram } from "../components/evaluation/RagPipelineDiagram";
import { DistributionBars, GroupedBarChart, type Series } from "../components/insights/Charts";
import { EmptyState, ErrorState, SectionHeading, Skeleton } from "../components/insights/States";
import { useAsync } from "../hooks/useAsync";
import { cn } from "../lib/cn";
import { getEvaluationOverview } from "../services/evaluation";
import type { EvaluationOverview, RetrievalRun } from "../types/evaluation";
import type { AsyncState } from "../utils/dashboardStats";
import { categoryRows, embeddingGroups, embeddingNote, rankDistribution, retrievalRunGroups, retrievalRunsNote, scoreLabel, selectedRun } from "../utils/evaluationCharts";

const RUN_SERIES: Series[] = [
  { key: "r1", label: "Recall@1", color: "#0f766e" },
  { key: "r3", label: "Recall@3", color: "#5eead4" },
  { key: "r4", label: "Recall@4", color: "#94a3b8" },
  { key: "mrr", label: "MRR", color: "#0b1f33" },
];

const EMBED_SERIES: Series[] = [
  { key: "r1", label: "Recall@1", color: "#0f766e" },
  { key: "r3", label: "Recall@3", color: "#5eead4" },
  { key: "r5", label: "Recall@5", color: "#94a3b8" },
  { key: "mrr", label: "MRR", color: "#0b1f33" },
];

export function Evaluation() {
  const [params, setParams] = useSearchParams();
  const demo = params.get("demo") === "1";
  const overview = useAsync(getEvaluationOverview);
  const runs = overview.state.status === "ready" ? overview.state.data.retrieval_runs : [];
  const run = selectedRun(runs, params.get("run"));

  const wasDemo = useRef(demo);
  useEffect(() => {
    if (demo && !wasDemo.current) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      document.getElementById("metrics")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }
    wasDemo.current = demo;
  }, [demo]);

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value === null) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  return (
    <PageShell>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 py-5">
          <div className="max-w-2xl">
            <h1 className="text-2xl font-extrabold tracking-tight text-[#0b1f33] sm:text-3xl">Evaluation Dashboard</h1>
            <p className="mt-1 text-sm text-slate-600">Retrieval metrics show whether the expected reference note was found. They are not a measure of diagnostic accuracy.</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            {runs.length ? (
              <label className="text-xs font-bold text-slate-600">
                Evaluation run
                <select
                  value={run?.id ?? ""}
                  onChange={(event) => setParam("run", event.target.value)}
                  className="mt-1 block min-h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900"
                >
                  {runs.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label} ({item.metrics.n} queries)
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <button
              type="button"
              onClick={() => setParam("demo", demo ? null : "1")}
              aria-pressed={demo}
              title={demo ? "Turn off Presentation Mode" : "Turn on Presentation Mode"}
              className={cn(
                "inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-bold transition-colors motion-reduce:transition-none",
                demo ? "border-teal-700 bg-teal-700 text-white hover:bg-teal-800" : "border-slate-300 bg-white text-[#0b1f33] hover:border-teal-700",
              )}
            >
              <Presentation size={15} aria-hidden /> Presentation Mode
              <span aria-hidden className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-extrabold uppercase", demo ? "bg-white/20" : "bg-slate-100 text-slate-500")}>
                {demo ? "On" : "Off"}
              </span>
            </button>
            {demo ? (
              <button
                type="button"
                onClick={() => setParam("demo", null)}
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-slate-300 bg-white px-4 text-sm font-bold text-slate-700 hover:border-slate-400"
              >
                <X size={14} aria-hidden /> Exit Presentation Mode
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-6">
        {overview.state.status === "error" ? <ErrorState title="Evaluation data could not be loaded" message={overview.state.message} onRetry={overview.reload} /> : null}

        <section id="metrics" aria-labelledby="metrics-title" className="scroll-mt-20">
          <SectionHeading id="metrics-title" title="Metrics" />
          <div className="mt-4">
            <MetricsBlock state={overview.state} run={run} />
          </div>
        </section>

        <section id="charts" aria-labelledby="charts-title" className="scroll-mt-20">
          <SectionHeading id="charts-title" title="Charts" />
          <div className="mt-4">
            <ChartsBlock state={overview.state} run={run} />
          </div>
        </section>

        <section id="pipeline" aria-labelledby="pipeline-title" className="scroll-mt-20">
          <SectionHeading id="pipeline-title" title="RAG pipeline" />
          <div className="mt-4">
            <RagPipelineDiagram />
          </div>
        </section>
      </div>
    </PageShell>
  );
}

function MetricsBlock({ state, run }: { state: AsyncState<EvaluationOverview>; run: RetrievalRun | null }) {
  if (state.status === "loading") {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6" aria-busy>
        {[0, 1, 2, 3, 4, 5].map((index) => (
          <div key={index} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-3 h-8 w-20" />
          </div>
        ))}
      </div>
    );
  }
  if (state.status === "error") return null;
  if (!run) return <EmptyState title="No stored evaluation run is available." />;
  return <MetricCards run={run} />;
}

function ChartCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("min-w-0 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5", className)}>{children}</div>;
}

function ChartsBlock({ state, run }: { state: AsyncState<EvaluationOverview>; run: RetrievalRun | null }) {
  if (state.status === "loading") {
    return (
      <div className="grid gap-4 lg:grid-cols-2" aria-busy>
        <Skeleton className="h-64 w-full lg:col-span-2" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (state.status === "error") return null;
  if (!run) return <EmptyState title="No stored evaluation run to chart." />;

  const runs = state.data.retrieval_runs;
  const embeddings = state.data.embedding_comparison;
  const ranks = rankDistribution(run);
  const categories = categoryRows(run);
  const embedGroups = embeddingGroups(embeddings);
  const embedCaption = embeddingNote(embeddings);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard className="lg:col-span-2">
        <GroupedBarChart
          title="Retrieval runs over time"
          description={`Recall@1, Recall@3, Recall@4, and MRR for ${runs.length} stored runs, oldest first. MRR is a rank score, not a recall rate. Rank and category charts follow ${run.label}.`}
          yLabel="Score (0 to 1)"
          series={RUN_SERIES}
          format={scoreLabel}
          groups={retrievalRunGroups(runs, run.id)}
        />
        <p className="mt-2 text-xs leading-5 text-slate-500">{retrievalRunsNote(runs)}</p>
      </ChartCard>
      {ranks ? (
        <ChartCard>
          <DistributionBars
            title={`Where the expected note ranked (${run.label})`}
            description={`Rank of the expected note for ${run.metrics.n} test queries in ${run.label}. Not in the top four means it was not retrieved at rank 1, 2, 3, or 4.`}
            total={run.metrics.n}
            items={ranks}
          />
        </ChartCard>
      ) : null}
      {categories ? (
        <ChartCard>
          <CategoryTable run={run} rows={categories} />
        </ChartCard>
      ) : null}
      <ChartCard className="lg:col-span-2">
        {embedGroups.length ? (
          <>
            <GroupedBarChart
              title="Embedding model comparison (earlier experiment)"
              description="Recall@1, Recall@3, Recall@5, and MRR from the stored embedding experiment. This is a different question set from the retrieval runs above."
              yLabel="Score (0 to 1)"
              series={EMBED_SERIES}
              format={scoreLabel}
              groups={embedGroups}
            />
            <p className="mt-2 text-xs leading-5 text-slate-500">{embedCaption}</p>
          </>
        ) : (
          <EmptyState title="No embedding comparison is available." />
        )}
      </ChartCard>
    </div>
  );
}

function CategoryTable({ run, rows }: { run: RetrievalRun; rows: NonNullable<ReturnType<typeof categoryRows>> }) {
  return (
    <figure className="min-w-0">
      <figcaption className="text-sm font-extrabold text-[#0b1f33]">By question category ({run.label})</figcaption>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[18rem] text-left text-xs">
          <caption className="sr-only">Recall@1 and MRR by question category for {run.label}</caption>
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th scope="col" className="py-1.5 pr-3 font-bold">Category</th>
              <th scope="col" className="py-1.5 pr-3 text-right font-bold">Queries</th>
              <th scope="col" className="py-1.5 pr-3 text-right font-bold">Recall@1</th>
              <th scope="col" className="py-1.5 text-right font-bold">MRR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.category} className="border-b border-slate-100">
                <th scope="row" className="py-1.5 pr-3 font-bold text-slate-700">{row.category}</th>
                <td className="py-1.5 pr-3 text-right tabular-nums">{row.queries}</td>
                <td className="py-1.5 pr-3 text-right tabular-nums">{row.recallAt1}</td>
                <td className="py-1.5 text-right tabular-nums">{row.mrr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
