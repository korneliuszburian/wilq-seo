import {
  ActionObjectSchema,
  ActionConfirmResultSchema,
  ActionImpactCheckResultSchema,
  ActionApplyResultSchema,
  ActionApplyRequestSchema,
  ActionMutationReadinessResponseSchema,
  ActionMutationReadinessSummaryResponseSchema,
  ActionPreviewRequestSchema,
  ActionPreviewResultSchema,
  ActionReviewResultSchema,
  ActionValidationResultSchema,
  AdsDiagnosticsResponseSchema,
  AhrefsDiagnosticsResponseSchema,
  CommandCenterResponseSchema,
  ContentInitialDraftRequestSchema,
  ContentInitialDraftResponseSchema,
  ContentDiagnosticsResponseSchema,
  ContentSelectedWorkspaceSchema,
  ContentTargetDiscoverySchema,
  ContentTargetMappingConfirmationCommandSchema,
  ContentTargetMappingConfirmationResultSchema,
  ContentTargetDraftPreviewSchema,
  ContentTargetDraftActionCommandSchema,
  ContentNewPageDeliveryReadinessSchema,
  ContentNewPageDraftActionCommandSchema,
  ContentTargetMappingPreviewSchema,
  ContentPublicDeploymentConfirmationCommandSchema,
  ContentPublicDeploymentConfirmationResponseSchema,
  ContentPublicDeploymentReadResponseSchema,
  ContentWorkflowEntryResponseSchema,
  ContentNewPageBriefInputSchema,
  ContentNewPageTopicRecommendationsSchema,
  ContentNewPageBriefWorkspaceSchema,
  ContentNewPageFoundationCommandSchema,
  ContentNewPageFoundationResultSchema,
  ContentNewPagePlanningProposalRequestSchema,
  ContentNewPagePlanningProposalWorkspaceSchema,
  ContentNewPageCanonicalDocumentWorkspaceSchema,
  ContentNewPageRevisionReviewConflictSchema,
  ContentNewPageRevisionReviewResponseSchema,
  ContentDraftRevisionConflictSchema,
  ContentDraftRevisionReviewRequestSchema,
  ContentDraftRevisionReviewResponseSchema,
  ContentEditorialIntegrityReportSchema,
  ContentRevisionHtmlPackageResponseSchema,
  ContentSemanticReviewResponseSchema,
  ContentPlanningProposalRequestSchema,
  ContentPlanningProposalResponseSchema,
  ContentRegulatorySourceReviewCommandSchema,
  ContentRegulatorySourceReviewConflictSchema,
  ContentRegulatorySourceReviewSchema,
  ContentRegulatorySourceSnapshotReadResponseSchema,
  ContentServiceProfileResponseSchema,
  ContentInventoryCatalogResponseSchema,
  ContentOperatorContextSchema,
  ContentWorkItemMeasurementWindowRequestSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  ContentWorkItemMeasurementOutcomeRequestSchema,
  ContentWorkItemMeasurementOutcomeResponseSchema,
  ContentWorkItemLearningProposalRequestSchema,
  ContentWorkItemLearningProposalResponseSchema,
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  DemandGenReadinessContractSchema,
  EvidenceSchema,
  Ga4DiagnosticsResponseSchema,
  KnowledgeCardSchema,
  KnowledgeSourceFactViewSchema,
  KnowledgeSourceMaterialViewSchema,
  KnowledgeSourceMaterialReadinessSchema,
  KnowledgeOperatingMapResponseSchema,
  LocaloDiagnosticsResponseSchema,
  MarketingBriefSchema,
  MarketingPlaybookSchema,
  MerchantDiagnosticsResponseSchema,
  OpportunitySchema,
  SocialHistoryInventorySchema,
  SocialPublisherContextPackSchema,
  SocialReuseProposalResponseSchema,
  SocialReuseProposalListResponseSchema,
  SocialReuseReviewRequestSchema,
  SocialReuseReviewResponseSchema,
  SocialReuseRevisionRequestSchema,
  TacticalQueueResponseSchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type ActionConfirmRequest,
  type ActionConfirmResult,
  type ActionImpactCheckRequest,
  type ActionImpactCheckResult,
  type ActionApplyRequest,
  type ActionApplyResult,
  type ActionMutationReadinessResponse,
  type ActionMutationReadinessSummaryResponse,
  type ActionPreviewRequest,
  type ActionPreviewCardViewModel,
  type ActionPreviewResult,
  type ActionReviewRequest,
  type ActionReviewResult,
  type ActionValidationResult,
  type AdsDiagnosticsResponse,
  type AhrefsDiagnosticsResponse,
  type CommandCenterResponse,
  type ContentInitialDraftRequest,
  type ContentInitialDraftResponse,
  type ContentDiagnosticsResponse,
  type ContentDocumentWorkspace,
  type ContentSelectedWorkspace,
  type ContentTargetDiscovery,
  type ContentTargetMappingConfirmationCommand,
  type ContentTargetMappingConfirmationResult,
  type ContentTargetMappingPreview,
  type ContentTargetDraftPreview,
  type ContentTargetDraftActionCommand,
  type ContentNewPageDeliveryReadiness,
  type ContentNewPageDraftActionCommand,
  type ContentPublicDeploymentConfirmationCommand,
  type ContentPublicDeploymentConfirmationResponse,
  type ContentPublicDeploymentReadResponse,
  type ContentWorkflowEntryResponse,
  type ContentNewPageBriefInput,
  type ContentNewPageTopicCandidate,
  type ContentNewPageTopicRecommendations,
  type ContentNewPageBriefWorkspace,
  type ContentNewPageFoundationCommand,
  type ContentNewPageFoundationResult,
  type ContentNewPagePlanningProposalRequest,
  type ContentNewPagePlanningProposalWorkspace,
  type ContentNewPageCanonicalDocumentWorkspace,
  type ContentNewPageRevisionReviewConflict,
  type ContentNewPageRevisionReviewResponse,
  type ContentDraftRevision,
  type ContentDraftRevisionBinding,
  type ContentDraftRevisionConflict,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReview,
  type ContentDraftRevisionReviewRequest,
  type ContentDraftRevisionReviewResponse,
  type ContentEditorialIntegrityReport,
  type ContentRevisionHtmlPackageResponse,
  type ContentSemanticReviewResponse,
  type ContentDraftRevisionSection,
  type ContentFreshnessAssessment,
  type ContentClaimLedger,
  type ContentPlanningProposalRequest,
  type ContentPlanningProposal,
  type ContentPlanningProposalResponse,
  type ContentRegulatorySourceReviewCommand,
  type ContentRegulatorySourceReview,
  type ContentRegulatorySourceReviewConflict,
  type ContentRegulatorySourceSnapshotReadResponse,
  type ContentPlanningWorkspace,
  type ContentServiceProfileResponse,
  type ContentInventoryCatalogResponse,
  type ContentOperatorContext,
  type ContentWorkItemMeasurementWindowRequest,
  type ContentWorkItemMeasurementWindowResponse,
  type ContentWorkItemMeasurementOutcomeRequest,
  type ContentWorkItemMeasurementOutcomeResponse,
  type ContentWorkItemLearningProposalRequest,
  type ContentWorkItemLearningProposalResponse,
  type ConnectorRefreshRun,
  type ConnectorStatus,
  type DemandGenReadinessContract,
  type Evidence,
  type ExpertRule,
  type Ga4DiagnosticsResponse,
  type KnowledgeCard,
  type KnowledgeSourceFactView,
  type KnowledgeSourceMaterialView,
  type KnowledgeSourceMaterialReadiness,
  type KnowledgeOperatingMapResponse,
  type LocaloDiagnosticsResponse,
  type MarketingBrief,
  type MarketingBriefItem,
  type MarketingPlaybook,
  type MerchantDiagnosticsResponse,
  type MetricFact,
  type Opportunity,
  type SocialDraftContext,
  type SocialHistoryInventory,
  type SocialPublisherContextPack,
  type SocialReuseProposalResponse,
  type SocialReuseProposalListResponse,
  type SocialReuseReviewRequest,
  type SocialReuseReviewResponse,
  type SocialReuseRevisionRequest,
  type TacticalQueueResponse,
  type Workflow,
  type WorkflowRun,
  type WorkOrder,
} from "@wilq/shared-schemas";
import { z } from "zod";

