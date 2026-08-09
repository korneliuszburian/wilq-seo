import {
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  type ConnectorRefreshRun,
  type ConnectorStatus
} from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet, apiPost } from "./common";

export function getConnectors(): Promise<ConnectorStatus[]> {
  return apiGet("/api/connectors", z.array(ConnectorStatusSchema));
}

export function refreshConnector(connectorId: string): Promise<ConnectorRefreshRun> {
  return apiPost(
    `/api/connectors/${encodeURIComponent(connectorId)}/refresh`,
    ConnectorRefreshRunSchema,
    { mode: "vendor_read", reason: "dashboard_source_health", run_async: true }
  );
}

export function getConnectorRefreshRun(runId: string): Promise<ConnectorRefreshRun> {
  return apiGet(
    `/api/connectors/refresh-runs/${encodeURIComponent(runId)}`,
    ConnectorRefreshRunSchema
  );
}
