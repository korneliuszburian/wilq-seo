import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileText, ShieldCheck, Stamp } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getWordPressAuthoringProfile,
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
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
  type ContentWorkItemQueueCandidate,
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
  type ContentWordPressDraftActivationPacketResponse,
  type ContentWordPressDraftWriteReadinessResponse,
  type ContentOpportunityEnrichment,
  type ContentOpportunityEnrichmentResponse,
  type WordPressAuthoringProfile
} from "../lib/api";
import {
  buildWorkflowSteps,
  loadContentWorkflowSnapshot,
  type ContentWorkflowSnapshot,
  type WorkflowStep
} from "./contentWorkflowRuntime";

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
type ContentWorkItemQueueQuery = UseQueryResult<ContentWorkItemQueueResponse, Error>;
type ContentWorkflowSnapshotQuery = UseQueryResult<ContentWorkflowSnapshot, Error>;
type ContentOpportunityEnrichmentQuery = UseQueryResult<
  ContentOpportunityEnrichmentResponse,
  Error
>;
type WordPressAuthoringProfileQuery = UseQueryResult<WordPressAuthoringProfile, Error>;
type WordPressDraftWriteReadinessQuery = UseQueryResult<
  ContentWordPressDraftWriteReadinessResponse,
  Error
>;
type WordPressDraftActivationPacketQuery = UseQueryResult<
  ContentWordPressDraftActivationPacketResponse,
  Error
>;

export function ContentWorkflowSurface() {
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<string | null>(null);
  const queue = useQuery({
    queryKey: ["content-workflow", "queue"],
    queryFn: getContentWorkItemQueue
  });
  const activeWorkItemId =
    selectedWorkItemId ?? (queue.data ? defaultSelectedWorkItemId(queue.data) : null);

  const selectedCandidate = useMemo(
    () =>
      queue.data?.candidates.find((candidate) => candidate.work_item_id === activeWorkItemId) ??
      null,
    [activeWorkItemId, queue.data]
  );
  const selectedCandidateBlocked = selectedCandidate?.recommended_mode === "block";
  const workflow = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId],
    queryFn: () => loadContentWorkflowSnapshot(activeWorkItemId ?? undefined),
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked)
  });
  const enrichment = useQuery({
    queryKey: ["content-workflow", "work-item", activeWorkItemId, "enrichment"],
    queryFn: () => getContentWorkItemEnrichment(activeWorkItemId ?? ""),
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked)
  });
  const authoringProfile = useQuery({
    queryKey: ["content-workflow", "wordpress-authoring-profile"],
    queryFn: getWordPressAuthoringProfile
  });
  const draftWriteReadiness = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-write-readiness"],
    queryFn: getContentWordPressDraftWriteReadiness
  });
  const draftActivationPacket = useQuery({
    queryKey: ["content-workflow", "wordpress-draft-activation-packet", activeWorkItemId],
    queryFn: () => getContentWordPressDraftActivationPacket(activeWorkItemId),
    enabled: Boolean(activeWorkItemId && !selectedCandidateBlocked)
  });

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
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (workflow.isLoading) return <LoadingBand />;
  if (workflow.error || !workflow.data) return <ContentWorkflowError />;
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

function ContentWorkflowError() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-wait/30 bg-wait/10 p-4 text-sm text-wait">
        Nie udało się odczytać workflow treści z WILQ. Nie pokazujemy decyzji bez kontraktów API.
      </div>
    </main>
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
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={item.topic} />
      <ContentWorkflowTodayPanel data={data} queue={queue} />
      <ContentCandidateQueuePanel
        queue={queue}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
      <WorkflowProofSummary data={data} />
      <WordPressAuthoringReadinessPanel authoringProfile={authoringProfile} />
      <WordPressDraftActivationPacketPanel draftActivationPacket={draftActivationPacket} />
      <WordPressDraftWriteReadinessPanel draftWriteReadiness={draftWriteReadiness} />
      <ClaimLedgerGatePanel data={data} />
      <ContentOpportunityEnrichmentPanel enrichment={enrichment} />
      <WorkflowStepsList steps={steps} />
      <WorkflowOperatorControls
        data={data}
        actions={actions}
      />
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
    </main>
  );
}

