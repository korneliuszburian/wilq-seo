import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileText, ShieldCheck, Stamp } from "lucide-react";
import type { ReactNode } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
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
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
};

export function ContentWorkflowSurface() {
  const queryClient = useQueryClient();
  const workflow = useQuery({
    queryKey: ["content-workflow", "diagnostics-snapshot"],
    queryFn: loadContentWorkflowSnapshot
  });
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
  const executionMutation = useMutation({
    mutationFn: postContentWorkItemWordPressDraftExecution
  });

  if (workflow.isLoading) return <LoadingBand />;
  if (workflow.error || !workflow.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <div className="rounded-md border border-wait/30 bg-wait/10 p-4 text-sm text-wait">
          Nie udało się odczytać workflow treści z WILQ. Nie pokazujemy decyzji bez kontraktów API.
        </div>
      </main>
    );
  }

  const data = workflow.data;
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={item.topic} />
      <WorkflowProofSummary data={data} />
      <WorkflowStepsList steps={steps} />
      <WorkflowOperatorControls
        data={data}
        reviewPending={reviewMutation.isPending}
        auditPending={auditMutation.isPending}
        executionPending={executionMutation.isPending}
        executionResult={executionMutation.data?.execution_result ?? null}
        onReview={() => {
          if (!draft) return;
          reviewMutation.mutate({
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
          });
        }}
        onAudit={() => {
          const review = data.humanReview.review;
          if (!review) return;
          auditMutation.mutate({
            audit: {
              audit_id: `audit_${item.id}`,
              actor: "wilku",
              reason:
                "Operator zatwierdził przekazanie wyłącznie w trybie szkicu. WordPress może dostać wyłącznie szkic.",
              evidence_ids: unique(item.evidence_ids),
              human_review_id: review.id
            }
          });
        }}
        onExecutionDryRun={() => {
          if (!handoff || !draft) return;
          executionMutation.mutate({
            handoff,
            draft_package: draft,
            mode: "dry_run"
          });
        }}
      />
      <WorkflowSafetyPanels
        data={data}
        draft={draft}
        handoff={handoff}
        window={window}
        executionResult={executionMutation.data?.execution_result ?? null}
      />
    </main>
  );
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
                {step.status}
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
  executionPending,
  executionResult,
  onReview,
  onAudit,
  onExecutionDryRun
}: {
  data: ContentWorkflowSnapshot;
  reviewPending: boolean;
  auditPending: boolean;
  executionPending: boolean;
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
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
  executionResult
}: WorkflowSafetyPanelsProps) {
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-4">
      <SafetyPanel
        icon={<FileText aria-hidden="true" size={18} />}
        title="Paczka szkicu"
        text={draftSafetyText(draft?.publish_ready)}
      />
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
