import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createContentNewPageInitialDraft,
  createContentNewPagePlanningProposal,
  getContentNewPagePlanningProposal,
  type ContentNewPagePlanningProposalWorkspace
} from "../lib/api";
import { textPreparationRecovery } from "./contentTextPreparationCopy";

type NewPageProposal = NonNullable<
  NonNullable<ContentNewPagePlanningProposalWorkspace["proposal_status"]>["proposal"]
>;

type ExactNewPageProposal = NewPageProposal & {
  proposal_id: string;
  planning_digest: string;
  planning_input_digest: string;
};

/** Server-owned planning stays internal; this owns the one visible text action. */
export function ContentNewPageTextPreparation({
  briefId,
  autoStart = false
}: {
  briefId: string;
  autoStart?: boolean;
}) {
  const queryClient = useQueryClient();
  const [requestedInputDigest, setRequestedInputDigest] = useState<string | null>(null);
  const startedProposalId = useRef<string | null>(null);
  const consumedAutoStart = useRef(false);
  const workspace = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId, "planning-proposal"],
    queryFn: () => getContentNewPagePlanningProposal(briefId),
    staleTime: 15_000,
    refetchInterval: (query) =>
      query.state.data?.proposal_status?.status === "generating" ? 3_000 : false
  });
  const generate = useMutation({
    mutationFn: (digest: string) =>
      createContentNewPagePlanningProposal(briefId, {
        expected_planning_input_digest: digest,
        requested_by: "Wilku"
      }),
    onMutate: (digest) => setRequestedInputDigest(digest),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["content-workflow", "new-page-brief", briefId] })
  });
  const prepareDocument = useMutation({
    mutationFn: ({ proposalId, planningDigest, planningInputDigest }: {
      proposalId: string;
      planningDigest: string;
      planningInputDigest: string;
    }) =>
      createContentNewPageInitialDraft(briefId, {
        expected_proposal_id: proposalId,
        expected_planning_digest: planningDigest,
        expected_planning_input_digest: planningInputDigest,
        requested_by: "wilku"
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["content-workflow", "new-page-brief", briefId] }),
    onError: () => {
      startedProposalId.current = null;
      setRequestedInputDigest(null);
    }
  });

  const readiness = workspace.data?.readiness ?? null;
  const proposal = workspace.data?.proposal_status ?? null;
  const exactProposal = exactNewPageProposal(proposal?.proposal);
  const proposalReady = Boolean(
    exactProposal && ["ready", "created", "idempotent"].includes(proposal?.status ?? "")
  );

  useEffect(() => {
    if (
      !requestedInputDigest ||
      !exactProposal ||
      requestedInputDigest !== exactProposal.planning_input_digest ||
      !proposalReady ||
      startedProposalId.current === exactProposal.proposal_id ||
      prepareDocument.isPending
    ) return;
    startedProposalId.current = exactProposal.proposal_id;
    prepareDocument.mutate({
      proposalId: exactProposal.proposal_id,
      planningDigest: exactProposal.planning_digest,
      planningInputDigest: exactProposal.planning_input_digest
    });
  }, [exactProposal, prepareDocument, proposalReady, requestedInputDigest]);

  useEffect(() => {
    if (!autoStart || consumedAutoStart.current || workspace.isLoading || !readiness) return;
    consumedAutoStart.current = true;
    if (readiness.status !== "ready") return;
    if (proposalReady && exactProposal) {
      if (startedProposalId.current !== exactProposal.proposal_id) {
        startedProposalId.current = exactProposal.proposal_id;
        prepareDocument.mutate({
          proposalId: exactProposal.proposal_id,
          planningDigest: exactProposal.planning_digest,
          planningInputDigest: exactProposal.planning_input_digest
        });
      }
      return;
    }
    if (readiness.planning_input_digest) generate.mutate(readiness.planning_input_digest);
  }, [autoStart, exactProposal, generate, prepareDocument, proposalReady, readiness, workspace.isLoading]);

  if (workspace.isLoading) {
    return <p className="mt-4 text-sm leading-6 text-slate-600">Sprawdzam dane do przygotowania tekstu…</p>;
  }
  if (workspace.error || !workspace.data || !readiness) {
    return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 px-3 py-2 text-sm leading-6 text-ink">Nie udało się odczytać danych do przygotowania tekstu. Brief i wybrana wiedza pozostają zapisane; odśwież widok i spróbuj ponownie.</p>;
  }
  if (readiness.status === "blocked") {
    const blocker = readiness.blockers[0];
    return <div className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm leading-6 text-ink"><p className="font-semibold">{blocker?.label ?? "Tekst jest jeszcze zablokowany"}</p><p className="mt-1">{blocker?.reason ?? readiness.safe_next_step}</p><p className="mt-2 text-slate-700">{textPreparationRecovery(blocker?.code)}</p></div>;
  }

  const preparingText = generate.isPending || proposal?.status === "generating" || prepareDocument.isPending;
  const prepareText = () => {
    if (proposalReady && exactProposal) {
      setRequestedInputDigest(exactProposal.planning_input_digest);
      if (startedProposalId.current !== exactProposal.proposal_id) {
        startedProposalId.current = exactProposal.proposal_id;
        prepareDocument.mutate({
          proposalId: exactProposal.proposal_id,
          planningDigest: exactProposal.planning_digest,
          planningInputDigest: exactProposal.planning_input_digest
        });
      }
      return;
    }
    if (readiness.planning_input_digest) generate.mutate(readiness.planning_input_digest);
  };
  if (preparingText) {
    return <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-ink" data-testid="new-page-planning-generating"><p className="font-semibold">Przygotowuję pierwszy tekst</p><p className="mt-1">WILQ sprawdza exact dane robocze i przygotowuje pierwszy tekst; nie uruchomi drugiej wersji dla tych samych danych.</p></div>;
  }
  if (!readiness.planning_input_digest) {
    return <div className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm leading-6 text-ink"><p className="font-semibold">Nie można jeszcze przygotować tekstu</p><p className="mt-1">Brakuje dokładnych danych roboczych. Odśwież brief i spróbuj ponownie.</p></div>;
  }
  return <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-sm leading-6 text-ink" data-testid="new-page-planning-ready"><p className="font-semibold">Tekst nowej strony jest gotowy do przygotowania</p><p className="mt-1">WILQ użyje dokładnego briefu i wybranego kontekstu usługi. Nie przypisuje tej nowej stronie starego URL-a, inventory ani historycznych metryk.</p><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white" onClick={prepareText}>Przygotuj tekst</button>{generate.isError || prepareDocument.isError ? <p className="mt-2 text-wait">Nie udało się przygotować tekstu. Odśwież stan i spróbuj ponownie.</p> : null}</div>;
}

function exactNewPageProposal(proposal: NewPageProposal | null | undefined): ExactNewPageProposal | null {
  return proposal?.proposal_id && proposal.planning_digest && proposal.planning_input_digest
    ? proposal as ExactNewPageProposal
    : null;
}