function ContentWorkflowTodayPanel({
  data,
  queue
}: {
  data: ContentWorkflowSnapshot;
  queue: ContentWorkItemQueueResponse;
}) {
  const item = data.preflight.item;
  const blockedSteps = data.operatorSteps.filter((step) =>
    step.statusLabel.toLowerCase().includes("zablok")
  );
  const readySteps = data.operatorSteps.filter(
    (step) => !step.statusLabel.toLowerCase().includes("zablok")
  );
  const activeCandidate = queue.candidates.find(
    (candidate) => candidate.work_item_id === item.id
  );

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Workflow treści: co dziś zrobić
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            Pracuj tylko na propozycji, która przeszła bramki
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {queue.operator_summary}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <FactTile label="Propozycje" value={`${queue.candidate_count}`} />
          <FactTile label="Gotowe" value={`${queue.actionable_candidate_count}`} />
          <FactTile label="Dowody" value={`${unique(item.evidence_ids).length}`} />
          <FactTile label="Etapy zablokowane" value={`${blockedSteps.length}`} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Aktywny temat</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">{item.topic}</p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            {activeCandidate?.recommended_mode_label ??
              data.preflight.preflight_verdict.recommended_mode}
          </p>
          <div className="mt-3 grid gap-1 text-xs leading-5 text-slate-600">
            {readySteps.slice(0, 3).map((step) => (
              <div key={step.id}>
                {step.title}: {step.statusLabel}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Co jeszcze blokuje szkic</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Nie przechodź do szkicu ani WordPress, dopóki WILQ nie odblokuje briefu,
            paczki szkicu, decyzji człowieka i audytu.
          </p>
          <div className="mt-3 grid gap-1 text-xs leading-5 text-slate-600">
            {blockedSteps.slice(0, 4).map((step) => (
              <div key={step.id}>
                {step.title}: {step.statusLabel}
              </div>
            ))}
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

function ContentWorkflowEmptyQueue({ queue }: { queue: ContentWorkItemQueueResponse }) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic="Kolejka treści" />
      <section className="rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
          Brak propozycji do pracy nad treścią
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">{queue.operator_summary}</p>
      </section>
    </main>
  );
}

function ContentCandidateQueuePanel({
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Kolejka tematów
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {queue.operator_summary}
          </p>
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <FactTile label="Propozycje" value={`${queue.candidate_count}`} />
          <FactTile label="Gotowe do pracy" value={`${queue.actionable_candidate_count}`} />
        </div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        {queue.candidates.map((candidate) => (
          <button
            key={candidate.work_item_id}
            type="button"
            className={`rounded-md border p-3 text-left text-sm ${
              candidate.work_item_id === selectedWorkItemId
                ? "border-action bg-action/10"
                : "border-line bg-surface"
            }`}
            onClick={() => onSelectWorkItem(candidate.work_item_id)}
          >
            <div className="font-semibold text-ink">{candidate.title}</div>
            <div className="mt-1 text-xs font-medium uppercase tracking-normal text-slate-500">
              {candidate.recommended_mode_label} · {candidate.status_label}
            </div>
            <p className="mt-2 leading-6 text-slate-600">{candidate.reason}</p>
            <div className="mt-2 text-xs text-slate-500">
              {candidate.evidence_ids.length} dowody · {candidate.measurement_readiness.label}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type WordPressHandoff =
  ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
type AcfFieldPreview =
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"]["sections"][number]["field_previews"][number];

function defaultSelectedWorkItemId(queue: ContentWorkItemQueueResponse) {
  return (
    queue.candidates.find((candidate) => candidate.recommended_mode !== "block")?.work_item_id ??
    queue.candidates[0]?.work_item_id ??
    null
  );
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
  handoff: WordPressHandoff
): ContentWorkItemWordPressDraftExecutionRequest | null {
  if (!draft || !handoff) return null;
  return {
    handoff,
    draft_package: draft,
    mode: "dry_run"
  };
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

function ContentWorkflowHeader({ topic }: { topic: string }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">Workflow treści bez slopu</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
          Pierwszy kontrolny tor pokazuje, czy WILQ potrafi przeprowadzić temat od sprawdzenia pisania
          do szkicu WordPress i okna pomiaru bez pomijania bramek.
        </p>
      </div>
      <div className="rounded-md border border-line bg-white px-4 py-3 text-sm">
        <div className="text-xs uppercase tracking-normal text-slate-500">Temat</div>
        <div className="mt-1 font-semibold text-ink">{topic}</div>
      </div>
    </div>
  );
}

function WorkflowProofSummary({ data }: { data: ContentWorkflowSnapshot }) {
  const item = data.preflight.item;
  const salesBrief = data.salesBrief.sales_brief_result.brief;
  const signalQuality = salesBrief?.signal_quality ?? null;
  const knowledgeConstraints = salesBrief?.knowledge_constraints.slice(0, 3) ?? [];
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co WILQ już potwierdził
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Finalny adres pozostaje publicznym adresem Ekologus, podgląd dev jest tylko kontekstem
            projektu, a WordPress nie dostaje publikacji automatycznej.
          </p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {signalQuality
              ? signalQuality.reason
              : "Sales Brief jest zablokowany, więc WILQ nie pokazuje jakości sygnału jako rekomendacji."}
          </p>
          {knowledgeConstraints.length ? (
            <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm">
              <div className="font-semibold text-ink">Ograniczenia wiedzy i dowody</div>
              <ul className="mt-2 space-y-2">
                {knowledgeConstraints.map((constraint) => (
                  <li key={`${constraint.card_id}-${constraint.constraint_type}-${constraint.reason}`}>
                    <span className="font-medium text-slate-700">{constraint.label}</span>
                    <span className="text-slate-600">: {constraint.reason}</span>
                    <div className="mt-1 text-xs text-slate-500">
                      Dowody WILQ:{" "}
                      {constraint.evidence_ids.length
                        ? constraint.evidence_ids.join(", ")
                        : "brak dowodu przy tym ograniczeniu"}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-3">
          <FactTile label="Dowody" value={`Dowody: ${unique(item.evidence_ids).length}`} />
          <FactTile label="Tryb" value={data.preflight.preflight_verdict.recommended_mode} />
          <FactTile label="Jakość briefu" value={signalQuality?.status_label ?? "brief zablokowany"} />
        </div>
      </div>
    </section>
  );
}

function WordPressAuthoringReadinessPanel({
  authoringProfile
}: {
  authoringProfile: WordPressAuthoringProfileQuery;
}) {
  if (authoringProfile.isLoading) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          WordPress: sprawdzanie trybu szkicu
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          WILQ odczytuje gotowość REST/ACF/WP-CLI bez wykonywania zapisu.
        </p>
      </section>
    );
  }
  if (authoringProfile.error || !authoringProfile.data) {
    return (
      <section className="mb-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
          WordPress: brak odczytu gotowości szkicu
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          WILQ nie pokazuje gotowości WordPress bez API. Nie próbuj przekazywać
          szkicu poza ścieżką review i audytu.
        </p>
      </section>
    );
  }
  const profile = authoringProfile.data;
  const layoutLabel = profile.acf.layouts_discovered
    ? `${profile.acf.layouts.length} sekcji ACF rozpoznanych`
    : "brak rozpoznanych sekcji ACF";
  const blocker = profile.blockers[0] ?? null;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            WordPress: szkic bez publikacji
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ rozpoznaje techniczny tor przekazania treści do WordPress, ale
            nie wykonuje zapisu i nie publikuje. Każdy zapis nadal wymaga
            sprawdzenia, podglądu, decyzji człowieka i audytu.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <FactTile label="REST" value={authoringReadinessLabel(profile.rest_api.status)} />
          <FactTile label="ACF" value={layoutLabel} />
          <FactTile label="WP-CLI" value={authoringReadinessLabel(profile.wp_cli.status)} />
          <FactTile label="Publikacja" value="zablokowana" />
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <SafetyPanel
          icon={<Stamp aria-hidden="true" size={18} />}
          title="Zapis zewnętrzny"
          text="Ten odczyt nie wykonał żadnego zapisu zewnętrznego."
        />
        <SafetyPanel
          icon={<ShieldCheck aria-hidden="true" size={18} />}
          title="Tryb WordPress"
          text="Bezpośredni zapis do WordPress jest zablokowany poza ścieżką sprawdzenia w WILQ."
        />
        <SafetyPanel
          icon={<FileText aria-hidden="true" size={18} />}
          title="Najbliższy blok"
          text={
            blocker
              ? `${blocker.reason} Następny krok: ${blocker.next_step}`
              : "Brak blokad authoringu; nadal obowiązuje draft-only review i audyt przed zapisem."
          }
        />
      </div>
    </section>
  );
}

function WordPressDraftWriteReadinessPanel({
  draftWriteReadiness
}: {
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
}) {
  if (draftWriteReadiness.isLoading) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          WordPress: sprawdzanie gotowości zapisu draftu
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          WILQ sprawdza env, REST i ślad audytu bez zapisu do WordPress.
        </p>
      </section>
    );
  }
  if (draftWriteReadiness.error || !draftWriteReadiness.data) {
    return (
      <section className="mb-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
          WordPress: brak readiness zapisu draftu
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Nie ma potwierdzenia gotowości zapisu szkicu. Zostań przy podglądzie
          zmian i podglądzie ACF.
        </p>
      </section>
    );
  }

  const readiness = draftWriteReadiness.data;
  const firstBlocker = readiness.blockers[0] ?? null;

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-action">
            WordPress: gotowość realnego draftu
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
            Ten panel pokazuje, czy WILQ może wykonać wyłącznie zapis szkicu
            WordPress. Publikacja pozostaje zablokowana; brak warunku oznacza stop,
            nie ręczne obejście.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <FactTile label="Write" value={readiness.ready ? "gotowy" : "zablokowany"} />
          <FactTile
            label="Env"
            value={readiness.live_write_enabled_by_env ? "włączony" : "wyłączony"}
          />
          <FactTile
            label="REST"
            value={readiness.rest_adapter_configured ? "gotowy" : "brak"}
          />
          <FactTile
            label="Auth"
            value={wordpressWriteAuthorizationStatusLabel(
              readiness.write_authorization_status
            )}
          />
          <FactTile
            label="Braki"
            value={`${readiness.missing_audit_event_types.length}`}
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Następny bezpieczny krok</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {readiness.operator_next_step}
          </p>
          {firstBlocker ? (
            <p className="mt-3 text-sm leading-6 text-risk">
              {firstBlocker.label}: {firstBlocker.reason}
            </p>
          ) : null}
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Ślad wymagany przed write</h3>
          <div className="mt-2 grid gap-1 text-sm leading-6 text-slate-700">
            {readiness.required_audit_events.map((requirement) => (
              <div key={requirement.event_type} className="flex justify-between gap-3">
                <span>{requirement.label}</span>
                <span className={requirement.satisfied ? "text-success" : "text-risk"}>
                  {requirement.satisfied ? "jest" : "brak"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function WordPressDraftActivationPacketPanel({
  draftActivationPacket
}: {
  draftActivationPacket: WordPressDraftActivationPacketQuery;
}) {
  if (draftActivationPacket.isLoading) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Aktywacja szkicu WordPress
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          WILQ sprawdza paczkę szkicu, review, audyt, handoff i podgląd zmian
          bez zapisu do WordPress.
        </p>
      </section>
    );
  }
  if (draftActivationPacket.error || !draftActivationPacket.data) {
    return (
      <section className="mb-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
          Aktywacja szkicu WordPress niedostępna
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Nie ma API-owned paczki aktywacji, więc WILQ zostaje przy podglądzie
          i nie próbuje zapisu.
        </p>
      </section>
    );
  }

  const packet = draftActivationPacket.data;
  const blockers = [...packet.handoff_blockers, ...packet.execution_blockers];

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-action">
            Aktywacja szkicu WordPress
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
            {packet.operator_next_step}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {packet.topic}
            {packet.final_canonical_url ? ` · ${packet.final_canonical_url}` : ""}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <FactTile
            label="Paczka szkicu"
            value={readyLabel(packet.draft_package_ready)}
          />
          <FactTile
            label="Review człowieka"
            value={readyLabel(packet.human_review_ready)}
          />
          <FactTile label="Audit" value={readyLabel(packet.audit_ready)} />
          <FactTile label="Handoff" value={readyLabel(packet.handoff_ready)} />
          <FactTile label="Podgląd zmian" value={readyLabel(packet.dry_run_ready)} />
          <FactTile
            label="Live write"
            value={packet.live_write_enabled_by_env ? "włączony" : "wyłączony"}
          />
          <FactTile label="Publikacja" value="zablokowana" />
          <FactTile label="Zapis zewnętrzny" value="nie wykonano" />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Co blokuje aktywację</h3>
          {blockers.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2 text-sm">
              {blockers.map((blocker) => (
                <span
                  key={blocker}
                  className="rounded-md border border-risk/30 bg-risk/10 px-2 py-1 text-risk"
                >
                  {wordpressActivationBlockerLabel(blocker)}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Brak blokad w paczce aktywacji, ale publikacja i destrukcyjne
              aktualizacje nadal są niedozwolone.
            </p>
          )}
          {packet.draft_package_id ? (
            <p className="mt-3 text-xs text-slate-500">
              Paczka szkicu istnieje w WILQ i czeka na review.
            </p>
          ) : null}
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Review przed handoffem</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {packet.review_preview_status_label}
          </p>
          {packet.human_review_checklist.length ? (
            <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-700">
              {packet.human_review_checklist.map((item) => (
                <li key={item}>- {item}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Następne kroki</h3>
          <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-700">
            {packet.next_steps.map((step) => (
              <li key={step}>- {step}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            Dowody: {packet.evidence_ids.length} · Źródła:{" "}
            {packet.source_connectors.length}
          </p>
        </div>
      </div>
    </section>
  );
}

function readyLabel(ready: boolean): string {
  return ready ? "gotowe" : "brakuje";
}

function wordpressActivationBlockerLabel(blocker: string): string {
  const labels: Record<string, string> = {
    missing_human_review: "brakuje review człowieka",
    missing_audit: "brakuje audytu",
    missing_handoff: "brakuje handoffu"
  };
  return labels[blocker] ?? blocker;
}

function wordpressWriteAuthorizationStatusLabel(status: string): string {
  if (status === "available") {
    return "gotowe";
  }
  if (status === "audit_actor_mismatch") {
    return "aktor";
  }
  return "brak audytu";
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
    <section className="mb-6 rounded-md border border-line bg-white p-4">
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
          <div className="text-xs uppercase tracking-normal text-slate-500">Dopasowanie usługi</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.service_fit}</p>
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

function WorkflowStepsList({ steps }: { steps: WorkflowStep[] }) {
  return (
    <ol aria-label="Kroki workflow treści" className="grid gap-3 lg:grid-cols-3">
      {steps.map((step) => (
        <li key={step.title} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-surface p-2 text-action">
              <CheckCircle2 aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-ink">{step.title}</h2>
              <div className="mt-1 text-xs font-medium uppercase tracking-normal text-slate-500">
                {step.statusLabel}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.summary}</p>
            </div>
          </div>
        </li>
      ))}
    </ol>
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
    <section className="mt-6 rounded-md border border-line bg-white p-4">
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
  if (result.external_write_attempted) {
    return "Zatrzymaj workflow: podgląd nie powinien wykonywać zewnętrznego zapisu.";
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

function authoringReadinessLabel(status: string) {
  if (status === "configured") return "skonfigurowane";
  if (status === "available") return "dostępne";
  if (status === "not_configured") return "nieustawione";
  if (status === "missing") return "brakuje danych";
  if (status === "blocked") return "zablokowane";
  return "do sprawdzenia";
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
