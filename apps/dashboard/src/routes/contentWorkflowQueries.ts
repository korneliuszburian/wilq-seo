import { useMemo } from "react";
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

import {
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getContentWorkItemDecisionContext,
  getContentWorkItemDocumentWorkspace,
  getContentWorkItemTargetDiscovery,
  getContentRevisionTargetMapping,
  getContentWorkItemInitialDraft,
  getContentWorkItemEnrichment,
  getContentWorkflowEntry,
  getContentInventoryCatalog,
  getContentServiceProfile,
  getContentOperatorContext,
  getContentWorkItemQueue,
  getKnowledgeSourceMaterialReadiness,
  getKnowledgeSourceMaterials,
  getWordPressAuthoringProfile,
  type ContentWorkItemQueueCandidate,
  type ContentWorkItemQueueResponse,
  type ContentDecisionContext,
  type ContentDocumentWorkspace,
  type ContentTargetDiscovery,
  type ContentTargetMappingPreview,
  type ContentWorkflowEntryResponse,
  type ContentInitialDraftResponse,
  type ContentInventoryCatalogResponse,
  type ContentServiceProfileResponse,
  type ContentOperatorContext,
  type ContentOpportunityEnrichmentResponse,
  type ContentWordPressDraftActivationPacketResponse,
  type ContentWordPressDraftWriteReadinessResponse,
  type KnowledgeSourceMaterialReadiness,
  type KnowledgeSourceMaterialView,
  type WordPressAuthoringProfile
} from "../lib/api";
import { loadContentWorkflowSnapshot, type ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

const READ_ONLY_WORKFLOW_STALE_TIME_MS = 30_000;

export type ContentWorkItemQueueQuery = UseQueryResult<ContentWorkItemQueueResponse, Error>;
export type ContentDecisionContextQuery = UseQueryResult<ContentDecisionContext, Error>;
export type ContentDocumentWorkspaceQuery = UseQueryResult<ContentDocumentWorkspace, Error>;
export type ContentTargetDiscoveryQuery = UseQueryResult<ContentTargetDiscovery, Error>;
export type ContentTargetMappingPreviewQuery = UseQueryResult<ContentTargetMappingPreview, Error>;
export type ContentWorkflowEntryQuery = UseQueryResult<ContentWorkflowEntryResponse, Error>;
export type ContentInitialDraftQuery = UseQueryResult<ContentInitialDraftResponse, Error>;
export type ContentInventoryCatalogQuery = UseQueryResult<ContentInventoryCatalogResponse, Error>;
export type ContentServiceProfileQuery = UseQueryResult<ContentServiceProfileResponse, Error>;
export type ContentOperatorContextQuery = UseQueryResult<ContentOperatorContext, Error>;
export type ContentWorkflowSnapshotQuery = UseQueryResult<ContentWorkflowSnapshot, Error>;
export type ContentOpportunityEnrichmentQuery = UseQueryResult<
  ContentOpportunityEnrichmentResponse,
  Error
>;
export type WordPressAuthoringProfileQuery = UseQueryResult<WordPressAuthoringProfile, Error>;
export type WordPressDraftWriteReadinessQuery = UseQueryResult<
  ContentWordPressDraftWriteReadinessResponse,
  Error
>;
export type WordPressDraftActivationPacketQuery = UseQueryResult<
  ContentWordPressDraftActivationPacketResponse,
  Error
>;
export type KnowledgeSourceMaterialReadinessQuery = UseQueryResult<
  KnowledgeSourceMaterialReadiness,
  Error
>;
export type KnowledgeSourceMaterialsQuery = UseQueryResult<KnowledgeSourceMaterialView[], Error>;

export function contentDecisionContextQueryKey(workItemId: string | null) {
  return ["content-workflow", "work-item", workItemId, "decision-context"] as const;
}

export function useContentTargetDiscovery(
  workItemId: string,
  enabled: boolean
): ContentTargetDiscoveryQuery {
  return useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "target-discovery"],
    queryFn: () => getContentWorkItemTargetDiscovery(workItemId),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled
  });
}

