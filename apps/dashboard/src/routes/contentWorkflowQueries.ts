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
  const queue = useQuery({
    queryKey: ["content-workflow", "queue", selectedWorkItemId],
    queryFn: () => getContentWorkItemQueue(selectedWorkItemId ?? undefined),
    // Keep the already loaded decision queue visible while the selected
    // candidate's API-owned response is fetched. This prevents a click from
    // looking like a route reset; the selected queue request still replaces
    // the placeholder with its exact server response.
    placeholderData: selectedWorkItemId
      ? () =>
          queryClient.getQueryData<ContentWorkItemQueueResponse>([
            "content-workflow",
            "queue",
            null
          ])
      : undefined
  });
  const inventory = useQuery({
    queryKey: ["content-workflow", "inventory-catalog"],
    queryFn: getContentInventoryCatalog
  });
  const serviceProfile = useQuery({
    queryKey: ["content-workflow", "service-profile"],
    queryFn: getContentServiceProfile
  });
  const knowledgeReadiness = useQuery({
    queryKey: ["content-workflow", "knowledge-source-material-readiness"],
    queryFn: getKnowledgeSourceMaterialReadiness
  });
  const knowledgeMaterials = useQuery({
    queryKey: ["content-workflow", "knowledge-source-materials"],
    queryFn: getKnowledgeSourceMaterials
  });
  const operatorContext = useQuery({
    queryKey: ["content-workflow", "operator-context"],
    queryFn: getContentOperatorContext
  });
  const requestedCandidate = queue.data?.candidates.find(
    (candidate) => candidate.work_item_id === selectedWorkItemId
  );
  const activeWorkItemId = requestedCandidate?.work_item_id ?? null;
  const selectedCandidate =
    queue.data?.candidates.find((candidate) => candidate.work_item_id === activeWorkItemId) ?? null;
  const selectedCandidateBlocked = selectedCandidate?.recommended_mode === "block";
  const workflow = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId],
    queryFn: () => loadContentWorkflowSnapshot(activeWorkItemId ?? undefined),
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked)
  });
  const enrichment = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "enrichment"],
    queryFn: () => getContentWorkItemEnrichment(activeWorkItemId ?? ""),
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked && workflow.data)
  });
  const authoringProfile = useQuery({
    queryKey: ["content-workflow", "wordpress-authoring-profile"],
    queryFn: getWordPressAuthoringProfile,
    enabled: Boolean(workflow.data)
  });
  const draftWriteReadiness = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-write-readiness"],
    queryFn: getContentWordPressDraftWriteReadiness,
    enabled: Boolean(workflow.data)
  });
  const draftActivationPacket = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-activation-packet", activeWorkItemId],
    queryFn: () => getContentWordPressDraftActivationPacket(activeWorkItemId),
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
    queue,
    selectedCandidate,
    workflow
  };
}

export type { ContentWorkItemQueueCandidate };
