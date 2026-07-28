import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getContentSelectedWorkspace,
  getContentWorkItemTargetDiscovery,
  getContentRevisionTargetMapping,
  getContentRevisionTargetDraftPreview,
  getContentWorkflowEntry,
  getContentInventoryCatalog,
  getContentOperatorContext,
  type ContentSelectedWorkspace,
  type ContentTargetDiscovery,
  type ContentTargetMappingPreview,
  type ContentTargetDraftPreview,
  type ContentWorkflowEntryResponse,
  type ContentInventoryCatalogResponse,
  type ContentOperatorContext,
} from "../lib/api";
const READ_ONLY_WORKFLOW_STALE_TIME_MS = 30_000;

// Retained for the inactive compatibility panel. Selected routes themselves
// deliberately do not consume this read as an identity authority.
export function contentDecisionContextQueryKey(workItemId: string) {
  return ["content-workflow", "work-item", workItemId, "decision-context"] as const;
}

export type ContentSelectedWorkspaceQuery = UseQueryResult<ContentSelectedWorkspace, Error>;
export type ContentTargetDiscoveryQuery = UseQueryResult<ContentTargetDiscovery, Error>;
export type ContentTargetMappingPreviewQuery = UseQueryResult<ContentTargetMappingPreview, Error>;
export type ContentTargetDraftPreviewQuery = UseQueryResult<ContentTargetDraftPreview, Error>;
export type ContentWorkflowEntryQuery = UseQueryResult<ContentWorkflowEntryResponse, Error>;
export type ContentInventoryCatalogQuery = UseQueryResult<ContentInventoryCatalogResponse, Error>;
export type ContentOperatorContextQuery = UseQueryResult<ContentOperatorContext, Error>;

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

export function useContentRevisionTargetDraftPreview(
  workItemId: string,
  revisionId: string | null,
  enabled: boolean
): ContentTargetDraftPreviewQuery {
  return useQuery({
    queryKey: [
      "content-workflow",
      "work-item",
      workItemId,
      "draft-revisions",
      revisionId,
      "target-mapping",
      "draft-preview"
    ],
    queryFn: () => getContentRevisionTargetDraftPreview(workItemId, revisionId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(enabled && revisionId)
  });
}

export function useContentWorkflowQueries(
  selectedWorkItemId: string | null,
  _reviewOpen = false,
  browseInventory = false
) {
  // A selected route owns its identity. Navigation catalogues are never an
  // authority for a deep-linked document or review state.
  const entry = useQuery({
    queryKey: ["content-workflow", "entry"],
    queryFn: () => getContentWorkflowEntry(),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: !selectedWorkItemId
  });
  const inventory = useQuery({
    queryKey: ["content-workflow", "inventory-catalog"],
    queryFn: getContentInventoryCatalog,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: browseInventory
  });
  const operatorContext = useQuery({
    queryKey: ["content-workflow", "operator-context"],
    queryFn: getContentOperatorContext,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    // Identity can be refreshed independently for a review save, but neither
    // its latency nor failure may replace the exact review workspace.
    enabled: Boolean(selectedWorkItemId && _reviewOpen)
  });
  const selectedWorkspace = useQuery({
    queryKey: ["content-workflow", "work-item", selectedWorkItemId, "selected-workspace"],
    queryFn: () => getContentSelectedWorkspace(selectedWorkItemId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(selectedWorkItemId)
  });

  return {
    selectedWorkspace,
    entry,
    inventory,
    operatorContext
  };
}
