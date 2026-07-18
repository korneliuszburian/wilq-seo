import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  applyAction,
  confirmAction,
  getAction,
  impactCheckAction,
  previewAction,
  reviewAction,
  validateAction,
  type ActionApplyResult,
  type ActionObject,
  type ContentDraftRevisionBinding,
  type ContentWordPressDraftActivationPacketResponse
} from "../lib/api";

const ACTION_ID = "act_apply_wordpress_draft_handoff";
const OPERATOR = "operator_local_dashboard";

const WIZARD_STAGES = [
  {
    id: "preview",
    eventType: "action_preview_generated",
    label: "Podgląd",
    title: "Sprawdź dokładną wersję",
    summary:
      "WILQ sprawdzi akcję i pokaże zakres przekazania. Ten krok nie zapisuje niczego w WordPressie.",
    buttonLabel: "Sprawdź wersję i podgląd"
  },
  {
    id: "review",
    eventType: "human_review_approved_for_prepare",
    label: "Review",
    title: "Zatwierdź przygotowanie draftu",
    summary:
      "Potwierdź, że podgląd dotyczy tej wersji i że celem jest wyłącznie nowy szkic na devie.",
    buttonLabel: "Zapisz review akcji"
  },
  {
    id: "confirm",
    eventType: "action_apply_confirmed",
    label: "Potwierdzenie",
    title: "Potwierdź zamiar zapisu",
    summary:
      "To jawne potwierdzenie operatora. Nadal nie publikuje, nie aktualizuje i nie usuwa treści.",
    buttonLabel: "Potwierdź draft-only"
  },
  {
    id: "impact",
    eventType: "action_impact_check_completed",
    label: "Bezpieczeństwo",
    title: "Sprawdź bezpieczeństwo zapisu",
    summary:
      "WILQ sprawdzi wymagany ślad, źródła i blokady przed dopuszczeniem adaptera WordPress.",
    buttonLabel: "Sprawdź gotowość zapisu"
  },
  {
    id: "apply",
    eventType: "action_apply_completed",
    label: "Draft",
    title: "Utwórz nowy szkic na devie",
    summary:
      "Jedyna dozwolona operacja to utworzenie nowego wpisu ze statusem draft. Publikacja i destrukcyjne zmiany pozostają zablokowane.",
    buttonLabel: "Utwórz szkic na devie"
  }
] as const;

type WizardStageId = (typeof WIZARD_STAGES)[number]["id"];

type WizardMutationResult = {
  stage: WizardStageId;
  status: "ready" | "blocked";
  message: string;
  nextStep: string;
  applyResult?: ActionApplyResult;
};

type DraftReadback = ContentWordPressDraftActivationPacketResponse["draft_readback"];

