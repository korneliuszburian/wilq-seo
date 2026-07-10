import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";

import {
  ActionObject,
  Evidence,
  getAction,
  getActionMutationReadiness,
  getEvidenceById,
  getOpportunities,
  Opportunity
} from "../lib/api";
import { LoadingBand } from "../components/OperatorPrimitives";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { StatusBadge } from "../components/StatusBadge";
import {
  ActionHumanReviewControls,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionValidationControls
} from "./ActionPanels";

export function ActionDetailSurface({ actionId }: { actionId: string }) {
  const action = useQuery({
    queryKey: ["actions", actionId],
    queryFn: () => getAction(actionId)
  });
  const mutationReadiness = useQuery({
    queryKey: ["actions", actionId, "mutation-readiness"],
    queryFn: () => getActionMutationReadiness(actionId)
  });

  if (action.isLoading) return <LoadingBand />;
  if (action.error) return <ErrorState />;

  if (action.data) {
    return (
      <ActionDetail
        action={action.data}
        mutationReadiness={mutationReadiness.data}
        mutationReadinessError={mutationReadiness.error}
        mutationReadinessLoading={mutationReadiness.isLoading}
      />
    );
  }
  return <ErrorState />;
}

export function OpportunityDetailSurface({ opportunityId }: { opportunityId: string }) {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });

  if (opportunities.isLoading) return <LoadingBand />;
  if (opportunities.error) return <ErrorState />;

  const opportunity = (opportunities.data ?? []).find((item) => item.id === opportunityId);
  if (opportunity) return <OpportunityDetail opportunity={opportunity} />;
  return <ErrorState />;
}

function ActionDetail({
  action,
  mutationReadiness,
  mutationReadinessError,
  mutationReadinessLoading
}: {
  action: ActionObject;
  mutationReadiness: Awaited<ReturnType<typeof getActionMutationReadiness>> | undefined;
  mutationReadinessError: unknown;
  mutationReadinessLoading: boolean;
}) {
  const visibleAuditEvents = action.audit_events.slice(0, 6);
  const hiddenAuditEventCount = Math.max(0, action.audit_events.length - visibleAuditEvents.length);

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
      <ActionOperatorDecisionHero
        action={action}
        mutationReadiness={mutationReadiness}
        mutationReadinessLoading={mutationReadinessLoading}
        mutationReadinessError={mutationReadinessError}
      />
      <section id="action-review" className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd, review i walidacja" />
        <p className="text-sm leading-6 text-slate-700">
          Tu wykonujesz bezpieczną część pracy: sprawdzenie, podgląd, review i potwierdzenie.
          Zapis zmian pozostaje blokowany, dopóki WILQ nie ma pełnej ścieżki zgody i audytu.
        </p>
        <ActionReviewGatePanel action={action} />
        <ActionHumanReviewControls action={action} />
        <ActionPreviewControls action={action} />
        <ActionValidationControls action={action} />
      </section>
      <ActionMutationReadinessPanel
        loading={mutationReadinessLoading}
        error={mutationReadinessError}
        readiness={mutationReadiness}
      />
      <section id="action-preview" className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd zmian" />
        <ActionChangePreviewSummary action={action} />
        <TechnicalDetailsPanel
          openLabel="Pokaż dane techniczne akcji"
          closeLabel="Ukryj dane techniczne akcji"
        >
          <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(action.payload, null, 2)}
          </pre>
        </TechnicalDetailsPanel>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Dowody i audyt" />
        <div className="rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Dlaczego WILQ pokazał tę akcję</div>
          <p className="mt-1">{action.human_diagnosis}</p>
          <p className="mt-2 text-xs text-slate-600">Dowody: {action.evidence_summary_label}</p>
        </div>
        {action.audit_events.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">
            Brak zapisanych zdarzeń audytu. Traktuj akcję jako przygotowaną do pracy, nie jako wykonaną.
          </p>
        ) : (
          <TechnicalDetailsPanel
            className="mt-3"
            openLabel="Pokaż historię audytu"
            closeLabel="Ukryj historię audytu"
          >
            <div className="mt-3 grid gap-3">
              {hiddenAuditEventCount > 0 ? (
                <p className="text-xs text-slate-500">
                  Pokazano 6 najnowszych z {action.audit_events.length} zdarzeń audytu.
                </p>
              ) : null}
              {visibleAuditEvents.map((event) => (
                <div key={event.id} className="rounded-md border border-line bg-white p-3 text-sm">
                  <div className="font-medium">{event.event_type_label}</div>
                  <div className="mt-1 text-slate-600">
                    {event.summary}
                  </div>
                </div>
              ))}
            </div>
          </TechnicalDetailsPanel>
        )}
      </section>
    </main>
  );
}