const API_BASE = import.meta.env.VITE_WILQ_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_TIMEOUT_MS = 30_000;
const CODEX_PROPOSAL_TIMEOUT_MS = 135_000;

type ApiSchema<T extends z.ZodTypeAny> = T;

async function apiFetch(
  path: string,
  init?: RequestInit,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<Response> {
  if (typeof AbortController === "undefined") {
    return fetch(`${API_BASE}${path}`, init);
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
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

async function apiPostWithDetailConflict<T extends z.ZodTypeAny>(
  path: string,
  schema: ApiSchema<T>,
  body: unknown
): Promise<z.infer<T>> {
  const response = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (response.status === 409) {
    const payload: unknown = await response.json();
    const detail = z.object({ detail: z.unknown() }).parse(payload).detail;
    return schema.parse(detail);
  }
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return schema.parse(await response.json());
}

async function apiPostWithConflict<
  TSuccess extends z.ZodTypeAny,
  TConflict extends z.ZodTypeAny
>(
  path: string,
  successSchema: ApiSchema<TSuccess>,
  conflictSchema: ApiSchema<TConflict>,
  body: unknown,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<z.infer<TSuccess> | z.infer<TConflict>> {
  const response = await apiFetch(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    },
    timeoutMs
  );
  if (response.status === 409) {
    return conflictSchema.parse(await response.json());
  }
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, path));
  }
  return successSchema.parse(await response.json());
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

export function getSocialPublisherContextPack(): Promise<SocialPublisherContextPack> {
  return apiPost(
    "/api/codex/context-pack",
    SocialPublisherContextPackSchema,
    { skill: "wilq-social-publisher" }
  );
}

export function getSocialHistoryInventory(): Promise<SocialHistoryInventory> {
  return apiGet("/api/social/history-inventory", SocialHistoryInventorySchema);
}

export function getSocialReuseProposals(
  workItemId?: string | null
): Promise<SocialReuseProposalListResponse> {
  const query = workItemId ? `?work_item_id=${encodeURIComponent(workItemId)}` : "";
  return apiGet(
    `/api/social/reuse-proposals${query}`,
    SocialReuseProposalListResponseSchema
  );
}

export function reviewSocialReuseProposal(
  proposalId: string,
  request: SocialReuseReviewRequest
): Promise<SocialReuseReviewResponse> {
  return apiPostWithConflict(
    `/api/social/reuse-proposals/${encodeURIComponent(proposalId)}/review`,
    SocialReuseReviewResponseSchema,
    SocialReuseReviewResponseSchema,
    SocialReuseReviewRequestSchema.parse(request)
  );
}

export function reviseSocialReuseProposal(
  proposalId: string,
  request: SocialReuseRevisionRequest
): Promise<SocialReuseProposalResponse> {
  return apiPostWithConflict(
    `/api/social/reuse-proposals/${encodeURIComponent(proposalId)}/revise`,
    SocialReuseProposalResponseSchema,
    SocialReuseProposalResponseSchema,
    SocialReuseRevisionRequestSchema.parse(request)
  );
}

export function getActionMutationReadiness(
  actionId: string
): Promise<ActionMutationReadinessResponse> {
  return apiGet(
    `/api/actions/${encodeURIComponent(actionId)}/mutation-readiness`,
    ActionMutationReadinessResponseSchema
  );
}

export function getActionsMutationReadiness(): Promise<ActionMutationReadinessSummaryResponse> {
  return apiGet(
    "/api/actions/mutation-readiness",
    ActionMutationReadinessSummaryResponseSchema
  );
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

export function getContentServiceProfile(): Promise<ContentServiceProfileResponse> {
  return apiGet("/api/content/service-profile", ContentServiceProfileResponseSchema);
}

export function getContentOperatorContext(): Promise<ContentOperatorContext> {
  return apiGet("/api/content/operator-context", ContentOperatorContextSchema);
}

export function getContentSelectedWorkspace(
  workItemId: string
): Promise<ContentSelectedWorkspace> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/selected-workspace`,
    ContentSelectedWorkspaceSchema
  );
}

export function getContentWorkItemTargetDiscovery(
  workItemId: string
): Promise<ContentTargetDiscovery> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/target-discovery`,
    ContentTargetDiscoverySchema
  );
}