export function ContentWordPressDraftActionWizard({
  actionId,
  binding,
  draftReadback,
  handoffBlocker,
  revisionNumber
}: {
  actionId: string | null;
  binding: ContentDraftRevisionBinding | null;
  draftReadback: DraftReadback;
  handoffBlocker: { label: string; reason: string; next_step: string } | null;
  revisionNumber: number | null;
}) {
  const queryClient = useQueryClient();
  const [reviewAcknowledgementKey, setReviewAcknowledgementKey] = useState<string | null>(null);
  const [confirmationAcknowledgementKey, setConfirmationAcknowledgementKey] = useState<
    string | null
  >(null);
  const action = useQuery({
    queryKey: ["actions", ACTION_ID],
    queryFn: () => getAction(ACTION_ID),
    enabled: binding !== null && actionId === ACTION_ID,
    retry: false
  });
  const completedStageCount = binding
    ? matchingCompletedStageCount(action.data?.audit_events ?? [], binding)
    : 0;
  const currentStage = WIZARD_STAGES[Math.min(completedStageCount, WIZARD_STAGES.length - 1)];
  const complete = completedStageCount === WIZARD_STAGES.length;
  const terminalApplyBlocker =
    binding && action.data
      ? latestMatchingApplyBlocker(action.data.audit_events, binding)
      : null;
  const currentAcknowledgementKey = binding
    ? acknowledgementKey(binding, completedStageCount, action.data?.audit_events ?? [])
    : null;
  const reviewAcknowledged = reviewAcknowledgementKey === currentAcknowledgementKey;
  const confirmationAcknowledged =
    confirmationAcknowledgementKey === currentAcknowledgementKey;
  const runStage = useMutation({
    retry: false,
    mutationFn: async (stage: WizardStageId): Promise<WizardMutationResult> => {
      if (!binding) {
        return {
          stage,
          status: "blocked",
          message: "Brakuje powiązania z zaakceptowaną wersją treści.",
          nextStep: "Wróć do review i przygotuj handoff tej dokładnej wersji."
        };
      }
      if (stage === "preview") {
        const validation = await validateAction(ACTION_ID);
        if (!validation.valid) {
          return {
            stage,
            status: "blocked",
            message: validation.errors[0] ?? "Akcja nie przeszła walidacji WILQ.",
            nextStep: "Usuń wskazaną blokadę i uruchom sprawdzenie ponownie."
          };
        }
        const preview = await previewAction(ACTION_ID, {
          requested_by: OPERATOR,
          max_items: 8,
          wordpress_draft: binding
        });
        return {
          stage,
          status: preview.status === "preview_ready" ? "ready" : "blocked",
          message:
            preview.status === "preview_ready"
              ? "Podgląd tej wersji jest gotowy."
              : preview.blocker_labels[0] ?? preview.blockers[0] ?? "Podgląd został zablokowany.",
          nextStep:
            preview.status === "preview_ready"
              ? "Przejdź do review zapisu."
              : "Usuń wskazaną blokadę przed review."
        };
      }
      if (stage === "review") {
        const review = await reviewAction(ACTION_ID, {
          outcome: "approved_for_prepare",
          reviewed_by: OPERATOR,
          notes: "Sprawdzono podgląd dokładnej wersji i zakres WordPress draft-only.",
          checked_items: [
            "Podgląd dotyczy zaakceptowanej wersji treści.",
            "Dozwolone jest wyłącznie utworzenie nowego szkicu.",
            "Publikacja, aktualizacja i usuwanie pozostają zablokowane."
          ],
          blockers: [],
          wordpress_draft: binding
        });
        return {
          stage,
          status: "ready",
          message: review.status_label || "Review akcji zostało zapisane.",
          nextStep: "Jawnie potwierdź zamiar utworzenia draftu."
        };
      }
      if (stage === "confirm") {
        const confirmation = await confirmAction(ACTION_ID, {
          confirmed_by: OPERATOR,
          notes: "Potwierdzam utworzenie wyłącznie nowego szkicu tej dokładnej wersji.",
          preview_acknowledged: true,
          wordpress_draft: binding
        });
        return {
          stage,
          status: confirmation.status === "confirmed" ? "ready" : "blocked",
          message:
            confirmation.status === "confirmed"
              ? confirmation.status_label || "Potwierdzenie zostało zapisane."
              : confirmation.blocker_labels[0] ??
                confirmation.blockers[0] ??
                "Potwierdzenie zostało zablokowane.",
          nextStep:
            confirmation.status === "confirmed"
              ? "Sprawdź gotowość i bezpieczeństwo zapisu."
              : "Usuń wskazaną blokadę przed kolejnym krokiem."
        };
      }
      if (stage === "impact") {
        const impact = await impactCheckAction(ACTION_ID, {
          checked_by: OPERATOR,
          notes: "Sprawdzam gotowość bez claimu wyniku i bez zapisu do WordPressa.",
          pre_window_days: 7,
          post_window_days: 7,
          wordpress_draft: binding
        });
        return {
          stage,
          status: impact.status === "checked" ? "ready" : "blocked",
          message:
            impact.status === "checked"
              ? impact.status_label || "Kontrola bezpieczeństwa jest gotowa."
              : impact.blocker_labels[0] ?? impact.blockers[0] ?? "Kontrola została zablokowana.",
          nextStep:
            impact.status === "checked"
              ? "Utwórz nowy szkic na devie."
              : "Usuń wskazaną blokadę przed zapisem."
        };
      }
      const applied = await applyAction(ACTION_ID, {
        confirm: true,
        confirmed_by: OPERATOR,
        wordpress_draft: binding
      });
      const revisionBlocker = applied.wordpress_revision_blockers[0];
      return {
        stage,
        status: applied.status === "applied" ? "ready" : "blocked",
        message:
          applied.status === "applied"
            ? applied.status_label || "Szkic został utworzony na devie."
            : revisionBlocker?.label ?? applied.errors[0] ?? "Zapis szkicu został zablokowany.",
        nextStep:
          applied.status === "applied"
            ? "Otwórz odczytany szkic i sprawdź go na devie."
            : revisionBlocker?.next_step ?? "Usuń wskazaną blokadę. WILQ nie ponowi zapisu automatycznie.",
        applyResult: applied
      };
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["actions", ACTION_ID] });
      if (result.applyResult?.status === "applied" && binding) {
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: ["content-workflow", "work-item", binding.work_item_id]
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "content-workflow",
              "wordpress-draft-activation-packet",
              binding.work_item_id
            ]
          }),
          queryClient.invalidateQueries({
            queryKey: ["content-workflow", "wordpress-draft-write-readiness"]
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "content-workflow",
              "existing-draft-update-readiness",
              binding.work_item_id
            ]
          })
        ]);
      }
    }
  });

  if (!binding || actionId !== ACTION_ID) {
    return (
      <section
        className="rounded-md border border-wait/30 bg-wait/10 p-4"
        aria-labelledby="dev-draft-workspace-title"
        data-testid="content-wordpress-draft-action-wizard"
      >
        <h2 id="dev-draft-workspace-title" className="text-base font-semibold text-ink">
          Szkic na devie
        </h2>
        <p className="mt-2 text-sm font-semibold text-wait">
          {handoffBlocker?.label ??
            (actionId !== ACTION_ID
              ? "Brakuje kanonicznej akcji zapisu draftu"
              : "Brakuje bezpiecznego przekazania zaakceptowanej wersji")}
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-700">
          {handoffBlocker?.reason ??
            (actionId !== ACTION_ID
              ? "Pakiet aktywacyjny nie wskazuje jedynej dozwolonej akcji WordPress draft-only."
              : "WILQ nie dostał z API niezmiennego powiązania wersji, akceptacji i handoffu.")}
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Następny krok: {handoffBlocker?.next_step ?? "Wróć do review dokładnej wersji."}
        </p>
      </section>
    );
  }

  if (action.isLoading) {
    return (
      <section className="rounded-md border border-line bg-white p-4" aria-live="polite">
        <h2 className="text-base font-semibold text-ink">Szkic na devie</h2>
        <p className="mt-2 text-sm text-slate-600">Odczytuję bezpieczny ślad tej wersji.</p>
      </section>
    );
  }

  if (action.error || !action.data) {
    return (
      <section className="rounded-md border border-danger/30 bg-danger/10 p-4" role="alert">
        <h2 className="text-base font-semibold text-danger">Nie można otworzyć zapisu draftu</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          WILQ nie odczytał kanonicznej akcji. Nic nie zostało zapisane w WordPressie.
        </p>
      </section>
    );
  }

  const acknowledgementMissing =
    (currentStage.id === "review" && !reviewAcknowledged) ||
    (currentStage.id === "confirm" && !confirmationAcknowledged);
  const activeResult =
    runStage.data?.stage === currentStage.id || runStage.data?.status === "blocked"
      ? runStage.data
      : null;
  const currentError = runStage.error instanceof Error ? runStage.error.message : null;
  const applyLocked = currentStage.id === "apply" && terminalApplyBlocker !== null;

  return (
    <section
      className="overflow-hidden rounded-md border border-action/25 bg-white shadow-sm"
      aria-labelledby="dev-draft-workspace-title"
      data-testid="content-wordpress-draft-action-wizard"
    >
      <div className="border-b border-action/15 bg-blue-50 px-4 py-3 sm:flex sm:items-start sm:justify-between sm:gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-action">
            Dokładnie zaakceptowana wersja
          </p>
          <h2 id="dev-draft-workspace-title" className="mt-1 text-base font-semibold text-ink">
            Szkic aktualnego tekstu → dev
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Treść {binding.content_digest.slice(0, 10)} · wyłącznie nowy draft
          </p>
        </div>
        <span className="mt-3 inline-flex rounded-md border border-success/25 bg-white px-3 py-2 text-xs font-semibold text-success sm:mt-0">
          bez publikacji · bez aktualizacji
        </span>
      </div>

      <ol className="grid grid-cols-2 gap-2 border-b border-line p-3 sm:grid-cols-5" aria-label="Etapy zapisu szkicu">
        {WIZARD_STAGES.map((stage, index) => {
          const state = index < completedStageCount ? "done" : index === completedStageCount ? "current" : "pending";
          return (
            <li
              key={stage.id}
              aria-current={state === "current" ? "step" : undefined}
              className={`rounded-md border px-2 py-2 text-center text-xs font-semibold ${
                state === "done"
                  ? "border-success/25 bg-success/5 text-success"
                  : state === "current"
                    ? "border-action/40 bg-blue-50 text-action"
                    : "border-line bg-surface text-slate-500"
              }`}
            >
              {index + 1}. {stage.label}
            </li>
          );
        })}
      </ol>

      <div className="p-4">
        {complete ? (
          <DraftCreatedSummary draftReadback={draftReadback} />
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Krok {completedStageCount + 1} z {WIZARD_STAGES.length}
            </p>
            <h3 className="mt-1 text-base font-semibold text-ink">{currentStage.title}</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              {currentStage.summary}
            </p>

            {currentStage.id === "review" ? (
              <label className="mt-4 flex items-start gap-3 rounded-md border border-line bg-surface p-3 text-sm leading-6 text-slate-700">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={reviewAcknowledged}
                  onChange={(event) =>
                    setReviewAcknowledgementKey(
                      event.target.checked ? currentAcknowledgementKey : null
                    )
                  }
                />
                Sprawdziłem podgląd tej wersji; akcja ma utworzyć tylko nowy szkic na devie.
              </label>
            ) : null}
            {currentStage.id === "confirm" ? (
              <label className="mt-4 flex items-start gap-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={confirmationAcknowledged}
                  onChange={(event) =>
                    setConfirmationAcknowledgementKey(
                      event.target.checked ? currentAcknowledgementKey : null
                    )
                  }
                />
                Potwierdzam zamiar utworzenia wyłącznie draftu; bez publikacji, aktualizacji i usuwania.
              </label>
            ) : null}

            <button
              type="button"
              onClick={() => runStage.mutate(currentStage.id)}
              disabled={runStage.isPending || acknowledgementMissing || applyLocked}
              className="mt-4 inline-flex min-h-11 items-center rounded-md bg-action px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runStage.isPending ? "WILQ sprawdza..." : currentStage.buttonLabel}
            </button>
          </>
        )}

        {activeResult?.status === "blocked" ? (
          <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3" role="alert">
            <p className="text-sm font-semibold text-wait">{activeResult.message}</p>
            <p className="mt-1 text-sm leading-6 text-slate-700">
              Następny krok: {activeResult.nextStep}
            </p>
          </div>
        ) : null}
        {!activeResult && applyLocked ? (
          <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3" role="alert">
            <p className="text-sm font-semibold text-wait">{terminalApplyBlocker.label}</p>
            <p className="mt-1 text-sm leading-6 text-slate-700">
              {terminalApplyBlocker.reason} Następny krok: {terminalApplyBlocker.nextStep}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              WILQ nie ponowi zapisu tej samej zgody automatycznie.
            </p>
          </div>
        ) : null}
        {currentError ? (
          <div className="mt-4 rounded-md border border-danger/30 bg-danger/10 p-3" role="alert">
            <p className="text-sm font-semibold text-danger">WILQ zatrzymał ten krok</p>
            <p className="mt-1 text-sm leading-6 text-slate-700">
              Nic nie zostało ponowione automatycznie. Sprawdź stan akcji i spróbuj dopiero po usunięciu blokady.
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function DraftCreatedSummary({ draftReadback }: { draftReadback: DraftReadback }) {
  return (
    <div className="rounded-md border border-success/25 bg-success/5 p-4">
      <p className="text-sm font-semibold text-success">Nowy szkic został zapisany jako draft</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        WILQ zakończył kanoniczną akcję. Publikacja i zmiany destrukcyjne nadal są zablokowane.
      </p>
      {draftReadback?.status === "available" ? (
        <div className="mt-3">
          <p className="text-sm font-semibold text-ink">{draftReadback.title || "Szkic bez tytułu"}</p>
          {draftReadback.link ? (
            <a
              href={draftReadback.link}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex min-h-10 items-center rounded-md border border-action/40 bg-white px-3 py-2 text-sm font-semibold text-action"
            >
              Otwórz odczytany szkic na devie
            </a>
          ) : null}
        </div>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Odczyt szkicu jest odświeżany. Nie uznawaj zapisu za sprawdzony, dopóki WILQ nie pokaże readbacku.
        </p>
      )}
    </div>
  );
}

function matchingCompletedStageCount(
  events: ActionObject["audit_events"],
  binding: ContentDraftRevisionBinding
) {
  const orderedEvents = [...events].sort((left, right) =>
    left.created_at.localeCompare(right.created_at)
  );
  let lastMatchIndex = -1;
  let completed = 0;
  for (const stage of WIZARD_STAGES) {
    const eventFamily = stageEventFamily(stage.id);
    const latestIndex = findLastIndex(orderedEvents, (event) =>
      eventFamily.includes(event.event_type)
    );
    if (latestIndex <= lastMatchIndex) break;
    const latestEvent = orderedEvents[latestIndex];
    if (
      latestEvent.event_type !== stage.eventType ||
      !sameRevisionBinding(latestEvent.details.wordpress_draft_binding, binding)
    ) {
      break;
    }
    lastMatchIndex = latestIndex;
    completed += 1;
  }
  return completed;
}

function stageEventFamily(stage: WizardStageId): string[] {
  if (stage === "preview") return ["action_preview_generated"];
  if (stage === "review") {
    return [
      "human_review_approved_for_prepare",
      "human_review_needs_changes",
      "human_review_rejected",
      "human_review_deferred"
    ];
  }
  if (stage === "confirm") {
    return [
      "action_apply_confirmed",
      "action_apply_confirmation_confirmed",
      "action_confirmation_blocked",
      "action_apply_confirmation_blocked"
    ];
  }
  if (stage === "impact") {
    return ["action_impact_check_completed", "action_impact_check_blocked"];
  }
  return ["action_apply_completed", "action_apply_blocked", "apply_confirmation_missing"];
}

function findLastIndex<T>(values: T[], predicate: (value: T) => boolean) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (predicate(values[index])) return index;
  }
  return -1;
}

function acknowledgementKey(
  binding: ContentDraftRevisionBinding,
  completedStageCount: number,
  events: ActionObject["audit_events"]
) {
  const latestEvent = [...events].sort((left, right) =>
    left.created_at.localeCompare(right.created_at)
  )[events.length - 1];
  return [
    binding.work_item_id,
    binding.revision_id,
    binding.content_digest,
    completedStageCount,
    events.length,
    latestEvent?.event_type ?? "no_event",
    latestEvent?.created_at ?? "no_timestamp"
  ].join(":");
}

function latestMatchingApplyBlocker(
  events: ActionObject["audit_events"],
  binding: ContentDraftRevisionBinding
) {
  const orderedEvents = [...events].sort((left, right) =>
    left.created_at.localeCompare(right.created_at)
  );
  const latestApplyIndex = findLastIndex(orderedEvents, (event) =>
    stageEventFamily("apply").includes(event.event_type)
  );
  if (latestApplyIndex === -1) return null;
  const event = orderedEvents[latestApplyIndex];
  if (
    !["action_apply_blocked", "apply_confirmation_missing"].includes(event.event_type) ||
    !sameRevisionBinding(event.details.wordpress_draft_binding, binding)
  ) {
    return null;
  }
  const rawBlockers = event.details.wordpress_revision_blockers;
  if (!Array.isArray(rawBlockers)) {
    return {
      label: "Poprzednia próba zapisu została zablokowana",
      reason: "Ślad akcji nie zawiera bezpiecznego opisu blokady.",
      nextStep: "Odczytaj readiness i rozpocznij nowy review dopiero po wyjaśnieniu wyniku."
    };
  }
  const blocker = rawBlockers[0];
  if (typeof blocker !== "object" || blocker === null) return null;
  const value = blocker as Record<string, unknown>;
  return {
    label:
      typeof value.label === "string" ? value.label : "Poprzednia próba zapisu została zablokowana",
    reason:
      typeof value.reason === "string" ? value.reason : "WILQ zatrzymał zapis przed adapterem.",
    nextStep:
      typeof value.next_step === "string"
        ? value.next_step
        : "Wyjaśnij blokadę przed nową zgodą na zapis."
  };
}

function sameRevisionBinding(candidate: unknown, binding: ContentDraftRevisionBinding) {
  if (typeof candidate !== "object" || candidate === null) return false;
  const value = candidate as Record<string, unknown>;
  return (
    value.work_item_id === binding.work_item_id &&
    value.handoff_id === binding.handoff_id &&
    value.revision_id === binding.revision_id &&
    value.content_digest === binding.content_digest &&
    value.draft_package_id === binding.draft_package_id &&
    value.draft_package_digest === binding.draft_package_digest &&
    value.approval_decision_id === binding.approval_decision_id &&
    value.final_canonical_url === binding.final_canonical_url
  );
}
