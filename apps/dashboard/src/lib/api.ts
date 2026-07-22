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
  ContentCodexSectionProposalRequestSchema,
  ContentCodexSectionProposalResponseSchema,
  ContentInitialDraftRequestSchema,
  ContentInitialDraftResponseSchema,
  ContentSemanticReviewRequestSchema,
  ContentSemanticReviewResponseSchema,
  ContentDiagnosticsResponseSchema,
  ContentDecisionContextSchema,
  ContentDraftRevisionConflictSchema,
  ContentDraftRevisionReviewRequestSchema,
  ContentDraftRevisionReviewResponseSchema,
  ContentDraftRevisionSaveRequestSchema,
  ContentDraftRevisionSaveResponseSchema,
  ContentKnowledgeCardsResponseSchema,
  ContentPlanningProposalRequestSchema,
  ContentPlanningProposalResponseSchema,
  ContentPlanningReviewConflictSchema,
  ContentPlanningReviewRequestSchema,
  ContentPlanningReviewResponseSchema,
  ContentServiceProfileResponseSchema,
  ContentPreflightResponseSchema,
  ContentOpportunityEnrichmentResponseSchema,
  ContentInventoryCatalogResponseSchema,
  ContentInventoryMaterialResponseSchema,
  ContentInventoryBindingResponseSchema,
  ContentOperatorContextSchema,
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
  ContentWorkItemSalesBriefRequestSchema,
  ContentWorkItemSalesBriefResponseSchema,
  ContentWorkItemSnapshotAuditRequestSchema,
  ContentWorkItemSnapshotHumanReviewRequestSchema,
  ContentWorkItemSnapshotResponseSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema,
  ContentWorkItemWordPressDraftExecutionRequestSchema,
  ContentWorkItemWordPressDraftExecutionResponseSchema,
  ContentWorkItemWordPressDraftHandoffRequestSchema,
  ContentWorkItemWordPressDraftHandoffResponseSchema,
  ContentWordPressDraftActivationPacketResponseSchema,
  ContentWordPressDraftWriteReadinessResponseSchema,
  ContentWordPressExistingDraftUpdateReadinessResponseSchema,
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
  WordPressAuthoringProfileSchema,
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
  type ContentCodexSectionProposalRequest,
  type ContentCodexSectionProposalResponse,
  type ContentInitialDraftRequest,
  type ContentInitialDraftResponse,
  type ContentSemanticReview,
  type ContentSemanticReviewRequest,
  type ContentSemanticReviewResponse,
  type ContentDiagnosticsResponse,
  type ContentDecisionContext,
  type ContentDraftRevision,
  type ContentDraftRevisionBinding,
  type ContentDraftRevisionConflict,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReviewRequest,
  type ContentDraftRevisionReviewResponse,
  type ContentDraftRevisionSaveRequest,
  type ContentDraftRevisionSaveResponse,
  type ContentDraftRevisionSection,
  type ContentFreshnessAssessment,
  type ContentClaimLedger,
  type ContentKnowledgeCardsResponse,
  type ContentPlanningProposalRequest,
  type ContentPlanningProposal,
  type ContentPlanningProposalResponse,
  type ContentPlanningReviewConflict,
  type ContentPlanningReviewRequest,
  type ContentPlanningReviewResponse,
  type ContentPlanningWorkspace,
  type ContentServiceProfileResponse,
  type ContentPreflightResponse,
  type ContentOpportunityEnrichment,
  type ContentOpportunityEnrichmentResponse,
  type ContentInventoryCatalogResponse,
  type ContentInventoryMaterialResponse,
  type ContentInventoryBindingResponse,
  type ContentOperatorContext,
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
  type ContentWorkItemSalesBriefRequest,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemSnapshotAuditRequest,
  type ContentWorkItemSnapshotHumanReviewRequest,
  type ContentWorkItemSnapshotResponse,
  type ContentWorkItemServiceCandidate,
  type ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
  type ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentWorkItemWordPressDraftHandoffRequest,
  type ContentWorkItemWordPressDraftHandoffResponse,
  type ContentWordPressDraftActivationPacketResponse,
  type ContentWordPressDraftWriteReadinessResponse,
  type ContentWordPressExistingDraftUpdateReadinessResponse,
  type ContentWorkItemWorkflowSnapshotResponse,
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
  type WordPressAuthoringProfile
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

