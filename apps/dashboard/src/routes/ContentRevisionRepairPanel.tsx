import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  postContentWorkItemRevisionRepairProposal,
  type ContentDocumentWorkspace
} from "../lib/api";

type RepairTarget =
  | { kind: "section"; id: string; label: string }
  | { kind: "cta"; id: string; label: string };

export function ContentRevisionRepairPanel({
  workspace,
  operatorLabel,
  onChanged
}: {
  workspace: ContentDocumentWorkspace;
  operatorLabel: string | null;
  onChanged: () => void;
}) {
  const revision = workspace.canonical_document.revision ?? null;
  const review = workspace.canonical_document.review ?? null;
  const targets = useMemo<RepairTarget[]>(() => {
    if (!revision) return [];
    return [
      ...revision.sections.flatMap((section) => section.section_id
        ? [{ kind: "section" as const, id: section.section_id, label: section.heading }]
        : []),
      ...revision.cta_blocks.map((cta) => ({
        kind: "cta" as const,
        id: cta.cta_id,
        label: `Wezwanie do działania: ${cta.placement}`
      }))
    ];
  }, [revision]);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(targets[0]?.id ?? null);
  const selectedTarget = targets.find((target) => target.id === selectedTargetId) ?? null;
  const repair = useMutation({
    mutationFn: () => {
      if (!revision || !selectedTarget || !operatorLabel) throw new Error("Brakuje dokładnego wyboru do poprawy.");
      return postContentWorkItemRevisionRepairProposal({
        expected_base_digest: revision.content_digest,
        selected_section_ids: selectedTarget.kind === "section" ? [selectedTarget.id] : [],
        selected_cta_ids: selectedTarget.kind === "cta" ? [selectedTarget.id] : [],
        requested_by: operatorLabel
      }, workspace.work_item_id, revision.revision_id);
    },
    onSuccess: onChanged
  });

  if (!revision || !review || !["needs_changes", "rejected"].includes(review.decision)) return null;

  return (
    <section className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-4" data-testid="content-revision-repair">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Popraw jeden element</p>
      <h2 className="mt-2 text-lg font-semibold text-ink">Przygotuj poprawioną wersję</h2>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        Wybierz jedną sekcję albo jedno wezwanie do działania. WILQ zachowa resztę tekstu i jego dowody, a wynik zapisze jako nową wersję do ponownego review.
      </p>
      {review.notes ? <p className="mt-3 text-sm leading-6 text-slate-700">Uwagi marketera: {review.notes}</p> : null}
      {!operatorLabel ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się potwierdzić osoby zlecającej poprawkę.</p> : null}
      <label className="mt-4 block text-sm font-semibold text-ink">
        Element do poprawy
        <select
          className="mt-2 block w-full rounded-md border border-line bg-white p-2 text-sm font-normal text-ink"
          value={selectedTarget?.id ?? ""}
          disabled={!operatorLabel || repair.isPending}
          onChange={(event) => setSelectedTargetId(event.target.value || null)}
        >
          {targets.map((target) => <option key={target.id} value={target.id}>{target.label}</option>)}
        </select>
      </label>
      {repair.data?.revision ? <p className="mt-3 text-sm font-semibold text-action">Utworzono nową wersję do review.</p> : null}
      {repair.data?.blockers[0] ? <p className="mt-3 text-sm leading-6 text-wait">{repair.data.blockers[0].reason}</p> : null}
      {repair.isError ? <p className="mt-3 text-sm leading-6 text-wait">Nie udało się przygotować poprawki. Odśwież workspace — wersja lub decyzja mogła się zmienić.</p> : null}
      <button
        type="button"
        className="mt-4 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!operatorLabel || !selectedTarget || repair.isPending}
        onClick={() => repair.mutate()}
      >
        {repair.isPending ? "Przygotowuję poprawkę…" : "Przygotuj poprawkę"}
      </button>
    </section>
  );
}
