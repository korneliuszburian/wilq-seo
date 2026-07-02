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
  ContentKnowledgeCardsResponseSchema,
  ContentServiceProfileResponseSchema,
  ContentPreflightResponseSchema,
  ContentOpportunityEnrichmentResponseSchema,
  ContentWorkItemDraftPackageRequestSchema,
  ContentWorkItemDraftPackageResponseSchema,
  ContentWorkItemHumanReviewRequestSchema,
  ContentWorkItemHumanReviewResponseSchema,
  ContentWorkItemMeasurementWindowRequestSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  ContentWorkItemPreflightRequestSchema,
  ContentWorkItemPreflightResponseSchema,
  ContentWorkItemQualityReviewRequestSchema,
  ContentWorkItemQualityReviewResponseSchema,
  ContentWorkItemQueueResponseSchema,
  ContentWorkItemRevisionPlanRequestSchema,
  ContentWorkItemRevisionPlanResponseSchema,
  ContentWorkItemSalesBriefRequestSchema,
  ContentWorkItemSalesBriefResponseSchema,
  ContentWorkItemStructuredDraftGenerationRequestSchema,
  ContentWorkItemStructuredDraftGenerationResponseSchema,
  ContentWorkItemStructuredDraftPreviewRequestSchema,
  ContentWorkItemStructuredDraftPreviewResponseSchema,
  ContentWorkItemStructuredDraftRuntimeRequestSchema,
  ContentWorkItemStructuredDraftRuntimeResponseSchema,
  ContentWorkItemSnapshotAuditRequestSchema,
  ContentWorkItemSnapshotHumanReviewRequestSchema,
  ContentWorkItemSnapshotResponseSchema,
  ContentWorkItemWordPressDraftExecutionRequestSchema,
  ContentWorkItemWordPressDraftExecutionResponseSchema,
  ContentWorkItemWordPressDraftHandoffRequestSchema,
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
  type ContentClaimLedger,
  type ContentKnowledgeCardsResponse,
  type ContentServiceProfileResponse,
  type ContentPreflightResponse,
  type ContentOpportunityEnrichment,
  type ContentOpportunityEnrichmentResponse,
  type ContentWorkItemDraftPackageRequest,
  type ContentWorkItemDraftPackageResponse,
  type ContentWorkItemHumanReviewRequest,
  type ContentWorkItemHumanReviewResponse,
  type ContentWorkItemMeasurementWindowRequest,
  type ContentWorkItemMeasurementWindowResponse,
  type ContentWorkItemPreflightRequest,
  type ContentWorkItemPreflightResponse,
  type ContentWorkItemQualityReviewRequest,
  type ContentWorkItemQualityReviewResponse,
  type ContentWorkItemQueueCandidate,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemRevisionPlanRequest,
  type ContentWorkItemRevisionPlanResponse,
  type ContentWorkItemSalesBriefRequest,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemStructuredDraftGenerationRequest,
  type ContentWorkItemStructuredDraftGenerationResponse,
  type ContentWorkItemStructuredDraftPreviewRequest,
  type ContentWorkItemStructuredDraftPreviewResponse,
  type ContentWorkItemStructuredDraftRuntimeRequest,
  type ContentWorkItemStructuredDraftRuntimeResponse,
  type ContentWorkItemSnapshotAuditRequest,
  type ContentWorkItemSnapshotHumanReviewRequest,
  type ContentWorkItemSnapshotResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentWorkItemWordPressDraftHandoffRequest,
  type ContentWorkItemWordPressDraftHandoffResponse,
  type ContentWorkItemWorkflowSnapshotResponse,
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
const API_TIMEOUT_MS = 30_000;

type ApiSchema<T extends z.ZodTypeAny> = T;

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (typeof AbortController === "undefined") {
    return fetch(`${API_BASE}${path}`, init);
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function apiErrorMessage(response: Response, path: string): Promise<string> {
  let detail = "";
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const rawDetail = (body as { detail?: unknown }).detail;
      const serializedDetail = JSON.stringify(rawDetail);
      detail =
        typeof rawDetail === "string"
          ? rawDetail
          : (serializedDetail ?? String(rawDetail)).slice(0, 500);
    }
  } catch {
    detail = "";
  }
  const suffix = detail ? `: ${detail}` : "";
  return `API request failed: ${path} (${response.status})${suffix}`;
}

async function apiGet<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>
): Promise<z.infer<T>> {
  const response = await apiFetch(path);
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return schema.parse(await response.json());
}

