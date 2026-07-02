import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileText, ShieldCheck, Stamp } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
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
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentOpportunityEnrichment,
  type ContentOpportunityEnrichmentResponse
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

  return (
    <ContentWorkflowRouteState
      activeWorkItemId={activeWorkItemId}
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
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
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
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
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
      enrichment={enrichment}
      queue={queue}
      workflow={workflow}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowSelectedReady({
  activeWorkItemId,
  enrichment,
  queue,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
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
  enrichment,
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  data: ContentWorkflowSnapshot;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const actions = useContentWorkflowActions(data, selectedWorkItemId);
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={item.topic} />
      <ContentCandidateQueuePanel
        queue={queue}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
      <WorkflowProofSummary data={data} />
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
        executionResult={actions.executionResult}
      />
    </main>
  );
}

function useContentWorkflowActions(
  data: ContentWorkflowSnapshot,
  selectedWorkItemId: string
) {
  const mutations = useContentWorkflowMutations(selectedWorkItemId);
  return contentWorkflowActions(data, mutations);
}

function useContentWorkflowMutations(selectedWorkItemId: string) {
  const queryClient = useQueryClient();
  const refreshWorkflow = () =>
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", selectedWorkItemId]
    });
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
  const executionMutation = useMutation({ mutationFn: postContentWorkItemWordPressDraftExecution });
  return {
    reviewMutation,
    auditMutation,
    structuredRuntimeMutation,
    structuredPreviewMutation,
    qualityReviewMutation,
    revisionPlanMutation,
    executionMutation
  };
}

function contentWorkflowActions(
  data: ContentWorkflowSnapshot,
  mutations: ContentWorkflowMutations
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
    executionPending: mutations.executionMutation.isPending,
    structuredRuntimeResult,
    structuredPreviewResult: previewResultFrom(mutations.structuredPreviewMutation.data),
    qualityReview,
    revisionPlan: revisionPlanFrom(mutations.revisionPlanMutation.data),
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
          <FactTile label="Kandydaci" value={`${queue.candidate_count}`} />
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
    claim_ledger: null,
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
  const signalQuality = data.salesBrief.sales_brief_result.brief?.signal_quality ?? null;
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