export function getContentRevisionTargetMapping(
  workItemId: string,
  revisionId: string
): Promise<ContentTargetMappingPreview> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/target-mapping`,
    ContentTargetMappingPreviewSchema
  );
}

export function postContentRevisionTargetMappingConfirmation(
  workItemId: string,
  revisionId: string,
  request: ContentTargetMappingConfirmationCommand
): Promise<ContentTargetMappingConfirmationResult> {
  return apiPost(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/target-mapping/confirmation`,
    ContentTargetMappingConfirmationResultSchema,
    ContentTargetMappingConfirmationCommandSchema.parse(request)
  );
}

export function getContentRevisionTargetDraftPreview(
  workItemId: string,
  revisionId: string
): Promise<ContentTargetDraftPreview> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/target-mapping/draft-preview`,
    ContentTargetDraftPreviewSchema
  );
}

export function postContentRevisionTargetDraftAction(
  workItemId: string,
  revisionId: string,
  request: ContentTargetDraftActionCommand
): Promise<ActionObject> {
  return apiPost(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/target-mapping/draft-action`,
    ActionObjectSchema,
    ContentTargetDraftActionCommandSchema.parse(request)
  );
}

export function getContentRevisionPublicDeployment(
  workItemId: string,
  revisionId: string
): Promise<ContentPublicDeploymentReadResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/public-deployment`,
    ContentPublicDeploymentReadResponseSchema
  );
}

export function postContentRevisionPublicDeployment(
  workItemId: string,
  revisionId: string,
  request: ContentPublicDeploymentConfirmationCommand
): Promise<ContentPublicDeploymentConfirmationResponse> {
  return apiPost(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/public-deployments`,
    ContentPublicDeploymentConfirmationResponseSchema,
    ContentPublicDeploymentConfirmationCommandSchema.parse(request)
  );
}

