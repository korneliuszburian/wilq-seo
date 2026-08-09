import { CodexRunSchema, type CodexRun } from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet } from "./common";

export function getCodexRuns(): Promise<CodexRun[]> {
  return apiGet("/api/codex/runs", z.array(CodexRunSchema));
}
