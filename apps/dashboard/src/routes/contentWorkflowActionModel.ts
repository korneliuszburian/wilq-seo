import type {
  ContentWorkItemQualityReviewResponse,
  ContentWorkItemRevisionPlanResponse,
  ContentWorkItemSnapshotAuditRequest,
  ContentWorkItemSnapshotHumanReviewRequest,
  ContentWorkItemStructuredDraftPreviewRequest,
  ContentWorkItemStructuredDraftPreviewResponse,
  ContentWorkItemStructuredDraftRuntimeRequest,
  ContentWorkItemStructuredDraftRuntimeResponse,
  ContentWorkItemQualityReviewRequest,
  ContentWorkItemRevisionPlanRequest,
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

function unique(values: string[]) {
  return [...new Set(values)];
}

export function runtimeResultFrom(response: ContentWorkItemStructuredDraftRuntimeResponse | undefined) {
  return response?.runtime_result ?? null;
}

export function previewResultFrom(response: ContentWorkItemStructuredDraftPreviewResponse | undefined) {
  return response?.preview_result ?? null;
}

export function qualityReviewFrom(response: ContentWorkItemQualityReviewResponse | undefined) {
  return response?.quality_review ?? null;
}

export function revisionPlanFrom(response: ContentWorkItemRevisionPlanResponse | undefined) {
  return response?.revision_plan ?? null;
}

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

export function structuredRuntimeDryRunRequest(
  data: ContentWorkflowSnapshot
): ContentWorkItemStructuredDraftRuntimeRequest | null {
  const contract = data.structuredGeneration.structured_generation_result.contract;
  if (!contract) return null;
  return {
    contract,
    model: "gpt-5",
    mode: "dry_run"
  };
}

export function structuredPreviewRequest(
  data: ContentWorkflowSnapshot,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
): ContentWorkItemStructuredDraftPreviewRequest | null {
  const contract = data.structuredGeneration.structured_generation_result.contract;
  const output = runtimeResult?.output;
  if (!contract || !output) return null;
  return { contract, output };
}

export function qualityReviewRequest(
  data: ContentWorkflowSnapshot,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
): ContentWorkItemQualityReviewRequest | null {
  const draft = data.draftPackage.draft_package_result.draft_package;
  const output = runtimeResult?.output;
  if (!draft || !output) return null;
  return {
    item: data.preflight.item,
    draft_package: draft,
    structured_output: output,
    claim_ledger: data.claimLedger,
    sales_brief: data.salesBrief.sales_brief_result.brief ?? null,
    duplicate_risk: "clear"
  };
}

export function revisionPlanRequest(
  data: ContentWorkflowSnapshot,
  qualityReview: ContentWorkItemQualityReviewResponse["quality_review"] | null
): ContentWorkItemRevisionPlanRequest | null {
  if (!qualityReview) return null;
  return {
    item: data.preflight.item,
    quality_review: qualityReview
  };
}

export function humanReviewRequest(
  data: ContentWorkflowSnapshot,
  draft: DraftPackage
): ContentWorkItemSnapshotHumanReviewRequest | null {
  if (!draft) return null;
  const item = data.preflight.item;
  return {
    review: {
      id: `human_review_${item.id}`,
      work_item_id: item.id,
      stage: "draft_package",
      reviewed_by: "wilku",
      decision: "approved",
      notes:
        "Operator zatwierdził brief, ryzykowne twierdzenia i paczkę szkicu do przygotowania szkicu WordPress.",
      checked_items: [
        "Brief i paczka szkicu są zgodne z dowodami WILQ.",
        "Ryzykowne twierdzenia zostały usunięte albo obsłużone.",
        "Szkic pozostaje materiałem do sprawdzenia, nie publikacją."
      ],
      evidence_ids: unique(item.evidence_ids),
      blocked_claims_handled: unique(draft.claims_removed_or_blocked),
      draft_package_id: draft.id
    }
  };
}

export function auditRequest(data: ContentWorkflowSnapshot): ContentWorkItemSnapshotAuditRequest | null {
  const item = data.preflight.item;
  const review = data.humanReview.review;
  if (!review) return null;
  return {
    audit: {
      audit_id: `audit_${item.id}`,
      actor: "wilku",
      reason:
        "Operator zatwierdził przekazanie wyłącznie w trybie szkicu. WordPress może dostać wyłącznie szkic.",
      evidence_ids: unique(item.evidence_ids),
      human_review_id: review.id
    }
  };
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

