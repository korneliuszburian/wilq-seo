import {
  ActionApplyRequestSchema,
  ActionApplyResultSchema,
  ActionConfirmResultSchema,
  ActionImpactCheckResultSchema,
  ActionMutationReadinessResponseSchema,
  ActionMutationReadinessSummaryResponseSchema,
  ActionObjectSchema,
  ActionPreviewRequestSchema,
  ActionPreviewResultSchema,
  ActionReviewResultSchema,
  ActionValidationResultSchema,
  type ActionApplyRequest,
  type ActionApplyResult,
  type ActionConfirmRequest,
  type ActionConfirmResult,
  type ActionImpactCheckRequest,
  type ActionImpactCheckResult,
  type ActionMutationReadinessResponse,
  type ActionMutationReadinessSummaryResponse,
  type ActionObject,
  type ActionPreviewRequest,
  type ActionPreviewResult,
  type ActionReviewRequest,
  type ActionReviewResult,
  type ActionValidationResult
} from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet, apiPost, apiPostWithDetailConflict } from "./common";

export function getActionMutationReadiness(
  actionId: string
): Promise<ActionMutationReadinessResponse> {
  return apiGet(
    `/api/actions/${encodeURIComponent(actionId)}/mutation-readiness`,
    ActionMutationReadinessResponseSchema
  );
}

export function getActionsMutationReadiness(): Promise<ActionMutationReadinessSummaryResponse> {
  return apiGet(
    "/api/actions/mutation-readiness",
    ActionMutationReadinessSummaryResponseSchema
  );
}

export function getActions(): Promise<ActionObject[]> {
  return apiGet("/api/actions", z.array(ActionObjectSchema));
}

export function actionApiPath(actionId: string, suffix = ""): string {
  return `/api/actions/${encodeURIComponent(actionId)}${suffix}`;
}

export function getAction(actionId: string): Promise<ActionObject> {
  return apiGet(actionApiPath(actionId), ActionObjectSchema);
}

export function validateAction(actionId: string): Promise<ActionValidationResult> {
  return apiPost(actionApiPath(actionId, "/validate"), ActionValidationResultSchema);
}

export function previewAction(
  actionId: string,
  request: ActionPreviewRequest = {
    requested_by: "operator_local_dashboard",
    max_items: 8
  }
): Promise<ActionPreviewResult> {
  return apiPost(
    actionApiPath(actionId, "/preview"),
    ActionPreviewResultSchema,
    ActionPreviewRequestSchema.parse(request)
  );
}

export function reviewAction(
  actionId: string,
  request: ActionReviewRequest
): Promise<ActionReviewResult> {
  return apiPost(actionApiPath(actionId, "/review"), ActionReviewResultSchema, request);
}

export function confirmAction(
  actionId: string,
  request: ActionConfirmRequest
): Promise<ActionConfirmResult> {
  return apiPost(actionApiPath(actionId, "/confirm"), ActionConfirmResultSchema, request);
}

export function impactCheckAction(
  actionId: string,
  request: ActionImpactCheckRequest
): Promise<ActionImpactCheckResult> {
  return apiPost(
    actionApiPath(actionId, "/impact-check"),
    ActionImpactCheckResultSchema,
    request
  );
}

export function applyAction(
  actionId: string,
  request: ActionApplyRequest
): Promise<ActionApplyResult> {
  return apiPostWithDetailConflict(
    actionApiPath(actionId, "/apply"),
    ActionApplyResultSchema,
    ActionApplyRequestSchema.parse(request)
  );
}
