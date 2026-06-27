import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CheckCircle2,
  ClipboardCheck,
  FileJson,
  RefreshCw,
  ShieldAlert
} from "lucide-react";

import {
  ActionConfirmResult,
  ActionImpactCheckResult,
  ActionObject,
  ActionPreviewResult,
  ActionReviewRequest,
  ActionValidationResult,
  confirmAction,
  impactCheckAction,
  previewAction,
  reviewAction,
  validateAction
} from "../lib/api";
import { ActionPayloadPreviewToggle } from "../components/ActionPayloadPreviewToggle";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { adsMissingReadContractLabel, marketerBlockedClaimLabelText } from "./marketingLabels";

export function ActionObjectFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak akcji dla tego workflow. WILQ może pokazać dowody, ale nie powinien sugerować zapisu zmian bez podglądu." />
    );
  }

  return (
    <section>
      <SectionHeading title="Akcje do sprawdzenia" />
      <div className="grid gap-3 xl:grid-cols-2">
        {actions.map((action) => (
          <article key={action.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{action.title}</h3>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {actionConnectorLabel(action.connector)} / {actionModeLabel(action.mode)}
                </p>
              </div>
              <StatusBadge value={action.validation_status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={action.status} />
              <StatusBadge value={action.risk} />
            </div>
            {action.mode !== "apply" ? (
            <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-wait">
                Zapis zmian zablokowany: ta akcja jest w trybie przygotowania.
                Najpierw sprawdzenie w WILQ, podgląd zmian i jawna zgoda operatora.
              </div>
            ) : null}
            <ActionReviewGatePanel action={action} />
            <ActionHumanReviewControls action={action} />
            <ActionPreviewControls action={action} />
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <TraceLine label="Akcja" values={["1 akcja do sprawdzenia"]} />
              <LinkedTraceLine label="Dowody" values={action.evidence_ids} kind="evidence" />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionValidationControls action={action} />
            <ActionPayloadPreviewToggle
              payload={action.payload}
              intro="Domyślnie schowany, żeby karta pokazywała decyzję i warunki przeglądu."
            />
          </article>
        ))}
      </div>
    </section>
  );
}

export function ActionPreviewControls({ action }: { action: ActionObject }) {
  const previewMutation = useMutation({
    mutationFn: () => previewAction(action.id)
  });

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Podgląd zmian
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Generuje podgląd zmian i zapis audytu bez zmian w zewnętrznych systemach.
          </p>
        </div>
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {previewMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <FileJson aria-hidden="true" size={15} />
          )}
          {previewMutation.isPending ? "Generuję" : "Generuj podgląd"}
        </button>
      </div>
      <ActionPreviewResultPanel
        result={previewMutation.data}
        error={previewMutation.error instanceof Error ? previewMutation.error.message : null}
      />
    </div>
  );
}

function ActionPreviewResultPanel({
  result,
  error
}: {
  result?: ActionPreviewResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Podgląd zablokowany: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Podgląd: <span className="font-semibold">{actionResultStatusLabel(result.status)}</span>
      </div>
      <div>
        Bez zapisu zmian: {result.dry_run ? "tak" : "nie"}; zapis zmian:{" "}
        {result.mutation_allowed ? "dopuszczone" : "zablokowane"}
      </div>
      <div>
        Pozycje podglądu: {result.preview_items.length}/{result.preview_items_total}
        {result.omitted_items > 0 ? `, pominięto ${result.omitted_items}` : ""}
      </div>
      <TraceLine label="Blokady podglądu" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Ślad bezpieczeństwa: {actionAuditEventLabel(result.audit_event.event_type)}</div>
    </div>
  );
}

export function ActionObjectIdFocus({ actionIds, note }: { actionIds: string[]; note: string }) {
  const actionCountLabel =
    actionIds.length === 1 ? "1 akcja do sprawdzenia" : `${actionIds.length} akcji do sprawdzenia`;

  return (
    <section>
      <SectionHeading title="Akcje do sprawdzenia" />
      <div className="rounded-md border border-line bg-white p-4 text-sm leading-6 text-slate-700">
        <p>{note}</p>
        <div className="mt-3">
          <TraceLine label="Akcje" values={actionIds.length > 0 ? [actionCountLabel] : []} empty="brak" />
        </div>
      </div>
    </section>
  );
}

type ActionReviewOutcome = ActionReviewRequest["outcome"];

const ACTION_REVIEW_OPTIONS: Array<{ value: ActionReviewOutcome; label: string }> = [
  { value: "approved_for_prepare", label: "zatwierdzone do przygotowania" },
  { value: "needs_changes", label: "wymaga poprawek" },
  { value: "rejected", label: "odrzucone" },
  { value: "deferred", label: "odłożone" }
];