export function getContentWorkflowEntry(search?: string): Promise<ContentWorkflowEntryResponse> {
  const query = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
  return apiGet(`/api/content/workflow-entry${query}`, ContentWorkflowEntryResponseSchema);
}

export function createContentNewPageBrief(
  request: ContentNewPageBriefInput
): Promise<ContentNewPageBriefWorkspace> {
  return apiPost(
    "/api/content/new-page-briefs",
    ContentNewPageBriefWorkspaceSchema,
    ContentNewPageBriefInputSchema.parse(request)
  );
}

export function getContentNewPageTopicRecommendations(): Promise<ContentNewPageTopicRecommendations> {
  return apiGet(
    "/api/content/new-page-topics",
    ContentNewPageTopicRecommendationsSchema
  );
}

export function getContentNewPageBriefWorkspace(
  briefId: string
): Promise<ContentNewPageBriefWorkspace> {
  return apiGet(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}`,
    ContentNewPageBriefWorkspaceSchema
  );
}

export function createContentNewPageFoundation(
  briefId: string,
  request: ContentNewPageFoundationCommand
): Promise<ContentNewPageFoundationResult> {
  return apiPost(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/planning-foundation`,
    ContentNewPageFoundationResultSchema,
    ContentNewPageFoundationCommandSchema.parse(request)
  );
}

export function getContentNewPagePlanningProposal(
  briefId: string
): Promise<ContentNewPagePlanningProposalWorkspace> {
  return apiGet(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/planning-proposal`,
    ContentNewPagePlanningProposalWorkspaceSchema
  );
}

export function createContentNewPagePlanningProposal(
  briefId: string,
  request: ContentNewPagePlanningProposalRequest
): Promise<ContentNewPagePlanningProposalWorkspace> {
  return apiPost(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/planning-proposal`,
    ContentNewPagePlanningProposalWorkspaceSchema,
    ContentNewPagePlanningProposalRequestSchema.parse(request)
  );
}

export function getContentNewPageCanonicalDocument(
  briefId: string
): Promise<ContentNewPageCanonicalDocumentWorkspace> {
  return apiGet(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/canonical-document`,
    ContentNewPageCanonicalDocumentWorkspaceSchema
  );
}

export function getContentNewPageDeliveryReadiness(
  briefId: string
): Promise<ContentNewPageDeliveryReadiness> {
  return apiGet(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/delivery-readiness`,
    ContentNewPageDeliveryReadinessSchema
  );
}

export function createContentNewPageDeliveryAction(
  briefId: string,
  request: ContentNewPageDraftActionCommand
): Promise<ActionObject> {
  return apiPost(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/delivery-action`,
    ActionObjectSchema,
    ContentNewPageDraftActionCommandSchema.parse(request)
  );
}

export function createContentNewPageInitialDraft(
  briefId: string,
  request: ContentInitialDraftRequest
): Promise<ContentInitialDraftResponse> {
  return apiPost(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/initial-draft`,
    ContentInitialDraftResponseSchema,
    ContentInitialDraftRequestSchema.parse(request)
  );
}

