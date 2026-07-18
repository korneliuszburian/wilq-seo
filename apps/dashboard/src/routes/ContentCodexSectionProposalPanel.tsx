import type {
  ContentDraftRevisionWorkspace,
  ContentStructuredGenerationBrowserReadiness
} from "@wilq/shared-schemas";
import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";

import type {
  ContentCodexSectionProposalResponse,
  ContentDraftRevision
} from "../lib/api";
import { ContentCodexSectionProposalResult } from "./ContentCodexSectionProposalResult";

type ProposalSelectionState = {
  revisionId: string | null;
  keys: string[];
};

type ContentCodexSectionProposalPanelProps = {
  workItemId: string;
  workspace: ContentDraftRevisionWorkspace;
  generationReadiness: ContentStructuredGenerationBrowserReadiness;
  hasUnsavedChanges: boolean;
  pending: boolean;
  error: Error | null;
  result: ContentCodexSectionProposalResponse | null;
  submittedBaseRevision: ContentDraftRevision | null;
  suggestedSectionIds: string[];
  onSubmit: (selection: { sectionIds: string[] } | { sectionHeadings: string[] }) => void;
  onRefresh: () => void;
};

const proposalReadyStatuses = new Set(["needs_changes", "rejected"]);

export function ContentCodexSectionProposalPanel({
  workItemId,
  workspace,
  generationReadiness,
  hasUnsavedChanges,
  pending,
  error,
  result,
  submittedBaseRevision,
  suggestedSectionIds,
  onSubmit,
  onRefresh
}: ContentCodexSectionProposalPanelProps) {
  const latestRevision = workspace.latest_revision;
  const [selectionState, setSelectionState] = useState<ProposalSelectionState>({
    revisionId: null,
    keys: []
  });
  const selectedKeys =
    selectionState.revisionId === latestRevision?.revision_id ? selectionState.keys : [];
  const availableSections = latestRevision
    ? latestRevision.sections
        .filter((section) => generationReadiness.editable_section_headings.includes(section.heading))
    : [];
  const usesStableIds = availableSections.every((section) => Boolean(section.section_id));
  const createdResult = isCreatedResult(result) ? result : null;

  if (createdResult) {
    return (
      <ContentCodexSectionProposalResult
        expectedWorkItemId={workItemId}
        baseRevision={submittedBaseRevision}
        result={createdResult}
        onRefresh={onRefresh}
      />
    );
  }

  const workspaceEligible = Boolean(
    latestRevision &&
      workspace.context_current &&
      workspace.can_save &&
      proposalReadyStatuses.has(workspace.status)
  );
  if (!workspaceEligible) {
    return (
      <section className="mt-4 rounded-md border border-line bg-surface p-3">
        <p className="text-sm font-semibold text-ink">Poprawka wybranych sekcji z Codexem</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{workspace.safe_next_step}</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Codex poprawia dopiero dokładną wersję oznaczoną przez człowieka jako wymagającą zmian.
        </p>
      </section>
    );
  }

  if (generationReadiness.status === "blocked" || availableSections.length === 0) {
    const blocker = generationReadiness.blockers[0];
    return (
      <section className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3">
        <p className="text-sm font-semibold text-wait">
          {blocker?.label ?? "Brakuje gotowego kontraktu poprawki"}
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-700">
          {blocker?.reason ?? generationReadiness.safe_next_step}
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-700">
          Następny krok: {blocker?.next_step ?? generationReadiness.safe_next_step}
        </p>
      </section>
    );
  }

  const confirmedFailure = result && !isCreatedResult(result) ? result : null;
  const submitBlocked = Boolean(
    pending ||
      error ||
      confirmedFailure ||
      hasUnsavedChanges ||
      selectedKeys.length === 0
  );

  return (
    <section
      className="mt-4 rounded-md border border-action/25 bg-action/5 p-3 sm:p-4"
      aria-labelledby="codex-section-proposal-title"
    >
      <div className="flex items-start gap-3">
        <span className="rounded-md border border-action/20 bg-white p-2 text-action">
          <Sparkles aria-hidden="true" size={18} />
        </span>
        <div className="min-w-0">
          <h3 id="codex-section-proposal-title" className="text-sm font-semibold text-ink">
            Popraw aktualny tekst z Codexem
          </h3>
          {workspace.latest_review?.notes ? (
            <p className="mt-1 text-sm leading-6 text-slate-700">
              Uwagi z review: „{workspace.latest_review.notes}”
            </p>
          ) : null}
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Codex dostaje kontekst i dowody z WILQ. Nie zatwierdza ani nie publikuje treści.
          </p>
        </div>
      </div>

      <fieldset className="mt-4" disabled={pending || Boolean(error || confirmedFailure)}>
        <legend className="text-sm font-semibold text-ink">1. Wybierz sekcje do poprawy</legend>
        <div className="mt-2 grid min-w-0 gap-2 sm:grid-cols-2">
          {availableSections.map((section) => {
            const selectionKey = usesStableIds ? String(section.section_id) : section.heading;
            const checked = selectedKeys.includes(selectionKey);
            const suggested = Boolean(
              section.section_id && suggestedSectionIds.includes(section.section_id)
            );
            return (
              <label
                key={selectionKey}
                className="flex min-w-0 cursor-pointer items-start gap-2 rounded-md border border-line bg-white p-3 text-sm leading-5 text-slate-700"
              >
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={checked}
                  onChange={() =>
                    setSelectionState({
                      revisionId: latestRevision?.revision_id ?? null,
                      keys: checked
                        ? selectedKeys.filter((selected) => selected !== selectionKey)
                        : [...selectedKeys, selectionKey]
                    })
                  }
                />
                <span className="min-w-0 break-words">
                  {section.heading}
                  {suggested ? (
                    <span className="mt-1 block text-xs font-semibold text-action">
                      Wskazane w advisory review
                    </span>
                  ) : null}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {hasUnsavedChanges ? (
        <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
          Masz niezapisane zmiany w edytorze. Zapisz je jako nową wersję i wykonaj review,
          zanim poprosisz Codexa o poprawkę.
        </p>
      ) : null}

      <button
        type="button"
        disabled={submitBlocked}
        onClick={() =>
          onSubmit(
            usesStableIds
              ? { sectionIds: selectedKeys }
              : { sectionHeadings: selectedKeys }
          )
        }
        className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      >
        {pending
          ? "Codex poprawia sekcje..."
          : `Popraw ${selectedKeys.length || 0} ${sectionCountLabel(selectedKeys.length)} z Codexem`}
        <ArrowRight aria-hidden="true" size={16} />
      </button>

      {pending ? (
        <p role="status" className="mt-3 text-sm leading-6 text-slate-700">
          Codex poprawia {selectedKeys.length} {sectionCountLabel(selectedKeys.length)} i
          sprawdza przypisane dowody. Może to potrwać do 2 minut.
        </p>
      ) : null}
      {error ? <UncertainProposalError onRefresh={onRefresh} /> : null}
      {confirmedFailure ? (
        <ConfirmedProposalBlocker result={confirmedFailure} onRefresh={onRefresh} />
      ) : null}
    </section>
  );
}

function ConfirmedProposalBlocker({
  result,
  onRefresh
}: {
  result: ContentCodexSectionProposalResponse;
  onRefresh: () => void;
}) {
  const blocker = result.blockers[0];
  return (
    <div role="alert" className="mt-3 rounded-md border border-wait/30 bg-white p-3">
      <p className="text-sm font-semibold text-wait">
        {blocker?.label ?? "WILQ zatrzymał propozycję"}
      </p>
      <p className="mt-1 text-sm leading-6 text-slate-700">
        {blocker?.reason ?? "Nie powstała wersja, którą można bezpiecznie porównać."}
      </p>
      <p className="mt-1 text-sm leading-6 text-slate-700">
        Następny krok: {blocker?.next_step ?? result.safe_next_step}
      </p>
      <RefreshButton onRefresh={onRefresh} />
    </div>
  );
}

function UncertainProposalError({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div role="alert" className="mt-3 rounded-md border border-danger/30 bg-white p-3">
      <p className="text-sm font-semibold text-danger">Nie mamy potwierdzenia wyniku</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">
        Połączenie zakończyło się bez jednoznacznej odpowiedzi. Odśwież workspace przed ponownym
        uruchomieniem — child revision mogła zostać zapisana po stronie serwera.
      </p>
      <RefreshButton onRefresh={onRefresh} />
    </div>
  );
}

function RefreshButton({ onRefresh }: { onRefresh: () => void }) {
  return (
    <button
      type="button"
      onClick={onRefresh}
      className="mt-3 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-semibold text-action"
    >
      Odśwież workspace
    </button>
  );
}

function isCreatedResult(
  result: ContentCodexSectionProposalResponse | null
): result is ContentCodexSectionProposalResponse {
  return result?.status === "created" || result?.status === "idempotent";
}

function sectionCountLabel(count: number) {
  if (count === 1) return "sekcję";
  if (count >= 2 && count <= 4) return "sekcje";
  return "sekcji";
}
