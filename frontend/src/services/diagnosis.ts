import { apiFetch } from "./api";

export function diagnose(query: string, topK?: number): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/diagnosis", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK ?? null }),
  });
}