async function apiPost<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>,
  body?: unknown
): Promise<z.infer<T>> {
  const response = await apiFetch(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
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

export function getContentKnowledgeCards(): Promise<ContentKnowledgeCardsResponse> {
  return apiGet("/api/content/knowledge-cards", ContentKnowledgeCardsResponseSchema);
}

export function getContentServiceProfile(): Promise<ContentServiceProfileResponse> {
  return apiGet("/api/content/service-profile", ContentServiceProfileResponseSchema);
}

export function getContentWorkItemQueue(): Promise<ContentWorkItemQueueResponse> {
  return apiGet("/api/content/work-items/queue", ContentWorkItemQueueResponseSchema);
}

export function getContentWorkItemSnapshot(
  workItemId?: string
): Promise<ContentWorkItemSnapshotResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/snapshot"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/snapshot`;
  return apiGet(
    path,
    ContentWorkItemSnapshotResponseSchema
  );
}

export function getContentWorkItemEnrichment(
  workItemId: string
): Promise<ContentOpportunityEnrichmentResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/enrichment`,
    ContentOpportunityEnrichmentResponseSchema
  );
}

export function postContentWorkItemPreflight(
  request: ContentWorkItemPreflightRequest
): Promise<ContentWorkItemPreflightResponse> {
  return apiPost(
    "/api/content/work-items/preflight",
    ContentWorkItemPreflightResponseSchema,
    ContentWorkItemPreflightRequestSchema.parse(request)
  );
}

export function postContentWorkItemSalesBrief(
  request: ContentWorkItemSalesBriefRequest
): Promise<ContentWorkItemSalesBriefResponse> {
  return apiPost(
    "/api/content/work-items/sales-brief",
    ContentWorkItemSalesBriefResponseSchema,
    ContentWorkItemSalesBriefRequestSchema.parse(request)
  );
}

export function postContentWorkItemDraftPackage(
  request: ContentWorkItemDraftPackageRequest
): Promise<ContentWorkItemDraftPackageResponse> {
  return apiPost(
    "/api/content/work-items/draft-package",
    ContentWorkItemDraftPackageResponseSchema,
    ContentWorkItemDraftPackageRequestSchema.parse(request)
  );
}

export function postContentWorkItemStructuredDraftGeneration(
  request: ContentWorkItemStructuredDraftGenerationRequest
): Promise<ContentWorkItemStructuredDraftGenerationResponse> {
  return apiPost(
    "/api/content/work-items/structured-draft-generation",
    ContentWorkItemStructuredDraftGenerationResponseSchema,
    ContentWorkItemStructuredDraftGenerationRequestSchema.parse(request)
  );
}

export function postContentWorkItemStructuredDraftRuntime(
  request: ContentWorkItemStructuredDraftRuntimeRequest
): Promise<ContentWorkItemStructuredDraftRuntimeResponse> {
  return apiPost(
    "/api/content/work-items/structured-draft-runtime",
    ContentWorkItemStructuredDraftRuntimeResponseSchema,
    ContentWorkItemStructuredDraftRuntimeRequestSchema.parse(request)
  );
}

export function postContentWorkItemStructuredDraftPreview(
  request: ContentWorkItemStructuredDraftPreviewRequest,
  workItemId?: string
): Promise<ContentWorkItemStructuredDraftPreviewResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/structured-draft-preview"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/structured-draft-preview`;
  return apiPost(
    path,
    ContentWorkItemStructuredDraftPreviewResponseSchema,
    ContentWorkItemStructuredDraftPreviewRequestSchema.parse(request)
  );
}

export function postContentWorkItemQualityReview(
  request: ContentWorkItemQualityReviewRequest,
  workItemId?: string
): Promise<ContentWorkItemQualityReviewResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/quality-review"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/quality-review`;
  return apiPost(
    path,
    ContentWorkItemQualityReviewResponseSchema,
    ContentWorkItemQualityReviewRequestSchema.parse(request)
  );
}

export function postContentWorkItemRevisionPlan(
  request: ContentWorkItemRevisionPlanRequest,
  workItemId?: string
): Promise<ContentWorkItemRevisionPlanResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/revision-plan"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/revision-plan`;
  return apiPost(
    path,
    ContentWorkItemRevisionPlanResponseSchema,
    ContentWorkItemRevisionPlanRequestSchema.parse(request)
  );
}

export function postContentWorkItemHumanReview(
  request: ContentWorkItemHumanReviewRequest
): Promise<ContentWorkItemHumanReviewResponse> {
  return apiPost(
    "/api/content/work-items/human-review",
    ContentWorkItemHumanReviewResponseSchema,
    ContentWorkItemHumanReviewRequestSchema.parse(request)
  );
}

export function saveContentWorkItemSnapshotHumanReview(
  request: ContentWorkItemSnapshotHumanReviewRequest,
  workItemId?: string
): Promise<ContentWorkItemHumanReviewResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/snapshot/human-review"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/human-review`;
  return apiPost(
    path,
    ContentWorkItemHumanReviewResponseSchema,
    ContentWorkItemSnapshotHumanReviewRequestSchema.parse(request)
  );
}

