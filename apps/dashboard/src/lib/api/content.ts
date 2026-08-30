import {
  ActionObjectSchema,
  ContentDiagnosticsResponseSchema,
  ContentDraftRevisionConflictSchema,
  ContentDraftRevisionReviewRequestSchema,
  ContentDraftRevisionReviewResponseSchema,
  ContentDraftRevisionSaveResponseSchema,
  ContentEditorialIntegrityReportSchema,
  ContentInitialDraftConflictResponseSchema,
  ContentInitialDraftGenerationResponseSchema,
  ContentInitialDraftRequestSchema,
  ContentWorkItemInitialDraftRequestSchema,
  ContentWorkItemInitialDraftResponseSchema,
  ContentInventoryCatalogResponseSchema,
  ContentNewPageBriefInputSchema,
  ContentNewPageBriefWorkspaceSchema,
  ContentNewPageCanonicalDocumentWorkspaceSchema,
  ContentNewPageDeliveryReadinessSchema,
  ContentNewPageDraftActionCommandSchema,
  ContentNewPageFoundationCommandSchema,
  ContentNewPageFoundationResultSchema,
  ContentNewPagePlanningProposalRequestSchema,
  ContentNewPagePlanningProposalWorkspaceSchema,
  ContentNewPageRevisionReviewConflictSchema,
  ContentNewPageRevisionReviewResponseSchema,
  ContentNewPageTopicRecommendationsSchema,
  ContentOfficialSourceLineageRebaseRequestSchema,
  ContentOperatorContextSchema,
  ContentPlanningProposalRequestSchema,
  ContentPlanningProposalResponseSchema,
  ContentPublicDeploymentConfirmationCommandSchema,
  ContentPublicDeploymentConfirmationResponseSchema,
  ContentPublicDeploymentReadResponseSchema,
  ContentRegulatorySourceFactProposalResponseSchema,
  ContentRegulatorySourceFactProposalReviewCommandSchema,
  ContentRegulatorySourceReviewCommandSchema,
  ContentRegulatorySourceReviewConflictSchema,
  ContentRegulatorySourceReviewSchema,
  ContentRegulatorySourceSnapshotReadResponseSchema,
  ContentRevisionHtmlPackageResponseSchema,
  ContentRevisionRepairProposalRequestSchema,
  ContentRevisionRepairProposalResponseSchema,
  ContentSelectedWorkspaceSchema,
  ContentSemanticReviewResponseSchema,
  ContentServiceProfileResponseSchema,
  ContentTargetDiscoverySchema,
  ContentTargetDraftActionCommandSchema,
  ContentTargetDraftPreviewSchema,
  ContentTargetMappingConfirmationCommandSchema,
  ContentTargetMappingConfirmationResultSchema,
  ContentTargetMappingPreviewSchema,
  ContentWorkflowEntryResponseSchema,
  ContentWorkItemLearningProposalRequestSchema,
  ContentWorkItemLearningProposalResponseSchema,
  ContentWorkItemMeasurementOutcomeRequestSchema,
  ContentWorkItemMeasurementOutcomeResponseSchema,
  ContentMeasurementReadResponseSchema,
  ContentWorkItemMeasurementWindowRequestSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  type ActionObject,
  type ContentDiagnosticsResponse,
  type ContentDraftRevisionConflict,
  type ContentDraftRevisionReviewRequest,
  type ContentDraftRevisionReviewResponse,
  type ContentDraftRevisionSaveResponse,
  type ContentEditorialIntegrityReport,
  type ContentInitialDraftConflictResponse,
  type ContentInitialDraftGenerationResponse,
  type ContentInitialDraftRequest,
  type ContentWorkItemInitialDraftRequest,
  type ContentWorkItemInitialDraftResponse,
  type ContentInventoryCatalogResponse,
  type ContentNewPageBriefInput,
  type ContentNewPageBriefWorkspace,
  type ContentNewPageCanonicalDocumentWorkspace,
  type ContentNewPageDeliveryReadiness,
  type ContentNewPageDraftActionCommand,
  type ContentNewPageFoundationCommand,
  type ContentNewPageFoundationResult,
  type ContentNewPagePlanningProposalRequest,
  type ContentNewPagePlanningProposalWorkspace,
  type ContentNewPageRevisionReviewConflict,
  type ContentNewPageRevisionReviewResponse,
  type ContentNewPageTopicRecommendations,
  type ContentOfficialSourceLineageRebaseRequest,
  type ContentOperatorContext,
  type ContentPlanningProposalRequest,
  type ContentPlanningProposalResponse,
  type ContentPublicDeploymentConfirmationCommand,
  type ContentPublicDeploymentConfirmationResponse,
  type ContentPublicDeploymentReadResponse,
  type ContentRegulatorySourceFactProposalResponse,
  type ContentRegulatorySourceFactProposalReviewCommand,
  type ContentRegulatorySourceReview,
  type ContentRegulatorySourceReviewCommand,
  type ContentRegulatorySourceReviewConflict,
  type ContentRegulatorySourceSnapshotReadResponse,
  type ContentRevisionHtmlPackageResponse,
  type ContentRevisionRepairProposalRequest,
  type ContentRevisionRepairProposalResponse,
  type ContentSelectedWorkspace,
  type ContentSemanticReviewResponse,
  type ContentServiceProfileResponse,
  type ContentTargetDiscovery,
  type ContentTargetDraftActionCommand,
  type ContentTargetDraftPreview,
  type ContentTargetMappingConfirmationCommand,
  type ContentTargetMappingConfirmationResult,
  type ContentTargetMappingPreview,
  type ContentWorkflowEntryResponse,
  type ContentWorkItemLearningProposalRequest,
  type ContentWorkItemLearningProposalResponse,
  type ContentWorkItemMeasurementOutcomeRequest,
  type ContentWorkItemMeasurementOutcomeResponse,
  type ContentMeasurementReadResponse,
  type ContentWorkItemMeasurementWindowRequest,
  type ContentWorkItemMeasurementWindowResponse
} from "@wilq/shared-schemas";

