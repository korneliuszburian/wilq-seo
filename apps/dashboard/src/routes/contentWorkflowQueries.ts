import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getContentSelectedWorkspace,
  getContentWorkItemPlanningProposal,
  getContentWorkItemTargetDiscovery,
  getContentRevisionTargetMapping,
  getContentRevisionTargetDraftPreview,
  getContentRevisionPublicDeployment,
  getContentWorkflowEntry,
  getContentDiagnostics,
  getContentInventoryCatalog,
  getContentOperatorContext,
  type ContentSelectedWorkspace,
  type ContentTargetDiscovery,
  type ContentTargetMappingPreview,
  type ContentTargetDraftPreview,
  type ContentPublicDeploymentReadResponse,
  type ContentWorkflowEntryResponse,
  type ContentDiagnosticsResponse,
  type ContentInventoryCatalogResponse,
  type ContentOperatorContext,
  type ContentPlanningProposalResponse,
} from "../lib/api";
const READ_ONLY_WORKFLOW_STALE_TIME_MS = 30_000;

export type ContentSelectedWorkspaceQuery = UseQueryResult<ContentSelectedWorkspace, Error>;
export type ContentTargetDiscoveryQuery = UseQueryResult<ContentTargetDiscovery, Error>;
export type ContentTargetMappingPreviewQuery = UseQueryResult<ContentTargetMappingPreview, Error>;
export type ContentTargetDraftPreviewQuery = UseQueryResult<ContentTargetDraftPreview, Error>;
export type ContentPublicDeploymentQuery = UseQueryResult<ContentPublicDeploymentReadResponse, Error>;
export type ContentWorkflowEntryQuery = UseQueryResult<ContentWorkflowEntryResponse, Error>;
export type ContentDiagnosticsQuery = UseQueryResult<ContentDiagnosticsResponse, Error>;
export type ContentInventoryCatalogQuery = UseQueryResult<ContentInventoryCatalogResponse, Error>;
export type ContentOperatorContextQuery = UseQueryResult<ContentOperatorContext, Error>;
export type ContentPlanningProposalQuery = UseQueryResult<ContentPlanningProposalResponse, Error>;

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

export function useContentRevisionPublicDeployment(
  workItemId: string,
  revisionId: string | null,
  enabled: boolean
): ContentPublicDeploymentQuery {
  return useQuery({
    queryKey: [
      "content-workflow",
      "work-item",
      workItemId,
      "draft-revisions",
      revisionId,
      "public-deployment"
    ],
    queryFn: () => getContentRevisionPublicDeployment(workItemId, revisionId ?? ""),
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    enabled: Boolean(enabled && revisionId)
  });
}

export function useContentPlanningProposal(
  workItemId: string,
  enabled = true
): ContentPlanningProposalQuery {
  return useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "planning-proposal"],
    queryFn: () => getContentWorkItemPlanningProposal(workItemId),
    staleTime: 5_000,
    enabled,
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 1500 : false
  });
}

export function useContentWorkflowQueries(
  selectedWorkItemId: string | null,
  browseInventory = false,
  showEntryDiagnostics = false
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
  const diagnostics = useQuery({
    queryKey: ["content-workflow", "diagnostics"],
    queryFn: getContentDiagnostics,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    // This explains an empty entry queue. It is neither a route identity
    // authority nor a condition for selected, review, browse, or new-page work.
    enabled: showEntryDiagnostics
  });
  const operatorContext = useQuery({
    queryKey: ["content-workflow", "operator-context"],
    queryFn: getContentOperatorContext,
    staleTime: READ_ONLY_WORKFLOW_STALE_TIME_MS,
    // Identity can be refreshed independently for an exact review or repair
    // command, but neither its latency nor failure may replace the workspace.
    enabled: Boolean(selectedWorkItemId)
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
    diagnostics,
    operatorContext
  };
}
