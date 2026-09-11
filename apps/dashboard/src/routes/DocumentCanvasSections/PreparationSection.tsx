import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  type ContentInitialDraftResponse,
  type ContentPlanningProposalResponse,
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  postContentWorkItemInitialDraft,
  postContentWorkItemPlanningProposal
} from "../../lib/api";
import { useContentPlanningProposal } from "../contentWorkflowQueries";
import { RegulatorySourceReviewCandidates } from "../PlanningEvidenceDetails";
import { planningRequestFromResponse } from "./planningRequest";
import type { ContentDocumentWorkspace } from "./shared";

type DocumentPreparationPhase = "idle" | "planning" | "drafting" | "complete";

export function ContentDocumentPreparationAction({
  workspace,
  requestedBy,
  onPrepared
}: {
  workspace: ContentDocumentWorkspace;
  requestedBy: string;
  onPrepared: () => void;
}) {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<DocumentPreparationPhase>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const planning = useContentPlanningProposal(workspace.work_item_id, true);
  const preparationMutation = useMutation({
    mutationFn: async () => {
      setPhase("planning");
      let planningResponse = planning.data ?? (await planning.refetch()).data;
      if (!planningResponse) {
        throw new Error("Nie udało się odczytać aktualnego wejścia planu.");
      }
      if (
        !planningResponseCanCreateDraft(planningResponse) &&
        planningResponse.status !== "generating"
      ) {
        planningResponse = await postContentWorkItemPlanningProposal(
          planningRequestFromResponse(planningResponse, requestedBy),
          workspace.work_item_id
        );
      }
      planningResponse = await pollPlanningResponse(
        planningResponse,
        workspace.work_item_id
      );
      if (!planningResponseCanCreateDraft(planningResponse)) {
        throw new Error(planningResponse.safe_next_step);
      }
      const proposal = planningResponse.proposal;
      if (
        !proposal?.proposal_id ||
        !proposal.planning_digest ||
        !proposal.planning_input_digest
      ) {
        throw new Error(planningResponse.safe_next_step);
      }
      setPhase("drafting");
      const initialResponse = await postContentWorkItemInitialDraft({
        expected_proposal_id: proposal.proposal_id,
        expected_planning_digest: proposal.planning_digest,
        expected_planning_input_digest: proposal.planning_input_digest,
        requested_by: requestedBy
      }, workspace.work_item_id);
      const completedDraft = await pollInitialDraftResponse(
        initialResponse,
        workspace.work_item_id
      );
      if (completedDraft.status !== "created") {
        throw new Error(completedDraft.safe_next_step);
      }
      return completedDraft;
    },
    onSuccess: () => {
      setPhase("complete");
      void queryClient.refetchQueries({
        queryKey: [
          "content-workflow",
          "work-item",
          workspace.work_item_id,
          "selected-workspace"
        ]
      }).then(onPrepared);
    },
    onError: (error) => {
      setPhase("idle");
      setMessage(error instanceof Error ? error.message : "Nie udało się przygotować dokumentu.");
    }
  });
  const pending = phase !== "idle";
  const label = phase === "planning"
    ? "Przygotowuję plan…"
    : phase === "drafting"
      ? "Przygotowuję dokument…"
      : phase === "complete"
        ? "Odświeżam dokument…"
        : workspace.next_action.label;

  return (
    <>
      <button
        type="button"
        className="mt-3 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending || planning.isPending}
        onClick={() => {
          setMessage(null);
          preparationMutation.mutate();
        }}
      >
        {label}
      </button>
      {message ? <p className="mt-3 text-sm leading-5 text-wait">{message}</p> : null}
      <RegulatorySourceReviewCandidates
        candidates={workspace.regulatory_review_candidates}
        onRecorded={() => void queryClient.invalidateQueries({ queryKey: ["content-workflow"] })}
        title="Źródła urzędowe do sprawdzenia przed przygotowaniem dokumentu"
      />
    </>
  );
}

function planningResponseCanCreateDraft(response: ContentPlanningProposalResponse): boolean {
  return (
    ["created", "idempotent", "ready"].includes(response.status) &&
    Boolean(
      response.proposal?.proposal_id &&
      response.proposal.planning_digest &&
      response.proposal.planning_input_digest
    )
  );
}

const DOCUMENT_PREPARATION_POLL_LIMIT = 200;

async function pollPlanningResponse(
  initial: ContentPlanningProposalResponse,
  workItemId: string
): Promise<ContentPlanningProposalResponse> {
  let response = initial;
  for (
    let attempt = 0;
    response.status === "generating" && attempt < DOCUMENT_PREPARATION_POLL_LIMIT;
    attempt += 1
  ) {
    await waitForDocumentPreparationPoll(response.retry_after_seconds);
    response = await getContentWorkItemPlanningProposal(workItemId);
  }
  return response;
}

async function pollInitialDraftResponse(
  initial: ContentInitialDraftResponse,
  workItemId: string
): Promise<ContentInitialDraftResponse> {
  let response = initial;
  for (
    let attempt = 0;
    response.status === "generating" && attempt < DOCUMENT_PREPARATION_POLL_LIMIT;
    attempt += 1
  ) {
    await waitForDocumentPreparationPoll(
      response.blockers[0]?.retry_after_seconds
    );
    response = await getContentWorkItemInitialDraft(workItemId);
  }
  return response;
}

function waitForDocumentPreparationPoll(retryAfterSeconds?: number | null): Promise<void> {
  const delayMs = Math.max(1, retryAfterSeconds ?? 1.5) * 1_000;
  return new Promise((resolve) => window.setTimeout(resolve, delayMs));
}
