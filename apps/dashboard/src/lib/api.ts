import {
  ActionObjectSchema,
  ActionConfirmResultSchema,
  ActionImpactCheckResultSchema,
  ActionPreviewResultSchema,
  ActionReviewResultSchema,
  ActionValidationResultSchema,
  AdsDiagnosticsResponseSchema,
  AhrefsDiagnosticsResponseSchema,
  CommandCenterResponseSchema,
  ContentDiagnosticsResponseSchema,
  ContentPreflightResponseSchema,
  ContentWorkItemDraftPackageResponseSchema,
  ContentWorkItemHumanReviewResponseSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  ContentWorkItemPreflightResponseSchema,
  ContentWorkItemSalesBriefResponseSchema,
  ContentWorkItemWordPressDraftHandoffResponseSchema,
  ConnectorStatusSchema,
  DemandGenReadinessContractSchema,
  EvidenceSchema,
  Ga4DiagnosticsResponseSchema,
  KnowledgeCardSchema,
  KnowledgeOperatingMapResponseSchema,
  LocaloDiagnosticsResponseSchema,
  MarketingBriefSchema,
  MarketingPlaybookSchema,
  MerchantDiagnosticsResponseSchema,
  OpportunitySchema,
  TacticalQueueResponseSchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type ActionConfirmRequest,
  type ActionConfirmResult,
  type ActionImpactCheckRequest,
  type ActionImpactCheckResult,
  type ActionPreviewCardViewModel,
  type ActionPreviewResult,
  type ActionReviewRequest,
  type ActionReviewResult,
  type ActionValidationResult,
  type AdsDiagnosticsResponse,
  type AhrefsDiagnosticsResponse,
  type CommandCenterResponse,
  type ContentDiagnosticsResponse,
  type ContentPreflightResponse,
  type ContentWorkItemDraftPackageResponse,
  type ContentWorkItemHumanReviewResponse,
  type ContentWorkItemMeasurementWindowResponse,
  type ContentWorkItemPreflightResponse,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemWordPressDraftHandoffResponse,
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

export function getAdsDiagnosticsSummary(): Promise<AdsDiagnosticsResponse> {
  return apiGet("/api/ads/diagnostics?view=summary", AdsDiagnosticsResponseSchema);
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

export function getContentPreflight(): Promise<ContentPreflightResponse> {
  return apiGet("/api/content/preflight", ContentPreflightResponseSchema);
}

export function postContentWorkItemPreflight(
  request: unknown
): Promise<ContentWorkItemPreflightResponse> {
  return apiPost(
    "/api/content/work-items/preflight",
    ContentWorkItemPreflightResponseSchema,
    request
  );
}

export function postContentWorkItemSalesBrief(
  request: unknown
): Promise<ContentWorkItemSalesBriefResponse> {
  return apiPost(
    "/api/content/work-items/sales-brief",
    ContentWorkItemSalesBriefResponseSchema,
    request
  );
}

export function postContentWorkItemDraftPackage(
  request: unknown
): Promise<ContentWorkItemDraftPackageResponse> {
  return apiPost(
    "/api/content/work-items/draft-package",
    ContentWorkItemDraftPackageResponseSchema,
    request
  );
}

export function postContentWorkItemHumanReview(
  request: unknown
): Promise<ContentWorkItemHumanReviewResponse> {
  return apiPost(
    "/api/content/work-items/human-review",
    ContentWorkItemHumanReviewResponseSchema,
    request
  );
}

export function postContentWorkItemWordPressDraftHandoff(
  request: unknown
): Promise<ContentWorkItemWordPressDraftHandoffResponse> {
  return apiPost(
    "/api/content/work-items/wordpress-draft-handoff",
    ContentWorkItemWordPressDraftHandoffResponseSchema,
    request
  );
}

export function postContentWorkItemMeasurementWindow(
  request: unknown
): Promise<ContentWorkItemMeasurementWindowResponse> {
  return apiPost(
    "/api/content/work-items/measurement-window",
    ContentWorkItemMeasurementWindowResponseSchema,
    request
  );
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

export function getOpportunities(): Promise<Opportunity[]> {
  return apiGet("/api/opportunities", z.array(OpportunitySchema));
}

export function getActions(): Promise<ActionObject[]> {
  return apiGet("/api/actions", z.array(ActionObjectSchema));
}

export function getAction(actionId: string): Promise<ActionObject> {
  return apiGet(`/api/actions/${encodeURIComponent(actionId)}`, ActionObjectSchema);
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

export function confirmAction(
  actionId: string,
  request: ActionConfirmRequest
): Promise<ActionConfirmResult> {
  return apiPost(`/api/actions/${actionId}/confirm`, ActionConfirmResultSchema, request);
}

export function impactCheckAction(
  actionId: string,
  request: ActionImpactCheckRequest
): Promise<ActionImpactCheckResult> {
  return apiPost(`/api/actions/${actionId}/impact-check`, ActionImpactCheckResultSchema, request);
}

export function getEvidence(): Promise<Evidence[]> {
  return apiGet("/api/evidence", z.array(EvidenceSchema));
}

export function getEvidenceById(evidenceId: string): Promise<Evidence> {
  return apiGet(`/api/evidence/${encodeURIComponent(evidenceId)}`, EvidenceSchema);
}

export function getWorkflows(): Promise<Workflow[]> {
  return apiGet("/api/workflows", z.array(WorkflowSchema));
}

export function getWorkflowRuns(): Promise<WorkflowRun[]> {
  return apiGet("/api/workflow-runs", z.array(WorkflowRunSchema));
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
  ActionConfirmResult,
  ActionImpactCheckResult,
  ActionPreviewCardViewModel,
  ActionPreviewResult,
  ActionReviewRequest,
  ActionReviewResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  AhrefsDiagnosticsResponse,
  CommandCenterResponse,
  ContentDiagnosticsResponse,
  ContentPreflightResponse,
  ContentWorkItemDraftPackageResponse,
  ContentWorkItemHumanReviewResponse,
  ContentWorkItemMeasurementWindowResponse,
  ContentWorkItemPreflightResponse,
  ContentWorkItemSalesBriefResponse,
  ContentWorkItemWordPressDraftHandoffResponse,
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
  Opportunity,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun
};