export function reviewContentNewPageRevision(
  briefId: string,
  revisionId: string,
  request: ContentDraftRevisionReviewRequest
): Promise<ContentNewPageRevisionReviewResponse | ContentNewPageRevisionReviewConflict> {
  return apiPostWithConflict(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/draft-revisions/${encodeURIComponent(revisionId)}/review`,
    ContentNewPageRevisionReviewResponseSchema,
    ContentNewPageRevisionReviewConflictSchema,
    ContentDraftRevisionReviewRequestSchema.parse(request)
  );
}

export function getContentInventoryCatalog(): Promise<ContentInventoryCatalogResponse> {
  return apiGet("/api/content/inventory/catalog", ContentInventoryCatalogResponseSchema);
}

export function getContentWorkItemPlanningProposal(
  workItemId: string
): Promise<ContentPlanningProposalResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/planning-proposals`,
    ContentPlanningProposalResponseSchema
  );
}

export function postContentWorkItemPlanningProposal(
  request: ContentPlanningProposalRequest,
  workItemId: string
): Promise<ContentPlanningProposalResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/planning-proposals`;
  return apiPostWithConflict(
    path,
    ContentPlanningProposalResponseSchema,
    ContentPlanningProposalResponseSchema,
    ContentPlanningProposalRequestSchema.parse(request)
  );
}

export function getContentRegulatorySourceSnapshot(
  candidateId: string
): Promise<ContentRegulatorySourceSnapshotReadResponse> {
  return apiGet(
    `/api/content/regulatory-source-candidates/${encodeURIComponent(candidateId)}/snapshot`,
    ContentRegulatorySourceSnapshotReadResponseSchema
  );
}

export function postContentRegulatorySourceReview(
  request: ContentRegulatorySourceReviewCommand
): Promise<ContentRegulatorySourceReview | ContentRegulatorySourceReviewConflict> {
  return apiPostWithConflict(
    "/api/content/regulatory-source-reviews",
    ContentRegulatorySourceReviewSchema,
    ContentRegulatorySourceReviewConflictSchema,
    ContentRegulatorySourceReviewCommandSchema.parse(request)
  );
}

export function saveContentWorkItemDraftRevisionReview(
  request: ContentDraftRevisionReviewRequest,
  workItemId: string,
  revisionId: string
): Promise<ContentDraftRevisionReviewResponse | ContentDraftRevisionConflict> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/review`;
  return apiPostWithConflict(
    path,
    ContentDraftRevisionReviewResponseSchema,
    ContentDraftRevisionConflictSchema,
    ContentDraftRevisionReviewRequestSchema.parse(request)
  );
}

export function getContentWorkItemRevisionHtmlPackage(
  workItemId: string,
  revisionId: string
): Promise<ContentRevisionHtmlPackageResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/html-package`,
    ContentRevisionHtmlPackageResponseSchema
  );
}

export function getContentWorkItemEditorialIntegrity(
  workItemId: string,
  revisionId: string
): Promise<ContentEditorialIntegrityReport> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/editorial-integrity`,
    ContentEditorialIntegrityReportSchema
  );
}

export function getContentWorkItemSemanticReview(
  workItemId: string,
  revisionId: string
): Promise<ContentSemanticReviewResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/semantic-review`,
    ContentSemanticReviewResponseSchema
  );
}

export function postContentWorkItemInitialDraft(
  request: ContentInitialDraftRequest,
  workItemId: string
): Promise<ContentInitialDraftResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/initial-draft`;
  return apiPostWithConflict(
    path,
    ContentInitialDraftResponseSchema,
    ContentInitialDraftResponseSchema,
    ContentInitialDraftRequestSchema.parse(request),
    CODEX_PROPOSAL_TIMEOUT_MS
  );
}

