import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileText, ShieldCheck, Stamp } from "lucide-react";
import type { ReactNode } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemSnapshotAuditRequest,
  type ContentWorkItemSnapshotHumanReviewRequest,
  type ContentWorkItemStructuredDraftPreviewRequest,
  type ContentWorkItemStructuredDraftPreviewResponse,
  type ContentWorkItemStructuredDraftRuntimeRequest,
  type ContentWorkItemStructuredDraftRuntimeResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentWorkItemWordPressDraftExecutionResponse
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
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
};

export function ContentWorkflowSurface() {
  const workflow = useQuery({
    queryKey: ["content-workflow", "diagnostics-snapshot"],
    queryFn: loadContentWorkflowSnapshot
  });

  if (workflow.isLoading) return <LoadingBand />;
  if (workflow.error || !workflow.data) return <ContentWorkflowError />;
  return <ContentWorkflowLoaded data={workflow.data} />;
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

function ContentWorkflowLoaded({ data }: { data: ContentWorkflowSnapshot }) {
  const queryClient = useQueryClient();
  const refreshWorkflow = () =>
    queryClient.invalidateQueries({ queryKey: ["content-workflow", "diagnostics-snapshot"] });
  const reviewMutation = useMutation({
    mutationFn: saveContentWorkItemSnapshotHumanReview,
    onSuccess: refreshWorkflow
  });
  const auditMutation = useMutation({
    mutationFn: saveContentWorkItemSnapshotAudit,
    onSuccess: refreshWorkflow
  });
  const structuredRuntimeMutation = useMutation({
    mutationFn: postContentWorkItemStructuredDraftRuntime
  });
  const structuredPreviewMutation = useMutation({
    mutationFn: postContentWorkItemStructuredDraftPreview
  });
  const executionMutation = useMutation({
    mutationFn: postContentWorkItemWordPressDraftExecution
  });
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);
  const structuredRuntimeResult = runtimeResultFrom(structuredRuntimeMutation.data);
  const structuredPreviewResult = previewResultFrom(structuredPreviewMutation.data);
  const executionResult = executionResultFrom(executionMutation.data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={item.topic} />
      <WorkflowProofSummary data={data} />
      <WorkflowStepsList steps={steps} />
      <WorkflowOperatorControls
        data={data}
        reviewPending={reviewMutation.isPending}
        auditPending={auditMutation.isPending}
        structuredRuntimePending={structuredRuntimeMutation.isPending}
        structuredPreviewPending={structuredPreviewMutation.isPending}
        executionPending={executionMutation.isPending}
        structuredRuntimeResult={structuredRuntimeResult}
        structuredPreviewResult={structuredPreviewResult}
        executionResult={executionResult}
        onStructuredRuntimeDryRun={() =>
          submitIfReady(structuredRuntimeDryRunRequest(data), (request) =>
            structuredRuntimeMutation.mutate(request)
          )
        }
        onStructuredPreview={() =>
          submitIfReady(structuredPreviewRequest(data, structuredRuntimeResult), (request) =>
            structuredPreviewMutation.mutate(request)
          )
        }
        onReview={() =>
          submitIfReady(humanReviewRequest(data, draft), (request) =>
            reviewMutation.mutate(request)
          )
        }
        onAudit={() =>
          submitIfReady(auditRequest(data), (request) => auditMutation.mutate(request))
        }
        onExecutionDryRun={() =>
          submitIfReady(wordpressExecutionRequest(draft, handoff), (request) =>
            executionMutation.mutate(request)
          )
        }
      />
      <WorkflowSafetyPanels
        data={data}
        draft={draft}
        handoff={handoff}
        window={window}
        structuredRuntimeResult={structuredRuntimeResult}
        structuredPreviewResult={structuredPreviewResult}
        executionResult={executionResult}
      />
    </main>
  );
}

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type WordPressHandoff =
  ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];

function runtimeResultFrom(response: ContentWorkItemStructuredDraftRuntimeResponse | undefined) {
  return response?.runtime_result ?? null;
}

function previewResultFrom(response: ContentWorkItemStructuredDraftPreviewResponse | undefined) {
  return response?.preview_result ?? null;
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
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-3">
          <FactTile label="Dowody" value={`Dowody: ${unique(item.evidence_ids).length}`} />
          <FactTile label="Tryb" value={data.preflight.preflight_verdict.recommended_mode} />
          <FactTile label="Adres" value="canonical publiczny" />
        </div>
      </div>
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
  reviewPending,
  auditPending,
  structuredRuntimePending,
  structuredPreviewPending,
  executionPending,
  structuredRuntimeResult,
  structuredPreviewResult,
  executionResult,
  onStructuredRuntimeDryRun,
  onStructuredPreview,
  onReview,
  onAudit,
  onExecutionDryRun
}: {
  data: ContentWorkflowSnapshot;
  reviewPending: boolean;
  auditPending: boolean;
  structuredRuntimePending: boolean;
  structuredPreviewPending: boolean;
  executionPending: boolean;
  structuredRuntimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null;
  structuredPreviewResult: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null;
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
  onStructuredRuntimeDryRun: () => void;
  onStructuredPreview: () => void;
  onReview: () => void;
  onAudit: () => void;
  onExecutionDryRun: () => void;
}) {
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const review = data.humanReview.review;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const reviewDisabledReason = reviewControlDisabledReason(data, Boolean(draft), reviewPending);
  const auditDisabledReason = auditControlDisabledReason(data, auditPending);
  const structuredRuntimeDisabledReason = structuredRuntimeControlDisabledReason(
    data,
    structuredRuntimePending,
    structuredRuntimeResult
  );
  const structuredPreviewDisabledReason = structuredPreviewControlDisabledReason(
    data,
    structuredPreviewPending,
    structuredPreviewResult,
    structuredRuntimeResult
  );
  const executionDisabledReason = executionControlDisabledReason(
    Boolean(draft),
    Boolean(handoff),
    executionPending,
    executionResult
  );
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
          <WorkflowControlButton
            label={review ? "Sprawdzenie zapisane" : "Zatwierdź sprawdzenie"}
            disabledReason={reviewDisabledReason}
            pending={reviewPending}
            onClick={onReview}
          />
          <WorkflowControlButton
            label={handoff ? "Audyt zapisany" : "Zapisz audyt przekazania"}
            disabledReason={auditDisabledReason}
            pending={auditPending}
            onClick={onAudit}
          />
          <WorkflowControlButton
            label={structuredRuntimeResult ? "Próba szkicu gotowa" : "Sprawdź gotowość szkicu"}
            disabledReason={structuredRuntimeDisabledReason}
            pending={structuredRuntimePending}
            onClick={onStructuredRuntimeDryRun}
          />
          <WorkflowControlButton
            label={structuredPreviewResult ? "Podgląd treści gotowy" : "Pokaż podgląd treści"}
            disabledReason={structuredPreviewDisabledReason}
            pending={structuredPreviewPending}
            onClick={onStructuredPreview}
          />
          <WorkflowControlButton
            label={executionResult ? "Podgląd szkicu gotowy" : "Sprawdź podgląd szkicu"}
            disabledReason={executionDisabledReason}
            pending={executionPending}
            onClick={onExecutionDryRun}
          />
        </div>
      </div>
    </section>
  );
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
