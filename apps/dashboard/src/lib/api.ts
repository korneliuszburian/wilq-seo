import {
  ActionObjectSchema,
  ActionApplyResultSchema,
  ActionValidationResultSchema,
  AdsDiagnosticsResponseSchema,
  CommandCenterResponseSchema,
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  EvidenceSchema,
  ExpertRuleSchema,
  KnowledgeCardSchema,
  MarketingBriefSchema,
  MarketingPlaybookSchema,
  MetricFactSchema,
  MetricStoreStatusSchema,
  OpportunitySchema,
  TacticalQueueResponseSchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type ActionApplyRequest,
  type ActionApplyResult,
  type ActionValidationResult,
  type AdsDiagnosticsResponse,
  type CommandCenterResponse,
  type ConnectorRefreshRun,
  type ConnectorStatus,
  type Evidence,
  type ExpertRule,
  type KnowledgeCard,
  type MarketingBrief,
  type MarketingBriefItem,
  type MarketingPlaybook,
  type MetricFact,
  type MetricStoreStatus,
  type Opportunity,
  type TacticalQueueResponse,
  type Workflow,
  type WorkflowRun
} from "@wilq/shared-schemas";
import { z } from "zod";

const API_BASE = import.meta.env.VITE_WILQ_API_BASE_URL ?? "http://127.0.0.1:8000";

type ApiSchema<T> = {
  parse: (data: unknown) => T;
};

async function apiGet<T>(path: string, schema: ApiSchema<T>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return schema.parse(await response.json());
}

async function apiPost<T>(path: string, schema: ApiSchema<T>, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return schema.parse(await response.json());
}

export function getCommandCenter(): Promise<CommandCenterResponse> {
  return apiGet("/api/dashboard/command-center", CommandCenterResponseSchema);
}

export function getMarketingBrief(): Promise<MarketingBrief> {
  return apiGet("/api/marketing/brief", MarketingBriefSchema);
}

export function getTacticalQueue(): Promise<TacticalQueueResponse> {
  return apiGet("/api/marketing/tactical-queue", TacticalQueueResponseSchema);
}

export function getAdsDiagnostics(): Promise<AdsDiagnosticsResponse> {
  return apiGet("/api/ads/diagnostics", AdsDiagnosticsResponseSchema);
}

export function getConnectors(): Promise<ConnectorStatus[]> {
  return apiGet("/api/connectors", z.array(ConnectorStatusSchema));
}

export function getConnectorRefreshRuns(): Promise<ConnectorRefreshRun[]> {
  return apiGet("/api/connectors/refresh-runs", z.array(ConnectorRefreshRunSchema));
}

export function getMetricFacts(limit = 24): Promise<MetricFact[]> {
  return apiGet(`/api/metrics?limit=${limit}`, z.array(MetricFactSchema));
}

export function getMetricStoreStatus(): Promise<MetricStoreStatus> {
  return apiGet("/api/metrics/status", MetricStoreStatusSchema);
}

export function getOpportunities(): Promise<Opportunity[]> {
  return apiGet("/api/opportunities", z.array(OpportunitySchema));
}

export function getActions(): Promise<ActionObject[]> {
  return apiGet("/api/actions", z.array(ActionObjectSchema));
}

export function validateAction(actionId: string): Promise<ActionValidationResult> {
  return apiPost(`/api/actions/${actionId}/validate`, ActionValidationResultSchema);
}

export function applyAction(
  actionId: string,
  request: ActionApplyRequest
): Promise<ActionApplyResult> {
  return apiApplyAction(actionId, request);
}

async function apiApplyAction(
  actionId: string,
  request: ActionApplyRequest
): Promise<ActionApplyResult> {
  const response = await fetch(`${API_BASE}/api/actions/${actionId}/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  const payload = await response.json();
  if (!response.ok && payload && typeof payload === "object" && "detail" in payload) {
    return ActionApplyResultSchema.parse(payload.detail);
  }
  if (!response.ok) {
    throw new Error(`API request failed: /api/actions/${actionId}/apply`);
  }
  return ActionApplyResultSchema.parse(payload);
}

export function getEvidence(): Promise<Evidence[]> {
  return apiGet("/api/evidence", z.array(EvidenceSchema));
}

export function getWorkflows(): Promise<Workflow[]> {
  return apiGet("/api/workflows", z.array(WorkflowSchema));
}

export function getWorkflowRuns(): Promise<WorkflowRun[]> {
  return apiGet("/api/workflow-runs", z.array(WorkflowRunSchema));
}

export function getExpertRules(): Promise<ExpertRule[]> {
  return apiGet("/api/expert/rules", z.array(ExpertRuleSchema));
}

export function getKnowledgeCards(): Promise<KnowledgeCard[]> {
  return apiGet("/api/knowledge/cards", z.array(KnowledgeCardSchema));
}

export function getKnowledgePlaybooks(): Promise<MarketingPlaybook[]> {
  return apiGet("/api/knowledge/playbooks", z.array(MarketingPlaybookSchema));
}

export type {
  ActionObject,
  ActionApplyResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  CommandCenterResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  KnowledgeCard,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MetricFact,
  MetricStoreStatus,
  Opportunity,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun
};
