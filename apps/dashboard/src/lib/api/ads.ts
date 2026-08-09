import {
  AdsDiagnosticsResponseSchema,
  DemandGenReadinessContractSchema,
  type AdsDiagnosticsResponse,
  type DemandGenReadinessContract
} from "@wilq/shared-schemas";

import { apiGet } from "./common";

export function getAdsDiagnostics(): Promise<AdsDiagnosticsResponse> {
  return apiGet("/api/ads/diagnostics", AdsDiagnosticsResponseSchema);
}

export function getAdsDiagnosticsSummary(): Promise<AdsDiagnosticsResponse> {
  return apiGet("/api/ads/diagnostics?view=summary", AdsDiagnosticsResponseSchema);
}

export function getDemandGenDiagnostics(): Promise<DemandGenReadinessContract> {
  return apiGet("/api/demand-gen/diagnostics", DemandGenReadinessContractSchema);
}
