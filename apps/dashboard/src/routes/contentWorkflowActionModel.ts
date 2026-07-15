import type {
  ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  ContentWorkItemWordPressDraftExecutionRequest,
  ContentWorkItemWordPressDraftExecutionResponse,
  WordPressAuthoringProfile
} from "../lib/api";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type WordPressHandoff = ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
type WordPressDraftSectionOverride = NonNullable<ContentWorkItemWordPressDraftExecutionRequest["section_overrides"]>[number];

export function executionResultFrom(
  response: ContentWorkItemWordPressDraftExecutionResponse | undefined
) {
  return response?.execution_result ?? null;
}

export function acfPreviewResultFrom(
  response: ContentWorkItemWordPressAuthoringPayloadPreviewResponse | undefined
) {
  return response?.preview_result ?? null;
}

export function submitIfReady<TRequest>(request: TRequest | null, submit: (request: TRequest) => void) {
  if (request) submit(request);
}

export function wordpressExecutionRequest(
  draft: DraftPackage,
  handoff: WordPressHandoff,
  sectionOverrides: WordPressDraftSectionOverride[] = []
): ContentWorkItemWordPressDraftExecutionRequest | null {
  if (!draft || !handoff) return null;
  const request: ContentWorkItemWordPressDraftExecutionRequest = {
    handoff,
    draft_package: draft,
    mode: "dry_run",
    write_authorization: null
  };
  if (sectionOverrides.length) {
    request.section_overrides = sectionOverrides;
  }
  return request;
}

export function acfPreviewRequest(
  draft: DraftPackage,
  handoff: WordPressHandoff,
  authoringProfile: WordPressAuthoringProfile | null
): ContentWorkItemWordPressAuthoringPayloadPreviewRequest | null {
  if (!draft || !handoff || !authoringProfile) return null;
  return {
    handoff,
    draft_package: draft,
    authoring_profile: authoringProfile
  };
}
