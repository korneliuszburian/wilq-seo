import type {
  ContentPlanningProposalRequest,
  ContentPlanningProposalResponse
} from "@wilq/shared-schemas";

export function planningRequestFromResponse(
  response: ContentPlanningProposalResponse,
  requestedBy: string
): ContentPlanningProposalRequest {
  const contentKind = response.content_kind ?? "service";
  if (!response.planning_input_digest || (contentKind === "service" && !response.service_card_id)) {
    throw new Error(response.safe_next_step);
  }
  return {
    content_kind: contentKind,
    service_card_id: response.service_card_id ?? null,
    expected_planning_input_digest: response.planning_input_digest,
    requested_by: requestedBy,
    operator_hint: "",
    regenerate_stale_mapping: false,
    regenerate_after_review: false
  };
}
