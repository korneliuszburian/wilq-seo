import type { ContentDraftRevision } from "@wilq/shared-schemas";
import { ArrowRight } from "lucide-react";

import type { ContentCodexSectionProposalResponse } from "../lib/api";

export function ContentCodexSectionProposalResult({
  expectedWorkItemId,
  baseRevision,
  result,
  onRefresh
}: {
  expectedWorkItemId: string;
  baseRevision: ContentDraftRevision | null;
  result: ContentCodexSectionProposalResponse;
  onRefresh: () => void;
}) {
  const revision = result.revision;
  const metadata = revision?.proposal_metadata ?? null;
  const selectedSectionsPresent = Boolean(
    baseRevision &&
      revision &&
      result.selected_section_headings.every(
        (heading) =>
          baseRevision.sections.filter((section) => section.heading === heading).length === 1 &&
          revision.sections.filter((section) => section.heading === heading).length === 1
      )
  );
  const comparisonValid = Boolean(
    baseRevision &&
      revision &&
      result.work_item_id === expectedWorkItemId &&
      baseRevision.work_item_id === expectedWorkItemId &&
      result.work_item_id === baseRevision.work_item_id &&
      revision.work_item_id === baseRevision.work_item_id &&
      revision.base_revision_id === baseRevision.revision_id &&
      result.base_revision_id === baseRevision.revision_id &&
      metadata?.codex_run_id === result.run_id &&
      result.runtime.status === "completed" &&
      !result.runtime.external_call_attempted &&
      selectedSectionsPresent &&
      JSON.stringify(metadata?.selected_section_headings) ===
        JSON.stringify(result.selected_section_headings)
  );
  if (!revision || !result.quality_review || !metadata || !comparisonValid || !baseRevision) {
    return (
      <section role="alert" className="mt-4 rounded-md border border-danger/30 bg-danger/10 p-4">
        <p className="text-sm font-semibold text-danger">Nie można potwierdzić porównania wersji</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">
          Odśwież workspace i sprawdź najnowszą zapisaną wersję. Nie oceniaj tego wyniku z pamięci.
        </p>
        <RefreshButton onRefresh={onRefresh} />
      </section>
    );
  }

  const lineage = metadata.section_lineage;
  const evidenceCount = new Set(lineage.flatMap((section) => section.evidence_ids)).size;
  const claimCount = new Set(lineage.flatMap((section) => section.claim_ids)).size;
  const findings = result.quality_review.findings;

  return (
    <section
      className="mt-4 rounded-md border border-success/30 bg-success/5 p-3 sm:p-4"
      data-testid="codex-proposal-result"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-success">
            Poprawiona wersja aktualnego tekstu · wymaga review człowieka
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            Ocena WILQ: {qualityVerdictLabel(result.quality_review.verdict)}.
          </p>
        </div>
        <span className="rounded-md border border-wait/30 bg-white px-3 py-2 text-xs font-semibold text-wait">
          Szkic nie jest gotowy do publikacji
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
        <span className="rounded-md border border-line bg-white px-2 py-1">
          {evidenceCount} dowodów
        </span>
        <span className="rounded-md border border-line bg-white px-2 py-1">
          {claimCount} twierdzeń
        </span>
        <span className="rounded-md border border-line bg-white px-2 py-1">
          {result.runtime.external_call_attempted
            ? "wynik zablokowany po próbie narzędzia"
            : "brak zaobserwowanej próby narzędzia"}
        </span>
      </div>

      <div className="mt-4 space-y-4" data-testid="codex-proposal-diff">
        {result.selected_section_headings.map((heading) => {
          const baseSection = baseRevision.sections.find((section) => section.heading === heading);
          const childSection = revision.sections.find((section) => section.heading === heading);
          if (!baseSection || !childSection) return null;
          return (
            <article key={heading} className="min-w-0 rounded-md border border-line bg-white p-3">
              <h4 className="break-words text-sm font-semibold text-ink">{heading}</h4>
              <div className="mt-3 grid min-w-0 gap-3 lg:grid-cols-2">
                <VersionText label="Baza" body={baseSection.body_markdown} />
                <VersionText label="Propozycja Codexa" body={childSection.body_markdown} />
              </div>
            </article>
          );
        })}
      </div>

      {findings.length ? (
        <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3">
          <p className="text-sm font-semibold text-ink">Co nadal wymaga poprawy</p>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
            {findings.slice(0, 3).map((finding) => (
              <li key={`${finding.code}-${finding.affected_section ?? "draft"}`}>
                <span className="font-semibold">{finding.label}:</span> {finding.reason}
              </li>
            ))}
          </ul>
          {findings.length > 3 ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm font-semibold text-action">
                Pokaż pozostałe uwagi ({findings.length - 3})
              </summary>
              <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
                {findings.slice(3).map((finding) => (
                  <li key={`${finding.code}-${finding.affected_section ?? "draft"}`}>
                    <span className="font-semibold">{finding.label}:</span> {finding.reason}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}

      <div className="mt-4 rounded-md border border-danger/20 bg-white p-3 text-sm leading-6 text-slate-700">
        <p className="font-semibold text-danger">Semantyka nadal wymaga sprawdzenia człowieka</p>
        <p className="mt-1">
          Przeczytaj pełny tekst, porównaj go z dowodami i dopiero wtedy zapisz decyzję review.
          Codex nie zatwierdził zgodności ani obietnic w tej treści.
        </p>
      </div>

      <details className="mt-3 rounded-md border border-line bg-white">
        <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-action">
          Pokaż identyfikatory dowodów i twierdzeń
        </summary>
        <div className="border-t border-line p-3 text-xs leading-5 text-slate-600">
          <p className="break-all">
            Run Codex: {metadata.codex_run_id} · status: {result.runtime.status}
          </p>
          {lineage.map((section) => (
            <div key={section.heading} className="mt-3 first:mt-0">
              <p className="font-semibold text-ink">{section.heading}</p>
              <p className="mt-1 break-all">
                Dowody: {section.evidence_ids.length ? section.evidence_ids.join(", ") : "brak"}
              </p>
              <p className="mt-1 break-all">
                Twierdzenia: {section.claim_ids.length ? section.claim_ids.join(", ") : "brak"}
              </p>
            </div>
          ))}
        </div>
      </details>

      <button
        type="button"
        onClick={onRefresh}
        className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-action px-4 text-sm font-semibold text-white sm:w-auto"
      >
        Przejdź do review aktualnego tekstu
        <ArrowRight aria-hidden="true" size={16} />
      </button>
    </section>
  );
}

function VersionText({ label, body }: { label: string; body: string }) {
  return (
    <div className="min-w-0 rounded-md border border-line bg-surface p-3">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">{body}</p>
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

function qualityVerdictLabel(verdict: string) {
  if (verdict === "ready_for_human_review") return "gotowa do dokładnego review";
  if (verdict === "reviewable") return "możliwa do sprawdzenia";
  return "wymaga dalszych zmian";
}
