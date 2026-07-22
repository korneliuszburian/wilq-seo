import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  getContentWorkItemSemanticReview,
  type ContentCodexSectionProposalResponse,
  type ContentDraftRevision,
  type ContentDraftRevisionConflict,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionSection,
  type ContentInitialDraftResponse,
  type ContentOpportunityEnrichment,
  type ContentPlanningReviewConflict,
  type ContentSemanticReviewResponse
} from "../lib/api";
import { ContentFullPagePreview } from "./ContentFullPagePreview";
import {
  ContentPlanningReviewPanel,
  planningInventorySourceLabel
} from "./ContentPlanningReviewPanel";
import { ContentPlanningGenerationPanel } from "./ContentPlanningGenerationPanel";
import { ContentSourceStatusBar } from "./ContentSourceStatusBar";
import { ContentWordPressDraftActionWizard } from "./ContentWordPressDraftActionWizard";
import { planningPageAssetsReady } from "./contentPageWorkbenchModel";
import type { ContentWorkflowSnapshot, WorkflowStepId } from "./contentWorkflowRuntime";
import { selectDevPage } from "./contentWorkflowTarget";
import type {
  WordPressAuthoringProfileQuery,
  WordPressDraftActivationPacketQuery
} from "./contentWorkflowQueries";

type ContentPageWorkbenchActions = {
  planningReviewPending: boolean;
  planningReviewConflict: ContentPlanningReviewConflict | null;
  planningReviewError: Error | null;
  refreshPlanningWorkspace: () => void;
  savePlanningReview: (
    stage: "scope" | "section_map",
    decision: "approved" | "needs_changes",
    notes: string,
    checkedItems: string[],
    serviceCardId?: string
  ) => void;
  revisionSavePending: boolean;
  revisionSaveConflict: ContentDraftRevisionConflict | null;
  revisionSaveError: Error | null;
  revisionReviewPending: boolean;
  revisionReviewConflict: ContentDraftRevisionConflict | null;
  revisionReviewError: Error | null;
  saveDraftRevision: (title: string, sections: ContentDraftRevisionSection[]) => void;
  saveRevisionReview: (
    decision: ContentDraftRevisionDecision,
    notes: string,
    checkedItems: string[]
  ) => void;
  codexProposalPending: boolean;
  codexProposalError: Error | null;
  codexProposalResult: ContentCodexSectionProposalResponse | null;
  codexProposalBaseRevision: ContentDraftRevision | null;
  runCodexSectionProposal: (
    selection: { sectionIds: string[] } | { sectionHeadings: string[] }
  ) => void;
  refreshCodexProposalWorkspace: () => void;
  initialDraftPending: boolean;
  initialDraftError: Error | null;
  initialDraftResult: ContentInitialDraftResponse | null;
  generateInitialDraft: () => void;
  semanticReviewPending: boolean;
  semanticReviewError: Error | null;
  semanticReviewResult: ContentSemanticReviewResponse | null;
  generateSemanticReview: () => void;
};

function unique(values: string[]) {
  return [...new Set(values)];
}

function exactSemanticReviewForRevision(
  result: ContentSemanticReviewResponse | null,
  revision: ContentDraftRevision | null
) {
  if (
    !result ||
    !revision ||
    result.work_item_id !== revision.work_item_id ||
    result.revision_id !== revision.revision_id ||
    result.revision_digest !== revision.content_digest ||
    (result.review !== null &&
      result.review !== undefined &&
      (result.review.work_item_id !== revision.work_item_id ||
        result.review.revision_id !== revision.revision_id ||
        result.review.revision_digest !== revision.content_digest))
  ) {
    return null;
  }
  return result;
}

function authoringTargetSummary(
  handoffMode: string | undefined,
  contentSourceKind: string | null | undefined
) {
  if (handoffMode === "acf_flexible_content" || contentSourceKind === "acf" || contentSourceKind === "acf_flexible_content") {
    return "Profil strony wskazuje na ACF/flexible content. WILQ powinien przygotować mapowanie do konkretnych pól, a nie wysyłać tekst do the_content.";
  }
  if (handoffMode === "the_content" || contentSourceKind === "the_content") {
    return "Profil strony wskazuje na główny edytor WordPress (the_content/WYSIWYG). Wynikiem jest semantyczny HTML do tego miejsca.";
  }
  return "Sposób authoringu nie jest jeszcze potwierdzony. Najpierw trzeba odczytać profil strony; WILQ nie zgaduje pola docelowego.";
}