export function saveContentWorkItemSnapshotAudit(
  request: ContentWorkItemSnapshotAuditRequest,
  workItemId?: string
): Promise<ContentWorkItemWordPressDraftHandoffResponse> {
  const path =
    workItemId === undefined
      ? "/api/content/work-items/snapshot/audit"
      : `/api/content/work-items/${encodeURIComponent(workItemId)}/audit`;
  return apiPost(
    path,
    ContentWorkItemWordPressDraftHandoffResponseSchema,
    ContentWorkItemSnapshotAuditRequestSchema.parse(request)
  );
}

export function postContentWorkItemWordPressDraftHandoff(
  request: ContentWorkItemWordPressDraftHandoffRequest
): Promise<ContentWorkItemWordPressDraftHandoffResponse> {
  return apiPost(
    "/api/content/work-items/wordpress-draft-handoff",
    ContentWorkItemWordPressDraftHandoffResponseSchema,
    ContentWorkItemWordPressDraftHandoffRequestSchema.parse(request)
  );
}

export function postContentWorkItemWordPressDraftExecution(
  request: ContentWorkItemWordPressDraftExecutionRequest
): Promise<ContentWorkItemWordPressDraftExecutionResponse> {
  return apiPost(
    "/api/content/work-items/wordpress-draft-execution",
    ContentWorkItemWordPressDraftExecutionResponseSchema,
    ContentWorkItemWordPressDraftExecutionRequestSchema.parse(request)
  );
}

export function postContentWorkItemMeasurementWindow(
  request: ContentWorkItemMeasurementWindowRequest
): Promise<ContentWorkItemMeasurementWindowResponse> {
  return apiPost(
    "/api/content/work-items/measurement-window",
    ContentWorkItemMeasurementWindowResponseSchema,
    ContentWorkItemMeasurementWindowRequestSchema.parse(request)
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

export function actionApiPath(actionId: string, suffix = ""): string {
  return `/api/actions/${encodeURIComponent(actionId)}${suffix}`;
}

export function getAction(actionId: string): Promise<ActionObject> {
  return apiGet(actionApiPath(actionId), ActionObjectSchema);
}

export function validateAction(actionId: string): Promise<ActionValidationResult> {
  return apiPost(actionApiPath(actionId, "/validate"), ActionValidationResultSchema);
}

export function previewAction(actionId: string): Promise<ActionPreviewResult> {
  return apiPost(actionApiPath(actionId, "/preview"), ActionPreviewResultSchema, {
    requested_by: "operator_local_dashboard",
    max_items: 8
  });
}

export function reviewAction(
  actionId: string,
  request: ActionReviewRequest
): Promise<ActionReviewResult> {
  return apiPost(actionApiPath(actionId, "/review"), ActionReviewResultSchema, request);
}

export function confirmAction(
  actionId: string,
  request: ActionConfirmRequest
): Promise<ActionConfirmResult> {
  return apiPost(actionApiPath(actionId, "/confirm"), ActionConfirmResultSchema, request);
}

export function impactCheckAction(
  actionId: string,
  request: ActionImpactCheckRequest
): Promise<ActionImpactCheckResult> {
  return apiPost(actionApiPath(actionId, "/impact-check"), ActionImpactCheckResultSchema, request);
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
  ContentClaimLedger,
  ContentKnowledgeCardsResponse,
  ContentServiceProfileResponse,
  ContentPreflightResponse,
  ContentOpportunityEnrichment,
  ContentOpportunityEnrichmentResponse,
  ContentWorkItemDraftPackageRequest,
  ContentWorkItemDraftPackageResponse,
  ContentWorkItemHumanReviewRequest,
  ContentWorkItemHumanReviewResponse,
  ContentWorkItemMeasurementWindowRequest,
  ContentWorkItemMeasurementWindowResponse,
  ContentWorkItemPreflightRequest,
  ContentWorkItemPreflightResponse,
  ContentWorkItemQualityReviewRequest,
  ContentWorkItemQualityReviewResponse,
  ContentWorkItemQueueCandidate,
  ContentWorkItemQueueResponse,
  ContentWorkItemRevisionPlanRequest,
  ContentWorkItemRevisionPlanResponse,
  ContentWorkItemSalesBriefRequest,
  ContentWorkItemSalesBriefResponse,
  ContentWorkItemSnapshotAuditRequest,
  ContentWorkItemSnapshotHumanReviewRequest,
  ContentWorkItemSnapshotResponse,
  ContentWorkItemStructuredDraftGenerationRequest,
  ContentWorkItemStructuredDraftGenerationResponse,
  ContentWorkItemStructuredDraftPreviewRequest,
  ContentWorkItemStructuredDraftPreviewResponse,
  ContentWorkItemStructuredDraftRuntimeRequest,
  ContentWorkItemStructuredDraftRuntimeResponse,
  ContentWorkItemWordPressDraftExecutionRequest,
  ContentWorkItemWordPressDraftExecutionResponse,
  ContentWorkItemWordPressDraftHandoffRequest,
  ContentWorkItemWordPressDraftHandoffResponse,
  ContentWorkItemWorkflowSnapshotResponse,
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
