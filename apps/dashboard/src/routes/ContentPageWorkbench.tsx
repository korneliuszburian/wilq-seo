import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";

import {
  getContentWordPressExistingDraftUpdateReadiness,
  type ContentOpportunityEnrichment,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemWordPressDraftExecutionResponse
} from "../lib/api";
import { AcfCurrentVsProposedPanel } from "./AcfCurrentVsProposedPanel";
import { ContentDevTargetColumn } from "./ContentDevTargetColumn";
import { ContentFreshnessBanner } from "./ContentWorkflowBoundaryStates";
import { ContentMapConnectors } from "./ContentMapPrimitives";
import { ContentPublicPageColumn } from "./ContentPublicPageColumn";
import { ContentSignalColumn } from "./ContentSignalColumn";
import { ContentSourceStatusBar } from "./ContentSourceStatusBar";
import { ServiceProfileDecisionStrip } from "./ServiceProfileDecisionStrip";
import {
  blockedClaimsForWorkbench,
  contentMetricTilesForWorkbench,
  contentSignalRows,
  environmentLabel,
  evidenceRowsForWorkbench,
  queryChipsForWorkbench
} from "./contentPageWorkbenchModel";
import {
  defaultSectionBody,
  sectionOverrideKey,
  shortSectionTabLabel
} from "./contentWorkflowDraftSectionModel";
import type { ContentWorkflowSnapshot, WorkflowStepId } from "./contentWorkflowRuntime";
import { normalizedPath, selectDevPage } from "./contentWorkflowTarget";
import type {
  WordPressAuthoringProfileQuery,
  WordPressDraftActivationPacketQuery
} from "./contentWorkflowQueries";

type ContentPageWorkbenchActions = {
  executionPending: boolean;
  executionError: Error | null;
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
  runExecutionDryRunWithSections: (sections: Array<{ heading: string; body_markdown: string; evidence_ids: string[] }>) => void;
};

type DraftPreviewTrigger = "editor" | "preview";

function unique(values: string[]) {
  return [...new Set(values)];
}

