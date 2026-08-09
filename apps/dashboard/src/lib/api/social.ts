import {
  SocialHistoryInventorySchema,
  SocialPublisherContextPackSchema,
  SocialReuseProposalListResponseSchema,
  SocialReuseProposalResponseSchema,
  SocialReuseReviewRequestSchema,
  SocialReuseReviewResponseSchema,
  SocialReuseRevisionRequestSchema,
  type SocialHistoryInventory,
  type SocialPublisherContextPack,
  type SocialReuseProposalListResponse,
  type SocialReuseProposalResponse,
  type SocialReuseReviewRequest,
  type SocialReuseReviewResponse,
  type SocialReuseRevisionRequest
} from "@wilq/shared-schemas";

import { apiGet, apiPost, apiPostWithConflict } from "./common";

export function getSocialPublisherContextPack(): Promise<SocialPublisherContextPack> {
  return apiPost("/api/codex/context-pack", SocialPublisherContextPackSchema, {
    skill: "wilq-social-publisher"
  });
}

export function getSocialHistoryInventory(): Promise<SocialHistoryInventory> {
  return apiGet("/api/social/history-inventory", SocialHistoryInventorySchema);
}

export function getSocialReuseProposals(
  workItemId?: string | null
): Promise<SocialReuseProposalListResponse> {
  const query = workItemId ? `?work_item_id=${encodeURIComponent(workItemId)}` : "";
  return apiGet(
    `/api/social/reuse-proposals${query}`,
    SocialReuseProposalListResponseSchema
  );
}

export function reviewSocialReuseProposal(
  proposalId: string,
  request: SocialReuseReviewRequest
): Promise<SocialReuseReviewResponse> {
  return apiPostWithConflict(
    `/api/social/reuse-proposals/${encodeURIComponent(proposalId)}/review`,
    SocialReuseReviewResponseSchema,
    SocialReuseReviewResponseSchema,
    SocialReuseReviewRequestSchema.parse(request)
  );
}

export function reviseSocialReuseProposal(
  proposalId: string,
  request: SocialReuseRevisionRequest
): Promise<SocialReuseProposalResponse> {
  return apiPostWithConflict(
    `/api/social/reuse-proposals/${encodeURIComponent(proposalId)}/revise`,
    SocialReuseProposalResponseSchema,
    SocialReuseProposalResponseSchema,
    SocialReuseRevisionRequestSchema.parse(request)
  );
}