export function getWordPressAuthoringProfile(): Promise<WordPressAuthoringProfile> {
  return apiGet("/api/content/wordpress/authoring-profile", WordPressAuthoringProfileSchema);
}

export function getContentWordPressDraftWriteReadiness(): Promise<
  ContentWordPressDraftWriteReadinessResponse
> {
  return apiGet(
    "/api/content/wordpress/draft-write-readiness",
    ContentWordPressDraftWriteReadinessResponseSchema
  );
}

export function getContentWordPressExistingDraftUpdateReadiness(
  workItemId?: string | null
): Promise<ContentWordPressExistingDraftUpdateReadinessResponse> {
  const query = workItemId ? `?work_item_id=${encodeURIComponent(workItemId)}` : "";
  return apiGet(
    `/api/content/wordpress/existing-draft-update-readiness${query}`,
    ContentWordPressExistingDraftUpdateReadinessResponseSchema
  );
}

export function getContentWordPressDraftActivationPacket(
  workItemId?: string | null
): Promise<
  ContentWordPressDraftActivationPacketResponse
> {
  const query = workItemId ? `?work_item_id=${encodeURIComponent(workItemId)}` : "";
  return apiGet(
    `/api/content/wordpress/draft-activation-packet${query}`,
    ContentWordPressDraftActivationPacketResponseSchema
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

export function getContentPreflight(): Promise<ContentPreflightResponse> {
  return apiGet("/api/content/preflight", ContentPreflightResponseSchema);
}

export function getContentKnowledgeCards(): Promise<ContentKnowledgeCardsResponse> {
  return apiGet("/api/content/knowledge-cards", ContentKnowledgeCardsResponseSchema);
}

export function getContentServiceProfile(): Promise<ContentServiceProfileResponse> {
  return apiGet("/api/content/service-profile", ContentServiceProfileResponseSchema);
}

export function getContentOperatorContext(): Promise<ContentOperatorContext> {
  return apiGet("/api/content/operator-context", ContentOperatorContextSchema);
}

export function getContentWorkItemQueue(workItemId?: string): Promise<ContentWorkItemQueueResponse> {
  const query = workItemId ? `?work_item_id=${encodeURIComponent(workItemId)}` : "";
  return apiGet(`/api/content/work-items/queue${query}`, ContentWorkItemQueueResponseSchema);
}

export function getContentWorkItemDecisionContext(
  workItemId: string
): Promise<ContentDecisionContext> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/decision-context`,
    ContentDecisionContextSchema
  );
}

export function getContentInventoryCatalog(): Promise<ContentInventoryCatalogResponse> {
  return apiGet("/api/content/inventory/catalog", ContentInventoryCatalogResponseSchema);
}

export function getContentInventoryMaterial(url: string): Promise<ContentInventoryMaterialResponse> {
  return apiGet(
    `/api/content/inventory/material?url=${encodeURIComponent(url)}`,
    ContentInventoryMaterialResponseSchema
  );
}

export function postContentInventoryBinding(url: string): Promise<ContentInventoryBindingResponse> {
  return apiPost(
    "/api/content/inventory/bind",
    ContentInventoryBindingResponseSchema,
    { url }
  );
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

export function saveContentWorkItemDraftRevision(
  request: ContentDraftRevisionSaveRequest,
  workItemId: string
): Promise<ContentDraftRevisionSaveResponse | ContentDraftRevisionConflict> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions`;
  return apiPostWithConflict(
    path,
    ContentDraftRevisionSaveResponseSchema,
    ContentDraftRevisionConflictSchema,
    ContentDraftRevisionSaveRequestSchema.parse(request)
  );
}

export function saveContentWorkItemPlanningReview(
  request: ContentPlanningReviewRequest,
  workItemId: string
): Promise<ContentPlanningReviewResponse | ContentPlanningReviewConflict> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/planning-review`;
  return apiPostWithConflict(
    path,
    ContentPlanningReviewResponseSchema,
    ContentPlanningReviewConflictSchema,
    ContentPlanningReviewRequestSchema.parse(request)
  );
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

export function postContentWorkItemCodexSectionProposal(
  request: ContentCodexSectionProposalRequest,
  workItemId: string,
  baseRevisionId: string
): Promise<ContentCodexSectionProposalResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(baseRevisionId)}/codex-proposal`;
  const parsedRequest = ContentCodexSectionProposalRequestSchema.parse(request);
  return apiPostWithConflict(
    path,
    ContentCodexSectionProposalResponseSchema,
    ContentCodexSectionProposalResponseSchema,
    parsedRequest,
    CODEX_PROPOSAL_TIMEOUT_MS
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

export function getContentWorkItemSemanticReview(
  workItemId: string,
  revisionId: string
): Promise<ContentSemanticReviewResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/semantic-review`,
    ContentSemanticReviewResponseSchema
  );
}

export function postContentWorkItemSemanticReview(
  request: ContentSemanticReviewRequest,
  workItemId: string,
  revisionId: string
): Promise<ContentSemanticReviewResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/semantic-review`;
  return apiPostWithConflict(
    path,
    ContentSemanticReviewResponseSchema,
    ContentSemanticReviewResponseSchema,
    ContentSemanticReviewRequestSchema.parse(request),
    CODEX_PROPOSAL_TIMEOUT_MS
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

export function postContentWorkItemWordPressAuthoringPayloadPreview(
  request: ContentWorkItemWordPressAuthoringPayloadPreviewRequest
): Promise<ContentWorkItemWordPressAuthoringPayloadPreviewResponse> {
  return apiPost(
    "/api/content/work-items/wordpress-authoring-payload-preview",
    ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema,
    ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema.parse(request)
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
  ContentDecisionContext,
  ContentCodexSectionProposalRequest,
  ContentCodexSectionProposalResponse,
  ContentInitialDraftRequest,
  ContentInitialDraftResponse,
  ContentSemanticReview,
  ContentSemanticReviewRequest,
  ContentSemanticReviewResponse,
  ContentDraftRevision,
  ContentDraftRevisionBinding,
  ContentDraftRevisionConflict,
  ContentDraftRevisionDecision,
  ContentDraftRevisionReviewRequest,
  ContentDraftRevisionReviewResponse,
  ContentDraftRevisionSaveRequest,
  ContentDraftRevisionSaveResponse,
  ContentDraftRevisionSection,
  ContentFreshnessAssessment,
  ContentClaimLedger,
  ContentKnowledgeCardsResponse,
  ContentPlanningProposalRequest,
  ContentPlanningProposal,
  ContentPlanningProposalResponse,
  ContentPlanningReviewConflict,
  ContentPlanningReviewRequest,
  ContentPlanningReviewResponse,
  ContentPlanningWorkspace,
  ContentServiceProfileResponse,
  ContentPreflightResponse,
  ContentOpportunityEnrichment,
  ContentOpportunityEnrichmentResponse,
  ContentInventoryCatalogResponse,
  ContentInventoryMaterialResponse,
  ContentInventoryBindingResponse,
  ContentOperatorContext,
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
  ContentWorkItemSalesBriefRequest,
  ContentWorkItemSalesBriefResponse,
  ContentWorkItemSnapshotAuditRequest,
  ContentWorkItemSnapshotHumanReviewRequest,
  ContentWorkItemSnapshotResponse,
  ContentWorkItemServiceCandidate,
  ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  ContentWorkItemWordPressDraftExecutionRequest,
  ContentWorkItemWordPressDraftExecutionResponse,
  ContentWorkItemWordPressDraftHandoffRequest,
  ContentWorkItemWordPressDraftHandoffResponse,
  ContentWorkItemWorkflowSnapshotResponse,
  ContentWordPressDraftActivationPacketResponse,
  ContentWordPressDraftWriteReadinessResponse,
  ContentWordPressExistingDraftUpdateReadinessResponse,
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
  WorkOrder,
  WordPressAuthoringProfile
};