export function ContentPageWorkbench({
  actions,
  authoringProfile,
  data,
  draftActivationPacket,
  enrichment,
  queue,
  activeStepId
}: {
  actions: ContentPageWorkbenchActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  activeStepId: WorkflowStepId;
}) {
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const profile = authoringProfile.data ?? null;
  const [selectedDevPageLink, setSelectedDevPageLink] = useState<string | null>(null);
  const devPage = selectDevPage(profile, item, selectedDevPageLink);
  const draftReadback = draftActivationPacket.data?.draft_readback ?? null;
  const dryRunReady = Boolean(
    draftActivationPacket.data?.dry_run_ready &&
      draftActivationPacket.data.execution_blockers.length === 0
  );
  const existingDraftUpdateReadiness = useQuery({
    queryKey: ["content-workflow", "existing-draft-update-readiness", item.id],
    queryFn: () => getContentWordPressExistingDraftUpdateReadiness(item.id),
    enabled: activeStepId === "draft"
  });
  const activeCandidate = queue.candidates.find(
    (candidate) => candidate.work_item_id === item.id
  );
  const publicUrl =
    item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? "";
  const sourceTitle = item.wordpress_title_or_h1 ?? draft?.title ?? item.topic;
  const publicSections = item.wordpress_section_headings ?? [];
  const devSections = devPage?.sections ?? [];
  const draftSections = useMemo(() => draft?.sections.slice(0, 5) ?? [], [draft]);
  const sectionDraftDefaults = useMemo(
    () =>
      Object.fromEntries(
        draftSections.map((section) => [
          sectionOverrideKey(section.heading),
          defaultSectionBody(section)
        ])
      ),
    [draftSections]
  );
  const [sectionEditorState, setSectionEditorState] = useState<{
    draftId: string | null;
    texts: Record<string, string>;
  }>({ draftId: null, texts: {} });
  const [selectedSectionKey, setSelectedSectionKey] = useState<string | null>(null);
  const [draftPreviewTrigger, setDraftPreviewTrigger] = useState<DraftPreviewTrigger | null>(null);
  const draftEditorId = draft?.id ?? null;
  const sectionTexts =
    sectionEditorState.draftId === draftEditorId
      ? sectionEditorState.texts
      : sectionDraftDefaults;
  const selectedSection =
    draftSections.find((section) => sectionOverrideKey(section.heading) === selectedSectionKey) ??
    draftSections[0] ??
    null;
  const selectedSectionEditorKey = selectedSection
    ? sectionOverrideKey(selectedSection.heading)
    : "";
  const selectedSectionText = selectedSection
    ? sectionTexts[selectedSectionEditorKey] ?? defaultSectionBody(selectedSection)
    : "";
  const sectionOverrides = draftSections
    .map((section) => ({
      heading: section.heading,
      body_markdown:
        sectionTexts[sectionOverrideKey(section.heading)] ?? defaultSectionBody(section),
      evidence_ids: unique(section.evidence_ids)
    }))
    .filter((section) => section.body_markdown.trim().length > 0);
  const signalRows = contentSignalRows(data, enrichment, activeCandidate);
  const blockedClaims = blockedClaimsForWorkbench(data);
  const evidenceRows = evidenceRowsForWorkbench(data, enrichment);
  const pageTitle = publicUrl && normalizedPath(publicUrl) === "/"
    ? `Strona główna ${environmentLabel(publicUrl)}`
    : sourceTitle || item.topic;
  const queryChips = queryChipsForWorkbench(data, enrichment, activeCandidate);
  const metricTiles = contentMetricTilesForWorkbench(item, devPage);
  const runDraftPreview = (trigger: DraftPreviewTrigger) => {
    setDraftPreviewTrigger(trigger);
    actions.runExecutionDryRunWithSections(sectionOverrides);
  };
  return (
    <section className="mb-5" data-active-workspace={activeStepId}>
      <ContentFreshnessBanner assessment={queue.freshness_assessment} />
      <div className="hidden sm:block">
        <ContentSourceStatusBar data={data} devPage={devPage} profile={profile} />
      </div>

      <div className={`grid gap-4 ${activeStepId === "draft" ? "xl:grid-cols-[minmax(0,1fr)_280px] 2xl:grid-cols-[minmax(0,1fr)_300px]" : "grid-cols-1"}`}>
        <div className="min-w-0 space-y-3">
          {activeStepId === "scope" ? (
            <section className="rounded-md border border-line bg-white p-4 shadow-sm" aria-labelledby="scope-workspace-title">
              <h2 id="scope-workspace-title" className="text-base font-semibold text-ink">
                Zakres strony i usługi
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                Sprawdź, czy wybrana strona, intencja i profil usługi opisują właściwe zadanie przed mapowaniem sekcji.
              </p>
              <div className="mt-3">
                <ServiceProfileDecisionStrip context={data.serviceProfileContext} />
              </div>
            </section>
          ) : null}

          {activeStepId === "section_map" ? (
            <>
              <div className="relative grid gap-3 lg:grid-cols-3">
                <ContentMapConnectors />
                <ContentPublicPageColumn
                  publicUrl={publicUrl}
                  publicSections={publicSections}
                  environmentLabel={publicUrl ? environmentLabel(publicUrl) : "publiczna treść"}
                />

                <ContentSignalColumn
                  queryChips={queryChips}
                  metricTiles={metricTiles}
                  signalRows={signalRows}
                />

                <ContentDevTargetColumn
                  profile={profile}
                  devPage={devPage}
                  devSections={devSections}
                  onSelectDevPage={setSelectedDevPageLink}
                />
              </div>

              <AcfCurrentVsProposedPanel devSections={devSections} draftSections={draftSections} />
            </>
          ) : null}

          {activeStepId === "draft" ? (
            <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className="rounded-md border border-line bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-ink">Tekst sekcji do szkicu</h2>
                </div>
                <span className="rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                  Niezapisany szkic roboczy
                </span>
              </div>

              {draftSections.length ? (
                <div className="mt-4">
                  <div
                    className="grid min-w-0 grid-cols-2 gap-x-2 gap-y-1 border-b border-line sm:flex sm:flex-wrap sm:gap-x-5"
                    data-testid="draft-section-tabs"
                  >
                    {draftSections.map((section) => {
                      const key = sectionOverrideKey(section.heading);
                      const active = key === selectedSectionEditorKey;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setSelectedSectionKey(key)}
                          className={`min-w-0 break-words border-b-2 px-1 pb-3 text-left text-sm font-semibold ${
                            active
                              ? "border-action text-action"
                              : "border-transparent text-slate-600"
                          }`}
                        >
                          {shortSectionTabLabel(section.heading)}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-3 border-b border-line pb-3 text-sm">
                    <span className="rounded-md border border-line bg-white px-3 py-2 text-slate-700">
                      Akapit
                    </span>
                    <span className="font-bold text-ink">B</span>
                    <span className="italic text-ink">I</span>
                    <span className="text-slate-500">link</span>
                    <span className="text-slate-500">lista</span>
                    <span className="ml-auto rounded-md border border-line bg-white px-3 py-2 text-slate-700">
                      Wstaw dowód
                    </span>
                  </div>
                  {selectedSection ? (
                    <label className="mt-4 block">
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <span className="text-lg font-semibold text-ink">
                          {selectedSection.heading}
                        </span>
                        <span className="text-xs text-slate-500">
                          Dowody: {selectedSection.evidence_ids.length || "brak"}
                        </span>
                      </div>
                      <textarea
                        className="min-h-40 w-full resize-y rounded-md border border-line bg-white p-4 text-sm leading-6 text-ink outline-none focus:border-action focus:ring-2 focus:ring-action/20"
                        value={selectedSectionText}
                        onChange={(event) =>
                          setSectionEditorState({
                            draftId: draftEditorId,
                            texts: {
                              ...sectionTexts,
                              [selectedSectionEditorKey]: event.target.value
                            }
                          })
                        }
                        aria-label={`Tekst sekcji ${selectedSection.heading}`}
                      />
                    </label>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => runDraftPreview("editor")}
                      disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending}
                      aria-controls="draft-preview-feedback"
                      className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {actions.executionPending && draftPreviewTrigger === "editor"
                        ? "Sprawdzam tekst..."
                        : "Sprawdź tekst szkicu"}
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setSectionEditorState({
                          draftId: draftEditorId,
                          texts: sectionDraftDefaults
                        })
                      }
                      className="inline-flex h-10 items-center rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink"
                    >
                      Przywróć brief
                    </button>
                  </div>
                  {draftPreviewTrigger === "editor" ? (
                    <DraftPreviewFeedback actions={actions} />
                  ) : null}
                </div>
              ) : (
                <p className="mt-4 rounded-md border border-wait/25 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
                  Brakuje paczki szkicu z sekcjami. Najpierw przygotuj brief i draft package dla tej
                  strony.
                </p>
              )}
            </div>

            <div className="rounded-md border border-line bg-white p-4 shadow-sm">
              <h2 className="text-base font-semibold text-ink">Podgląd sekcji na devie</h2>
              {draftReadback?.status === "available" ? (
                <div className="mt-3 rounded-md border border-success/25 bg-success/5 p-3">
                  <p className="text-sm font-semibold text-success">Dev draft odczytany</p>
                  <p className="mt-2 text-sm font-semibold text-ink">
                    {draftReadback.title || "Szkic bez tytułu"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {draftReadback.content_summary || "WordPress zwrócił szkic bez streszczenia."}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                    <span className="rounded-md border border-line bg-white px-2 py-1">
                      {draftReadback.content_word_count ?? 0} słów
                    </span>
                    <span className="rounded-md border border-line bg-white px-2 py-1">
                      {draftReadback.acf_field_count ?? 0} pól ACF
                    </span>
                  </div>
                  {draftReadback.link ? (
                    <a
                      href={draftReadback.link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-action/40 text-sm font-semibold text-action"
                    >
                      Otwórz podgląd na dev
                      <ExternalLink aria-hidden="true" size={14} />
                    </a>
                  ) : null}
                </div>
              ) : (
                <div className="mt-3 rounded-md border border-action/20 bg-white p-4">
                  <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                    {selectedSection ? shortSectionTabLabel(selectedSection.heading) : "Sekcja"}
                  </div>
                  <div className="mt-3 text-xl font-semibold leading-7 text-ink">
                    {selectedSection?.heading ?? pageTitle}
                  </div>
                  <p className="mt-3 line-clamp-6 text-sm leading-6 text-slate-700">
                    {selectedSectionText || "Wybierz sekcję szkicu po lewej."}
                  </p>
                </div>
              )}
              {devPage?.link ? (
                <a
                  href={devPage.link}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-action text-sm font-semibold text-white"
                >
                  Otwórz stronę dev
                  <ExternalLink aria-hidden="true" size={14} />
                </a>
              ) : null}
            </div>
            </div>
          ) : null}

          {activeStepId === "review" ? (
            <section className="rounded-md border border-wait/30 bg-wait/10 p-4" aria-labelledby="review-workspace-title">
              <h2 id="review-workspace-title" className="text-base font-semibold text-ink">
                Review konkretnej wersji szkicu
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                Ten krok pozostaje zamknięty, dopóki szkic nie ma zapisanej, niezmiennej wersji powiązanej z review.
              </p>
            </section>
          ) : null}

          {activeStepId === "dev_draft" ? (
            <section className="rounded-md border border-wait/30 bg-wait/10 p-4" aria-labelledby="dev-draft-workspace-title">
              <h2 id="dev-draft-workspace-title" className="text-base font-semibold text-ink">
                Szkic na devie
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                Przekazanie do WordPress pozostaje draft-only i wymaga akceptacji dokładnej wersji oraz śladu audytowego.
              </p>
            </section>
          ) : null}
        </div>

        {activeStepId === "draft" ? (
          <aside className="space-y-3 xl:sticky xl:top-4 xl:self-start">
          <div className="rounded-md border border-line bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Podgląd na devie</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Sprawdź propozycję na stronie roboczej i popraw sekcje przed review. Nic nie zostanie opublikowane.
            </p>
            <button
              type="button"
              onClick={() => runDraftPreview("preview")}
              disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending}
              aria-controls="draft-preview-feedback"
              className="mt-4 inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {actions.executionPending && draftPreviewTrigger === "preview"
                ? "Przygotowuję podgląd..."
                : "Przygotuj podgląd draftu"}
              <ArrowRight aria-hidden="true" size={16} />
            </button>
            {draftPreviewTrigger === "preview" ? (
              <DraftPreviewFeedback actions={actions} />
            ) : null}
            <p className="mt-3 text-xs leading-5 text-slate-500">
              Ten krok przygotowuje wyłącznie podgląd. Zapis wymaga osobnego zatwierdzenia.
            </p>
            {existingDraftUpdateReadiness.data ? (
              <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-slate-700">
                <div className="font-semibold text-wait">Aktualizacja istniejącego draftu</div>
                <p className="mt-1">
                  {existingDraftUpdateReadiness.data.blockers[0]?.label ??
                    "Przygotowanie aktualizacji wymaga osobnego review."}
                </p>
                {existingDraftUpdateReadiness.data.section_diff_preview.length ? (
                  <div className="mt-2 space-y-2">
                    {existingDraftUpdateReadiness.data.section_diff_preview.map((row) => (
                      <div key={row.heading} className="rounded border border-wait/20 bg-white p-2">
                        <div className="font-semibold text-ink">{row.heading}</div>
                        <div className="mt-1 text-slate-500">
                          Aktualne: {row.current_summary || "brak sekcji na devie"}
                        </div>
                        <div className="text-slate-700">
                          Proponowane: {row.proposed_summary || "brak propozycji"}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="rounded-md border border-line bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Źródła i twierdzenia</h2>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs text-slate-500">Dowody</div>
                <div className="mt-1 text-xl font-semibold text-ink">{evidenceRows.length}</div>
              </div>
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs text-slate-500">Twierdzenia do sprawdzenia</div>
                <div className="mt-1 text-xl font-semibold text-ink">{blockedClaims.length}</div>
              </div>
            </div>
            <details className="mt-3 rounded-md border border-line bg-white">
              <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-action">
                Pokaż ograniczenia i źródła
              </summary>
              <div className="border-t border-line p-3">
                <ul className="space-y-3">
                  {blockedClaims.slice(0, 3).map((claim) => (
                    <li key={claim.id}>
                      <div className="text-sm font-semibold text-ink">{claim.claim_text}</div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{claim.reason}</p>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 border-t border-line pt-3">
                  {evidenceRows.slice(0, 3).map((row) => (
                    <div key={`${row.label}-${row.summary}`} className="mt-2 first:mt-0">
                      <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                        {row.label}
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-600">
                        {row.summary}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </div>
          </aside>
        ) : null}
      </div>
    </section>
  );
}

function DraftPreviewFeedback({ actions }: { actions: ContentPageWorkbenchActions }) {
  if (actions.executionPending) {
    return (
      <div
        id="draft-preview-feedback"
        data-testid="draft-preview-feedback"
        role="status"
        className="mt-3 rounded-md border border-action/25 bg-action/5 p-3 text-sm leading-6 text-slate-700"
      >
        WILQ sprawdza podgląd w trybie bez zapisu.
      </div>
    );
  }
  if (actions.executionError) {
    return (
      <div
        id="draft-preview-feedback"
        data-testid="draft-preview-feedback"
        role="alert"
        className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm leading-6 text-slate-700"
      >
        <p className="font-semibold text-danger">Nie udało się sprawdzić podglądu</p>
        <p className="mt-1">Spróbuj ponownie. WILQ nie zapisał nic w WordPressie.</p>
      </div>
    );
  }

  const result = actions.executionResult;
  if (!result) return null;
  if (result.status === "dry_run_ready" && !result.external_write_attempted) {
    return (
      <div
        id="draft-preview-feedback"
        data-testid="draft-preview-feedback"
        role="status"
        className="mt-3 rounded-md border border-success/30 bg-success/10 p-3 text-sm leading-6 text-slate-700"
      >
        <p className="font-semibold text-success">Podgląd szkicu jest gotowy</p>
        <p className="mt-1">WILQ sprawdził propozycję bez wykonywania zapisu. Nic nie zapisano w WordPressie.</p>
      </div>
    );
  }

  const blocker = result.blockers[0];
  return (
    <div
      id="draft-preview-feedback"
      data-testid="draft-preview-feedback"
      role="alert"
      className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm leading-6 text-slate-700"
    >
      <p className="font-semibold text-danger">
        {blocker?.label ?? "Podgląd wymaga sprawdzenia technicznego"}
      </p>
      <p className="mt-1">
        {blocker?.reason ??
          "WILQ nie potwierdził bezpiecznego wyniku sprawdzenia. Nie przechodź do zapisu."}
      </p>
      {blocker?.next_step ? <p className="mt-1">Następny krok: {blocker.next_step}</p> : null}
    </div>
  );
}
