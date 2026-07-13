import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  getWordPressAuthoringProfile,
  type ContentWorkItemQueueCandidate,
  type ContentWorkItemQueueResponse,
  type ContentOpportunityEnrichmentResponse,
  type ContentWordPressDraftActivationPacketResponse,
  type ContentWordPressDraftWriteReadinessResponse,
  type WordPressAuthoringProfile
} from "../lib/api";
import { loadContentWorkflowSnapshot, type ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

export type ContentWorkItemQueueQuery = UseQueryResult<ContentWorkItemQueueResponse, Error>;
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

export function useContentWorkflowQueries(selectedWorkItemId: string | null) {
  const queue = useQuery({
    queryKey: ["content-workflow", "queue"],
    queryFn: getContentWorkItemQueue
  });
  const activeWorkItemId =
    selectedWorkItemId ?? (queue.data ? defaultSelectedWorkItemId(queue.data) : null);
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
    queue,
    selectedCandidate,
    workflow
  };
}

function defaultSelectedWorkItemId(queue: ContentWorkItemQueueResponse) {
  return (
    queue.candidates.find((candidate) => candidate.recommended_mode !== "block")?.work_item_id ??
    queue.candidates.find(
      (candidate) => candidate.source_public_url || candidate.final_canonical_url
    )?.work_item_id ??
    queue.candidates[0]?.work_item_id ??
    null
  );
}

export type { ContentWorkItemQueueCandidate };