export function ContentPageWorkbench({
  actions,
  authoringProfile,
  data,
  draftActivationPacket,
  activeStepId
}: {
  actions: ContentPageWorkbenchActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  activeStepId: WorkflowStepId;
  initialSectionHeading?: string;
}) {
  const item = data.preflight.item;
  const wordpressHandoff = data.wordpressHandoff.handoff_result.handoff;
  const revisionBinding = wordpressHandoff?.revision_binding ?? null;
  const profile = authoringProfile.data ?? null;
  const devPage = selectDevPage(profile, item, null);
  const draftReadback = draftActivationPacket.data?.draft_readback ?? null;
  const revisionWorkspace = data.revisionWorkspace;
  const [reviewDecision, setReviewDecision] = useState<ContentDraftRevisionDecision>(
    "needs_changes"
  );
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewChecks, setReviewChecks] = useState({
    exactContentRead: false,
    evidenceChecked: false
  });
  const reviewCheckedItems = [
    reviewChecks.exactContentRead ? "Przeczytano dokładną treść tej wersji." : null,
    reviewChecks.evidenceChecked ? "Sprawdzono dowody przypisane do tej wersji." : null
  ].filter((item): item is string => item !== null);
  const latestRevision = revisionWorkspace.latest_revision;
  const fullDraftReady = Boolean(latestRevision?.page_assets);
  const staleLineage = latestRevision
    ? {
        evidence_ids: unique(
          latestRevision.sections.flatMap((section) => section.evidence_ids ?? [])
        ),
        source_material_ids: latestRevision.source_material_ids,
        knowledge_card_ids: latestRevision.knowledge_card_ids,
        source_connectors: unique(data.preflight.item.source_connectors)
      }
    : undefined;
  const semanticReviewQuery = useQuery({
    queryKey: [
      "content-workflow",
      "semantic-review",
      item.id,
      latestRevision?.revision_id ?? "missing"
    ],
    queryFn: () =>
      getContentWorkItemSemanticReview(
        item.id,
        latestRevision?.revision_id ?? "missing"
      ),
    enabled: (activeStepId === "draft" || activeStepId === "review") && Boolean(latestRevision),
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 2000 : false,
    retry: false
  });
  const semanticReviewResult =
    exactSemanticReviewForRevision(actions.semanticReviewResult, latestRevision) ??
    exactSemanticReviewForRevision(semanticReviewQuery.data ?? null, latestRevision);
  const semanticReviewStorageBlocked = semanticReviewResult?.blockers.some(
    (blocker) => blocker.code === "storage_activation_required"
  ) ?? false;
  const revisionEvidenceCount = latestRevision
    ? unique([
        ...(latestRevision.sections?.flatMap((section) => section.evidence_ids ?? []) ?? []),
        ...(latestRevision.faq?.flatMap((item) => item.evidence_ids ?? []) ?? []),
        ...(latestRevision.cta_blocks?.flatMap((item) => item.evidence_ids ?? []) ?? []),
        ...(latestRevision.internal_links?.flatMap((item) => item.evidence_ids ?? []) ?? [])
      ]).length
    : 0;
  const revisionStatusLabel = latestRevision
    ? revisionWorkspace.context_current
      ? "Aktualny draft · wersja zapisana"
      : "Zapisana wersja · wymaga odświeżenia"
    : "Szkic nie ma jeszcze zapisanej wersji";
  const generatedPlanning = data.planningWorkspace?.proposal ?? null;
  const initialDraftReady = Boolean(
      (!latestRevision || !revisionWorkspace.context_current) &&
      generatedPlanning?.generation_status === "codex_generated" &&
      generatedPlanning.proposal_id &&
      generatedPlanning.planning_input_digest &&
      planningPageAssetsReady(generatedPlanning.page_assets) &&
      data.planningWorkspace?.scope_current &&
      data.planningWorkspace.section_map_current
  );
  const initialDraftGenerating =
    actions.initialDraftPending || actions.initialDraftResult?.status === "generating";
  const semanticReviewGenerating = semanticReviewResult?.status === "generating";
  return (
    <section className="mb-5" data-active-workspace={activeStepId}>
      <div className="hidden sm:block">
        <ContentSourceStatusBar data={data} devPage={devPage} profile={profile} />
      </div>

      <div className="min-w-0 space-y-3">
          {activeStepId === "scope" && data.planningWorkspace ? (
            <>
              <ContentPlanningReviewPanel
                actions={{
                  conflict: actions.planningReviewConflict,
                  error: actions.planningReviewError,
                  pending: actions.planningReviewPending,
                  refresh: actions.refreshPlanningWorkspace,
                  save: actions.savePlanningReview
                }}
                planning={data.planningWorkspace}
                serviceCandidates={data.serviceProfileContext.service_candidates}
                inventorySourceLabel={planningInventorySourceLabel(
                  data.preflight.item.wordpress_acf_section_inventory_status,
                  data.preflight.item.wordpress_content_inventory_status,
                  data.preflight.item.wordpress_acf_section_headings ?? []
                )}
                inventorySourceKind={data.preflight.item.wordpress_content_source_kind}
                inventoryExtractionRegion={data.preflight.item.wordpress_content_extraction_region}
                staleLineage={staleLineage}
                existingContentProvenanceRequired={
                  data.preflight.item.wordpress_content_material_confidence === "review_required"
                }
                stage="scope"
              />
              <ContentPlanningGenerationPanel
                serviceCardId={data.serviceProfileContext.service_card_id}
                workItemId={item.id}
                scopeCurrent={data.planningWorkspace.scope_current}
              />
            </>
          ) : null}

          {activeStepId === "section_map" && data.planningWorkspace ? (
            <>
              <ContentPlanningGenerationPanel
                serviceCardId={data.serviceProfileContext.service_card_id}
                workItemId={item.id}
                scopeCurrent={data.planningWorkspace.scope_current}
              />
              <ContentPlanningReviewPanel
                actions={{
                  conflict: actions.planningReviewConflict,
                  error: actions.planningReviewError,
                  pending: actions.planningReviewPending,
                  refresh: actions.refreshPlanningWorkspace,
                  save: actions.savePlanningReview
                }}
                planning={data.planningWorkspace}
                serviceCandidates={data.serviceProfileContext.service_candidates}
                inventorySourceLabel={planningInventorySourceLabel(
                  data.preflight.item.wordpress_acf_section_inventory_status,
                  data.preflight.item.wordpress_content_inventory_status,
                  data.preflight.item.wordpress_acf_section_headings ?? []
                )}
                inventorySourceKind={data.preflight.item.wordpress_content_source_kind}
                inventoryExtractionRegion={data.preflight.item.wordpress_content_extraction_region}
                staleLineage={staleLineage}
                existingContentProvenanceRequired={
                  data.preflight.item.wordpress_content_material_confidence === "review_required"
                }
                stage="section_map"
              />
            </>
          ) : null}

        {activeStepId === "draft" ? (
          <section
            className="rounded-md border border-line bg-white p-4 shadow-sm"
            data-testid="content-draft-workbench"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-action">Wynik pracy</p>
                <h2 className="mt-1 text-lg font-semibold text-ink">
                  {fullDraftReady ? "Pełny draft HTML do review" : "Pełny draft HTML — niegotowy"}
                </h2>
                <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                  WILQ przygotowuje kompletną rewizję HTML do review. Ten ekran służy do przeczytania wyniku i sprawdzenia kontekstu; sposób dalszego odbioru wybierzesz dopiero po review.
                </p>
              </div>
              <span className="rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                {revisionStatusLabel}
              </span>
            </div>
            {!latestRevision || !fullDraftReady ? (
              <div className="mt-4 rounded-md border border-action/25 bg-action/5 p-4">
                <p className="text-sm font-semibold text-ink">{latestRevision ? "Odśwież pełną rewizję HTML" : "Wygeneruj pełną pierwszą wersję"}</p>
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  WILQ użyje aktualnego, zatwierdzonego planu, inventory, zapytań i dokładnych faktów. Wynik pozostanie niezatwierdzony i nie dotknie WordPressa.
                </p>
                <button
                  type="button"
                  onClick={actions.generateInitialDraft}
                  disabled={!initialDraftReady || actions.initialDraftPending}
                  className="mt-3 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {initialDraftGenerating ? "Tworzę pełną rewizję..." : latestRevision ? "Odśwież pełny draft" : "Wygeneruj pełny tekst"}
                </button>
                {!initialDraftReady ? (
                  <p className="mt-2 text-xs leading-5 text-slate-600">Najpierw przygotuj aktualny plan z kompletem page assets i zapisz jego zakres.</p>
                ) : null}
                {actions.initialDraftResult && actions.initialDraftResult.status !== "created" && !initialDraftGenerating ? (
                  <p className="mt-2 text-sm text-danger" role="alert">{actions.initialDraftResult.blockers[0]?.reason ?? actions.initialDraftResult.safe_next_step}</p>
                ) : null}
                {actions.initialDraftError ? <p className="mt-2 text-sm text-danger" role="alert">Nie udało się utworzyć pełnej wersji. WILQ nie zapisał częściowego tekstu.</p> : null}
              </div>
            ) : (
              <>
                <div className={`mt-4 rounded-md border p-4 ${fullDraftReady ? "border-line bg-surface" : "border-wait/30 bg-wait/10"}`}>
                  <p className="text-sm font-semibold text-ink">Gdzie ten wynik może trafić?</p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{fullDraftReady ? authoringTargetSummary(wordpressHandoff?.authoring_mode, data.preflight.item.wordpress_content_source_kind) : "Ta zapisana rewizja nie zawiera pełnych page assets, więc WILQ nie pokazuje jej jako gotowej treści ani nie udaje, że marketer ma co tutaj edytować."}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{fullDraftReady ? "Najpierw review exact revision. Dopiero potem można przygotować paczkę HTML albo osobny, draft-only handoff do WordPressa. Ten ekran niczego nie publikuje." : "Potrzebna jest pełna rewizja v2 z tytułem, leadem, sekcjami, FAQ, CTA i linkowaniem. Poprzednia rewizja pozostaje niezmieniona w historii."}</p>
                </div>
                {fullDraftReady ? <div className="mt-4" data-testid="content-full-draft-preview"><ContentFullPagePreview revision={latestRevision} proposal={generatedPlanning} /></div> : null}
              </>
            )}
          </section>
        ) : null}

          {activeStepId === "review" ? (
            <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
            {latestRevision?.schema_version === "wilq_content_draft_revision_v2" ? (
              <ContentFullPagePreview revision={latestRevision} proposal={generatedPlanning} />
            ) : null}
            <section className="rounded-md border border-line bg-white p-4 shadow-sm" aria-labelledby="review-workspace-title">
              <h2 id="review-workspace-title" className="text-base font-semibold text-ink">
                Review konkretnej wersji szkicu
              </h2>
              <div className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm leading-6 text-slate-700">
                <p className="font-semibold text-ink">Co robisz teraz?</p>
                <ol className="mt-1 list-inside list-decimal space-y-0.5">
                  <li>Przeczytaj podgląd całej strony.</li>
                  <li>Uruchom review semantyczne i potraktuj je jako listę uwag.</li>
                  <li>Zapisz własną decyzję dla tej exact revision.</li>
                </ol>
              </div>
              {latestRevision ? (
                <div className="mt-3 space-y-4">
                  <div className="rounded-md border border-line bg-surface p-3 text-sm leading-6 text-slate-700">
                    <p className="font-semibold text-ink">
                      Aktualny draft: {latestRevision.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      {latestRevision?.sections.length ?? 0} sekcji · {latestRevision?.faq.length ?? 0} FAQ ·{" "}
                      {latestRevision?.cta_blocks.length ?? 0} CTA · {latestRevision?.internal_links.length ?? 0} linków ·{" "}
                      {revisionEvidenceCount ?? "—"} źródeł
                    </p>
                    <details className="mt-2 text-xs text-slate-600">
                      <summary className="cursor-pointer font-semibold text-action">
                        Szczegóły techniczne wersji
                      </summary>
                      <p className="mt-2 break-all leading-5">
                        Exact digest: {latestRevision.content_digest}
                      </p>
                    </details>
                  </div>

                  <details className="rounded-md border border-line bg-surface px-3 py-2">
                    <summary className="cursor-pointer text-sm font-semibold text-action">
                      Źródła i powiązania dokumentu
                    </summary>
                    <div className="mt-3 space-y-3" data-testid="immutable-revision-content">
                      {latestRevision.sections.map((section) => (
                        <article
                          key={section.heading}
                          className="rounded-md border border-line bg-white p-3"
                        >
                          <h3 className="text-sm font-semibold text-ink">{section.heading}</h3>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                            {section.body_markdown}
                          </p>
                          <p className="mt-2 break-all text-xs leading-5 text-slate-500">
                            Źródła: {section.evidence_ids.length
                              ? section.evidence_ids.join(", ")
                              : "brak przypisanych źródeł"}
                          </p>
                        </article>
                      ))}
                      {latestRevision.faq.map((item) => (
                        <article
                          key={item.faq_id}
                          className="rounded-md border border-line bg-white p-3"
                        >
                          <h3 className="text-sm font-semibold text-ink">
                            FAQ: {item.question}
                          </h3>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                            {item.answer_markdown}
                          </p>
                          <p className="mt-2 break-all text-xs leading-5 text-slate-500">
                            Źródła: {item.evidence_ids.length
                              ? item.evidence_ids.join(", ")
                              : "brak przypisanych źródeł"}
                          </p>
                        </article>
                      ))}
                      {latestRevision.cta_blocks.map((item) => (
                        <article
                          key={item.cta_id}
                          className="rounded-md border border-line bg-white p-3"
                        >
                          <h3 className="text-sm font-semibold text-ink">
                            CTA: {item.placement}
                          </h3>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                            {item.body_markdown}
                          </p>
                          <p className="mt-2 break-all text-xs leading-5 text-slate-500">
                            Źródła: {item.evidence_ids.length
                              ? item.evidence_ids.join(", ")
                              : "brak przypisanych źródeł"}
                          </p>
                        </article>
                      ))}
                      {latestRevision.internal_links.map((item) => (
                        <article
                          key={item.link_id}
                          className="rounded-md border border-line bg-white p-3"
                        >
                          <h3 className="text-sm font-semibold text-ink">
                            Link: {item.anchor_text}
                          </h3>
                          <p className="mt-2 text-sm leading-6 text-slate-700">
                            Miejsce: {item.placement}
                          </p>
                          <p className="mt-2 break-all text-xs leading-5 text-slate-500">
                            Źródła: {item.evidence_ids.length
                              ? item.evidence_ids.join(", ")
                              : "brak przypisanych źródeł"}
                          </p>
                        </article>
                      ))}
                    </div>
                  </details>

                  <section className="rounded-md border border-action/25 bg-action/5 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-ink">
                          Advisory review semantyczne
                        </h3>
                        <p className="mt-1 text-sm leading-6 text-slate-700">
                          Sprawdza odpowiedź, kompletność, logikę, konkret, intencję,
                          wiarygodność i konwersję. Nie zatwierdza tekstu.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={actions.generateSemanticReview}
                        disabled={
                          actions.semanticReviewPending ||
                          semanticReviewGenerating ||
                          semanticReviewStorageBlocked
                        }
                        className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {actions.semanticReviewPending || semanticReviewGenerating
                          ? "Analizuję wersję..."
                          : semanticReviewStorageBlocked
                            ? "Automatyczne sprawdzenie chwilowo niedostępne"
                          : semanticReviewResult?.status === "ready"
                            ? "Sprawdź exact review"
                            : "Uruchom review semantyczne"}
                      </button>
                    </div>
                    {semanticReviewResult?.review ? (
                      <div className="mt-4 space-y-3" data-testid="semantic-review-result">
                        <p className="text-sm font-semibold text-ink">
                          {semanticReviewResult.review.findings.length
                            ? `${semanticReviewResult.review.findings.length} konkretnych uwag do decyzji`
                            : "Brak konkretnego findingu; nadal wymagane review człowieka"}
                        </p>
                        {semanticReviewResult.status === "stale" ? (
                          <p className="text-sm text-wait">
                            To review dotyczy starszego digestu. Uruchom je dla bieżącej wersji.
                          </p>
                        ) : null}
                        {semanticReviewResult.review.findings.map((finding) => (
                          <article
                            key={finding.finding_id}
                            className="rounded-md border border-line bg-white p-3"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <h4 className="text-sm font-semibold text-ink">{finding.label}</h4>
                              <span className="text-xs font-semibold uppercase text-slate-500">
                                {semanticSeverityLabel(finding.severity)}
                              </span>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-slate-700">
                              {finding.reason}
                            </p>
                            <p className="mt-2 text-sm font-semibold leading-6 text-action">
                              {finding.instruction}
                            </p>
                          </article>
                        ))}
                        <details className="rounded-md border border-line bg-white px-3 py-2">
                          <summary className="cursor-pointer text-sm font-semibold text-action">
                            Wymiary i exact binding
                          </summary>
                          <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
                            {semanticReviewResult.review.dimensions.map((dimension) => (
                              <li key={dimension.dimension}>
                                <span className="font-semibold text-ink">
                                  {semanticDimensionLabel(dimension.dimension)}:
                                </span>{" "}
                                {dimension.reason}
                              </li>
                            ))}
                          </ul>
                          <p className="mt-3 break-all text-xs text-slate-500">
                            Review {semanticReviewResult.review.review_id} · rewizja {semanticReviewResult.review.revision_digest}
                          </p>
                        </details>
                      </div>
                    ) : null}
                    {semanticReviewResult && semanticReviewResult.blockers.length ? (
                      <p className="mt-3 text-sm text-wait" role="alert">
                        {semanticReviewStorageBlocked
                          ? "Automatyczne sprawdzenie tekstu jest chwilowo niedostępne. Możesz nadal przeczytać pełną wersję, sprawdzić źródła i zapisać własną decyzję. Najbliższy krok techniczny: administrator musi włączyć trwały zapis review."
                          : semanticReviewResult.blockers[0]?.reason}
                      </p>
                    ) : null}
                    {actions.semanticReviewError || semanticReviewQuery.error ? (
                      <p className="mt-3 text-sm text-danger" role="alert">
                        Nie udało się odczytać lub uruchomić review. Tekst nie został zmieniony.
                      </p>
                    ) : null}
                  </section>

                  <label className="block text-sm font-semibold text-ink">
                    Decyzja
                    <select
                      aria-label="Decyzja dla wersji szkicu"
                      value={reviewDecision}
                      onChange={(event) =>
                        setReviewDecision(event.target.value as ContentDraftRevisionDecision)
                      }
                      className="mt-2 h-11 w-full rounded-md border border-line bg-white px-3 text-sm font-normal text-ink"
                    >
                      <option value="needs_changes">Wymaga zmian</option>
                      <option value="approved">Akceptuję tę wersję</option>
                      <option value="rejected">Odrzucam tę wersję</option>
                      <option value="deferred">Odkładam decyzję</option>
                    </select>
                  </label>

                  <label className="block text-sm font-semibold text-ink">
                    Notatka do decyzji
                    <textarea
                      aria-label="Notatka do decyzji"
                      value={reviewNotes}
                      onChange={(event) => setReviewNotes(event.target.value)}
                      className="mt-2 min-h-24 w-full resize-y rounded-md border border-line bg-white p-3 text-sm font-normal leading-6 text-ink"
                      placeholder="Co zaakceptowano albo co trzeba poprawić?"
                    />
                  </label>

                  <fieldset className="rounded-md border border-line bg-surface p-3">
                    <legend className="px-1 text-sm font-semibold text-ink">
                      Potwierdzenie review
                    </legend>
                    <label className="mt-2 flex items-start gap-2 text-sm leading-6 text-slate-700">
                      <input
                        type="checkbox"
                        checked={reviewChecks.exactContentRead}
                        onChange={(event) =>
                          setReviewChecks((current) => ({
                            ...current,
                            exactContentRead: event.target.checked
                          }))
                        }
                        className="mt-1"
                      />
                      Przeczytano dokładną treść tej wersji.
                    </label>
                    <label className="mt-2 flex items-start gap-2 text-sm leading-6 text-slate-700">
                      <input
                        type="checkbox"
                        checked={reviewChecks.evidenceChecked}
                        onChange={(event) =>
                          setReviewChecks((current) => ({
                            ...current,
                            evidenceChecked: event.target.checked
                          }))
                        }
                        className="mt-1"
                      />
                      Sprawdzono dowody przypisane do tej wersji.
                    </label>
                  </fieldset>

                  {reviewDecision === "approved" && revisionEvidenceCount === 0 ? (
                    <p className="rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-slate-700">
                      Nie można zaakceptować wersji bez przypisanych dowodów.
                    </p>
                  ) : null}
                  {reviewDecision === "approved" &&
                  revisionEvidenceCount > 0 &&
                  reviewCheckedItems.length < 2 ? (
                    <p className="text-sm text-slate-600">
                      Przed akceptacją zaznacz oba potwierdzenia review.
                    </p>
                  ) : null}
                  {reviewDecision !== "approved" && reviewNotes.trim().length === 0 ? (
                    <p className="text-sm text-slate-600">
                      Dodaj krótką notatkę: co trzeba poprawić albo dlaczego decyzja jest odłożona.
                    </p>
                  ) : null}

                  <button
                    type="button"
                    onClick={() =>
                      actions.saveRevisionReview(
                        reviewDecision,
                        reviewNotes,
                        reviewCheckedItems
                      )
                    }
                    disabled={
                      !revisionWorkspace.can_review ||
                      actions.revisionReviewPending ||
                      (reviewDecision === "approved" &&
                        (revisionEvidenceCount === 0 || reviewCheckedItems.length < 2)) ||
                      (reviewDecision !== "approved" && reviewNotes.trim().length === 0)
                    }
                    className="inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {actions.revisionReviewPending
                      ? "Zapisuję decyzję..."
                      : "Zapisz decyzję dla aktualnego draftu"}
                  </button>
                  <RevisionMutationFeedback
                    conflict={actions.revisionReviewConflict}
                    error={actions.revisionReviewError}
                    kind="review"
                  />
                </div>
              ) : (
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Najpierw zapisz niezmienną wersję szkicu. Review nie może dotyczyć samej paczki
                  outline.
                </p>
              )}
            </section>
            </div>
          ) : null}

          {activeStepId === "dev_draft" ? (
            <ContentWordPressDraftActionWizard
              key={`${revisionBinding?.work_item_id ?? item.id}:${revisionBinding?.revision_id ?? "missing"}:${revisionBinding?.content_digest ?? "missing"}`}
              actionId={draftActivationPacket.data?.action_id ?? null}
              binding={revisionBinding}
              draftReadback={draftReadback}
              handoffBlocker={data.wordpressHandoff.handoff_result.blockers[0] ?? null}
              revisionNumber={latestRevision?.revision_number ?? null}
            />
          ) : null}
      </div>
    </section>
  );
}