function actionConnectorLabel(value: string) {
  const labels: Record<string, string> = {
    google_ads: "Google Ads",
    google_analytics_4: "GA4",
    google_merchant_center: "Merchant Center",
    google_search_console: "Google Search Console",
    wordpress_ekologus: "WordPress Ekologus",
    wordpress_sklep: "WordPress sklep",
    ahrefs: "Ahrefs",
    localo: "Localo",
    linkedin: "LinkedIn",
    facebook: "Facebook"
  };
  return labels[value] ?? value;
}

function actionModeLabel(value: string) {
  const labels: Record<string, string> = {
    prepare: "przygotowanie",
    review: "sprawdzenie",
    apply: "zapis zmian"
  };
  return labels[value] ?? value;
}

export function ActionHumanReviewControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const [outcome, setOutcome] = useState<ActionReviewOutcome>("approved_for_prepare");
  const [notes, setNotes] = useState(
    "Przegląd operatora: zapisuję decyzję bez zapisu zmian."
  );
  const reviewMutation = useMutation({
    mutationFn: () =>
      reviewAction(action.id, {
        outcome,
        reviewed_by: "operator_local_dashboard",
        notes: notes.trim(),
        checked_items: action.review_gate.operator_checklist.slice(0, 8),
        blockers: action.review_gate.apply_blockers.slice(0, 8)
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const lastOutcome = action.review_gate.last_review_outcome;
  const lastReviewLabel = lastOutcome
    ? ACTION_REVIEW_OPTIONS.find((option) => option.value === lastOutcome)?.label ?? lastOutcome
    : null;
  const canSave = notes.trim().length > 0 && !reviewMutation.isPending;

  return (
    <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Wynik przeglądu człowieka
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje lokalne zdarzenie audytu. Nie zapisuje zmian w zewnętrznych systemach.
          </p>
        </div>
        <StatusBadge value={lastReviewLabel ?? "brak przeglądu"} />
      </div>
      {action.review_gate.last_review_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          {actionAuditSummaryLabel(
            "human_review_approved_for_prepare",
            action.review_gate.last_review_summary
          )}
        </p>
      ) : null}
      <div className="mt-3 grid gap-3 md:grid-cols-[220px_1fr_auto]">
        <label className="grid gap-1">
          <span className="font-medium text-slate-600">Decyzja</span>
          <select
            value={outcome}
            onChange={(event) => setOutcome(event.target.value as ActionReviewOutcome)}
            className="min-h-9 rounded-md border border-line bg-white px-2 text-xs text-ink"
          >
            {ACTION_REVIEW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          <span className="font-medium text-slate-600">Notatka przeglądu</span>
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="min-h-20 rounded-md border border-line bg-white px-2 py-2 text-xs leading-5 text-ink"
          />
        </label>
        <div className="flex items-end">
          <button
            type="button"
            onClick={() => reviewMutation.mutate()}
            disabled={!canSave}
            className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reviewMutation.isPending ? (
              <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
            ) : (
              <ClipboardCheck aria-hidden="true" size={15} />
            )}
            {reviewMutation.isPending ? "Zapisuję" : "Zapisz przegląd"}
          </button>
        </div>
      </div>
      {reviewMutation.data ? (
        <div className="mt-2 text-slate-600">
          Zapisano sprawdzenie: {actionAuditEventLabel(reviewMutation.data.audit_event.event_type)}
        </div>
      ) : null}
      {reviewMutation.error instanceof Error ? (
        <div className="mt-2 text-risk">Błąd przeglądu: {reviewMutation.error.message}</div>
      ) : null}
    </div>
  );
}

export function ActionReviewGatePanel({ action }: { action: ActionObject }) {
  const gate = action.review_gate;
  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Warunki przeglądu
          </div>
          <p className="mt-1 leading-5 text-slate-600">{actionReviewGateSummary(gate)}</p>
        </div>
        <StatusBadge value={actionReviewGateStatusLabel(gate.status)} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <TraceLine
          label="Warunki"
          values={gate.operator_checklist_labels.slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Blokady zapisu zmian"
          values={gate.apply_blocker_labels.slice(0, 8)}
          empty="brak"
        />
      </div>
      <div className="mt-2 text-slate-600">
        Potwierdzenie człowieka: {gate.confirmation_required ? "wymagane" : "niewymagane"}.
        Zapis zmian: {gate.apply_allowed ? "dopuszczony" : "zablokowany"}.
      </div>
      {gate.last_confirmation_summary ? (
        <p className="mt-2 rounded-md border border-line bg-white p-2 text-slate-600">
          Ostatnie potwierdzenie: zapisane. Ten krok nie zmienia danych w zewnętrznych systemach.
        </p>
      ) : null}
      {gate.last_mutation_audit_summary ? (
        <div className="mt-2 rounded-md border border-risk/30 bg-white p-2 text-slate-600">
          <div className="font-semibold text-risk">Ostatni zapis bezpieczeństwa</div>
          <p className="mt-1 leading-5">{actionMutationAuditSummary(gate)}</p>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div>Wynik: {actionMutationAuditStatusLabel(gate.last_mutation_audit_status)}</div>
            <div>Czy próbowano zapisu: {gate.last_mutation_attempted ? "tak" : "nie"}</div>
            <div>
              System zewnętrzny: {gate.last_mutation_adapter ? "wskazany" : "brak"}
            </div>
            <div>
              Ślad bezpieczeństwa: {gate.last_mutation_audit_event_id ? "zapisany" : "brak"}
            </div>
          </div>
          <TraceLine
            label="Co blokuje zapis"
            values={(gate.last_mutation_blocker_labels ?? []).slice(0, 8)}
            empty="brak"
          />
        </div>
      ) : null}
    </div>
  );
}

function actionMutationAuditStatusLabel(value?: string | null) {
  const labels: Record<string, string> = {
    blocked: "zablokowany",
    applied: "zapisany",
    failed: "błąd"
  };
  return value ? labels[value] ?? value : "brak";
}

function actionReviewGateStatusLabel(value: string) {
  const labels: Record<string, string> = {
    pending_validation: "czeka na sprawdzenie",
    validated_prepare_only: "sprawdzone w WILQ",
    ready_to_apply: "gotowe do potwierdzenia",
    blocked_apply: "zapis zmian zablokowany"
  };
  return labels[value] ?? value;
}

export function actionGateLabel(value: string) {
  if (value.startsWith("blocked_claim:")) {
    return `nie wolno twierdzić: ${marketerBlockedClaimLabelText(value.slice("blocked_claim:".length))}`;
  }
  const labels: Record<string, string> = {
    action_mode_prepare_only: "tryb przygotowania bez zapisu zmian",
    action_validation_required: "wymagane sprawdzenie w WILQ",
    payload_apply_allowed_false: "podgląd zmian nie pozwala na zapis",
    destructive_actions_blocked: "destrukcyjne zmiany zablokowane",
    preview_acknowledgement_required: "wymagane potwierdzenie podglądu",
    dry_run_preview_required: "wymagany wcześniejszy podgląd zmian",
    action_confirmation_required: "wymagane potwierdzenie podglądu",
    metric_facts_required: "wymagane metryki z dowodami",
    evidence_ids_required: "wymagane ID dowodów",
    impact_sanity_check_required: "wymagane sprawdzenie efektu",
    vendor_mutation_adapter_required: "brak bezpiecznej ścieżki zapisu w zewnętrznym systemie",
    validate_action_object: "sprawdzenie akcji",
    human_review_before_apply: "sprawdzenie przez człowieka przed zapisem",
    human_confirm_before_apply: "potwierdzenie człowieka przed zapisem",
    compare_90_day_safety_read: "porównaj z 90-dniową kontrolą bezpieczeństwa",
    confirm_developer_token_approval: "potwierdź akceptację tokena deweloperskiego",
    review_campaign_activity: "sprawdź aktywność kampanii",
    verify_account_currency: "sprawdź walutę konta",
    budget_pacing: "sprawdź tempo wydawania budżetu",
    impression_share: "sprawdź udział w wyświetleniach",
    budget_apply_preview: "sprawdź podgląd zmiany budżetu",
    campaign_budget_apply_safety: "sprawdź bezpieczeństwo zmiany budżetu",
    campaign_budget_operation_preview: "sprawdź operację budżetu",
    human_budget_goal: "potwierdź cel budżetu",
    content_url_preflight_review: "potwierdzenie publicznego URL-a",
    final_canonical_review: "kontrola URL-a kanonicznego",
    canonical_review: "kontrola URL-a kanonicznego",
    canonical_review_outcome: "wynik kontroli URL-a kanonicznego",
    duplicate_or_cannibalization_check: "kontrola duplikacji i kanibalizacji",
    duplicate_review_outcome: "wynik kontroli duplikacji",
    legal_factual_review: "kontrola prawna i faktograficzna",
    legal_factual_review_outcome: "wynik kontroli prawnej i faktograficznej",
    content_draft_readiness_review: "kontrola gotowości szkicu",
    wordpress_draft_payload_preview: "podgląd wpisu WordPress",
    human_confirm_before_wordpress_write: "potwierdzenie człowieka przed zapisem WordPress",
    review_recommendation_type: "sprawdź typ rekomendacji",
    review_impact_metrics: "sprawdź metryki wpływu",
    review_change_history: "sprawdź historię zmian",
    review_business_goal: "sprawdź cel biznesowy",
    google_ads_rmf_compliance_review: "sprawdź zgodność Google Ads",
    group_issue_reasons: "pogrupuj powody problemów",
    identify_disapproved_products: "ustal produkty i zgłoszenia do sprawdzenia",
    negative_keyword_action_validation: "sprawdzenie w WILQ dla wykluczeń",
    prepare_feed_fix_preview: "przygotuj podgląd zmian feedu",
    require_human_confirm_before_apply: "człowiek potwierdza przed zapisem",
    reject_brand_or_low_intent_terms: "odrzuć brandowe lub niskointencyjne frazy",
    rerun_google_ads_data_read: "uruchom ponowny odczyt Google Ads",
    review_campaign_name_dimension: "sprawdź nazwę kampanii",
    review_conversion_or_key_event_mapping: "sprawdź mapowanie konwersji lub zdarzenia kluczowego",
    review_human_budget_goal: "sprawdź cel budżetu od człowieka",
    review_landing_page_dimension: "sprawdź stronę wejścia",
    review_ngram_intent: "sprawdź intencję tematu zapytań",
    review_profit_margin_model: "sprawdź model marży",
    review_source_medium_dimension: "sprawdź źródło i medium ruchu",
    review_source_search_terms: "sprawdź źródłowe wyszukiwane hasła",
    review_source_terms: "sprawdź źródłowe hasła",
    review_target_fit: "sprawdź dopasowanie do celu",
    verify_keyword_planner_idea_rows: "sprawdź wiersze Keyword Planner"
  };
  return labels[value] ?? adsMissingReadContractLabel(value);
}

function actionReviewGateSummary(gate: ActionObject["review_gate"]) {
  if (gate.apply_allowed) {
    return "Warunki sprawdzenia są spełnione. Przed zapisem nadal wymagane jest jawne potwierdzenie operatora.";
  }
  return "Akcja jest bezpieczna do sprawdzenia, ale zapis zmian pozostaje zablokowany do czasu spełnienia warunków i potwierdzenia operatora.";
}

function actionMutationAuditSummary(gate: ActionObject["review_gate"]) {
  if (gate.last_mutation_attempted) {
    return "Zapisano próbę zmiany i jej wynik. Sprawdź wynik przed kolejnym krokiem.";
  }
  return "Zapisano kontrolę bezpieczeństwa bez zmian w zewnętrznych systemach.";
}

export function ActionValidationControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const validationMutation = useMutation({
    mutationFn: () => validateAction(action.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const confirmMutation = useMutation({
    mutationFn: () =>
      confirmAction(action.id, {
        confirmed_by: "operator_local_dashboard",
        notes: "Operator potwierdza podgląd. Ten krok nie zapisuje zmian.",
        preview_acknowledged: true
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const validation = validationMutation.data;

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
            Sprawdzenie w WILQ
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            WILQ sprawdza dane akcji, źródło, ID dowodów i tryb działania. Ten krok nie zapisuje zmian.
          </p>
        </div>
        <button
          type="button"
          onClick={() => validationMutation.mutate()}
          disabled={validationMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {validationMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <CheckCircle2 aria-hidden="true" size={15} />
          )}
          {validationMutation.isPending ? "Sprawdzam" : "Sprawdź w WILQ"}
        </button>
      </div>
      <ActionValidationResultPanel
        validation={validation}
        error={validationMutation.error instanceof Error ? validationMutation.error.message : null}
      />
      <div className="mt-3 rounded-md border border-wait/30 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
          Jawne potwierdzenie podglądu
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Potwierdzenie wymaga wcześniejszego podglądu zmian. Zapisuje lokalne zdarzenie audytu,
          ale nie zapisuje zmian w zewnętrznych systemach.
        </p>
        <button
          type="button"
          onClick={() => confirmMutation.mutate()}
          disabled={confirmMutation.isPending}
          className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-md border border-wait bg-white px-3 py-2 text-xs font-medium text-wait hover:bg-wait/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {confirmMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ShieldAlert aria-hidden="true" size={15} />
          )}
          {confirmMutation.isPending ? "Zapisuję potwierdzenie" : "Potwierdź podgląd"}
        </button>
        <ActionConfirmResultPanel
          result={confirmMutation.data}
          error={confirmMutation.error instanceof Error ? confirmMutation.error.message : null}
        />
      </div>
      <ActionImpactCheckControls action={action} />
    </div>
  );
}

function ActionValidationResultPanel({
  validation,
  error
}: {
  validation?: ActionValidationResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Błąd sprawdzenia: {error}</div>;
  }
  if (!validation) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Wynik: <span className="font-semibold">{validation.valid ? "poprawna" : "wymaga poprawek"}</span>
      </div>
      <TraceLine label="Błędy" values={validation.errors} empty="brak" />
      <TraceLine label="Ostrzeżenia" values={validation.warnings} empty="brak" />
    </div>
  );
}

function ActionConfirmResultPanel({
  result,
  error
}: {
  result?: ActionConfirmResult;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="mt-3 text-xs leading-5 text-risk">
        Potwierdzenie zablokowane: {error}
      </div>
    );
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Potwierdzenie: <span className="font-semibold">{actionResultStatusLabel(result.status)}</span>
      </div>
      <TraceLine label="Blokady potwierdzenia" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Ślad bezpieczeństwa: {actionAuditEventLabel(result.audit_event.event_type)}</div>
      <div>
        Zapis zmian nadal: {result.review_gate.apply_allowed ? "dopuszczony" : "zablokowany"}.
      </div>
    </div>
  );
}

function ActionImpactCheckControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const impactMutation = useMutation({
    mutationFn: () =>
      impactCheckAction(action.id, {
        checked_by: "operator_local_dashboard",
        notes: "Operator sprawdza okno efektu przed jakimkolwiek zapisem zmian.",
        pre_window_days: 7,
        post_window_days: 7
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });

  return (
    <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Sprawdzenie efektu
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje okno przed i po zmianie na podstawie metryk akcji. Nie ocenia
            wzrostu i nie zapisuje zmian.
          </p>
        </div>
        <button
          type="button"
          onClick={() => impactMutation.mutate()}
          disabled={impactMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {impactMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ShieldAlert aria-hidden="true" size={15} />
          )}
          {impactMutation.isPending ? "Sprawdzam" : "Sprawdź efekt"}
        </button>
      </div>
      {action.review_gate.last_impact_check_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          Ostatnie sprawdzenie efektu: zapisane. Szczegóły metryk i blokad są dostępne w panelu wyniku.
        </p>
      ) : null}
      <ActionImpactCheckResultPanel
        result={impactMutation.data}
        error={impactMutation.error instanceof Error ? impactMutation.error.message : null}
      />
    </div>
  );
}

function ActionImpactCheckResultPanel({
  result,
  error
}: {
  result?: ActionImpactCheckResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Sprawdzenie efektu zablokowane: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Sprawdzenie efektu: <span className="font-semibold">{actionResultStatusLabel(result.status)}</span>
      </div>
      <div>
        Okna: {result.pre_window_days} dni przed / {result.post_window_days} dni po.
      </div>
      <div>Metryki z dowodami: {result.metric_fact_count}</div>
      <TraceLine label="Źródła" values={result.source_connectors} empty="brak" />
      <TraceLine label="Blokady sprawdzenia efektu" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Ślad bezpieczeństwa: {actionAuditEventLabel(result.audit_event.event_type)}</div>
      <div>
        Zapis zmian nadal: {result.review_gate.apply_allowed ? "dopuszczony" : "zablokowany"}.
      </div>
    </div>
  );
}

function actionResultStatusLabel(value: string) {
  const labels: Record<string, string> = {
    generated: "wygenerowany",
    confirmed: "potwierdzony",
    completed: "zapisane",
    blocked: "zablokowany",
    failed: "błąd"
  };
  return labels[value] ?? "zapisane";
}

function SectionHeading({ title }: { title: string }) {
  return (
    <h2 className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-500">
      {title}
    </h2>
  );
}

export function actionAuditEventLabel(eventType: string) {
  const labels: Record<string, string> = {
    action_preview_generated: "Podgląd zmian wygenerowany",
    human_review_approved_for_prepare: "Przegląd operatora zapisany",
    action_apply_confirmed: "Podgląd potwierdzony",
    action_impact_check_completed: "Sprawdzenie efektu zapisane"
  };
  return labels[eventType] ?? eventType;
}

export function actionAuditSummaryLabel(eventType: string, summary: string) {
  if (eventType === "human_review_approved_for_prepare") {
    return "Przegląd operatora zapisany. Zapis zmian w zewnętrznych systemach pozostaje zablokowany.";
  }
  if (eventType === "action_preview_generated") {
    return "Podgląd zmian wygenerowany. Nie zapisano zmian w zewnętrznych systemach.";
  }
  return summary;
}
