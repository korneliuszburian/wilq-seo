import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Clock3,
  Code2,
  ExternalLink,
  FileText,
  Globe2,
  Search,
  ShieldCheck,
  Stamp
} from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

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
  type ContentWorkflowSnapshot,
  type WorkflowStep
} from "./contentWorkflowRuntime";
import { normalizedPath, selectDevPage, type WordPressAuthoringDevPage } from "./contentWorkflowTarget";
import { AcfCurrentVsProposedPanel } from "./AcfCurrentVsProposedPanel";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { WorkflowStepper, workflowStepShortLabel } from "./WorkflowStepper";
import { WorkflowStepsList } from "./WorkflowStepsList";
import {
  ContentFreshnessBanner,
  ContentWorkflowError,
  ContentWorkflowEmptyQueue,
  ContentWorkflowSelectedLoading
} from "./ContentWorkflowBoundaryStates";
import { WordPressDraftReadbackStatus, WordPressDraftExecutionStatus, wordpressDraftExecutionStatusText } from "./WordPressDraftStatus";
import { ContentSourceStatusBar } from "./ContentSourceStatusBar";
import { ContentMapColumn, ContentMapConnectors, ContentSectionRow } from "./ContentMapPrimitives";
import { ContentWorkflowHeader } from "./ContentWorkflowHeader";
import { ContentPageIdentityCard } from "./ContentPageIdentityCard";
import {
  activeWorkflowStepIndex,
  blockedWorkflowSteps,
  claimLedgerSummary
} from "./contentWorkflowDecisionModel";
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

type WorkflowSafetyPanelsProps = {
  data: ContentWorkflowSnapshot;
  draft: ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
  handoff: ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
  window: ContentWorkflowSnapshot["measurementWindow"]["measurement_window_result"]["window"];
  structuredRuntimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null;
  structuredPreviewResult: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null;
  qualityReview: ContentWorkItemQualityReviewResponse["quality_review"] | null;
  revisionPlan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null;
  acfPreviewResult: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null;
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
};

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
            <WordPressDraftWorkPanel
              actions={actions}
              authoringProfile={authoringProfile}
              draftActivationPacket={draftActivationPacket}
              draftWriteReadiness={draftWriteReadiness}
            />
            <ContentSectionWritingWorkbench
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
            <WorkflowOperatorControls data={data} actions={actions} />
            <WorkflowProofSummary data={data} />
            <ClaimLedgerGatePanel data={data} />
            <ContentOpportunityEnrichmentPanel enrichment={enrichment} />
            <WorkflowStepsList steps={steps} />
            <WorkflowSafetyPanels
              data={data}
              draft={draft}
              handoff={handoff}
              window={window}
              structuredRuntimeResult={actions.structuredRuntimeResult}
              structuredPreviewResult={actions.structuredPreviewResult}
              qualityReview={actions.qualityReview}
              revisionPlan={actions.revisionPlan}
              acfPreviewResult={actions.acfPreviewResult}
              executionResult={actions.executionResult}
            />
          </div>
        ) : null}
      </details>
    </main>
  );
}