function semanticSeverityLabel(severity: "high" | "medium" | "low") {
  if (severity === "high") return "wysoki";
  if (severity === "medium") return "średni";
  return "niski";
}

function semanticDimensionLabel(dimension: string) {
  const labels: Record<string, string> = {
    answer_directness: "Bezpośredniość odpowiedzi",
    completeness: "Kompletność",
    logical_flow: "Logika",
    specificity: "Konkretność",
    repetition: "Powtórzenia",
    search_intent_fit: "Intencja wyszukiwania",
    buyer_fit: "Dopasowanie do odbiorcy",
    credibility: "Wiarygodność",
    conversion_clarity: "Następny krok"
  };
  return labels[dimension] ?? dimension;
}

function RevisionMutationFeedback({
  conflict,
  error,
  kind
}: {
  conflict: ContentDraftRevisionConflict | null;
  error: Error | null;
  kind: "save" | "review";
}) {
  if (conflict) {
    return (
      <div
        role="alert"
        data-testid={`${kind}-revision-conflict`}
        className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700"
      >
        <p className="font-semibold text-wait">Wersja na serwerze zmieniła się</p>
        <p className="mt-1">
          {kind === "save"
            ? "Twój tekst pozostał w edytorze i nie został nadpisany."
            : "Wybrana decyzja i notatka pozostały w formularzu."}
        </p>
        <p className="mt-1 break-all text-xs text-slate-600">
          Aktualna wersja: {conflict.current_revision_id ?? "brak zapisanej wersji"} · treść{" "}
          {conflict.current_digest ?? "brak aktualnego skrótu"}
        </p>
        <p className="mt-1">Następny krok: {conflict.safe_next_step}</p>
      </div>
    );
  }
  if (!error) return null;
  return (
    <div
      role="alert"
      className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm leading-6 text-slate-700"
    >
      <p className="font-semibold text-danger">
        {kind === "save" ? "Nie udało się zapisać wersji" : "Nie udało się zapisać decyzji"}
      </p>
      <p className="mt-1">Spróbuj ponownie. WILQ nie zmienił zapisanej wersji.</p>
    </div>
  );
}
