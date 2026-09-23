/** Exact action-ID gates for human packet review and local receipt apply. */

export function packetReviewCheckedItems(
  actionId: string,
  reviewedActionId: string | null
): string[] {
  return actionId === reviewedActionId ? ["reviewed_full_packet"] : [];
}

export function packetReviewApprovalAllowed(
  outcome: string,
  actionId: string,
  reviewedActionId: string | null,
  exactPacketVisible: boolean
): boolean {
  return outcome !== "approved_for_prepare" || (
    exactPacketVisible && actionId === reviewedActionId
  );
}

export function localAuthorityApplyAllowed(
  actionId: string,
  acknowledgedActionId: string | null,
  reviewGateAllows: boolean
): boolean {
  return reviewGateAllows && actionId === acknowledgedActionId;
}