function MobileContentTriage({
  data,
  onOpenDetails
}: {
  data: ContentWorkflowSnapshot;
  onOpenDetails: () => void;
}) {
  const candidate = data.candidate;
  const blockers = candidate.blockers.slice(0, 2);
  return (
    <section aria-label="Mobilny triage treści" className="mb-4 space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Treści i SEO · triage</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">Jedna strona na teraz</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Najpierw podejmij decyzję dla wybranej strony. Szczegóły otworzysz niżej.
        </p>
      </div>
      <article className="rounded-md border border-action/30 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-normal text-action">Decyzja</p>
        <h2 className="mt-2 text-lg font-semibold leading-6 text-ink">{candidate.title}</h2>
        <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-700">{candidate.reason}</p>
        <p className="mt-3 line-clamp-3 text-sm font-semibold leading-6 text-ink">{candidate.safe_next_step}</p>
        <button
          type="button"
          onClick={onOpenDetails}
          className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-md bg-action px-4 text-sm font-semibold text-white"
        >
          Otwórz szczegóły pracy
        </button>
      </article>
      <div className="rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold text-ink">Dwa najważniejsze blokery</h2>
        {blockers.length ? (
          <ul className="mt-3 space-y-3">
            {blockers.map((blocker) => (
              <li key={blocker.code} className="text-sm leading-5 text-slate-700">
                <span className="font-semibold text-ink">{blocker.label}</span>
                <span className="mt-1 block">{blocker.reason}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm leading-6 text-slate-700">Brak dodatkowych blockerów dla tej decyzji.</p>
        )}
      </div>
      <details className="rounded-md border border-line bg-white px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold text-action">Pokaż dowody i świeżość</summary>
        <div className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
          <p>Świeżość: {data.freshnessAssessment.state_label}</p>
          <p>Dowody źródłowe: {candidate.evidence_ids.length}</p>
          <p>Źródła: {candidate.source_connectors.join(", ")}</p>
        </div>
      </details>
    </section>
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
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal text-ink">
            Treści: praca nad stroną
          </h1>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-600">
            Publiczna strona, sygnały SEO, sekcje ACF i edytor szkicu w jednym miejscu.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink"
          >
            Dzisiaj
          </button>
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink"
            onClick={() => window.location.reload()}
          >
            Odśwież
          </button>
        </div>
      </div>

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
            <ContentMapColumn
              icon={<Globe2 aria-hidden="true" size={18} />}
              title="Aktualna strona"
              subtitle={publicUrl ? environmentLabel(publicUrl) : "publiczna treść"}
            >
              {publicSections.length ? (
                <ol className="space-y-2">
                  {publicSections.slice(0, 4).map((section, index) => (
                    <ContentSectionRow
                      key={`${section}-${index}`}
                      icon={<FileText aria-hidden="true" size={15} />}
                      title={section}
                      subtitle={`Sekcja ${index + 1}`}
                    />
                  ))}
                  {publicSections.length > 4 ? (
                    <li className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
                      + {publicSections.length - 4} sekcji niżej w kontekście
                    </li>
                  ) : null}
                </ol>
              ) : (
                <p className="rounded-md border border-wait/25 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
                  Brakuje listy publicznych sekcji dla tej strony.
                </p>
              )}
            </ContentMapColumn>

            <ContentMapColumn
              icon={<Search aria-hidden="true" size={18} />}
              title="Sygnały i braki"
              subtitle="GSC, Ahrefs i brief"
            >
              <div className="space-y-3">
                <div className="rounded-md border border-line bg-white p-3">
                  <div className="text-xs font-semibold text-slate-600">Kluczowe zapytania</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {queryChips.map((query) => (
                      <span key={query} className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                        {query}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {metricTiles.map((tile) => (
                    <div key={tile.label} className="rounded-md border border-line bg-surface px-3 py-2">
                      <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">
                        {tile.label}
                      </div>
                      <div className="mt-1 text-sm font-semibold text-ink">{tile.value}</div>
                    </div>
                  ))}
                </div>
                {signalRows.slice(0, 2).map((row) => (
                  <div key={row.label} className={`rounded-md border p-3 ${row.tone}`}>
                    <div className="text-xs font-semibold uppercase tracking-normal">{row.label}</div>
                    <p className="mt-1 line-clamp-3 text-sm leading-6 text-slate-700">
                      {row.summary}
                    </p>
                  </div>
                ))}
              </div>
            </ContentMapColumn>

            <ContentMapColumn
              icon={<Code2 aria-hidden="true" size={18} />}
              title="Dev draft / ACF"
              subtitle={devPage ? `${devPage.section_count} sekcji na devie` : "czeka na odczyt"}
            >
              {profile?.dev_content.pages.length ? (
                <label className="mb-3 block">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-normal text-slate-500">
                    Cel dev do podglądu
                  </span>
                  <select
                    className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
                    value={devPage?.link ?? ""}
                    onChange={(event) => setSelectedDevPageLink(event.target.value || null)}
                    aria-label="Cel dev do podglądu"
                  >
                    {profile.dev_content.pages.map((page) => (
                      <option key={page.link} value={page.link}>
                        {page.title || page.link} · {page.section_count} sekcji
                      </option>
                    ))}
                  </select>
                  <span className="mt-1 block text-xs leading-5 text-slate-500">
                    Zmienia tylko kontekst podglądu. Zapis do WordPress nadal wymaga osobnej, bezpiecznej ścieżki.
                  </span>
                </label>
              ) : null}
              {devSections.length ? (
                <ol className="space-y-2">
                  {devSections.slice(0, 5).map((section) => (
                    <ContentSectionRow
                      key={`${section.section_index}-${section.layout_name}`}
                      icon={<Code2 aria-hidden="true" size={15} />}
                      title={section.title || section.layout_label}
                      subtitle={section.layout_name}
                      meta={section.acf_field_name}
                      badge="dev"
                      tone="dev"
                    />
                  ))}
                  {devSections.length > 5 ? (
                    <li className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
                      + {devSections.length - 5} sekcji ACF w kontekście
                    </li>
                  ) : null}
                </ol>
              ) : (
                <p className="rounded-md border border-wait/25 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
                  {profile?.dev_content.status === "blocked"
                    ? profile.dev_content.blockers[0]?.reason
                    : "Nie mamy jeszcze czytelnych sekcji ACF z dev REST dla tej strony."}
                </p>
              )}
            </ContentMapColumn>
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

function MobileDecisionCard({
  candidate,
  publicUrl,
  topic,
  queue,
  onOpenDetails
}: {
  candidate: ContentWorkItemQueueCandidate | null;
  publicUrl: string;
  topic: string;
  queue: ContentWorkItemQueueResponse;
  onOpenDetails: () => void;
}) {
  const blocker = queue.blockers[0] ?? candidate?.blockers[0] ?? null;
  const blockerLabel = blocker?.label ?? queue.freshness_assessment.state_label;
  const blockerReason = blocker?.reason ?? queue.freshness_assessment.summary;
  const decision = candidate?.recommended_mode_label ?? "Wymaga sprawdzenia";

  return (
    <section
      className="mb-4 rounded-md border border-action/25 bg-white p-4 shadow-sm sm:hidden"
      aria-label="Decyzja mobilna"
    >
      <div className="text-xs font-semibold uppercase tracking-normal text-action">
        Decyzja teraz
      </div>
      <h2 className="mt-1 text-lg font-semibold leading-6 text-ink">{topic}</h2>
      {publicUrl ? (
        <p className="mt-1 truncate text-xs font-medium text-action">{publicUrl}</p>
      ) : null}
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-ink">{decision}</span>
        <span className="rounded-md bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">
          {blockerLabel}
        </span>
      </div>
      <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-700">{blockerReason}</p>
      <button
        type="button"
        onClick={onOpenDetails}
        className="mt-3 inline-flex h-10 w-full items-center justify-center rounded-md bg-action px-3 text-sm font-semibold text-white"
      >
        Otwórz decyzję i dowody
      </button>
    </section>
  );
}

function ContentWorkflowDecisionPanel({
  data,
  queue,
  steps
}: {
  data: ContentWorkflowSnapshot;
  queue: ContentWorkItemQueueResponse;
  steps: WorkflowStep[];
}) {
  const item = data.preflight.item;
  const blockedSteps = blockedWorkflowSteps(data.operatorSteps);
  const activeCandidate = queue.candidates.find(
    (candidate) => candidate.work_item_id === item.id
  );
  const activeStepIndex = activeWorkflowStepIndex(steps);
  const activeStep = steps[activeStepIndex] ?? steps[0] ?? null;
  const ledgerSummary = claimLedgerSummary(data);
  const nextStep =
    activeCandidate?.safe_next_step ??
    data.preflight.preflight_verdict.next_step ??
    activeStep?.summary ??
    "Najpierw domknij decyzję operatora i bramki publikacji.";
  const decisionTitle = activeCandidate
    ? `${activeCandidate.recommended_mode_label}: ${activeCandidate.title}`
    : `${data.preflight.preflight_verdict.recommended_mode}: ${item.topic}`;
  const decisionReason =
    activeCandidate?.reason ??
    data.preflight.preflight_verdict.next_step ??
    "WILQ pokazuje ten temat jako aktywną pracę po sprawdzeniu źródeł i bramek treści.";

  return (
    <section className="mb-6 rounded-md border border-line bg-white">
      <div className="border-b border-line p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-action">
              Workflow treści: jeden aktywny krok
            </div>
            <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
              {item.topic}
            </h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              Status: wymaga decyzji operatora. Publikacja i zapis WordPress pozostają
              zablokowane, dopóki plan, twierdzenia, review człowieka i audyt nie są domknięte.
            </p>
          </div>
          <div className="rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-sm font-semibold text-wait">
            Publikacja zablokowana
          </div>
        </div>
        <WorkflowStepper activeIndex={activeStepIndex} steps={steps} />
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-md border border-line bg-surface p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Następna decyzja operatora
            </h3>
            <span className="rounded-md bg-action/10 px-2 py-1 text-xs font-semibold text-action">
              Aktywny krok: {activeStep ? workflowStepShortLabel(activeStepIndex, activeStep) : "Plan"}
            </span>
          </div>
          <p className="mt-3 text-base font-semibold leading-6 text-ink">{decisionTitle}</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{decisionReason}</p>
          <div className="mt-4 grid gap-2 md:grid-cols-3">
            <FactTile label="Dowody WILQ" value={`${unique(item.evidence_ids).length}`} />
              <FactTile label="Twierdzenia do review" value={`${ledgerSummary.review}`} />
              <FactTile label="Twierdzenia zablokowane" value={`${ledgerSummary.blocked}`} />
          </div>
          <div className="mt-4">
            <div className="text-sm font-semibold text-ink">Następny krok</div>
            <p className="mt-1 text-sm leading-6 text-slate-700">{nextStep}</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              className="inline-flex items-center rounded-md bg-action px-4 py-2 text-sm font-semibold text-white"
              href="#content-workflow-actions"
            >
              Przejdź do decyzji operatora
            </a>
            <a
              className="inline-flex items-center rounded-md border border-action/40 px-4 py-2 text-sm font-semibold text-action"
              href="#content-workflow-proof"
            >
              Pokaż dowody
            </a>
          </div>
        </div>

        <div className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co blokuje publikację
          </h3>
          <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-700">
            <li>
              <span className="font-semibold text-ink">Brak zatwierdzenia człowieka.</span>{" "}
              Plan, twierdzenia i paczka szkicu muszą przejść review przed użyciem jako wiedza produkcyjna.
            </li>
            <li>
              <span className="font-semibold text-ink">WordPress zostaje tylko szkicem.</span>{" "}
              WILQ może przygotować podgląd, ale nie publikuje ani nie nadpisuje strony.
            </li>
            {blockedSteps.slice(0, 3).map((step) => (
              <li key={step.id}>
                <span className="font-semibold text-ink">{step.title}.</span>{" "}
                {step.statusLabel}: {step.summary}
              </li>
            ))}
          </ul>
          <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3">
            <div className="text-sm font-semibold text-wait">Nie wolno jeszcze twierdzić</div>
            <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-700 sm:grid-cols-2">
              <li>- automatyczna publikacja</li>
              <li>- wzrost ruchu bez okna pomiaru</li>
              <li>- poprawa pozycji bez obserwacji</li>
              <li>- pełna aktualność twierdzeń bez review</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-line p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Rejestr twierdzeń - skrót
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {ledgerSummary.allowed} do szkicu, {ledgerSummary.review} wymaga review,{" "}
              {ledgerSummary.blocked} zablokowane. Szczegóły twierdzeń i surowe dowody są niżej.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-claim-ledger">
              Otwórz rejestr twierdzeń
            </a>
            <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-proof">
              Otwórz brief
            </a>
            <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-wordpress">
              Pokaż szkic WP
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function WordPressDraftWorkPanel({
  actions,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness
}: {
  actions: ContentWorkflowActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
}) {
  const profile = authoringProfile.data;
  const readiness = draftWriteReadiness.data;
  const packet = draftActivationPacket.data;
  const isLoading =
    authoringProfile.isLoading || draftActivationPacket.isLoading || draftWriteReadiness.isLoading;

  if (isLoading) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold text-ink">Dev draft WordPress</h2>
        <p className="mt-2 text-sm text-slate-600">Sprawdzam dev, ACF i gotowość szkicu.</p>
      </section>
    );
  }

  if (authoringProfile.error || draftActivationPacket.error || draftWriteReadiness.error) {
    return (
      <section className="mb-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold text-wait">Dev draft WordPress</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Nie udało się odczytać pełnej gotowości dev WordPress. Nie zaczynaj zapisu bez profilu authoringu,
          paczki szkicu i readiness z WILQ API.
        </p>
      </section>
    );
  }

  const latestCreatedExecution =
    actions.executionResult ??
    (packet?.execution_result.status === "created" ? packet.execution_result : null);
  const draftReadback = packet?.draft_readback ?? null;
  const canPreviewDraft = Boolean(
    packet?.draft_package_ready &&
      packet.handoff_ready &&
      packet.dry_run_ready &&
      packet.execution_blockers.length === 0 &&
      !actions.executionPending
  );
  const canOpenCanonicalApplyReview = Boolean(
    packet?.draft_package_ready && packet.handoff_ready
  );
  const acfLayoutCount = profile?.acf.layouts.length ?? 0;
  const missingReadiness = [
    ...(packet?.activation_missing_readiness_labels ?? []),
    ...(readiness?.blockers.map((blocker) => blocker.label) ?? [])
  ].slice(0, 5);
  const nextStep =
    packet?.operator_next_step ??
    readiness?.operator_next_step ??
    "Najpierw przygotuj review paczki szkicu i zapis audytu w WILQ.";

  return (
    <section className="mb-6 overflow-hidden rounded-md border border-action/25 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-action/15 bg-blue-50 px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-action">Roboczy WordPress</p>
          <h2 className="mt-1 text-base font-semibold text-ink">Dev draft WordPress</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            Piszemy i układamy szkic na ekologus.dev.proudsite.pl. Publiczna strona pozostaje punktem
            odniesienia, ale dev nie jest kanonicznym adresem SEO.
          </p>
        </div>
        <span className="rounded-md bg-wait/10 px-3 py-2 text-sm font-semibold text-wait">
          zapis przez akcję zablokowany
        </span>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1fr]">
        <div>
          <div className="grid gap-3 sm:grid-cols-4">
            <FactTile label="Paczka szkicu" value={packet?.draft_package_ready ? "gotowa" : "brak"} />
            <FactTile label="Review" value={packet?.human_review_ready ? "gotowe" : "wymagane"} />
            <FactTile label="ACF" value={acfLayoutCount ? `${acfLayoutCount} layoutów` : "brak odczytu"} />
            <FactTile label="Publikacja" value="zablokowana" />
          </div>
          <div className="mt-4 rounded-md border border-line bg-surface p-3">
            <h3 className="text-sm font-semibold text-ink">Następny krok</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{nextStep}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => actions.runExecutionDryRun()}
                disabled={!canPreviewDraft}
                className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actions.executionPending ? "Sprawdzam podgląd" : "Sprawdź podgląd draftu"}
              </button>
              {canOpenCanonicalApplyReview ? (
                <a
                  href="/actions/act_apply_wordpress_draft_handoff"
                  className="inline-flex h-9 items-center rounded-md border border-action/40 px-3 text-sm font-semibold text-action"
                >
                  Otwórz kanoniczną akcję do review
                </a>
              ) : null}
            </div>
            {canOpenCanonicalApplyReview ? (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Ten link otwiera podgląd do sprawdzenia. Nie wykonuje zapisu ani publikacji.
              </p>
            ) : null}
            {latestCreatedExecution ? (
              <WordPressDraftExecutionStatus result={latestCreatedExecution} />
            ) : null}
            {draftReadback ? (
              <WordPressDraftReadbackStatus readback={draftReadback} />
            ) : null}
          </div>
        </div>

        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Co blokuje zapis szkicu</h3>
          {missingReadiness.length > 0 ? (
            <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
              {missingReadiness.map((label) => (
                <li key={label}>- {label}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm leading-6 text-slate-700">
              WILQ nie zgłasza brakujących etapów dla podglądu. Zapis nadal idzie przez akcję, review,
              potwierdzenie i audyt.
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href="https://ekologus.dev.proudsite.pl/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white"
            >
              Otwórz dev
            </a>
            <a
              href="https://ekologus.dev.proudsite.pl/wp-admin/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-semibold text-ink"
            >
              Otwórz WordPress admin
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function ContentSectionWritingWorkbench({
  actions,
  authoringProfile,
  data,
  draftActivationPacket
}: {
  actions: ContentWorkflowActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
}) {
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const publicSections = item.wordpress_section_headings ?? [];
  const draftSections = useMemo(() => draft?.sections ?? [], [draft]);
  const editableSections = useMemo(() => draftSections.slice(0, 4), [draftSections]);
  const sectionDraftDefaults = useMemo(
    () =>
      Object.fromEntries(
        editableSections.map((section) => [
          sectionOverrideKey(section.heading),
          defaultSectionBody(section)
        ])
      ),
    [editableSections]
  );
  const [sectionEditorState, setSectionEditorState] = useState<{
    draftId: string | null;
    texts: Record<string, string>;
  }>({ draftId: null, texts: {} });
  const draftEditorId = draft?.id ?? null;
  const sectionTexts =
    sectionEditorState.draftId === draftEditorId
      ? sectionEditorState.texts
      : sectionDraftDefaults;
  const sourceTitle = item.wordpress_title_or_h1 ?? draft?.title ?? item.topic;
  const sectionInventoryAvailable =
    item.wordpress_section_inventory_status === "available" && publicSections.length > 0;
  const profile = authoringProfile.data;
  const draftReadback = draftActivationPacket.data?.draft_readback ?? null;
  const dryRunReady = Boolean(
    draftActivationPacket.data?.dry_run_ready &&
      draftActivationPacket.data.execution_blockers.length === 0
  );
  const firstAcfSection = actions.acfPreviewResult?.sections[0] ?? null;
  const firstAcfFields = firstAcfSection?.field_previews ?? [];
  const sourceHref = item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? undefined;
  const canPrepareAcf = Boolean(
    profile && draft && handoff && !actions.acfPreviewResult
  );
  const sectionOverrides = editableSections
    .map((section) => ({
      heading: section.heading,
      body_markdown:
        sectionTexts[sectionOverrideKey(section.heading)] ?? defaultSectionBody(section),
      evidence_ids: unique(section.evidence_ids)
    }))
    .filter((section) => section.body_markdown.trim().length > 0);

  return (
    <section className="mb-6 overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line bg-surface px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-action">
            Roboczy plan treści
          </p>
          <h2 className="mt-1 text-base font-semibold text-ink">Plan sekcji i ACF</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            Zestawienie tego, co jest na publicznej stronie, co ma wejść do szkicu i jak można to
            przełożyć na dev WordPress/ACF. To jest miejsce pracy nad treścią, nie raport techniczny.
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink">
          {draftReadback?.status === "available" ? "dev draft odczytany" : "dev draft do sprawdzenia"}
        </span>
      </div>

      <div className="grid gap-4 p-4 xl:grid-cols-[1.05fr_1fr_0.95fr]">
        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-md border border-line bg-surface p-2 text-action">
              <FileText aria-hidden="true" size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">Aktualna publiczna treść</h3>
              <p className="mt-2 text-sm font-semibold text-ink">{sourceTitle}</p>
              <a
                href={sourceHref}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex text-sm font-semibold text-action"
              >
                Otwórz obecną stronę
              </a>
            </div>
          </div>
          {sectionInventoryAvailable ? (
            <ol className="mt-4 space-y-2 text-sm leading-6 text-slate-700">
              {publicSections.slice(0, 6).map((section, index) => (
                <li key={`${section}-${index}`} className="rounded-md border border-line bg-surface px-3 py-2">
                  {index + 1}. {section}
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-4 rounded-md border border-wait/25 bg-wait/10 px-3 py-2 text-sm leading-6 text-slate-700">
              Brakuje czytelnej listy sekcji z publicznego WordPressa. Nie przepisuj strony w ciemno:
              najpierw odczytaj sekcje albo pracuj tylko na sprawdzonym szkicu z dev.
            </p>
          )}
        </div>

        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-md border border-line bg-surface p-2 text-success">
              <ShieldCheck aria-hidden="true" size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">Tekst sekcji do szkicu</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {draftSections.length
                  ? "Przepisz konkretne sekcje tutaj i sprawdź podgląd przed centralną akcją zapisu."
                  : "Szkic nie ma jeszcze sekcji. Najpierw przygotuj paczkę szkicu."}
              </p>
            </div>
          </div>
          {editableSections.length ? (
            <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
              {editableSections.map((section, index) => {
                const key = sectionOverrideKey(section.heading);
                return (
                  <label key={`${section.heading}-${index}`} className="block rounded-md border border-line bg-surface p-3">
                    <p className="font-semibold text-ink">
                      {index + 1}. {section.heading}
                    </p>
                    <textarea
                      className="mt-3 min-h-32 w-full resize-y rounded-md border border-line bg-white p-3 text-sm leading-6 text-ink outline-none focus:border-action focus:ring-2 focus:ring-action/20"
                      value={sectionTexts[key] ?? defaultSectionBody(section)}
                      onChange={(event) =>
                        setSectionEditorState({
                          draftId: draftEditorId,
                          texts: {
                            ...sectionTexts,
                            [key]: event.target.value
                          }
                        })
                      }
                      aria-label={`Tekst sekcji ${section.heading}`}
                    />
                    {section.draft_notes.length ? (
                      <p className="mt-2 text-xs leading-5 text-slate-500">
                        Wskazówka: {section.draft_notes[0]}
                      </p>
                    ) : null}
                  </label>
                );
              })}
              <div className="rounded-md border border-action/20 bg-action/5 p-3">
                <p className="text-sm leading-6 text-slate-700">
                  Podgląd sprawdza tekst i proponowane sekcje. Publikacja i nadpisywanie publicznej
                  strony pozostają zablokowane.
                </p>
                <div className="mt-3 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => actions.runExecutionDryRunWithSections(sectionOverrides)}
                    disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending}
                    className="inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {actions.executionPending ? "Sprawdzam..." : "Sprawdź tekst szkicu"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setSectionEditorState({
                        draftId: draftEditorId,
                        texts: sectionDraftDefaults
                      })
                    }
                    className="inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink"
                  >
                    Przywróć tekst z briefu
                  </button>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  Ten ekran nie wykonuje bezpośredniego zapisu do WordPressa.
                </p>
              </div>
            </div>
          ) : null}
        </div>

        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-md border border-line bg-surface p-2 text-action">
              <Stamp aria-hidden="true" size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">Dev WordPress i ACF</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {firstAcfSection
                  ? "Mapowanie pokazuje, do których pól można przepiąć szkic."
                  : `${profile?.acf.layouts.length ?? 0} layoutów ACF jest dostępnych do przygotowania mapowania.`}
              </p>
            </div>
          </div>
          <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
            {draftReadback?.status === "available" ? (
              <div className="rounded-md border border-success/25 bg-success/5 p-3">
                <p className="font-semibold text-success">Szkic istnieje na devie</p>
                <p className="mt-1 font-semibold text-ink">{draftReadback.title || "Szkic bez tytułu"}</p>
                <p className="mt-1 text-xs text-slate-600">
                  {draftReadback.content_word_count ?? 0} słów · status {draftReadback.post_status || "draft"}
                </p>
                {draftReadback.link ? (
                  <a
                    href={draftReadback.link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-sm font-semibold text-action"
                  >
                    Otwórz szkic na dev
                  </a>
                ) : null}
              </div>
            ) : (
              <div className="rounded-md border border-line bg-surface p-3">
                Szkic na devie nie jest jeszcze potwierdzony. Najpierw utwórz albo odczytaj draft.
              </div>
            )}

            {firstAcfSection ? (
              <div className="rounded-md border border-line bg-surface p-3">
                <p className="text-xs uppercase tracking-normal text-slate-500">Wybrany layout</p>
                <p className="mt-1 font-semibold text-ink">
                  {firstAcfSection.layout_label} ({firstAcfSection.layout_name})
                </p>
                {firstAcfFields.length ? (
                  <AcfFieldPreviewList fields={firstAcfFields.slice(0, 3)} />
                ) : null}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => actions.runAcfPreview()}
                disabled={!canPrepareAcf || actions.acfPreviewPending}
                className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actions.acfPreviewPending ? "Przygotowuję ACF" : "Przygotuj mapowanie sekcji ACF"}
              </button>
            )}
          </div>
        </div>
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

function ContentWorkflowBlockedCandidate({
  queue,
  selectedCandidate,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const blocker = selectedCandidate.blockers[0];
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={selectedCandidate.topic} />
      <ContentFreshnessBanner assessment={queue.freshness_assessment} />
      <ContentCandidateQueuePanel
        queue={queue}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
      <section className="mt-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
          WILQ blokuje pisanie tego tematu
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {blocker?.reason ?? selectedCandidate.reason}
        </p>
        <p className="mt-2 text-sm font-medium text-ink">
          Następny bezpieczny krok: {blocker?.next_step ?? selectedCandidate.safe_next_step}
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <FactTile label="Tryb" value={selectedCandidate.recommended_mode_label} />
          <FactTile label="Pomiar" value={selectedCandidate.measurement_readiness.label} />
        </div>
      </section>
    </main>
  );
}

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type WordPressHandoff =
  ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
type AcfFieldPreview =
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"]["sections"][number]["field_previews"][number];
type WordPressDraftSectionOverride = NonNullable<
  ContentWorkItemWordPressDraftExecutionRequest["section_overrides"]
>[number];

function environmentLabel(value: string) {
  try {
    const url = new URL(value);
    return url.hostname.replace(/^www\./, "");
  } catch {
    return value.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  }
}

function contentMetricTilesForWorkbench(
  item: ContentWorkflowSnapshot["preflight"]["item"],
  devPage: WordPressAuthoringDevPage | null
) {
  const wordpressSectionCount = item.wordpress_section_count ?? item.wordpress_section_headings.length;
  return [
    {
      label: "Dowody",
      value: `${unique(item.evidence_ids).length}`
    },
    {
      label: "Źródła",
      value: `${unique(item.source_connectors).length}`
    },
    {
      label: "Sekcje WP",
      value: wordpressSectionCount ? `${wordpressSectionCount}` : "brak"
    },
    {
      label: "Sekcje dev",
      value: devPage ? `${devPage.section_count}` : "brak"
    }
  ];
}

function contentSignalRows(
  data: ContentWorkflowSnapshot,
  enrichment: ContentOpportunityEnrichment | null,
  candidate: ContentWorkItemQueueCandidate | undefined
) {
  const brief = data.salesBrief.sales_brief_result.brief;
  const rows: { label: string; summary: string; tone: string }[] = [];
  if (candidate?.reason) {
    rows.push({
      label: "Decyzja",
      summary: candidate.reason,
      tone: "border-action/20 bg-action/5"
    });
  }
  if (brief?.source_facts[0]) {
    rows.push({
      label: sourceConnectorLabel(brief.source_facts[0].source_connector),
      summary: brief.source_facts[0].summary,
      tone: "border-success/20 bg-success/5"
    });
  }
  if (enrichment?.source_facts[0]) {
    rows.push({
      label: enrichment.source_facts[0].label,
      summary: enrichment.source_facts[0].summary,
      tone: "border-wait/25 bg-wait/10"
    });
  }
  if (brief?.signal_quality.reason) {
    rows.push({
      label: "Jakość briefu",
      summary: brief.signal_quality.reason,
      tone: "border-line bg-surface"
    });
  }
  if (!rows.length) {
    rows.push({
      label: "Następny krok",
      summary: data.preflight.preflight_verdict.next_step,
      tone: "border-line bg-surface"
    });
  }
  return rows.slice(0, 4);
}

function queryChipsForWorkbench(
  data: ContentWorkflowSnapshot,
  enrichment: ContentOpportunityEnrichment | null,
  candidate: ContentWorkItemQueueCandidate | undefined
) {
  const item = data.preflight.item;
  const brief = data.salesBrief.sales_brief_result.brief;
  const candidates = [
    item.topic,
    candidate?.topic,
    brief?.search_intent,
    brief?.buyer_problem,
    ...(brief?.source_facts.map((fact) => fact.summary) ?? []),
    ...(enrichment?.source_facts.map((fact) => fact.summary) ?? [])
  ];
  const chips = candidates
    .flatMap((value) => extractReadablePhrases(value ?? ""))
    .filter((value) => value.length >= 4 && value.length <= 34);
  return unique(chips).slice(0, 5);
}

function extractReadablePhrases(value: string) {
  const quoted = [...value.matchAll(/"([^"]+)"/g)].map((match) => match[1] ?? "");
  if (quoted.length) return quoted;
  return value
    .split(/[;,.|/]/)
    .map((part) => part.trim().replace(/\s+/g, " "))
    .filter(Boolean)
    .slice(0, 2);
}

function blockedClaimsForWorkbench(data: ContentWorkflowSnapshot) {
  const blocked = data.claimLedger.entries.filter(
    (entry) => entry.status === "blocked" || entry.status === "blocked_until_measurement"
  );
  return blocked.length
    ? blocked.slice(0, 4)
    : data.claimLedger.entries
        .filter((entry) => entry.status === "needs_human_review")
        .slice(0, 4);
}

function evidenceRowsForWorkbench(
  data: ContentWorkflowSnapshot,
  enrichment: ContentOpportunityEnrichment | null
) {
  const brief = data.salesBrief.sales_brief_result.brief;
  const rows = [
    ...(brief?.source_facts.map((fact) => ({
      label: sourceConnectorLabel(fact.source_connector),
      summary: fact.summary
    })) ?? []),
    ...(enrichment?.source_facts.map((fact) => ({
      label: fact.label,
      summary: fact.summary
    })) ?? [])
  ];
  if (rows.length) return rows.slice(0, 5);
  return unique(data.preflight.item.evidence_ids).slice(0, 5).map((evidenceId) => ({
    label: "Dowód WILQ",
    summary: evidenceId
  }));
}

function sourceConnectorLabel(connector: string) {
  const labels: Record<string, string> = {
    google_search_console: "GSC",
    wordpress_ekologus: "WordPress",
    ahrefs: "Ahrefs",
    google_analytics_4: "GA4",
    google_ads: "Google Ads"
  };
  return labels[connector] ?? connector;
}

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

function ClaimLedgerGatePanel({ data }: { data: ContentWorkflowSnapshot }) {
  const ledger = data.claimLedger;
  const allowedClaims = ledger.entries.filter((entry) =>
    entry.status.startsWith("allowed")
  );
  const reviewClaims = ledger.entries.filter(
    (entry) => entry.status === "needs_human_review" || entry.strength === "weak"
  );
  const blockedClaims = ledger.entries.filter(
    (entry) => entry.status === "blocked" || entry.status === "blocked_until_measurement"
  );
  const requiredClaims = ledger.entries.filter((entry) => entry.required);

  return (
    <section id="content-workflow-claim-ledger" className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck aria-hidden="true" size={18} className="text-action" />
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Claim Ledger: co wolno powiedzieć
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To jest bramka między briefem a szkicem. WILQ pokazuje, które
            twierdzenia mają dowód, które wymagają decyzji człowieka i których
            nie wolno użyć w gotowym języku.
          </p>
        </div>
        <div className="grid w-full gap-2 text-sm sm:w-auto sm:min-w-80 sm:grid-cols-4">
          <FactTile label="Do szkicu" value={`${allowedClaims.length}`} />
          <FactTile label="Review" value={`${reviewClaims.length}`} />
          <FactTile label="Zablokowane" value={`${blockedClaims.length}`} />
          <FactTile label="Wymagane" value={`${requiredClaims.length}`} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <ClaimList title="Do szkicu" empty="Brak twierdzeń gotowych do szkicu." claims={allowedClaims} />
        <ClaimList
          title="Wymaga review"
          empty="Brak twierdzeń wymagających dodatkowego review."
          claims={reviewClaims}
        />
        <ClaimList
          title="Zablokowane"
          empty="Brak twierdzeń zablokowanych w ledgerze."
          claims={blockedClaims}
        />
      </div>
    </section>
  );
}

function ServiceProfileDecisionStrip({
  context
}: {
  context: ContentWorkflowSnapshot["serviceProfileContext"];
}) {
  const statusChips = compactServiceProfileText([
    context.source_summary_label,
    prefixedServiceProfileText("Stan wiedzy", context.freshness_label)
  ]);
  const blocker = context.missing_contracts[0] ?? null;

  return (
    <section
      aria-label="Decyzja usługi i zasad twierdzeń"
      className="mt-4 border-t border-line pt-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Usługa i zasady twierdzeń
          </div>
          <h3 className="mt-1 text-base font-semibold text-ink">
            {context.service_label ?? "Nie ustalono usługi dla tego work itemu"}
          </h3>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-700">{context.reason}</p>
        </div>
        <span className="rounded-md border border-wait/30 bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">
          {context.status_label}
        </span>
      </div>

      <ServiceProfileStatusChips chips={statusChips} />
      <ServiceProfileBlocker blocker={blocker} />

      <p className="mt-3 text-xs leading-5 text-slate-600">{context.claim_policy_scope_label}</p>
      <p className="mt-3 text-sm font-medium leading-6 text-ink">{context.safe_next_step}</p>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <FactTile label="Dopuszczalne dla usługi" value={`${context.allowed_claims.length}`} />
        <FactTile label="Review dla usługi" value={`${context.claims_needing_review.length}`} />
        <FactTile label="Nie używaj dla usługi" value={`${context.blocked_claims.length}`} />
      </div>

      <ServiceProfileTechnicalDetails context={context} />
    </section>
  );
}

function ServiceProfileStatusChips({ chips }: { chips: string[] }) {
  if (!chips.length) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
      {chips.map((chip) => (
        <span key={chip} className="rounded-md border border-line bg-surface px-2 py-1">
          {chip}
        </span>
      ))}
    </div>
  );
}

function ServiceProfileBlocker({ blocker }: { blocker: string | null }) {
  if (blocker === null) {
    return null;
  }

  return (
    <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-sm leading-6 text-wait">
      <span className="font-semibold">Bloker:</span> {blocker}
    </p>
  );
}

function ServiceProfileTechnicalDetails({
  context
}: {
  context: ContentWorkflowSnapshot["serviceProfileContext"];
}) {
  const details = compactServiceProfileText([
    ...context.evidence_requirements.slice(0, 3),
    ...context.missing_contracts.slice(1).map((contract) => `Brakuje: ${contract}`),
    ...serviceProfileClaimDetails(context),
    ...serviceProfileTechnicalTrace(context)
  ]);
  if (!details.length) {
    return null;
  }

  return (
    <details className="mt-3 rounded-md border border-line bg-surface px-3 py-2 text-sm text-slate-700">
      <summary className="cursor-pointer font-semibold text-ink">Dowody i warunki</summary>
      <div className="mt-3 space-y-2 leading-6">
        {details.map((detail) => (
          <p key={detail}>{detail}</p>
        ))}
      </div>
    </details>
  );
}

function serviceProfileClaimDetails(
  context: ContentWorkflowSnapshot["serviceProfileContext"]
): string[] {
  return [
    ...serviceProfileClaimLines("Dopuszczalne dla tej usługi", context.allowed_claims),
    ...serviceProfileClaimLines("Wymaga review dla tej usługi", context.claims_needing_review),
    ...serviceProfileClaimLines("Nie używaj dla tej usługi", context.blocked_claims)
  ];
}

function serviceProfileClaimLines(label: string, claims: string[]) {
  return claims.map((claim) => `${label}: ${claim}`);
}

function serviceProfileTechnicalTrace(
  context: ContentWorkflowSnapshot["serviceProfileContext"]
): Array<string | null> {
  return [
    serviceProfileTraceLine("Źródła techniczne", context.source_connectors),
    serviceProfileTraceLine("Dowody", context.evidence_ids),
    serviceProfileTraceLine("Karty wiedzy", context.knowledge_card_ids),
    serviceProfileReviewTrace(context)
  ];
}

function serviceProfileTraceLine(label: string, values: string[]) {
  return values.length ? `${label}: ${values.join(", ")}` : null;
}

function serviceProfileReviewTrace(context: ContentWorkflowSnapshot["serviceProfileContext"]) {
  if (!context.review_action_id) {
    return null;
  }
  const label = context.review_action_label ? ` — ${context.review_action_label}` : "";
  return `Akcja review: ${context.review_action_id}${label}`;
}

function prefixedServiceProfileText(prefix: string, value: string) {
  return value ? `${prefix}: ${value}` : null;
}

function compactServiceProfileText(values: Array<string | null>) {
  return values.filter((value): value is string => Boolean(value));
}

function ClaimList({
  title,
  empty,
  claims
}: {
  title: string;
  empty: string;
  claims: ContentWorkflowSnapshot["claimLedger"]["entries"];
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {claims.length ? (
        <ul className="mt-2 space-y-3">
          {claims.slice(0, 3).map((claim) => (
            <li key={claim.id} className="text-sm leading-6 text-slate-700">
              <div className="font-medium text-ink">{claim.claim_text}</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">{claim.reason}</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">
                Dowody:{" "}
                {claim.evidence_ids.length ? claim.evidence_ids.join(", ") : "brak"}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-600">{empty}</p>
      )}
    </div>
  );
}

function ContentOpportunityEnrichmentPanel({
  enrichment
}: {
  enrichment: ContentOpportunityEnrichment | null;
}) {
  if (!enrichment) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-md border border-line bg-surface p-2 text-action">
            <ShieldCheck aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Wzbogacenie tematu
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              WILQ nie pokazuje interpretacji tematu bez osobnego kontraktu wzbogacenia z API.
            </p>
          </div>
        </div>
      </section>
    );
  }

  const facts = enrichment.source_facts.slice(0, 3);
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck aria-hidden="true" size={18} className="text-action" />
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Wzbogacenie tematu
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {enrichment.buyer_problem}
          </p>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {enrichment.buyer_trigger}
          </p>
        </div>
        <div className="grid w-full gap-2 text-sm sm:w-auto sm:min-w-80 sm:grid-cols-2">
          <FactTile label="Intencja" value={enrichment.intent_label} />
          <FactTile label="Status" value={enrichment.status_label} />
        </div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-surface p-3">
          <div className="text-xs uppercase tracking-normal text-slate-500">Kontekst tematu</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.service_fit}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Nie zastępuje typed decyzji usługi pokazanej wyżej.
          </p>
        </div>
        <div className="rounded-md border border-line bg-surface p-3">
          <div className="text-xs uppercase tracking-normal text-slate-500">Kierunek CTA</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.cta_hypothesis}</p>
        </div>
        <div className="rounded-md border border-line bg-surface p-3">
          <div className="text-xs uppercase tracking-normal text-slate-500">Pomiar</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {enrichment.measurement_baseline.label}
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {enrichment.measurement_baseline.reason}
          </p>
        </div>
      </div>
      {facts.length ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {facts.map((fact) => (
            <div key={fact.id} className="rounded-md border border-line bg-surface p-3 text-sm">
              <div className="font-semibold text-ink">{fact.label}</div>
              <p className="mt-2 leading-6 text-slate-700">{fact.summary}</p>
            </div>
          ))}
        </div>
      ) : null}
      {enrichment.blockers.length ? (
        <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-wait">
          <div className="font-semibold">{enrichment.blockers[0]?.label}</div>
          <p className="mt-2 leading-6">{enrichment.blockers[0]?.reason}</p>
          <p className="mt-1 text-xs">{enrichment.blockers[0]?.next_step}</p>
        </div>
      ) : null}
    </section>
  );
}

function WorkflowOperatorControls({
  data,
  actions
}: {
  data: ContentWorkflowSnapshot;
  actions: ContentWorkflowActions;
}) {
  const item = data.preflight.item;
  const controls = workflowControlItems(data, actions);
  return (
    <section id="content-workflow-actions" className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Stamp aria-hidden="true" size={18} className="text-action" />
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Decyzje operatora
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Te przyciski zapisują sprawdzenie i audyt w WILQ. Nie publikują treści, nie nadpisują
            strony i nie tworzą publicznego wpisu w WordPress.
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Temat: <span className="font-medium text-ink">{item.topic}</span>
          </p>
        </div>
        <div className="grid w-full gap-3 sm:w-auto sm:min-w-80">
          {controls.map((control) => (
            <WorkflowControlButton key={control.label} {...control} />
          ))}
        </div>
      </div>
    </section>
  );
}

type WorkflowControlItem = {
  label: string;
  disabledReason: string | null;
  pending: boolean;
  onClick: () => void;
};

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

function WorkflowControlButton({
  label,
  disabledReason,
  pending,
  onClick
}: {
  label: string;
  disabledReason: string | null;
  pending: boolean;
  onClick: () => void;
}) {
  const disabled = Boolean(disabledReason) || pending;
  return (
    <div>
      <button
        type="button"
        className="w-full rounded-md border border-action bg-action px-4 py-2 text-sm font-semibold text-white disabled:border-line disabled:bg-surface disabled:text-slate-500"
        disabled={disabled}
        onClick={onClick}
      >
        {pending ? "Zapisywanie..." : label}
      </button>
      {disabledReason ? (
        <p className="mt-1 text-xs leading-5 text-slate-500">{disabledReason}</p>
      ) : null}
    </div>
  );
}

function WorkflowSafetyPanels({
  data,
  draft,
  handoff,
  window,
  structuredRuntimeResult,
  structuredPreviewResult,
  qualityReview,
  revisionPlan,
  acfPreviewResult,
  executionResult
}: WorkflowSafetyPanelsProps) {
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-3">
      <SafetyPanel
        icon={<FileText aria-hidden="true" size={18} />}
        title="Paczka szkicu"
        text={draftSafetyText(draft?.publish_ready)}
      />
      <SafetyPanel
        icon={<ShieldCheck aria-hidden="true" size={18} />}
        title="Szkic treści"
        text={structuredRuntimeSafetyText(structuredRuntimeResult)}
      />
      <StructuredDraftPreviewPanel result={structuredPreviewResult} />
      <ContentQualityReviewPanel review={qualityReview} />
      <ContentRevisionPlanPanel plan={revisionPlan} />
      <AcfPreviewPanel result={acfPreviewResult} />
      <SafetyPanel
        icon={<ShieldCheck aria-hidden="true" size={18} />}
        title="WordPress zostaje w trybie szkicu"
        text={handoffSafetyText(handoff?.publish_allowed)}
      />
      <SafetyPanel
        icon={<ShieldCheck aria-hidden="true" size={18} />}
        title="Podgląd szkicu WordPress"
        text={wordpressExecutionSafetyText(executionResult)}
      />
      <SafetyPanel
        icon={<Clock3 aria-hidden="true" size={18} />}
        title={data.measurementWindow.outcome_blockers[0]?.label ?? "Nie wolno jeszcze oceniać efektu"}
        text={measurementSafetyText(window)}
      />
    </div>
  );
}

function AcfPreviewPanel({
  result
}: {
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null;
}) {
  const firstSection = result?.sections[0] ?? null;
  const fieldPreviews = firstSection?.field_previews ?? [];
  const filledFields =
    firstSection && !fieldPreviews.length
      ? Object.entries(firstSection.field_values).filter(([, value]) => Boolean(value))
      : [];

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Mapowanie ACF</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {acfPreviewSafetyText(result)}
          </p>
          {firstSection ? (
            <div className="mt-3 space-y-3 text-sm text-slate-700">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs uppercase tracking-normal text-slate-500">
                  Wybrany layout
                </div>
                <div className="mt-1 font-semibold text-ink">
                  {firstSection.layout_label} ({firstSection.layout_name})
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  Sekcja: {firstSection.section_heading}
                </div>
              </div>
              {fieldPreviews.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">
                    Mapowanie pól ACF
                  </div>
                  <AcfFieldPreviewList fields={fieldPreviews.slice(0, 4)} />
                </div>
              ) : filledFields.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">
                    Pola, które WILQ wypełni
                  </div>
                  <dl className="mt-2 space-y-2">
                    {filledFields.slice(0, 4).map(([fieldName, value]) => (
                      <div key={fieldName}>
                        <dt className="font-medium text-ink">{fieldName}</dt>
                        <dd className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function AcfFieldPreviewList({
  fields,
  depth = 0
}: {
  fields: AcfFieldPreview[];
  depth?: number;
}) {
  return (
    <dl className={`${depth ? "mt-2 border-l border-line pl-3" : "mt-2"} space-y-2`}>
      {fields.map((field) => (
        <div key={`${field.field_name}-${field.field_type}-${depth}`}>
          <dt className="font-medium text-ink">
            {field.field_label} ({field.field_name})
          </dt>
          {field.value_preview ? (
            <dd className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">
              {field.value_preview}
            </dd>
          ) : null}
          {field.note ? (
            <dd className="mt-1 text-xs leading-5 text-slate-500">{field.note}</dd>
          ) : null}
          {field.row_candidates.length ? (
            <dd className="mt-2 space-y-2">
              {field.row_candidates.slice(0, 2).map((candidate) => (
                <div
                  key={`${field.field_name}-${candidate.row_type}-${candidate.row_label}`}
                  className="rounded-md border border-line bg-white p-2"
                >
                  <div className="text-xs font-semibold text-ink">
                    Kandydat wiersza ACF: {candidate.row_label}
                  </div>
                  <div className="mt-1 text-xs leading-5 text-slate-500">
                    Do ręcznego przeglądu. {candidate.note}
                  </div>
                  {candidate.field_values.length ? (
                    <dl className="mt-2 space-y-1">
                      {candidate.field_values.slice(0, 4).map((value) => (
                        <div key={`${candidate.row_label}-${value.field_name}`}>
                          <dt className="text-xs font-medium text-ink">
                            {value.field_label} ({value.field_name})
                          </dt>
                          {value.value_preview ? (
                            <dd className="mt-0.5 whitespace-pre-line text-xs leading-5 text-slate-600">
                              {value.value_preview}
                            </dd>
                          ) : value.note ? (
                            <dd className="mt-0.5 text-xs leading-5 text-slate-500">
                              {value.note}
                            </dd>
                          ) : null}
                        </div>
                      ))}
                    </dl>
                  ) : null}
                  {candidate.evidence_ids.length ? (
                    <div className="mt-2 text-xs text-slate-500">
                      Dowody: {candidate.evidence_ids.slice(0, 3).join(", ")}
                    </div>
                  ) : null}
                </div>
              ))}
            </dd>
          ) : null}
          {field.nested_values.length && depth < 2 ? (
            <dd>
              <AcfFieldPreviewList fields={field.nested_values.slice(0, 6)} depth={depth + 1} />
            </dd>
          ) : null}
        </div>
      ))}
    </dl>
  );
}

function ContentQualityReviewPanel({
  review
}: {
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null;
}) {
  const firstFinding = review?.blockers[0] ?? review?.findings[0] ?? null;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <ShieldCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Ocena jakości szkicu</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {qualityReviewSafetyText(review)}
          </p>
          {review ? (
            <div className="mt-3 space-y-3 text-sm text-slate-700">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs uppercase tracking-normal text-slate-500">
                  Następny krok
                </div>
                <div className="mt-1 font-medium text-ink">{review.safe_next_step}</div>
              </div>
              {firstFinding ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="font-semibold text-ink">{firstFinding.label}</div>
                  <p className="mt-2 leading-6">{firstFinding.reason}</p>
                  <p className="mt-2 text-xs text-slate-500">{firstFinding.next_step}</p>
                </div>
              ) : null}
              <div className="grid gap-2 sm:grid-cols-2">
                {[review.evidence_coverage, review.claim_safety, review.cta_quality].map(
                  (dimension) => (
                    <div key={dimension.label} className="rounded-md border border-line bg-surface p-3">
                      <div className="font-semibold text-ink">{dimension.label}</div>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{dimension.reason}</p>
                    </div>
                  )
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function ContentRevisionPlanPanel({
  plan
}: {
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null;
}) {
  const firstInstruction = plan?.instructions[0] ?? null;
  const firstBlocker = plan?.blockers[0] ?? null;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Plan poprawki</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{revisionPlanSafetyText(plan)}</p>
          {firstBlocker ? (
            <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm">
              <div className="font-semibold text-ink">{firstBlocker.label}</div>
              <p className="mt-2 leading-6 text-slate-700">{firstBlocker.reason}</p>
              <p className="mt-2 text-xs text-slate-500">{firstBlocker.next_step}</p>
            </div>
          ) : null}
          {firstInstruction ? (
            <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm">
              <div className="font-semibold text-ink">{firstInstruction.change}</div>
              <p className="mt-2 leading-6 text-slate-700">{firstInstruction.reason}</p>
              {firstInstruction.required_evidence_ids.length ? (
                <p className="mt-2 text-xs text-slate-500">
                  Wymagane dowody: {firstInstruction.required_evidence_ids.join(", ")}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function StructuredDraftPreviewPanel({
  result
}: {
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null;
}) {
  const preview = result?.preview;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Podgląd treści</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {structuredPreviewSafetyText(result)}
          </p>
          {preview ? (
            <div className="mt-3 space-y-3 text-sm text-slate-700">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs uppercase tracking-normal text-slate-500">Tytuł</div>
                <div className="mt-1 font-semibold text-ink">{preview.title}</div>
              </div>
              {preview.sections.slice(0, 2).map((section) => (
                <div key={section.heading} className="rounded-md border border-line bg-surface p-3">
                  <div className="font-semibold text-ink">{section.heading}</div>
                  <p className="mt-2 whitespace-pre-line leading-6">{section.body_markdown}</p>
                  <div className="mt-2 text-xs text-slate-500">
                    Dowody sekcji: {section.evidence_ids.join(", ")}
                  </div>
                </div>
              ))}
              {preview.human_review_checklist.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">
                    Do sprawdzenia przez człowieka
                  </div>
                  <ul className="mt-2 space-y-1">
                    {preview.human_review_checklist.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function FactTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function SafetyPanel({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">{icon}</div>
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
        </div>
      </div>
    </section>
  );
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