export function useContentRevisionTargetMapping(
  workItemId: string,
  revisionId: string | null,
  enabled: boolean
): ContentTargetMappingPreviewQuery {
  return useQuery({
    queryKey: [
      "content-workflow",
      "work-item",
      workItemId,
      "draft-revisions",
      revisionId,
      "target-mapping"
    ],
    queryFn: () => getContentRevisionTargetMapping(workItemId, revisionId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(enabled && revisionId)
  });
}

export function useContentWorkflowQueries(
  selectedWorkItemId: string | null,
  textWorkspaceOpen = false,
  reviewOpen = false,
  browseInventory = false
) {
  const queryClient = useQueryClient();
  // Text is a direct, read-only document surface.  It does not need the
  // selection catalogue or supporting panels just to identify the URL already
  // present in the route.  Review deliberately keeps its richer exact-state
  // reads below.
  const directTextWorkspace = Boolean(selectedWorkItemId && textWorkspaceOpen && !reviewOpen);
  const selectedWorkflowRead = Boolean(selectedWorkItemId && !directTextWorkspace);
  const entry = useQuery({
    queryKey: ["content-workflow", "entry"],
    queryFn: () => getContentWorkflowEntry(),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: !selectedWorkItemId
  });
  const queueCatalog = useQuery({
    queryKey: ["content-workflow", "queue", "catalog"],
    queryFn: () => getContentWorkItemQueue(),
    staleTime: 30_000,
    enabled: selectedWorkflowRead
  });
  const selectedQueue = useQuery({
    queryKey: ["content-workflow", "queue", "selected", selectedWorkItemId],
    queryFn: () => getContentWorkItemQueue(selectedWorkItemId ?? undefined),
    enabled: selectedWorkflowRead,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    // The selected response is intentionally lightweight. It opens the page
    // quickly while the catalog query fills the picker with every available
    // page instead of replacing the catalog with one selected candidate.
    placeholderData: () =>
      queryClient.getQueryData<ContentWorkItemQueueResponse>([
        "content-workflow",
        "queue",
        "catalog"
      ])
  });
  const queueData = useMemo(
    () => mergeContentWorkItemQueueCatalog(queueCatalog.data, selectedQueue.data),
    [queueCatalog.data, selectedQueue.data]
  );
  const queue = (selectedWorkItemId ? selectedQueue : queueCatalog) as ContentWorkItemQueueQuery;
  const mergedQueue = {
    ...queue,
    data: queueData,
    error: queue.error ?? queueCatalog.error,
    isLoading: queue.isLoading && !queueData,
    isPending: queue.isPending && !queueData
  } as ContentWorkItemQueueQuery;
  const inventory = useQuery({
    queryKey: ["content-workflow", "inventory-catalog"],
    queryFn: getContentInventoryCatalog,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(selectedWorkflowRead || browseInventory)
  });
  const serviceProfile = useQuery({
    queryKey: ["content-workflow", "service-profile"],
    queryFn: getContentServiceProfile,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: selectedWorkflowRead
  });
  const knowledgeReadiness = useQuery({
    queryKey: ["content-workflow", "knowledge-source-material-readiness"],
    queryFn: getKnowledgeSourceMaterialReadiness,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: selectedWorkflowRead
  });
  const knowledgeMaterials = useQuery({
    queryKey: ["content-workflow", "knowledge-source-materials"],
    queryFn: getKnowledgeSourceMaterials,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: selectedWorkflowRead
  });
  const operatorContext = useQuery({
    queryKey: ["content-workflow", "operator-context"],
    queryFn: getContentOperatorContext,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: selectedWorkflowRead
  });
  const requestedCandidate = mergedQueue.data?.candidates.find(
    (candidate) => candidate.work_item_id === selectedWorkItemId
  );
  const activeWorkItemId = directTextWorkspace
    ? selectedWorkItemId
    : requestedCandidate?.work_item_id ?? null;
  const selectedCandidate =
    mergedQueue.data?.candidates.find((candidate) => candidate.work_item_id === activeWorkItemId) ?? null;
  const decisionContext = useQuery({
    queryKey: contentDecisionContextQueryKey(activeWorkItemId),
    queryFn: () => getContentWorkItemDecisionContext(activeWorkItemId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(
      activeWorkItemId &&
      selectedCandidate?.source_public_url &&
      (!textWorkspaceOpen || reviewOpen)
    )
  });
  const documentWorkspace = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "document-workspace"],
    queryFn: () => getContentWorkItemDocumentWorkspace(activeWorkItemId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(activeWorkItemId && textWorkspaceOpen)
  });
  const workflow = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId],
    queryFn: () => loadContentWorkflowSnapshot(activeWorkItemId ?? undefined),
    staleTime: 10_000,
    // Review is the one Text substate that needs the persisted, exact
    // revision-review binding after a reload. Text itself stays lean.
    enabled: Boolean(activeWorkItemId && reviewOpen)
  });
  const enrichment = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "enrichment"],
    queryFn: () => getContentWorkItemEnrichment(activeWorkItemId ?? ""),
    staleTime: 10_000,
    enabled: false
  });
  const authoringProfile = useQuery({
    queryKey: ["content-workflow", "wordpress-authoring-profile"],
    queryFn: getWordPressAuthoringProfile,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: false
  });
  const draftWriteReadiness = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-write-readiness"],
    queryFn: getContentWordPressDraftWriteReadiness,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: false
  });
  const draftActivationPacket = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-activation-packet", activeWorkItemId],
    queryFn: () => getContentWordPressDraftActivationPacket(activeWorkItemId),
    staleTime: 10_000,
    enabled: false
  });
  const initialDraft = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "initial-draft"],
    queryFn: () => getContentWorkItemInitialDraft(activeWorkItemId ?? ""),
    staleTime: 10_000,
    enabled: Boolean(activeWorkItemId && reviewOpen)
  });

  return {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    draftWriteReadiness,
    decisionContext,
    documentWorkspace,
    entry,
    enrichment,
    inventory,
    initialDraft,
    knowledgeReadiness,
    knowledgeMaterials,
    operatorContext,
    serviceProfile,
    queue: mergedQueue,
    selectedCandidate,
    workflow
  };
}

export function mergeContentWorkItemQueueCatalog(
  catalog: ContentWorkItemQueueResponse | undefined,
  selected: ContentWorkItemQueueResponse | undefined
): ContentWorkItemQueueResponse | undefined {
  if (!selected) return catalog;
  if (!catalog) return selected;
  const selectedCandidate = selected.candidates[0];
  const candidates = catalog.candidates.some(
    (candidate) => candidate.work_item_id === selectedCandidate?.work_item_id
  )
    ? catalog.candidates
    : selectedCandidate
      ? [...catalog.candidates, selectedCandidate]
      : catalog.candidates;
  return { ...catalog, candidates, candidate_count: candidates.length };
}

export type { ContentWorkItemQueueCandidate };
