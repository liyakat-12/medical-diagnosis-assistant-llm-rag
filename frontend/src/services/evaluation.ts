import type { EvaluationOverview, LiveRetrieval, PipelineRun, RetrievalCasesResponse } from "../types/evaluation";
import { apiFetch } from "./api";
import { diagnose } from "./diagnosis";

export function getEvaluationOverview(): Promise<EvaluationOverview> {
  return apiFetch<EvaluationOverview>("/evaluation/overview");
}

export function getRetrievalCases(runId?: string): Promise<RetrievalCasesResponse> {
  const suffix = runId ? `?run=${encodeURIComponent(runId)}` : "";
  return apiFetch<RetrievalCasesResponse>(`/evaluation/retrieval/cases${suffix}`);
}

export function runLiveRetrieval(query: string, topK?: number): Promise<LiveRetrieval> {
  return apiFetch<LiveRetrieval>("/evaluation/retrieve", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK ?? null }),
  });
}

export async function runPipeline(query: string): Promise<PipelineRun> {
  return (await diagnose(query)) as unknown as PipelineRun;
}
