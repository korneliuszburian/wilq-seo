import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  getContentWordPressExistingDraftUpdateReadiness,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemSnapshotAuditRequest,
  type ContentWorkItemSnapshotHumanReviewRequest,
  type ContentWorkItemQualityReviewRequest,
  type ContentWorkItemQualityReviewResponse,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemRevisionPlanRequest,
  type ContentWorkItemRevisionPlanResponse,
  type ContentWorkItemStructuredDraftPreviewRequest,
  type ContentWorkItemStructuredDraftPreviewResponse,
  type ContentWorkItemStructuredDraftRuntimeRequest,
  type ContentWorkItemStructuredDraftRuntimeResponse,
  type ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
  type ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentOpportunityEnrichment,
  type WordPressAuthoringProfile
} from "../lib/api";
import {
  buildWorkflowSteps,
  type ContentWorkflowSnapshot
} from "./contentWorkflowRuntime";
import { normalizedPath, selectDevPage } from "./contentWorkflowTarget";
import { AcfCurrentVsProposedPanel } from "./AcfCurrentVsProposedPanel";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { WorkflowStepsList } from "./WorkflowStepsList";
import {
  ContentFreshnessBanner,
  ContentWorkflowError,
  ContentWorkflowEmptyQueue,
  ContentWorkflowSelectedLoading
} from "./ContentWorkflowBoundaryStates";
import { wordpressDraftExecutionStatusText } from "./WordPressDraftStatus";
import { ContentSourceStatusBar } from "./ContentSourceStatusBar";
import { ContentMapConnectors } from "./ContentMapPrimitives";
import { ContentPageIdentityCard } from "./ContentPageIdentityCard";
import { ContentSignalColumn } from "./ContentSignalColumn";
import { ContentDevTargetColumn } from "./ContentDevTargetColumn";
import { ContentPublicPageColumn } from "./ContentPublicPageColumn";
import { ContentOpportunityEnrichmentPanel } from "./ContentOpportunityEnrichmentPanel";
import { ClaimLedgerGatePanel } from "./ClaimLedgerGatePanel";
import { WorkflowSafetyPanels } from "./WorkflowSafetyPanels";
import { MobileContentTriage } from "./MobileContentTriage";
import { ContentWorkbenchHeader } from "./ContentWorkbenchHeader";
import { MobileDecisionCard } from "./MobileDecisionCard";
import { ContentWorkflowDecisionPanel } from "./ContentWorkflowDecisionPanel";
import { WordPressDraftWorkPanel as WordPressDraftWorkPanelView } from "./WordPressDraftWorkPanel";
import { ContentSectionWritingWorkbench as ContentSectionWritingWorkbenchView } from "./ContentSectionWritingWorkbench";
import { ServiceProfileDecisionStrip } from "./ServiceProfileDecisionStrip";
import {
  WorkflowOperatorControls as WorkflowOperatorControlsView,
  type WorkflowControlItem
} from "./WorkflowOperatorControls";
import { ContentWorkflowBlockedCandidate } from "./ContentWorkflowBlockedCandidate";
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
import { WorkflowProofSummary } from "./WorkflowProofSummary";
import {
  useContentWorkflowQueries,
  type ContentOpportunityEnrichmentQuery,
  type ContentWorkItemQueueQuery,
  type ContentWorkflowSnapshotQuery,
  type WordPressAuthoringProfileQuery,
  type WordPressDraftActivationPacketQuery,
  type WordPressDraftWriteReadinessQuery,
  type ContentWorkItemQueueCandidate
} from "./contentWorkflowQueries";

type ContentWorkflowActions = ReturnType<typeof useContentWorkflowActions>;
type ContentWorkflowMutations = ReturnType<typeof useContentWorkflowMutations>;
export function ContentWorkflowSurface() {
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<string | null>(null);
  const {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    draftWriteReadiness,
    enrichment,
    queue,
    selectedCandidate,
    workflow
  } = useContentWorkflowQueries(selectedWorkItemId);

  return (
    <ContentWorkflowRouteState
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      onSelectWorkItem={setSelectedWorkItemId}
    />
  );
}

