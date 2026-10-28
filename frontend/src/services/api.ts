import type { ApiError } from "../types";
import { PUBLIC_LOOKUP_ERROR, publicError } from "../utils/publicText";

const API_BASE = "/api/v1";
const AUTH_SKIP_REFRESH = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

export class HttpError extends Error implements ApiError {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

function parseDetail(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

function parseJson(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function shouldRefresh(path: string): boolean {
  return !AUTH_SKIP_REFRESH.some((item) => path.startsWith(item));
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((response) => response.ok)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const data = parseJson(text);
  if (!response.ok) {
    if (response.status === 401 && !retried && shouldRefresh(path)) {
      const refreshed = await refreshOnce();
      if (refreshed) return apiFetch<T>(path, init, true);
    }
    const fallback =
      response.status === 401
        ? "Your session has expired. Please sign in again."
        : "Unable to complete this request.";
    throw new HttpError(publicError(parseDetail(data, fallback), fallback), response.status);
  }
  return data as T;
}

export async function readSse(
  path: string,
  body: unknown,
  onEvent: (event: Record<string, unknown>) => void,
  signal?: AbortSignal,
  retried = false,
): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    const text = await response.text();
    if (response.status === 401 && !retried) {
      const refreshed = await refreshOnce();
      if (refreshed) return readSse(path, body, onEvent, signal, true);
    }
    throw new HttpError(
      publicError(parseDetail(parseJson(text), PUBLIC_LOOKUP_ERROR), PUBLIC_LOOKUP_ERROR),
      response.status,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const payload = chunk
        .split("\n")
        .filter((item) => item.startsWith("data:"))
        .map((item) => item.replace(/^data:\s?/, ""))
        .join("\n");
      if (!payload) continue;
      const parsed = parseJson(payload);
      if (parsed && typeof parsed === "object") onEvent(parsed as Record<string, unknown>);
    }
  }
}
