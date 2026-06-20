import {
  ActionObjectSchema,
  ActionApplyResultSchema,
  ActionPreviewResultSchema,
  ActionReviewResultSchema,
  ActionValidationResultSchema,
  AdsDiagnosticsResponseSchema,
  AhrefsDiagnosticsResponseSchema,
  CommandCenterResponseSchema,
  ContentDiagnosticsResponseSchema,
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  DemandGenReadinessContractSchema,
  EvidenceSchema,
  ExpertRuleSchema,
  Ga4DiagnosticsResponseSchema,
  KnowledgeCardSchema,
  KnowledgeOperatingMapResponseSchema,
  LocaloDiagnosticsResponseSchema,
  MarketingBriefSchema,
  MarketingPlaybookSchema,
  MerchantDiagnosticsResponseSchema,
  MetricFactSchema,
  MetricStoreStatusSchema,
  OpportunitySchema,
  TacticalQueueResponseSchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type ActionApplyRequest,
  type ActionApplyResult,
  type ActionPreviewResult,
  type ActionReviewRequest,
  type ActionReviewResult,
  type ActionValidationResult,
  type AdsDiagnosticsResponse,
  type AhrefsDiagnosticsResponse,
  type CommandCenterResponse,
  type ContentDiagnosticsResponse,
  type ConnectorRefreshRun,
  type ConnectorStatus,
  type DemandGenReadinessContract,
  type Evidence,
  type ExpertRule,
  type Ga4DiagnosticsResponse,
  type KnowledgeCard,
  type KnowledgeOperatingMapResponse,
  type LocaloDiagnosticsResponse,
  type MarketingBrief,
  type MarketingBriefItem,
  type MarketingPlaybook,
  type MerchantDiagnosticsResponse,
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

export function getAhrefsDiagnostics(): Promise<AhrefsDiagnosticsResponse> {
  return apiGet("/api/ahrefs/diagnostics", AhrefsDiagnosticsResponseSchema);
}

export function getMerchantDiagnostics(): Promise<MerchantDiagnosticsResponse> {
  return apiGet("/api/merchant/diagnostics", MerchantDiagnosticsResponseSchema);
}

export function getContentDiagnostics(): Promise<ContentDiagnosticsResponse> {
  return apiGet("/api/content/diagnostics", ContentDiagnosticsResponseSchema);
}

export function getGa4Diagnostics(): Promise<Ga4DiagnosticsResponse> {
  return apiGet("/api/ga4/diagnostics", Ga4DiagnosticsResponseSchema);
}

export function getLocaloDiagnostics(): Promise<LocaloDiagnosticsResponse> {
  return apiGet("/api/localo/diagnostics", LocaloDiagnosticsResponseSchema);
}

export function getDemandGenDiagnostics(): Promise<DemandGenReadinessContract> {
  return apiGet("/api/demand-gen/diagnostics", DemandGenReadinessContractSchema);
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

export function previewAction(actionId: string): Promise<ActionPreviewResult> {
  return apiPost(`/api/actions/${actionId}/preview`, ActionPreviewResultSchema, {
    requested_by: "operator_local_dashboard",
    max_items: 8
  });
}

export function reviewAction(
  actionId: string,
  request: ActionReviewRequest
): Promise<ActionReviewResult> {
  return apiPost(`/api/actions/${actionId}/review`, ActionReviewResultSchema, request);
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

export function getKnowledgeOperatingMap(): Promise<KnowledgeOperatingMapResponse> {
  return apiGet("/api/knowledge/operating-map", KnowledgeOperatingMapResponseSchema);
}

export type {
  ActionObject,
  ActionApplyResult,
  ActionPreviewResult,
  ActionReviewRequest,
  ActionReviewResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  AhrefsDiagnosticsResponse,
  CommandCenterResponse,
  ContentDiagnosticsResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  DemandGenReadinessContract,
  Evidence,
  ExpertRule,
  Ga4DiagnosticsResponse,
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  LocaloDiagnosticsResponse,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MerchantDiagnosticsResponse,
  MetricFact,
  MetricStoreStatus,
  Opportunity,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun
};
