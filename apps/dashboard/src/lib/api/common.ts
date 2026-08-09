import { z } from "zod";

export const API_BASE =
  import.meta.env.VITE_WILQ_API_BASE_URL ?? "http://127.0.0.1:8000";
export const API_TIMEOUT_MS = 30_000;
export const CODEX_PROPOSAL_TIMEOUT_MS = 135_000;

export type ApiSchema<T extends z.ZodTypeAny> = T;

export async function apiFetch(
  path: string,
  init?: RequestInit,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<Response> {
  if (typeof AbortController === "undefined") {
    return fetch(`${API_BASE}${path}`, init);
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function apiErrorMessage(response: Response, path: string): Promise<string> {
  let detail = "";
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const rawDetail = (body as { detail?: unknown }).detail;
      const serializedDetail = JSON.stringify(rawDetail);
      detail =
        typeof rawDetail === "string"
          ? rawDetail
          : (serializedDetail ?? String(rawDetail)).slice(0, 500);
    }
  } catch {
    detail = "";
  }
  const suffix = detail ? `: ${detail}` : "";
  return `API request failed: ${path} (${response.status})${suffix}`;
}

export async function apiGet<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>
): Promise<z.infer<T>> {
  const response = await apiFetch(path);
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return schema.parse(await response.json());
}

export async function apiPost<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>,
  body?: unknown
): Promise<z.infer<T>> {
  const response = await apiFetch(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return schema.parse(await response.json());
}

export async function apiPostWithDetailConflict<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>,
  body: unknown
): Promise<z.infer<T>> {
  const response = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (response.status === 409) {
    const payload: unknown = await response.json();
    const detail = z.object({ detail: z.unknown() }).parse(payload).detail;
    return schema.parse(detail);
  }
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return schema.parse(await response.json());
}

export async function apiPostWithConflict<
  TSuccess extends z.ZodTypeAny,
  TConflict extends z.ZodTypeAny
>(
  path: string,
  successSchema: ApiSchema<TSuccess>,
  conflictSchema: ApiSchema<TConflict>,
  body: unknown,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<z.infer<TSuccess> | z.infer<TConflict>> {
  const response = await apiFetch(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    },
    timeoutMs
  );
  if (response.status === 409) {
    return conflictSchema.parse(await response.json());
  }
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return successSchema.parse(await response.json());
}
