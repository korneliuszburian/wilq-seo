import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  reviewSocialReuseProposal,
  reviseSocialReuseProposal,
  type SocialReuseProposalListResponse
} from "../../lib/api";
import { LoadingBand, MetricTile } from "../../components/OperatorPrimitives";

export function SocialReuseProposalsPanel({
  proposals,
  loading
}: {
  proposals: SocialReuseProposalListResponse | undefined;
  loading: boolean;
}) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});
  const [revisionDrafts, setRevisionDrafts] = useState<
    Record<string, { audience: string; angle: string; body: string; measurement_hypothesis: string }>
  >({});
  const reviewMutation = useMutation({
    mutationFn: (input: {
      proposalId: string;
      digest: string;
      decision: "approved" | "needs_changes" | "rejected";
    }) =>
      reviewSocialReuseProposal(input.proposalId, {
        expected_proposal_digest: input.digest,
        reviewed_by: "wilku",
        decision: input.decision,
        notes: notes[input.proposalId]?.trim() ?? "",
        checked_items: [
          "Treść zgodna z dokładną rewizją źródłową",
          "Źródła i twierdzenia sprawdzone",
          "Publikacja pozostaje wyłączona"
        ],
        evidence_ids: proposals?.proposals
          .find((item) => item.proposal?.proposal_id === input.proposalId)
          ?.proposal?.source_evidence_ids ?? []
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["social-reuse-proposals"] });
    }
  });
  const revisionMutation = useMutation({
    mutationFn: (input: {
      proposalId: string;
      digest: string;
      claimIds: string[];
      draft: { audience: string; angle: string; body: string; measurement_hypothesis: string };
    }) => reviseSocialReuseProposal(input.proposalId, {
      expected_proposal_digest: input.digest,
      audience: input.draft.audience,
      angle: input.draft.angle,
      body: input.draft.body,
      claim_ids: input.claimIds,
      measurement_hypothesis: input.draft.measurement_hypothesis
    }),
    onSuccess: () => {
      setEditing({});
      void queryClient.invalidateQueries({ queryKey: ["social-reuse-proposals"] });
    }
  });
  if (loading) return <LoadingBand />;
  const items = proposals?.proposals ?? [];
  return (
    <section className="rounded-md border border-line bg-white p-4" aria-labelledby="social-reuse-proposals-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="social-reuse-proposals-title" className="text-base font-semibold text-ink">
            Propozycje treści do social
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Każda propozycja jest przypięta do konkretnej rewizji treści i wymaga osobnego sprawdzenia.
          </p>
        </div>
        <MetricTile label="propozycje" value={items.length} />
      </div>
      {items.length === 0 ? (
        <p className="mt-4 rounded border border-dashed border-line bg-surface p-3 text-sm text-slate-600">
          Brak zapisanych propozycji dla aktualnych źródeł. Najpierw musi powstać review-only materiał z dokładnej rewizji treści.
        </p>
      ) : (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {items.map((item) => {
            const proposal = item.proposal;
            if (!proposal) return null;
            const decision = item.review?.decision;
            const draft = revisionDrafts[proposal.proposal_id] ?? {
              audience: proposal.audience,
              angle: proposal.angle,
              body: proposal.body,
              measurement_hypothesis: proposal.measurement_hypothesis
            };
            return (
              <article key={proposal.proposal_id} className="rounded border border-line bg-surface p-3">
                <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                  <span className="font-semibold text-action">
                    {proposal.platform === "linkedin" ? "LinkedIn" : "Facebook"}
                  </span>
                  <span>{decision === "approved" ? "zaakceptowane" : decision === "needs_changes" ? "do poprawy" : decision === "rejected" ? "odrzucone" : "do review"}</span>
                </div>
                <h3 className="mt-2 text-sm font-semibold text-ink">{proposal.angle}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{proposal.body}</p>
                <p className="mt-3 text-xs text-slate-500">
                  {proposal.parent_proposal_id ? "Poprawiona wersja · " : ""}
                  {proposal.source_evidence_ids.length} źródeł treści · {proposal.duplicate_risk_evidence_ids.length} dowodów historii · publikacja wyłączona
                </p>
                {item.review?.notes ? (
                  <p className="mt-2 rounded bg-white px-2 py-1 text-xs text-slate-600">Uwagi: {item.review.notes}</p>
                ) : null}
                <label className="mt-3 block text-xs font-medium text-slate-600" htmlFor={`social-review-notes-${proposal.proposal_id}`}>
                  Uwagi do review (wymagane przy poprawie lub odrzuceniu)
                </label>
                <textarea
                  id={`social-review-notes-${proposal.proposal_id}`}
                  className="mt-1 min-h-16 w-full rounded border border-line bg-white p-2 text-sm text-ink"
                  value={notes[proposal.proposal_id] ?? ""}
                  onChange={(event) =>
                    setNotes((current) => ({ ...current, [proposal.proposal_id]: event.target.value }))
                  }
                  placeholder="Co dokładnie trzeba zmienić?"
                  disabled={reviewMutation.isPending}
                />
                {proposal.status === "review_required" ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded bg-action px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                      disabled={reviewMutation.isPending}
                      onClick={() =>
                        reviewMutation.mutate({
                          proposalId: proposal.proposal_id,
                          digest: proposal.proposal_digest,
                          decision: "approved"
                        })
                      }
                    >
                      Zatwierdź propozycję
                    </button>
                    <button
                      type="button"
                      className="rounded border border-wait/40 bg-wait/10 px-3 py-2 text-xs font-semibold text-ink disabled:opacity-50"
                      disabled={reviewMutation.isPending || !(notes[proposal.proposal_id] ?? "").trim()}
                      onClick={() =>
                        reviewMutation.mutate({
                          proposalId: proposal.proposal_id,
                          digest: proposal.proposal_digest,
                          decision: "needs_changes"
                        })
                      }
                    >
                      Wyślij do poprawy
                    </button>
                  </div>
                ) : null}
                {decision === "needs_changes" ? (
                  <div className="mt-3">
                    {!editing[proposal.proposal_id] ? (
                      <button
                        type="button"
                        className="rounded border border-action/40 bg-white px-3 py-2 text-xs font-semibold text-action"
                        onClick={() => setEditing((current) => ({ ...current, [proposal.proposal_id]: true }))}
                      >
                        Przygotuj poprawioną wersję
                      </button>
                    ) : (
                      <div className="rounded border border-action/20 bg-white p-3">
                        <p className="text-xs font-semibold text-ink">Jedna poprawiona wersja do ponownego review</p>
                        <label className="mt-2 block text-xs text-slate-600">
                          Odbiorca
                          <input
                            className="mt-1 w-full rounded border border-line p-2 text-sm"
                            value={draft.audience}
                            onChange={(event) => setRevisionDrafts((current) => ({
                              ...current,
                              [proposal.proposal_id]: { ...draft, audience: event.target.value }
                            }))}
                          />
                        </label>
                        <label className="mt-2 block text-xs text-slate-600">
                          Kąt komunikacji
                          <input
                            className="mt-1 w-full rounded border border-line p-2 text-sm"
                            value={draft.angle}
                            onChange={(event) => setRevisionDrafts((current) => ({
                              ...current,
                              [proposal.proposal_id]: { ...draft, angle: event.target.value }
                            }))}
                          />
                        </label>
                        <label className="mt-2 block text-xs text-slate-600">
                          Treść
                          <textarea
                            className="mt-1 min-h-28 w-full rounded border border-line p-2 text-sm"
                            value={draft.body}
                            onChange={(event) => setRevisionDrafts((current) => ({
                              ...current,
                              [proposal.proposal_id]: { ...draft, body: event.target.value }
                            }))}
                          />
                        </label>
                        <label className="mt-2 block text-xs text-slate-600">
                          Hipoteza pomiaru
                          <input
                            className="mt-1 w-full rounded border border-line p-2 text-sm"
                            value={draft.measurement_hypothesis}
                            onChange={(event) => setRevisionDrafts((current) => ({
                              ...current,
                              [proposal.proposal_id]: { ...draft, measurement_hypothesis: event.target.value }
                            }))}
                          />
                        </label>
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            className="rounded bg-action px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                            disabled={revisionMutation.isPending || !draft.body.trim() || !draft.angle.trim()}
                            onClick={() => revisionMutation.mutate({
                              proposalId: proposal.proposal_id,
                              digest: proposal.proposal_digest,
                              claimIds: proposal.source_claim_ids,
                              draft
                            })}
                          >
                            Zapisz poprawioną wersję
                          </button>
                          <button
                            type="button"
                            className="rounded border border-line px-3 py-2 text-xs text-slate-600"
                            onClick={() => setEditing((current) => ({ ...current, [proposal.proposal_id]: false }))}
                          >
                            Anuluj
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
      {reviewMutation.error instanceof Error ? (
        <p className="mt-3 rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          Nie zapisano review: {reviewMutation.error.message}
        </p>
      ) : null}
      {reviewMutation.data ? (
        <p className="mt-3 rounded border border-action/30 bg-action/5 p-3 text-sm text-slate-700">
          Review zapisany. {reviewMutation.data.next_step}
        </p>
      ) : null}
      {revisionMutation.error instanceof Error ? (
        <p className="mt-3 rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          Nie zapisano poprawionej wersji: {revisionMutation.error.message}
        </p>
      ) : null}
      {revisionMutation.data ? (
        <p className="mt-3 rounded border border-action/30 bg-action/5 p-3 text-sm text-slate-700">
          Poprawiona wersja została zapisana jako nowa rewizja i wymaga osobnego review.
        </p>
      ) : null}
    </section>
  );
}
