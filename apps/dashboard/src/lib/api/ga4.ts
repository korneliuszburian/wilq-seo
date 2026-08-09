import {
  Ga4DiagnosticsResponseSchema,
  LocaloDiagnosticsResponseSchema,
  type Ga4DiagnosticsResponse,
  type LocaloDiagnosticsResponse
} from "@wilq/shared-schemas";

import { apiGet } from "./common";

export function getGa4Diagnostics(): Promise<Ga4DiagnosticsResponse> {
  return apiGet("/api/ga4/diagnostics", Ga4DiagnosticsResponseSchema);
}

export function getLocaloDiagnostics(): Promise<LocaloDiagnosticsResponse> {
  return apiGet("/api/localo/diagnostics", LocaloDiagnosticsResponseSchema);
}
