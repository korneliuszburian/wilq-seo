import type { ActionObject } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import type { ActionMutationReadiness } from "./Shared";

export function ActionOperatorDecisionHero({
  action,
  mutationReadiness,
  mutationReadinessLoading,
  mutationReadinessError
}: {
  action: ActionObject;
  mutationReadiness: ActionMutationReadiness | undefined;
  mutationReadinessLoading: boolean;
  mutationReadinessError: unknown;
}) {
  // Adapter capability is a technical fact. The operator-facing state is
  // ready only when this exact request has no remaining readiness blockers.
  const requestReady = Boolean(mutationReadiness?.ready_to_request_apply);
  const writeBlocked = !requestReady;
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
                  : "Żądanie zapisu jest gotowe"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {mutationReadinessLoading
                ? "WILQ sprawdza szczegóły blokad. Do czasu potwierdzenia pracuj tylko na podglądzie i review."
                : mutationReadinessError
                ? "Nie udało się potwierdzić gotowości zapisu, więc WILQ nie powinien traktować tej akcji jako gotowej do zmian."
                : writeBlocked
                  ? mutationReadiness?.vendor_write_possible
                    ? "WILQ ma techniczną ścieżkę zapisu, ale to konkretne żądanie nadal blokują review, potwierdzenie lub audyt."
                    : "Możesz pracować na podglądzie i review, ale nie traktuj tej akcji jako zgody na zapis w zewnętrznym systemie."
                  : "WILQ potwierdził bramki tego exact żądania. Zapis nadal wymaga osobnego potwierdzenia w kanonicznym lifecycle."}
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

export function actionBlockerLabel(label: string): string {
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

export function readinessModeLabel(label: string): string {
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
