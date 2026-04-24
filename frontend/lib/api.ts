import { API_BASE_URL } from "@/lib/env";

type QueryValue = string | number | boolean | null | undefined;

type ApiRequestInit = RequestInit & {
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
};

function buildApiUrl(path: string, query?: Record<string, QueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  const url = new URL(normalizedPath, `${API_BASE_URL}/`);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === null || value === undefined) continue;
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { query, headers: customHeaders, timeoutMs = 15000, ...requestInit } = init;
  const headers = new Headers(customHeaders);
  const abortController = new AbortController();
  const upstreamSignal = requestInit.signal;
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (requestInit.body && !(requestInit.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const onAbort = () => abortController.abort();
  if (upstreamSignal) {
    if (upstreamSignal.aborted) {
      abortController.abort();
    } else {
      upstreamSignal.addEventListener("abort", onAbort, { once: true });
    }
  }

  try {
    if (timeoutMs > 0) {
      timeoutHandle = setTimeout(() => abortController.abort(), timeoutMs);
    }

    const response = await fetch(buildApiUrl(path, query), {
      ...requestInit,
      headers,
      signal: abortController.signal,
      cache: requestInit.cache ?? "no-store"
    });

    if (!response.ok) {
      const bodyText = await response.text();
      let detail = bodyText.trim();
      const contentType = response.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        try {
          const bodyJson = JSON.parse(bodyText) as {
            detail?:
              | string
              | Array<{ msg?: string; loc?: Array<string | number> }>
              | Record<string, unknown>;
            error?: string;
            message?: string;
          };
          if (typeof bodyJson.detail === "string") {
            detail = bodyJson.detail;
          } else if (Array.isArray(bodyJson.detail)) {
            const messages = bodyJson.detail
              .map((item) => (typeof item?.msg === "string" ? item.msg : null))
              .filter((value): value is string => Boolean(value));
            detail = messages.join("; ") || detail;
          } else {
            detail = bodyJson.error || bodyJson.message || detail;
          }
        } catch {
          detail = bodyText.trim();
        }
      }

      const clippedDetail = detail.length > 240 ? `${detail.slice(0, 237)}...` : detail;
      throw new Error(`API request failed (${response.status}): ${clippedDetail || response.statusText}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return (await response.json()) as T;
    }

    return (await response.text()) as T;
  } catch (error) {
    if (abortController.signal.aborted) {
      throw new Error("Request timed out while contacting Cred-ible API. Please retry.");
    }

    if (error instanceof Error && error.message.startsWith("API request failed")) {
      throw error;
    }

    if (error instanceof Error) {
      throw new Error(`Unable to reach Cred-ible API. ${error.message}`);
    }

    throw new Error("Unable to reach Cred-ible API.");
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
    upstreamSignal?.removeEventListener("abort", onAbort);
  }
}