export function getContentWorkItemInitialDraft(
  workItemId: string
): Promise<ContentInitialDraftResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/initial-draft`,
    ContentInitialDraftResponseSchema
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

export function postContentWorkItemMeasurementOutcome(
  request: ContentWorkItemMeasurementOutcomeRequest
): Promise<ContentWorkItemMeasurementOutcomeResponse> {
  return apiPost(
    "/api/content/work-items/measurement-outcome",
    ContentWorkItemMeasurementOutcomeResponseSchema,
    ContentWorkItemMeasurementOutcomeRequestSchema.parse(request)
  );
}

export function postContentWorkItemLearningProposal(
  request: ContentWorkItemLearningProposalRequest
): Promise<ContentWorkItemLearningProposalResponse> {
  return apiPost(
    "/api/content/work-items/learning-proposal",
    ContentWorkItemLearningProposalResponseSchema,
    ContentWorkItemLearningProposalRequestSchema.parse(request)
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

export function previewAction(
  actionId: string,
  request: ActionPreviewRequest = {
    requested_by: "operator_local_dashboard",
    max_items: 8
  }
): Promise<ActionPreviewResult> {
  return apiPost(
    actionApiPath(actionId, "/preview"),
    ActionPreviewResultSchema,
    ActionPreviewRequestSchema.parse(request)
  );
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

export function applyAction(
  actionId: string,
  request: ActionApplyRequest
): Promise<ActionApplyResult> {
  return apiPostWithDetailConflict(
    actionApiPath(actionId, "/apply"),
    ActionApplyResultSchema,
    ActionApplyRequestSchema.parse(request)
  );
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

export function getKnowledgeSourceFacts(): Promise<KnowledgeSourceFactView[]> {
  return apiGet("/api/knowledge/source-facts", z.array(KnowledgeSourceFactViewSchema));
}

export function getKnowledgeSourceMaterials(): Promise<KnowledgeSourceMaterialView[]> {
  return apiGet("/api/knowledge/source-materials", z.array(KnowledgeSourceMaterialViewSchema));
}

export function getKnowledgeSourceMaterialReadiness(): Promise<KnowledgeSourceMaterialReadiness> {
  return apiGet(
    "/api/knowledge/source-materials/readiness",
    KnowledgeSourceMaterialReadinessSchema
  );
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
  ActionApplyRequest,
  ActionApplyResult,
  ActionImpactCheckResult,
  ActionPreviewCardViewModel,
  ActionPreviewRequest,
  ActionPreviewResult,
  ActionReviewRequest,
  ActionReviewResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  AhrefsDiagnosticsResponse,
  CommandCenterResponse,
  ContentDiagnosticsResponse,
  ContentDocumentWorkspace,
  ContentSelectedWorkspace,
  ContentTargetDiscovery,
  ContentTargetMappingConfirmationCommand,
  ContentTargetMappingConfirmationResult,
  ContentTargetMappingPreview,
  ContentTargetDraftPreview,
  ContentTargetDraftActionCommand,
  ContentNewPageDeliveryReadiness,
  ContentNewPageDraftActionCommand,
  ContentPublicDeploymentConfirmationCommand,
  ContentPublicDeploymentConfirmationResponse,
  ContentPublicDeploymentReadResponse,
  ContentWorkflowEntryResponse,
  ContentNewPageBriefInput,
  ContentNewPageTopicCandidate,
  ContentNewPageTopicRecommendations,
  ContentNewPageBriefWorkspace,
  ContentNewPageFoundationCommand,
  ContentNewPageFoundationResult,
  ContentNewPagePlanningProposalRequest,
  ContentNewPagePlanningProposalWorkspace,
  ContentNewPageCanonicalDocumentWorkspace,
  ContentInitialDraftRequest,
  ContentInitialDraftResponse,
  ContentDraftRevision,
  ContentDraftRevisionBinding,
  ContentDraftRevisionConflict,
  ContentDraftRevisionDecision,
  ContentDraftRevisionReview,
  ContentDraftRevisionReviewRequest,
  ContentDraftRevisionReviewResponse,
  ContentEditorialIntegrityReport,
  ContentRevisionHtmlPackageResponse,
  ContentSemanticReviewResponse,
  ContentDraftRevisionSection,
  ContentFreshnessAssessment,
  ContentClaimLedger,
  ContentPlanningProposalRequest,
  ContentPlanningProposal,
  ContentPlanningProposalResponse,
  ContentPlanningWorkspace,
  ContentServiceProfileResponse,
  ContentInventoryCatalogResponse,
  ContentOperatorContext,
  ContentWorkItemMeasurementWindowRequest,
  ContentWorkItemMeasurementWindowResponse,
  ContentWorkItemMeasurementOutcomeRequest,
  ContentWorkItemMeasurementOutcomeResponse,
  ContentWorkItemLearningProposalRequest,
  ContentWorkItemLearningProposalResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  DemandGenReadinessContract,
  Evidence,
  ExpertRule,
  Ga4DiagnosticsResponse,
  KnowledgeCard,
  KnowledgeSourceFactView,
  KnowledgeSourceMaterialView,
  KnowledgeSourceMaterialReadiness,
  KnowledgeOperatingMapResponse,
  LocaloDiagnosticsResponse,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MerchantDiagnosticsResponse,
  MetricFact,
  Opportunity,
  SocialDraftContext,
  SocialHistoryInventory,
  SocialPublisherContextPack,
  SocialReuseProposalListResponse,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun,
  WorkOrder
};
