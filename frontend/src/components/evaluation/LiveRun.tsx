import { useCallback, useRef, useState, type ReactNode } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { runLiveRetrieval, runPipeline } from "../../services/evaluation";
import type { LiveRetrieval, PipelineRun } from "../../types/evaluation";
import type { AsyncState } from "../../utils/dashboardStats";
import { firstExpectedRank } from "../../utils/evaluationMetrics";
import { publicError } from "../../utils/publicText";
import { ErrorState, Skeleton } from "../insights/States";
import { AnswerGrounding } from "./GroundingView";
import { PipelineTraceView } from "./PipelineView";
import { LiveResultsTable } from "./RankLadder";

const RETRIEVAL_ERROR = "Live retrieval failed. Check that the API and retrieval index are available.";
const PIPELINE_ERROR = "The full pipeline could not complete. The language model provider may be unavailable or rate-limited.";

export type LiveRunState = { query: string; retrieval: AsyncState<LiveRetrieval>; pipeline: AsyncState<PipelineRun> } | null;

function failure(error: unknown, fallback: string): { status: "error"; message: string } {
  return { status: "error", message: publicError(error instanceof Error ? error.message : "", fallback) };
}

/** Runs retrieval and the full pipeline for one query; responses from superseded runs are dropped. */
export function useLiveRun(depth: number) {
  const [state, setState] = useState<LiveRunState>(null);
  const runId = useRef(0);

  const run = useCallback(
    (query: string) => {
      const id = ++runId.current;
      setState({ query, retrieval: { status: "loading" }, pipeline: { status: "loading" } });
      const update = (patch: Partial<NonNullable<LiveRunState>>) => {
        if (id === runId.current) setState((current) => (current ? { ...current, ...patch } : current));
      };
      runLiveRetrieval(query, depth).then(
        (data) => update({ retrieval: { status: "ready", data } }),
        (error) => update({ retrieval: failure(error, RETRIEVAL_ERROR) }),
      );
      runPipeline(query).then(
        (data) => update({ pipeline: { status: "ready", data } }),
        (error) => update({ pipeline: failure(error, PIPELINE_ERROR) }),
      );
    },
    [depth],
  );

  const reset = useCallback(() => {
    runId.current += 1;
    setState(null);
  }, []);

  return { state, run, reset };
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-w-0">
      <h4 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">{title}</h4>
      {children}
    </section>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-2" aria-busy>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-11/12" />
      <Skeleton className="h-4 w-4/5" />
    </div>
  );
}

export function LiveRunView({ state, expected, onRetry }: { state: NonNullable<LiveRunState>; expected: string[]; onRetry: () => void }) {
  const { retrieval, pipeline } = state;
  const liveRank = retrieval.status === "ready" ? firstExpectedRank(retrieval.data.results.map((item) => item.doc_id), expected) : null;

  return (
    <div className="grid gap-6 xl:grid-cols-2" aria-live="polite">
      <div className="space-y-6">
        <Block title="Live retrieval">
          {retrieval.status === "loading" ? <LoadingRows /> : null}
          {retrieval.status === "error" ? <ErrorState title="Retrieval failed" message={retrieval.message} onRetry={onRetry} /> : null}
          {retrieval.status === "ready" ? (
            <div className="space-y-2">
              <p className="text-xs text-slate-600">
                {expected.length ? (
                  <>
                    Expected note: <span className="font-bold">{liveRank ? `rank #${liveRank}` : `not in the top ${retrieval.data.results.length}`}</span> ·{" "}
                  </>
                ) : (
                  <>No expected label for this query · </>
                )}
                Retrieval <span className="font-bold tabular-nums">{Math.round(retrieval.data.timings.retrieve_ms)} ms</span> · Re-ranking {retrieval.data.rerank_enabled ? "on" : "off"}
              </p>
              {!retrieval.data.pipeline_retrieves && retrieval.data.pipeline_skip_reason ? (
                <p className="rounded-lg bg-amber-50 px-2 py-1.5 text-xs text-amber-900">{retrieval.data.pipeline_skip_reason} The table shows what retrieval alone would return.</p>
              ) : null}
              <LiveResultsTable results={retrieval.data.results} expected={expected} />
            </div>
          ) : null}
        </Block>
        <Block title="Pipeline trace">
          {pipeline.status === "loading" ? (
            <>
              <LoadingRows />
              <p className="mt-2 text-xs text-slate-500">Running the full pipeline, including answer generation. This can take several seconds.</p>
            </>
          ) : null}
          {pipeline.status === "error" ? <ErrorState title="Pipeline run failed" message={pipeline.message} onRetry={onRetry} /> : null}
          {pipeline.status === "ready" ? <PipelineTraceView run={pipeline.data} /> : null}
        </Block>
      </div>
      <div className="space-y-6">
        <Block title="Answer">
          {pipeline.status === "loading" ? <LoadingRows /> : null}
          {pipeline.status === "error" ? <p className="text-xs text-slate-500">No answer, because the pipeline run failed.</p> : null}
          {pipeline.status === "ready" ? (
            <div className="max-h-[26rem] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4">
              {pipeline.data.triage?.level === "emergency" ? (
                <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-xs font-bold text-rose-900 ring-1 ring-inset ring-rose-200">{pipeline.data.triage.label}: {pipeline.data.triage.guidance}</p>
              ) : null}
              <div className="space-y-2 text-sm leading-6 text-slate-700 [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-extrabold [&_ul]:list-disc [&_ul]:pl-5">
                <Markdown remarkPlugins={[remarkGfm]}>{pipeline.data.answer || "(No answer text returned.)"}</Markdown>
              </div>
              {pipeline.data.disclaimer ? <p className="mt-3 border-t border-slate-200 pt-2 text-[11px] leading-5 text-slate-500">{pipeline.data.disclaimer}</p> : null}
            </div>
          ) : null}
        </Block>
        <Block title="Evidence grounding">
          {pipeline.status === "loading" ? <LoadingRows /> : null}
          {pipeline.status === "ready" ? <AnswerGrounding run={pipeline.data} /> : null}
        </Block>
      </div>
    </div>
  );
}