import {
  CODEX_PROPOSAL_TIMEOUT_MS,
  apiGet,
  apiPost,
  apiPostWithConflict
} from "./common";

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

export function getContentWorkItemMeasurement(
  workItemId: string,
  revisionId: string
): Promise<ContentMeasurementReadResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/measurement`,
    ContentMeasurementReadResponseSchema
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
): Promise<ContentInitialDraftGenerationResponse> {
  return apiPost(
    `/api/content/new-page-briefs/${encodeURIComponent(briefId)}/initial-draft`,
    ContentInitialDraftGenerationResponseSchema,
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

export function postContentRegulatorySourceFactProposal(
  candidateId: string
): Promise<ContentRegulatorySourceFactProposalResponse> {
  return apiPost(
    `/api/content/regulatory-source-candidates/${encodeURIComponent(candidateId)}/fact-proposal`,
    ContentRegulatorySourceFactProposalResponseSchema,
    {}
  );
}

export function getContentRegulatorySourceFactProposal(
  candidateId: string
): Promise<ContentRegulatorySourceFactProposalResponse> {
  return apiGet(
    `/api/content/regulatory-source-candidates/${encodeURIComponent(candidateId)}/fact-proposal`,
    ContentRegulatorySourceFactProposalResponseSchema
  );
}

export function postContentRegulatorySourceFactProposalReview(
  proposalId: string,
  request: ContentRegulatorySourceFactProposalReviewCommand
): Promise<ContentRegulatorySourceReview | ContentRegulatorySourceReviewConflict> {
  return apiPostWithConflict(
    `/api/content/regulatory-source-fact-proposals/${encodeURIComponent(proposalId)}/review`,
    ContentRegulatorySourceReviewSchema,
    ContentRegulatorySourceReviewConflictSchema,
    ContentRegulatorySourceFactProposalReviewCommandSchema.parse(request)
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

export function postContentWorkItemOfficialSourceLineageRebase(
  request: ContentOfficialSourceLineageRebaseRequest,
  workItemId: string,
  revisionId: string
): Promise<ContentDraftRevisionSaveResponse | ContentDraftRevisionConflict> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(revisionId)}/official-source-lineage-rebase`;
  return apiPostWithConflict(
    path,
    ContentDraftRevisionSaveResponseSchema,
    ContentDraftRevisionConflictSchema,
    ContentOfficialSourceLineageRebaseRequestSchema.parse(request)
  );
}

export function postContentWorkItemRevisionRepairProposal(
  request: ContentRevisionRepairProposalRequest,
  workItemId: string,
  baseRevisionId: string
): Promise<ContentRevisionRepairProposalResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/draft-revisions/${encodeURIComponent(baseRevisionId)}/repair-proposal`;
  return apiPostWithConflict(
    path,
    ContentRevisionRepairProposalResponseSchema,
    ContentRevisionRepairProposalResponseSchema,
    ContentRevisionRepairProposalRequestSchema.parse(request),
    CODEX_PROPOSAL_TIMEOUT_MS
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
  request: ContentWorkItemInitialDraftRequest,
  workItemId: string
): Promise<ContentWorkItemInitialDraftResponse | ContentInitialDraftConflictResponse> {
  const path = `/api/content/work-items/${encodeURIComponent(workItemId)}/initial-draft`;
  return apiPostWithConflict(
    path,
    ContentWorkItemInitialDraftResponseSchema,
    ContentInitialDraftConflictResponseSchema,
    ContentWorkItemInitialDraftRequestSchema.parse(request),
    CODEX_PROPOSAL_TIMEOUT_MS
  );
}

export function getContentWorkItemInitialDraft(
  workItemId: string
): Promise<ContentWorkItemInitialDraftResponse> {
  return apiGet(
    `/api/content/work-items/${encodeURIComponent(workItemId)}/initial-draft`,
    ContentWorkItemInitialDraftResponseSchema
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
