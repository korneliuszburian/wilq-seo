import type { ActionObject } from "../../lib/api";
import { ActionPreviewCard } from "../../components/ActionPreviewCard";
import { StatusBadge } from "../../components/StatusBadge";
import { actionBlockerLabel, readinessModeLabel } from "./DecisionHeroSection";
import { SectionHeading, type ActionMutationReadiness } from "./Shared";
import { TechnicalDetailsPanel } from "./TechnicalSection";

export function ActionMutationReadinessPanel({
  loading,
  error,
  readiness
}: {
  loading: boolean;
  error: unknown;
  readiness: ActionMutationReadiness | undefined;
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
          value={readiness.ready_to_request_apply ? "ready" : "blocked"}
          label={readiness.ready_to_request_apply ? "żądanie gotowe do apply" : "zapis zablokowany"}
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
        <ReadinessTile
          label="Techniczna ścieżka zapisu"
          value={readiness.vendor_write_possible ? "adapter dostępny po bramkach" : "brak"}
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
  if (status === "blocked_outside_action_apply") {
    return "Ślad review istnieje, ale zapis poza kanoniczną akcją apply pozostaje zablokowany.";
  }
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

export function ActionChangePreviewSummary({ action }: { action: ActionObject }) {
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
