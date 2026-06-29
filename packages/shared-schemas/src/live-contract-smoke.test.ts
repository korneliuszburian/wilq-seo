import { describe, expect, it } from "vitest";
import type { ZodTypeAny } from "zod";

import {
  AdsDiagnosticsResponseSchema,
  AhrefsDiagnosticsResponseSchema,
  CommandCenterResponseSchema,
  ContentDiagnosticsResponseSchema,
  DemandGenReadinessContractSchema,
  Ga4DiagnosticsResponseSchema,
  LocaloDiagnosticsResponseSchema,
  MarketingBriefSchema,
  MerchantDiagnosticsResponseSchema,
  TacticalQueueResponseSchema
} from "./index";

const API_BASE = process.env.WILQ_API_BASE ?? "http://127.0.0.1:8000";
const LIVE_SCHEMA_SMOKE_ENABLED = process.env.WILQ_LIVE_SCHEMA_SMOKE === "1";

type LiveEndpoint = {
  name: string;
  path: string;
  schema: ZodTypeAny;
};

const liveEndpoints: LiveEndpoint[] = [
  {
    name: "command center",
    path: "/api/dashboard/command-center",
    schema: CommandCenterResponseSchema
  },
  {
    name: "marketing brief",
    path: "/api/marketing/brief",
    schema: MarketingBriefSchema
  },
  {
    name: "tactical queue",
    path: "/api/marketing/tactical-queue",
    schema: TacticalQueueResponseSchema
  },
  {
    name: "ads diagnostics summary",
    path: "/api/ads/diagnostics?view=summary",
    schema: AdsDiagnosticsResponseSchema
  },
  {
    name: "merchant diagnostics",
    path: "/api/merchant/diagnostics",
    schema: MerchantDiagnosticsResponseSchema
  },
  {
    name: "content diagnostics",
    path: "/api/content/diagnostics",
    schema: ContentDiagnosticsResponseSchema
  },
  {
    name: "ga4 diagnostics",
    path: "/api/ga4/diagnostics",
    schema: Ga4DiagnosticsResponseSchema
  },
  {
    name: "localo diagnostics",
    path: "/api/localo/diagnostics",
    schema: LocaloDiagnosticsResponseSchema
  },
  {
    name: "ahrefs diagnostics",
    path: "/api/ahrefs/diagnostics",
    schema: AhrefsDiagnosticsResponseSchema
  },
  {
    name: "demand gen diagnostics",
    path: "/api/demand-gen/diagnostics",
    schema: DemandGenReadinessContractSchema
  }
];

const describeLive = LIVE_SCHEMA_SMOKE_ENABLED ? describe : describe.skip;

describeLive("live WILQ API shared schema smoke", () => {
  it.each(liveEndpoints)("parses $name from live API", async (endpoint) => {
    const payload = await fetchJson(endpoint.path);
    const parsed = endpoint.schema.safeParse(payload);

    expect(parsed.success, formatParseFailure(endpoint, parsed)).toBe(true);
  }, 20000);
});

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed with HTTP ${response.status}`);
  }
  return response.json();
}

function formatParseFailure(
  endpoint: LiveEndpoint,
  parsed: ReturnType<ZodTypeAny["safeParse"]>,
): string {
  if (parsed.success) {
    return `${endpoint.name} parsed`;
  }
  return `${endpoint.name} schema mismatch at ${endpoint.path}: ${parsed.error.message}`;
}
