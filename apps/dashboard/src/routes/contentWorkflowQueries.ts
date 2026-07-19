import { useMemo } from "react";
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

import {
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getContentWorkItemEnrichment,
  getContentInventoryCatalog,
  getContentServiceProfile,
  getContentOperatorContext,
  getContentWorkItemQueue,
  getKnowledgeSourceMaterialReadiness,
  getKnowledgeSourceMaterials,
  getWordPressAuthoringProfile,
  type ContentWorkItemQueueCandidate,
  type ContentWorkItemQueueResponse,
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

export function useContentWorkflowQueries(selectedWorkItemId: string | null) {
  const queryClient = useQueryClient();
  const queueCatalog = useQuery({
    queryKey: ["content-workflow", "queue", "catalog"],
    queryFn: () => getContentWorkItemQueue(),
    staleTime: 30_000
  });
  const selectedQueue = useQuery({
    queryKey: ["content-workflow", "queue", "selected", selectedWorkItemId],
    queryFn: () => getContentWorkItemQueue(selectedWorkItemId ?? undefined),
    enabled: Boolean(selectedWorkItemId),
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
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS
  });
  const serviceProfile = useQuery({
    queryKey: ["content-workflow", "service-profile"],
    queryFn: getContentServiceProfile,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS
  });
  const knowledgeReadiness = useQuery({
    queryKey: ["content-workflow", "knowledge-source-material-readiness"],
    queryFn: getKnowledgeSourceMaterialReadiness,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS
  });
  const knowledgeMaterials = useQuery({
    queryKey: ["content-workflow", "knowledge-source-materials"],
    queryFn: getKnowledgeSourceMaterials,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS
  });
  const operatorContext = useQuery({
    queryKey: ["content-workflow", "operator-context"],
    queryFn: getContentOperatorContext,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS
  });
  const requestedCandidate = mergedQueue.data?.candidates.find(
    (candidate) => candidate.work_item_id === selectedWorkItemId
  );
  const activeWorkItemId = requestedCandidate?.work_item_id ?? null;
  const selectedCandidate =
    mergedQueue.data?.candidates.find((candidate) => candidate.work_item_id === activeWorkItemId) ?? null;
  const selectedCandidateBlocked = selectedCandidate?.recommended_mode === "block";
  const workflow = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId],
    queryFn: () => loadContentWorkflowSnapshot(activeWorkItemId ?? undefined),
    staleTime: 10_000,
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked)
  });
  const enrichment = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "enrichment"],
    queryFn: () => getContentWorkItemEnrichment(activeWorkItemId ?? ""),
    staleTime: 10_000,
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked && workflow.data)
  });
  const authoringProfile = useQuery({
    queryKey: ["content-workflow", "wordpress-authoring-profile"],
    queryFn: getWordPressAuthoringProfile,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(workflow.data)
  });
  const draftWriteReadiness = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-write-readiness"],
    queryFn: getContentWordPressDraftWriteReadiness,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(workflow.data)
  });
  const draftActivationPacket = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-activation-packet", activeWorkItemId],
    queryFn: () => getContentWordPressDraftActivationPacket(activeWorkItemId),
    staleTime: 10_000,
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked && workflow.data)
  });

  return {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    draftWriteReadiness,
    enrichment,
    inventory,
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
