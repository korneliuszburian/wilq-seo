import {
  AhrefsDiagnosticsResponseSchema,
  MerchantDiagnosticsResponseSchema,
  type AhrefsDiagnosticsResponse,
  type MerchantDiagnosticsResponse
} from "@wilq/shared-schemas";

import { apiGet } from "./common";

export function getAhrefsDiagnostics(): Promise<AhrefsDiagnosticsResponse> {
  return apiGet("/api/ahrefs/diagnostics", AhrefsDiagnosticsResponseSchema);
}

export function getMerchantDiagnostics(): Promise<MerchantDiagnosticsResponse> {
  return apiGet("/api/merchant/diagnostics", MerchantDiagnosticsResponseSchema);
}
