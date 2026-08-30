import type {
  ContentInitialDraftResponse,
  ContentSelectedWorkspace
} from "../lib/api";

type ProductionDecision = ContentSelectedWorkspace["production_decision"];
type AvailableProductionDecision = Exclude<ProductionDecision, { status: "missing" }>;

export type ReuseProductionDecision = Extract<
  AvailableProductionDecision,
  { decision: "reuse" }
>;
export type ReusableDocumentReady = Extract<
  ReuseProductionDecision["reusable_document"],
  { status: "ready" }
>;
export type ReusedInitialDraftResponse = Extract<
  ContentInitialDraftResponse,
  { status: "reused" }
>;
export type ApprovedReuseReview = ReusedInitialDraftResponse["reuse_binding"]["approved_review"];

export function hasExactReusedInitialDraft(
  response: ReusedInitialDraftResponse,
  selected: ContentSelectedWorkspace,
  productionDecision: ReuseProductionDecision,
  reusableDocument: ReusableDocumentReady
): boolean {
  const selectedBinding = productionDecision.revision_binding;
  const responseBinding = response.reuse_binding;
  const selectedRevision = reusableDocument.revision;
  const selectedReview = reusableDocument.review;
  const responseReview = responseBinding.approved_review;

  return (
    responseBinding.classification_run_id === productionDecision.run_id &&
    responseBinding.classification_run_digest === productionDecision.run_digest &&
    responseBinding.decision_set_digest === productionDecision.decision_set_digest &&
    responseBinding.requested_work_item_id === selected.requested_work_item_id &&
    response.work_item_id === selected.work_item_id &&
    responseBinding.current_work_item_id === selected.work_item_id &&
    responseBinding.current_work_item_id === productionDecision.current_work_item_id &&
    responseBinding.lookup_basis === productionDecision.lookup_basis &&
    responseBinding.retained_work_item_id === productionDecision.retained_work_item_id &&
    responseBinding.retained_work_item_id === selectedBinding.retained_work_item_id &&
    responseBinding.identity_reconciliation_status === selectedBinding.identity_reconciliation_status &&
    responseBinding.revision_work_item_id === selectedBinding.revision_work_item_id &&
    responseBinding.revision_id === selectedBinding.revision_id &&
    responseBinding.revision_digest === selectedBinding.revision_digest &&
    responseBinding.must_not_regenerate &&
    selectedBinding.must_not_regenerate &&
    response.revision.work_item_id === selectedBinding.revision_work_item_id &&
    response.revision.revision_id === selectedBinding.revision_id &&
    response.revision.content_digest === selectedBinding.revision_digest &&
    response.revision.work_item_id === selectedRevision.work_item_id &&
    response.revision.revision_id === selectedRevision.revision_id &&
    response.revision.content_digest === selectedRevision.content_digest &&
    responseReview.work_item_id === selectedReview.work_item_id &&
    responseReview.revision_id === selectedReview.revision_id &&
    responseReview.revision_digest === selectedReview.revision_digest &&
    responseReview.decision_id === selectedReview.decision_id &&
    responseReview.decision === selectedReview.decision
  );
}
