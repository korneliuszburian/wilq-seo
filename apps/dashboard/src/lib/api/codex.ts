import {
  CodexRunHistoryPageSchema,
  CodexRunSchema,
  type CodexRun,
  type CodexRunHistoryPage
} from "@wilq/shared-schemas";

import { apiGet } from "./common";

export function getCodexRunHistory(
  limit = 50,
  cursor: string | null = null
): Promise<CodexRunHistoryPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiGet(`/api/codex/run-history?${params.toString()}`, CodexRunHistoryPageSchema);
}

export function getCodexRun(runId: string): Promise<CodexRun> {
  return apiGet(`/api/codex/runs/${encodeURIComponent(runId)}`, CodexRunSchema);
}