function ActionOperatorDecisionHero({
  action,
  mutationReadiness,
  mutationReadinessLoading,
  mutationReadinessError
}: {
  action: ActionObject;
  mutationReadiness: Awaited<ReturnType<typeof getActionMutationReadiness>> | undefined;
  mutationReadinessLoading: boolean;
  mutationReadinessError: unknown;
}) {
  const writeBlocked = !mutationReadiness?.vendor_write_possible;
  const nextStep =
    actionOperatorNextStep(action, mutationReadiness?.operator_next_step) ||
    action.recommended_reason.trim() ||
    "Sprawdź podgląd i review, zanim potraktujesz tę akcję jako gotową.";
  const blockerLabels =
    mutationReadiness?.blockers.slice(0, 4).map((blocker) => actionBlockerLabel(blocker.label)) ?? [];
  const checklistLabels = action.review_gate.operator_checklist_labels.slice(0, 3);

  return (
    <section className="rounded-md border border-line bg-white">
      <div className="border-b border-line p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <a href="/actions" className="text-xs font-medium text-action">
              Akcje
            </a>
            <h1 className="mt-2 text-2xl font-semibold tracking-normal">{action.title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              {action.human_diagnosis}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={action.status} label={action.status_label} />
            <StatusBadge value={action.validation_status} label={action.validation_status_label} />
            <StatusBadge value={action.risk} label={action.risk_label} />
          </div>
        </div>
      </div>
      <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="p-4">
          <div className="rounded-md border border-action/20 bg-action/5 p-4">
            <div className="text-xs font-semibold uppercase tracking-normal text-action">
              Twoja decyzja
            </div>
            <h2 className="mt-2 text-lg font-semibold text-ink">
              {actionDecisionHeadline(action)}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">{nextStep}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <a
                href="#action-review"
                className="inline-flex rounded-md bg-action px-4 py-2 text-sm font-semibold text-white"
              >
                Przejdź do review
              </a>
              <a
                href="#action-preview"
                className="inline-flex rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
              >
                Zobacz podgląd
              </a>
            </div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <OperatorDecisionTile label="Tryb akcji" value={action.mode_label || action.mode} />
            <OperatorDecisionTile label="Obszar" value={action.connector_label || action.connector} />
            <OperatorDecisionTile label="Dowody" value={action.evidence_summary_label || "wymagane"} />
          </div>
          {checklistLabels.length > 0 ? (
            <div className="mt-4 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
              <div className="font-semibold text-ink">Co sprawdzić przed decyzją</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {checklistLabels.map((label) => (
                  <li key={label}>{label}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <div className="border-t border-line p-4 lg:border-l lg:border-t-0">
          <div
            className={`rounded-md border p-4 ${
              writeBlocked ? "border-risk/25 bg-risk/5" : "border-success/25 bg-success/5"
            }`}
          >
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
              Stan zapisu
            </div>
            <h2 className={`mt-2 text-lg font-semibold ${writeBlocked ? "text-risk" : "text-success"}`}>
              {mutationReadinessLoading
                ? "Zapis zablokowany"
                : writeBlocked
                  ? "Zapis zablokowany"
                  : "Zapis możliwy po potwierdzeniu"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {mutationReadinessLoading
                ? "WILQ sprawdza szczegóły blokad. Do czasu potwierdzenia pracuj tylko na podglądzie i review."
                : mutationReadinessError
                ? "Nie udało się potwierdzić gotowości zapisu, więc WILQ nie powinien traktować tej akcji jako gotowej do zmian."
                : writeBlocked
                  ? "Możesz pracować na podglądzie i review, ale nie traktuj tej akcji jako zgody na zapis w zewnętrznym systemie."
                  : "WILQ widzi ścieżkę zapisu, ale nadal wymagane są preview, review, potwierdzenie i audyt."}
            </p>
            {blockerLabels.length > 0 ? (
              <div className="mt-3">
                <div className="text-sm font-semibold text-ink">Co blokuje przejście dalej</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {blockerLabels.map((label) => (
                    <li key={label}>{label}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          {action.mode !== "apply" ? (
            <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
              Ta akcja jest w trybie przygotowania. Nie publikuje, nie zmienia budżetu i nie zapisuje zmian bez osobnej zgody.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function actionDecisionHeadline(action: ActionObject): string {
  if (action.mode === "apply") return "Sprawdź podgląd i potwierdź dopiero po review";
  if (action.mode === "prepare") return "Przygotuj i oceń bez zapisu zmian";
  return "Przejrzyj rekomendację przed jakąkolwiek decyzją";
}

function actionOperatorNextStep(action: ActionObject, nextStep: string | undefined): string {
  const trimmed = nextStep?.trim() ?? "";
  if (action.mode === "prepare" && trimmed.includes("apply-capable ActionObject")) {
    return "Użyj tej akcji do przygotowania i review. Jeśli po review trzeba będzie coś zapisać, WILQ powinien przygotować osobną akcję zapisu z podglądem i potwierdzeniem.";
  }
  return trimmed.replaceAll("ActionObject", "akcja do sprawdzenia");
}

function actionBlockerLabel(label: string): string {
  if (label === "Akcja jest tylko prepare/review") {
    return "To jest akcja do przygotowania i review, bez zapisu";
  }
  if (label === "Payload nadal blokuje apply") {
    return "Ten pakiet nie pozwala jeszcze na zapis";
  }
  if (label === "Brakuje adaptera zapisu") {
    return "Brak bezpiecznej ścieżki zapisu";
  }
  return label.replaceAll("ActionObject", "akcja do sprawdzenia").replaceAll("apply", "zapis");
}

function readinessModeLabel(label: string): string {
  return label
    .replace("draft-only", "tylko szkic")
    .replace("prepare", "tylko przygotowanie")
    .replace("review", "do sprawdzenia")
    .replace("apply", "zapis");
}

function OperatorDecisionTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function ActionMutationReadinessPanel({
  loading,
  error,
  readiness
}: {
  loading: boolean;
  error: unknown;
  readiness: Awaited<ReturnType<typeof getActionMutationReadiness>> | undefined;
}) {
  if (loading) {
    return (
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Czy można zapisać zmianę" />
        <p className="text-sm leading-6 text-slate-600">
          WILQ sprawdza, czy ta akcja ma podgląd, review, potwierdzenie i bezpieczną ścieżkę zapisu.
        </p>
      </section>
    );
  }
  if (error || !readiness) {
    return (
      <section className="mt-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <SectionHeading title="Czy można zapisać zmianę" />
        <p className="text-sm leading-6 text-slate-700">
          Nie udało się pobrać readiness zapisu. Nie traktuj tej akcji jako gotowej do zmian.
        </p>
      </section>
    );
  }
  const blockerLabels = readiness.blockers.slice(0, 6).map((blocker) => actionBlockerLabel(blocker.label));
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeading title="Czy można zapisać zmianę" />
          <p className="text-sm leading-6 text-slate-700">
            {readiness.operator_next_step}
          </p>
        </div>
        <StatusBadge
          value={readiness.vendor_write_possible ? "ready" : "blocked"}
          label={readiness.vendor_write_possible ? "zapis możliwy po zgodzie" : "zapis zablokowany"}
        />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <ReadinessTile label="Tryb pracy" value={readinessModeLabel(readiness.mode_label)} />
        <ReadinessTile
          label="Ścieżka zapisu"
          value={readiness.mutation_adapter ? "skonfigurowana" : "brak bezpiecznej ścieżki"}
        />
        <ReadinessTile
          label="Zapis w zewnętrznym systemie"
          value={readiness.would_attempt_vendor_write ? "możliwa po confirm" : "nie"}
        />
      </div>
      {readiness.write_authorization_status ? (
        <div className="mt-4 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Potwierdzenie operatora</div>
          <p className="mt-2">
            {actionWriteAuthorizationStatusLabel(readiness.write_authorization_status)}
          </p>
          {readiness.missing_audit_event_types.length > 0 ? (
            <p className="mt-1 text-slate-600">
              Brakuje: {readiness.missing_audit_event_types.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}
      {blockerLabels.length > 0 ? (
        <div className="mt-4 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Co blokuje zapis</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {blockerLabels.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {readiness.apply_contract ? (
        <TechnicalDetailsPanel
          className="mt-4"
          openLabel="Pokaż szczegóły przyszłego zapisu"
          closeLabel="Ukryj szczegóły przyszłego zapisu"
        >
          <div className="mt-3 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-700">
            <div className="font-semibold text-ink">Zakres przyszłego zapisu</div>
            <p className="mt-2">{readiness.apply_contract.operator_summary}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <ReadinessTile
                label="Operacja"
                value={readiness.apply_contract.allowed_operation}
              />
              <ReadinessTile
                label="Adapter"
                value={readiness.apply_contract.adapter_status === "implemented" ? "gotowy" : "brak"}
              />
              <ReadinessTile
                label="Publikacja"
                value={readiness.apply_contract.publication_allowed ? "dozwolona" : "zablokowana"}
              />
            </div>
          </div>
        </TechnicalDetailsPanel>
      ) : null}
    </section>
  );
}

function actionWriteAuthorizationStatusLabel(status: string): string {
  if (status === "available") {
    return "WILQ ma zapisane wymagane potwierdzenia operatora.";
  }
  if (status === "audit_actor_mismatch") {
    return "Audit istnieje, ale nie wskazuje jednego operatora potwierdzającego.";
  }
  return "Brakuje pełnego śladu review i potwierdzenia przed zapisem.";
}

function ReadinessTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function ActionChangePreviewSummary({ action }: { action: ActionObject }) {
  if (action.preview_cards.length > 0) {
    return (
      <div className="mb-4 grid gap-3">
        {action.preview_cards.map((card) => (
          <ActionPreviewCard key={card.id} card={card} />
        ))}
      </div>
    );
  }
  return null;
}

export function EvidenceDetailSurface({ evidenceId }: { evidenceId: string }) {
  const evidence = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => getEvidenceById(evidenceId),
    enabled: evidenceId.length > 0
  });

  if (evidence.isLoading) return <LoadingBand />;
  if (evidence.error || !evidence.data) return <ErrorState />;
  return <EvidenceDetail evidence={evidence.data} />;
}

function EvidenceDetail({ evidence }: { evidence: Evidence }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="break-words text-2xl font-semibold tracking-normal">
        {evidence.title_label}
      </h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <NeutralLabelChip>{evidence.source_connector_label}</NeutralLabelChip>
        <NeutralLabelChip>{evidence.source_type_label}</NeutralLabelChip>
        <StatusBadge value={evidence.freshness.state} label={evidence.freshness_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podsumowanie dowodu" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Źródło: {evidence.source_connector_label}</div>
          <div>Typ źródła: {evidence.source_type_label}</div>
          <div>Zebrano: {evidence.collected_at}</div>
          <div>Świeżość: {evidence.freshness_label}</div>
        </div>
        <TechnicalDetailsPanel
          className="mt-4"
          openLabel="Pokaż szczegóły techniczne dowodu"
          closeLabel="Ukryj szczegóły techniczne dowodu"
        >
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>Klucz dowodu w WILQ: {evidence.id}</div>
            <div>Klucz źródła: {evidence.source_id}</div>
            <div>
              Referencja źródłowa:{" "}
              {evidence.raw_ref ??
                "WILQ nie dostał osobnej referencji od źródła; decyzja musi opierać się na podsumowaniu, świeżości i śladzie dowodu."}
            </div>
          </div>
        </TechnicalDetailsPanel>
      </section>
    </main>
  );
}

function OpportunityDetail({ opportunity }: { opportunity: Opportunity }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{opportunity.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <NeutralLabelChip>{opportunity.domain_label}</NeutralLabelChip>
        <StatusBadge value={opportunity.risk} label={opportunity.risk_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Dowody: {opportunity.evidence_summary_label}</div>
          <div>Źródła: {opportunity.source_connector_labels.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Metryki z dowodów" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">
            Nie ma realnych metryk z dowodami; nie oceniaj wpływu tej szansy.
          </p>
        ) : (
          <>
            <MetricTileSummary tiles={opportunity.metric_tiles} />
            <TechnicalDetailsPanel
              className="mt-4"
              openLabel="Pokaż szczegóły techniczne metryk"
              closeLabel="Ukryj szczegóły techniczne metryk"
            >
              <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(opportunity.metrics, null, 2)}
              </pre>
            </TechnicalDetailsPanel>
          </>
        )}
      </section>
    </main>
  );
}

function MetricTileSummary({ tiles }: { tiles: Record<string, string | number> }) {
  const entries = Object.entries(tiles).slice(0, 8);
  if (entries.length === 0) {
    return <p className="text-sm text-slate-600">Metryki są dostępne w szczegółach technicznych.</p>;
  }
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {entries.map(([label, value]) => (
        <span
          key={label}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {label}: {value}
        </span>
      ))}
    </div>
  );
}

function NeutralLabelChip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded border border-line bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
      {children}
    </span>
  );
}

function TechnicalDetailsPanel({
  openLabel,
  closeLabel,
  className = "",
  children
}: {
  openLabel: string;
  closeLabel: string;
  className?: string;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className={`${className} rounded-md border border-line bg-slate-50 p-3 text-xs text-slate-700`}>
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="font-medium text-ink"
      >
        {isOpen ? closeLabel : openLabel}
      </button>
      {isOpen ? children : null}
    </div>
  );
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}