function ContentWorkflowRouteState({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueQuery;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (queue.isLoading) return <LoadingBand />;
  if (queue.error || !queue.data) return <ContentWorkflowError />;
  return (
    <ContentWorkflowQueueReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue.data}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowQueueReady({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (!activeWorkItemId) return <ContentWorkflowEmptyQueue queue={queue} />;
  if (selectedCandidate?.recommended_mode === "block") {
    return (
      <ContentWorkflowBlockedCandidate
        queue={queue}
        selectedCandidate={selectedCandidate}
        selectedWorkItemId={activeWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
    );
  }
  return (
    <ContentWorkflowSelectedReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowSelectedReady({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (selectedCandidate === null) return <ContentWorkflowError />;
  if (workflow.isLoading) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
      />
    );
  }
  if (workflow.error || !workflow.data) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
        error
      />
    );
  }
  return (
    <ContentWorkflowLoaded
      data={workflow.data}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment.data?.enrichment ?? null}
      queue={queue}
      selectedWorkItemId={activeWorkItemId}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowLoaded({
  data,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  data: ContentWorkflowSnapshot;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const actions = useContentWorkflowActions(
    data,
    selectedWorkItemId,
    authoringProfile.data ?? null
  );
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"marketer" | "technical">("marketer");
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="w-full px-4 py-5 lg:px-7 2xl:px-8">
      <div className="lg:hidden">
        <MobileContentTriage data={data} onOpenDetails={() => setDetailsOpen(true)} />
      </div>
      <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-white px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Widok pracy</p>
          <p className="mt-1 text-sm text-slate-700">
            {viewMode === "marketer"
              ? "Decyzja, blocker i następny bezpieczny krok."
              : "Dowody, audyt i kontrakty do sprawdzenia technicznego."}
          </p>
        </div>
        <div className="flex rounded-md border border-line bg-surface p-1" role="group" aria-label="Tryb widoku">
          <button
            type="button"
            aria-pressed={viewMode === "marketer"}
            onClick={() => {
              setViewMode("marketer");
              setDetailsOpen(false);
            }}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "marketer" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Marketer
          </button>
          <button
            type="button"
            aria-pressed={viewMode === "technical"}
            onClick={() => {
              setViewMode("technical");
              setDetailsOpen(true);
            }}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "technical" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Audyt techniczny
          </button>
        </div>
      </section>
          <ContentPageWorkbench
            actions={actions}
            authoringProfile={authoringProfile}
            data={data}
            draftActivationPacket={draftActivationPacket}
            enrichment={enrichment}
            queue={queue}
            onOpenDetails={() => setDetailsOpen(true)}
          />
      <details
        id="content-workflow-details"
        className="mb-6 rounded-md border border-line bg-white"
        open={detailsOpen}
        onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
      >
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
          {viewMode === "technical"
            ? "Audyt techniczny: workflow, kolejka i ślad działania"
            : "Szczegóły workflow, kolejka i audyt techniczny"}
        </summary>
        {detailsOpen ? (
          <div className="border-t border-line p-4">
            <ContentWorkflowDecisionPanel data={data} queue={queue} steps={steps} />
            <WordPressDraftWorkPanelView
              actions={actions}
              authoringProfile={authoringProfile}
              draftActivationPacket={draftActivationPacket}
              draftWriteReadiness={draftWriteReadiness}
            />
            <ContentSectionWritingWorkbenchView
              actions={actions}
              authoringProfile={authoringProfile}
              data={data}
              draftActivationPacket={draftActivationPacket}
            />
            <ContentCandidateQueuePanel
              queue={queue}
              selectedWorkItemId={selectedWorkItemId}
              onSelectWorkItem={onSelectWorkItem}
            />
            <WorkflowOperatorControlsView
              controls={workflowControlItems(data, actions)}
              topic={data.preflight.item.topic}
            />
            <WorkflowProofSummary data={data} />
            <ClaimLedgerGatePanel data={data} />
            <ContentOpportunityEnrichmentPanel enrichment={enrichment} />
            <WorkflowStepsList steps={steps} />
            <WorkflowSafetyPanels
              structuredPreviewResult={actions.structuredPreviewResult}
              draftSafetyText={draftSafetyText(draft?.publish_ready)}
              structuredRuntimeSafetyText={structuredRuntimeSafetyText(actions.structuredRuntimeResult)}
              structuredPreviewSafetyText={structuredPreviewSafetyText(actions.structuredPreviewResult)}
              qualityReviewSafetyText={qualityReviewSafetyText(actions.qualityReview)}
              revisionPlanSafetyText={revisionPlanSafetyText(actions.revisionPlan)}
              acfPreviewSafetyText={acfPreviewSafetyText(actions.acfPreviewResult)}
              handoffSafetyText={handoffSafetyText(handoff?.publish_allowed)}
              executionSafetyText={wordpressExecutionSafetyText(actions.executionResult)}
              measurementTitle={data.measurementWindow.outcome_blockers[0]?.label ?? "Nie wolno jeszcze oceniać efektu"}
              measurementSafetyText={measurementSafetyText(window)}
              qualityReview={actions.qualityReview}
              revisionPlan={actions.revisionPlan}
              acfPreviewResult={actions.acfPreviewResult}
            />
          </div>
        ) : null}
      </details>
    </main>
  );
}

function ContentPageWorkbench({
  actions,
  authoringProfile,
  data,
  draftActivationPacket,
  enrichment,
  queue,
  onOpenDetails
}: {
  actions: ContentWorkflowActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  onOpenDetails: () => void;
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
  const sourceSummary = [
    publicSections.length ? `${publicSections.length} sekcji publicznych` : null,
    devSections.length ? `${devSections.length} sekcji na devie` : null,
    item.source_connectors.includes("google_search_console") ? "GSC" : null,
    item.source_connectors.includes("ahrefs") ? "Ahrefs" : null
  ].filter(Boolean).join(" · ");

  return (
    <section className="mb-5">
      <ContentWorkbenchHeader />

      <ContentFreshnessBanner assessment={queue.freshness_assessment} />
      <ContentSourceStatusBar data={data} devPage={devPage} profile={profile} />
      <MobileDecisionCard
        candidate={activeCandidate ?? null}
        publicUrl={publicUrl}
        topic={pageTitle}
        queue={queue}
        onOpenDetails={onOpenDetails}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px] 2xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 space-y-3">
          <ContentPageIdentityCard
            pageTitle={pageTitle}
            publicUrl={publicUrl}
            sourceSummary={sourceSummary}
            recommendedModeLabel={
              activeCandidate?.recommended_mode_label ?? data.preflight.preflight_verdict.recommended_mode
            }
            fallbackDescription={
              activeCandidate?.reason ?? "Porównaj publiczną stronę, sygnały i aktualny dev draft."
            }
          >
            <ServiceProfileDecisionStrip context={data.serviceProfileContext} />
          </ContentPageIdentityCard>

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

          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className="rounded-md border border-line bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-ink">Tekst sekcji do szkicu</h2>
                </div>
                <span className="rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                  Wersja 1
                </span>
              </div>

              {draftSections.length ? (
                <div className="mt-4">
                  <div className="flex gap-5 border-b border-line">
                    {draftSections.map((section) => {
                      const key = sectionOverrideKey(section.heading);
                      const active = key === selectedSectionEditorKey;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setSelectedSectionKey(key)}
                          className={`border-b-2 px-1 pb-3 text-sm font-semibold ${
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
                      onClick={() => actions.runExecutionDryRunWithSections(sectionOverrides)}
                      disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending}
                      className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Sprawdź tekst szkicu
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
        </div>

        <aside className="space-y-3 xl:sticky xl:top-4 xl:self-start">
          <div className="rounded-md border border-line bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Podgląd na devie</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Sprawdź propozycję na stronie roboczej i popraw sekcje przed review. Nic nie zostanie opublikowane.
            </p>
            <button
              type="button"
              onClick={() => actions.runExecutionDryRunWithSections(sectionOverrides)}
              disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending}
              className="mt-4 inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              Przygotuj podgląd draftu
              <ArrowRight aria-hidden="true" size={16} />
            </button>
            <a
              href="#content-workflow-details"
              className="mt-3 inline-flex h-11 w-full items-center justify-center rounded-md border border-action/40 bg-white px-4 text-sm font-semibold text-action"
            >
              Pokaż kontekst
            </a>
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
      </div>
    </section>
  );
}
function useContentWorkflowActions(
  data: ContentWorkflowSnapshot,
  selectedWorkItemId: string,
  authoringProfile: WordPressAuthoringProfile | null
) {
  const mutations = useContentWorkflowMutations(selectedWorkItemId);
  return contentWorkflowActions(data, mutations, authoringProfile);
}

function useContentWorkflowMutations(selectedWorkItemId: string) {
  const queryClient = useQueryClient();
  const refreshWorkflow = () => {
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", selectedWorkItemId]
    });
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "wordpress-draft-activation-packet", selectedWorkItemId]
    });
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "wordpress-draft-write-readiness"]
    });
  };
  const reviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemSnapshotHumanReviewRequest) =>
      saveContentWorkItemSnapshotHumanReview(request, selectedWorkItemId),
    onSuccess: refreshWorkflow
  });
  const auditMutation = useMutation({
    mutationFn: (request: ContentWorkItemSnapshotAuditRequest) =>
      saveContentWorkItemSnapshotAudit(request, selectedWorkItemId),
    onSuccess: refreshWorkflow
  });
  const structuredRuntimeMutation = useMutation({
    mutationFn: postContentWorkItemStructuredDraftRuntime
  });
  const structuredPreviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemStructuredDraftPreviewRequest) =>
      postContentWorkItemStructuredDraftPreview(request, selectedWorkItemId)
  });
  const qualityReviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemQualityReviewRequest) =>
      postContentWorkItemQualityReview(request, selectedWorkItemId)
  });
  const revisionPlanMutation = useMutation({
    mutationFn: (request: ContentWorkItemRevisionPlanRequest) =>
      postContentWorkItemRevisionPlan(request, selectedWorkItemId)
  });
  const acfPreviewMutation = useMutation({
    mutationFn: postContentWorkItemWordPressAuthoringPayloadPreview
  });
  const executionMutation = useMutation({ mutationFn: postContentWorkItemWordPressDraftExecution });
  return {
    reviewMutation,
    auditMutation,
    structuredRuntimeMutation,
    structuredPreviewMutation,
    qualityReviewMutation,
    revisionPlanMutation,
    acfPreviewMutation,
    executionMutation
  };
}

function contentWorkflowActions(
  data: ContentWorkflowSnapshot,
  mutations: ContentWorkflowMutations,
  authoringProfile: WordPressAuthoringProfile | null
) {
  const structuredRuntimeResult = runtimeResultFrom(mutations.structuredRuntimeMutation.data);
  const qualityReview = qualityReviewFrom(mutations.qualityReviewMutation.data);
  return {
    reviewPending: mutations.reviewMutation.isPending,
    auditPending: mutations.auditMutation.isPending,
    structuredRuntimePending: mutations.structuredRuntimeMutation.isPending,
    structuredPreviewPending: mutations.structuredPreviewMutation.isPending,
    qualityReviewPending: mutations.qualityReviewMutation.isPending,
    revisionPlanPending: mutations.revisionPlanMutation.isPending,
    acfPreviewPending: mutations.acfPreviewMutation.isPending,
    executionPending: mutations.executionMutation.isPending,
    authoringProfileReady: Boolean(authoringProfile),
    structuredRuntimeResult,
    structuredPreviewResult: previewResultFrom(mutations.structuredPreviewMutation.data),
    qualityReview,
    revisionPlan: revisionPlanFrom(mutations.revisionPlanMutation.data),
    acfPreviewResult: acfPreviewResultFrom(mutations.acfPreviewMutation.data),
    executionResult: executionResultFrom(mutations.executionMutation.data),
    runStructuredRuntime: () =>
      submitIfReady(structuredRuntimeDryRunRequest(data), mutations.structuredRuntimeMutation.mutate),
    runStructuredPreview: () =>
      submitIfReady(
        structuredPreviewRequest(data, structuredRuntimeResult),
        mutations.structuredPreviewMutation.mutate
      ),
    runQualityReview: () =>
      submitIfReady(
        qualityReviewRequest(data, structuredRuntimeResult),
        mutations.qualityReviewMutation.mutate
      ),
    runRevisionPlan: () =>
      submitIfReady(revisionPlanRequest(data, qualityReview), mutations.revisionPlanMutation.mutate),
    saveReview: () =>
      submitIfReady(
        humanReviewRequest(data, data.draftPackage.draft_package_result.draft_package),
        mutations.reviewMutation.mutate
      ),
    saveAudit: () => submitIfReady(auditRequest(data), mutations.auditMutation.mutate),
    runAcfPreview: () =>
      submitIfReady(
        acfPreviewRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff,
          authoringProfile
        ),
        mutations.acfPreviewMutation.mutate
      ),
    runExecutionDryRun: () =>
      submitIfReady(
        wordpressExecutionRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff
        ),
        mutations.executionMutation.mutate
      ),
    runExecutionDryRunWithSections: (sectionOverrides: WordPressDraftSectionOverride[]) =>
      submitIfReady(
        wordpressExecutionRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff,
          sectionOverrides
        ),
        mutations.executionMutation.mutate
      )
  };
}

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type WordPressHandoff = ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
type WordPressDraftSectionOverride = NonNullable<
  ContentWorkItemWordPressDraftExecutionRequest["section_overrides"]
>[number];

function runtimeResultFrom(response: ContentWorkItemStructuredDraftRuntimeResponse | undefined) {
  return response?.runtime_result ?? null;
}

function previewResultFrom(response: ContentWorkItemStructuredDraftPreviewResponse | undefined) {
  return response?.preview_result ?? null;
}

function qualityReviewFrom(response: ContentWorkItemQualityReviewResponse | undefined) {
  return response?.quality_review ?? null;
}

function revisionPlanFrom(response: ContentWorkItemRevisionPlanResponse | undefined) {
  return response?.revision_plan ?? null;
}

function executionResultFrom(
  response: ContentWorkItemWordPressDraftExecutionResponse | undefined
) {
  return response?.execution_result ?? null;
}

function acfPreviewResultFrom(
  response: ContentWorkItemWordPressAuthoringPayloadPreviewResponse | undefined
) {
  return response?.preview_result ?? null;
}

function submitIfReady<TRequest>(request: TRequest | null, submit: (request: TRequest) => void) {
  if (request) submit(request);
}

function structuredRuntimeDryRunRequest(
  data: ContentWorkflowSnapshot
): ContentWorkItemStructuredDraftRuntimeRequest | null {
  const contract = data.structuredGeneration.structured_generation_result.contract;
  if (!contract) return null;
  return {
    contract,
    model: "gpt-5",
    mode: "dry_run"
  };
}

function structuredPreviewRequest(
  data: ContentWorkflowSnapshot,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
): ContentWorkItemStructuredDraftPreviewRequest | null {
  const contract = data.structuredGeneration.structured_generation_result.contract;
  const output = runtimeResult?.output;
  if (!contract || !output) return null;
  return { contract, output };
}

function qualityReviewRequest(
  data: ContentWorkflowSnapshot,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
): ContentWorkItemQualityReviewRequest | null {
  const draft = data.draftPackage.draft_package_result.draft_package;
  const output = runtimeResult?.output;
  if (!draft || !output) return null;
  return {
    item: data.preflight.item,
    draft_package: draft,
    structured_output: output,
    claim_ledger: data.claimLedger,
    sales_brief: data.salesBrief.sales_brief_result.brief ?? null,
    duplicate_risk: "clear"
  };
}

function revisionPlanRequest(
  data: ContentWorkflowSnapshot,
  qualityReview: ContentWorkItemQualityReviewResponse["quality_review"] | null
): ContentWorkItemRevisionPlanRequest | null {
  if (!qualityReview) return null;
  return {
    item: data.preflight.item,
    quality_review: qualityReview
  };
}

function humanReviewRequest(
  data: ContentWorkflowSnapshot,
  draft: DraftPackage
): ContentWorkItemSnapshotHumanReviewRequest | null {
  if (!draft) return null;
  const item = data.preflight.item;
  return {
    review: {
      id: `human_review_${item.id}`,
      work_item_id: item.id,
      stage: "draft_package",
      reviewed_by: "wilku",
      decision: "approved",
      notes:
        "Operator zatwierdził brief, ryzykowne twierdzenia i paczkę szkicu do przygotowania szkicu WordPress.",
      checked_items: [
        "Brief i paczka szkicu są zgodne z dowodami WILQ.",
        "Ryzykowne twierdzenia zostały usunięte albo obsłużone.",
        "Szkic pozostaje materiałem do sprawdzenia, nie publikacją."
      ],
      evidence_ids: unique(item.evidence_ids),
      blocked_claims_handled: unique(draft.claims_removed_or_blocked),
      draft_package_id: draft.id
    }
  };
}

function auditRequest(data: ContentWorkflowSnapshot): ContentWorkItemSnapshotAuditRequest | null {
  const item = data.preflight.item;
  const review = data.humanReview.review;
  if (!review) return null;
  return {
    audit: {
      audit_id: `audit_${item.id}`,
      actor: "wilku",
      reason:
        "Operator zatwierdził przekazanie wyłącznie w trybie szkicu. WordPress może dostać wyłącznie szkic.",
      evidence_ids: unique(item.evidence_ids),
      human_review_id: review.id
    }
  };
}

function wordpressExecutionRequest(
  draft: DraftPackage,
  handoff: WordPressHandoff,
  sectionOverrides: WordPressDraftSectionOverride[] = []
): ContentWorkItemWordPressDraftExecutionRequest | null {
  if (!draft || !handoff) return null;
  const request: ContentWorkItemWordPressDraftExecutionRequest = {
    handoff,
    draft_package: draft,
    mode: "dry_run",
    write_authorization: null
  };
  if (sectionOverrides.length) {
    request.section_overrides = sectionOverrides;
  }
  return request;
}

function acfPreviewRequest(
  draft: DraftPackage,
  handoff: WordPressHandoff,
  authoringProfile: WordPressAuthoringProfile | null
): ContentWorkItemWordPressAuthoringPayloadPreviewRequest | null {
  if (!draft || !handoff || !authoringProfile) return null;
  return {
    handoff,
    draft_package: draft,
    authoring_profile: authoringProfile
  };
}

function workflowControlItems(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem[] {
  const draft = data.draftPackage.draft_package_result.draft_package;
  const review = data.humanReview.review;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  return [
    {
      label: review ? "Sprawdzenie zapisane" : "Zatwierdź sprawdzenie",
      disabledReason: reviewControlDisabledReason(data, Boolean(draft), actions.reviewPending),
      pending: actions.reviewPending,
      onClick: actions.saveReview
    },
    {
      label: handoff ? "Audyt zapisany" : "Zapisz audyt przekazania",
      disabledReason: auditControlDisabledReason(data, actions.auditPending),
      pending: actions.auditPending,
      onClick: actions.saveAudit
    },
    structuredRuntimeControlItem(data, actions),
    structuredPreviewControlItem(data, actions),
    qualityReviewControlItem(actions),
    revisionPlanControlItem(actions),
    {
      label: actions.acfPreviewResult ? "Mapowanie ACF gotowe" : "Pokaż mapowanie ACF",
      disabledReason: acfPreviewControlDisabledReason(
        Boolean(draft),
        Boolean(handoff),
        actions.authoringProfileReady,
        actions.acfPreviewPending,
        actions.acfPreviewResult
      ),
      pending: actions.acfPreviewPending,
      onClick: actions.runAcfPreview
    },
    {
      label: actions.executionResult ? "Podgląd szkicu gotowy" : "Sprawdź podgląd szkicu",
      disabledReason: executionControlDisabledReason(
        Boolean(draft),
        Boolean(handoff),
        actions.executionPending,
        actions.executionResult
      ),
      pending: actions.executionPending,
      onClick: actions.runExecutionDryRun
    }
  ];
}

function structuredRuntimeControlItem(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem {
  return {
    label: actions.structuredRuntimeResult ? "Próba szkicu gotowa" : "Sprawdź gotowość szkicu",
    disabledReason: structuredRuntimeControlDisabledReason(
      data,
      actions.structuredRuntimePending,
      actions.structuredRuntimeResult
    ),
    pending: actions.structuredRuntimePending,
    onClick: actions.runStructuredRuntime
  };
}

function structuredPreviewControlItem(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem {
  return {
    label: actions.structuredPreviewResult ? "Podgląd treści gotowy" : "Pokaż podgląd treści",
    disabledReason: structuredPreviewControlDisabledReason(
      data,
      actions.structuredPreviewPending,
      actions.structuredPreviewResult,
      actions.structuredRuntimeResult
    ),
    pending: actions.structuredPreviewPending,
    onClick: actions.runStructuredPreview
  };
}

function qualityReviewControlItem(actions: ContentWorkflowActions): WorkflowControlItem {
  return {
    label: actions.qualityReview ? "Ocena jakości gotowa" : "Sprawdź jakość szkicu",
    disabledReason: qualityReviewControlDisabledReason(
      actions.qualityReviewPending,
      actions.qualityReview,
      actions.structuredRuntimeResult
    ),
    pending: actions.qualityReviewPending,
    onClick: actions.runQualityReview
  };
}

function revisionPlanControlItem(actions: ContentWorkflowActions): WorkflowControlItem {
  return {
    label: actions.revisionPlan ? "Plan poprawki gotowy" : "Pokaż plan poprawki",
    disabledReason: revisionPlanControlDisabledReason(
      actions.revisionPlanPending,
      actions.revisionPlan,
      actions.qualityReview
    ),
    pending: actions.revisionPlanPending,
    onClick: actions.runRevisionPlan
  };
}

function draftSafetyText(publishReady?: boolean) {
  if (publishReady) return "Szkic wymaga zatrzymania, bo został oznaczony jako gotowy do publikacji.";
  return "Szkic jest paczką do review, nie tekstem do automatycznej publikacji.";
}

function handoffSafetyText(publishAllowed?: boolean) {
  if (publishAllowed === undefined) {
    return "WordPress nie dostaje jeszcze szkicu. Najpierw człowiek musi zatwierdzić brief, ryzykowne twierdzenia i paczkę szkicu, a WILQ musi zapisać audyt.";
  }
  if (publishAllowed) {
    return "Publikacja wymaga osobnej blokady, bo WILQ nie powinien publikować automatycznie.";
  }
  return "Handoff przygotowuje tylko szkic. Publikacja i nadpisanie treści są zablokowane.";
}

function structuredRuntimeSafetyText(
  result: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (!result) {
    return "WILQ może sprawdzić przygotowanie szkicu bez pisania na żywo. Ten krok nie wywołuje modelu.";
  }
  if (result.status === "generated" && result.output) {
    return "Szkic został wygenerowany w kontrolowanym trybie. Przed WordPress musi przejść podgląd treści i sprawdzenie człowieka.";
  }
  if (result.external_call_attempted) {
    return "Zatrzymaj workflow: próba przygotowania szkicu nie powinna wywoływać modelu na żywo.";
  }
  if (result.status === "blocked") {
    return result.blockers[0]?.reason ?? "WILQ zablokował przygotowanie próby szkicu.";
  }
  return "Próba gotowa: WILQ ma kontrakt szkicu i nie wygenerował treści na żywo.";
}

function structuredPreviewSafetyText(
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null
) {
  if (!result) {
    return "Po wygenerowaniu szkicu WILQ pokaże treść do sprawdzenia. To nadal nie jest publikacja.";
  }
  if (result.blockers.length) {
    return result.blockers[0]?.reason ?? "WILQ zablokował podgląd treści.";
  }
  if (result.preview) {
    return "Podgląd gotowy do sprawdzenia przez człowieka. WordPress i publikacja nadal są zablokowane.";
  }
  return "WILQ nie zwrócił treści do podglądu.";
}

function qualityReviewSafetyText(
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null
) {
  if (!review) {
    return (
      "Po podglądzie treści WILQ sprawdzi dowody, ryzykowne obietnice, CTA, " +
      "dopasowanie do usługi i gotowość pomiaru. To nie jest wynik SEO."
    );
  }
  if (review.blockers.length) {
    return review.blockers[0]?.reason ?? "WILQ blokuje szkic przed sprawdzeniem człowieka.";
  }
  if (review.revision_instructions.length) {
    return "Szkic wymaga ograniczonej poprawki przed sprawdzeniem człowieka.";
  }
  return "Szkic może trafić do sprawdzenia człowieka. Nadal nie jest publikacją.";
}

function revisionPlanSafetyText(
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null
) {
  if (!plan) {
    return "Plan poprawki może powstać tylko z oceny jakości WILQ. Nie regenerujemy szkicu wolnym promptem.";
  }
  if (plan.blockers.length) {
    return plan.blockers[0]?.reason ?? "WILQ blokuje plan poprawki.";
  }
  if (plan.instructions.length) {
    return "Poprawka jest ograniczona do wskazanych zmian i dowodów. Po poprawce trzeba ponownie uruchomić ocenę jakości.";
  }
  return "Ocena jakości nie wymaga poprawki. Następny krok to sprawdzenie człowieka.";
}

function wordpressExecutionSafetyText(
  result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null
) {
  if (!result) {
    return "Po audycie WILQ może pokazać, co trafiłoby do WordPress. Ten krok nie wykonuje zewnętrznego zapisu.";
  }
  if (result.status === "created") {
    return wordpressDraftExecutionStatusText(result);
  }
  if (result.external_write_attempted) {
    return "Zatrzymaj workflow: WordPress zgłosił próbę zapisu bez potwierdzonego utworzenia szkicu.";
  }
  if (result.status === "blocked") {
    return result.blockers[0]?.reason ?? "WILQ zablokował przygotowanie podglądu szkicu.";
  }
  if (result.payload) {
    return `Podgląd gotowy: WordPress dostałby status ${result.payload.post_status}. Publikacja: zablokowana. Nadpisywanie treści: zablokowane.`;
  }
  return "WILQ sprawdził przekazanie, ale nie zwrócił paczki podglądu.";
}

function acfPreviewSafetyText(
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null
) {
  if (!result) {
    return "Po audycie WILQ może pokazać, który layout ACF i które pola szkicu wypełni. Ten krok nie wykonuje zapisu w WordPress.";
  }
  if (result.external_write_attempted) {
    return "Zatrzymaj workflow: mapowanie ACF nie powinno wykonywać zewnętrznego zapisu.";
  }
  if (result.blockers.length) {
    return result.blockers[0]?.reason ?? "WILQ zablokował mapowanie ACF.";
  }
  const firstSection = result.sections[0] ?? null;
  const fieldCount = firstSection
    ? Object.values(firstSection.field_values).filter((value) => Boolean(value)).length
    : 0;
  if (firstSection) {
    return `Mapowanie gotowe: WILQ użyje layoutu ${firstSection.layout_label} i wypełni ${fieldCount} pól. Publikacja i nadpisywanie pozostają zablokowane.`;
  }
  return "Mapowanie ACF jest gotowe, ale WILQ nie zwrócił sekcji do pokazania.";
}

function measurementSafetyText(
  window: ContentWorkflowSnapshot["measurementWindow"]["measurement_window_result"]["window"]
) {
  if (!window) return "Brak okna pomiaru blokuje jakiekolwiek wnioski o efekcie treści.";
  return `Pierwsza ocena po ${window.earliest_verdict_date}. Do tego czasu WILQ zbiera dane, ale nie claimuje sukcesu ani porażki.`;
}

function reviewControlDisabledReason(
  data: ContentWorkflowSnapshot,
  hasDraft: boolean,
  pending: boolean
) {
  if (pending) return "WILQ zapisuje sprawdzenie.";
  if (data.humanReview.review) return "Sprawdzenie człowieka jest już zapisane dla tego tematu.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu do sprawdzenia.";
  if (!data.preflight.item.evidence_ids.length) {
    return "Sprawdzenie nie może ruszyć bez dowodów przypiętych do tematu.";
  }
  return null;
}

function auditControlDisabledReason(data: ContentWorkflowSnapshot, pending: boolean) {
  if (pending) return "WILQ zapisuje audyt przekazania szkicu.";
  if (data.wordpressHandoff.handoff_result.handoff) {
    return "Audyt jest zapisany, a przekazanie do WordPress pozostaje przygotowane tylko jako szkic.";
  }
  if (!data.humanReview.review) return "Najpierw zapisz sprawdzenie człowieka.";
  if (!data.humanReview.wordpress_handoff_allowed) {
    return (
      data.humanReview.blockers[0]?.reason ??
      "WILQ nie odblokował przekazania do WordPress po sprawdzeniu."
    );
  }
  return null;
}

function structuredRuntimeControlDisabledReason(
  data: ContentWorkflowSnapshot,
  pending: boolean,
  result: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza gotowość szkicu.";
  if (result) return "Próba przygotowania szkicu jest już sprawdzona dla tej sesji.";
  if (!data.structuredGeneration.structured_generation_result.contract) {
    return (
      data.structuredGeneration.structured_generation_result.blockers[0]?.reason ??
      "Najpierw WILQ musi przygotować kontrakt szkicu."
    );
  }
  return null;
}

function structuredPreviewControlDisabledReason(
  data: ContentWorkflowSnapshot,
  pending: boolean,
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza podgląd treści.";
  if (result) return "Podgląd treści jest już przygotowany dla tej sesji.";
  if (!data.structuredGeneration.structured_generation_result.contract) {
    return (
      data.structuredGeneration.structured_generation_result.blockers[0]?.reason ??
      "Najpierw WILQ musi przygotować kontrakt szkicu."
    );
  }
  if (!runtimeResult?.output) {
    return "Najpierw WILQ musi mieć wygenerowany szkic. Sama próba gotowości nie tworzy treści.";
  }
  return null;
}

function qualityReviewControlDisabledReason(
  pending: boolean,
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza jakość szkicu.";
  if (review) return "Ocena jakości jest już przygotowana dla tej sesji.";
  if (!runtimeResult?.output) {
    return "Najpierw WILQ musi mieć wygenerowany szkic do oceny jakości.";
  }
  return null;
}

function revisionPlanControlDisabledReason(
  pending: boolean,
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null,
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null
) {
  if (pending) return "WILQ przygotowuje plan poprawki.";
  if (plan) return "Plan poprawki jest już przygotowany dla tej sesji.";
  if (!review) return "Najpierw uruchom ocenę jakości szkicu.";
  return null;
}

function acfPreviewControlDisabledReason(
  hasDraft: boolean,
  hasHandoff: boolean,
  hasAuthoringProfile: boolean,
  pending: boolean,
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null
) {
  if (pending) return "WILQ sprawdza mapowanie ACF.";
  if (result) return "Mapowanie ACF jest już przygotowane dla tej sesji.";
  if (!hasAuthoringProfile) return "Najpierw WILQ musi odczytać profil WordPress/ACF.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu.";
  if (!hasHandoff) return "Najpierw zapisz audyt i przygotuj przekazanie szkicu do WordPress.";
  return null;
}

function executionControlDisabledReason(
  hasDraft: boolean,
  hasHandoff: boolean,
  pending: boolean,
  result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null
) {
  if (pending) return "WILQ przygotowuje podgląd szkicu WordPress.";
  if (result) return "Podgląd szkicu WordPress jest już przygotowany dla tej sesji.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu.";
  if (!hasHandoff) return "Najpierw zapisz audyt i przygotuj przekazanie szkicu do WordPress.";
  return null;
}

function unique(values: string[]) {
  return Array.from(new Set(values));
}
