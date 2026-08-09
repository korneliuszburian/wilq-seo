import type { ActionCreatedWordPressDraftReadback } from "@wilq/shared-schemas";

import { StatusBadge } from "../../components/StatusBadge";
import { TraceLine } from "../../components/TraceLine";
import type { ActionObject } from "./shared";

export function ActionReviewGatePanel({
  action,
  lastCreatedDraft
}: {
  action: ActionObject;
  lastCreatedDraft?: ActionCreatedWordPressDraftReadback | null;
}) {
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
        <StatusBadge value={gate.status} label={gate.status_label} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <TraceLine
          label="Warunki"
          values={gate.operator_checklist_labels.slice(0, 6)}
          empty="WILQ nie podał dodatkowych warunków; nadal obowiązuje sprawdzenie i jawna zgoda."
        />
        <TraceLine
          label="Blokady zapisu zmian"
          values={[gate.apply_blocker_summary_label]}
          empty="WILQ nie zgłosił blokad zapisu zmian."
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
            <div>Wynik: {gate.last_mutation_audit_status_label}</div>
            <div>Czy próbowano zapisu: {gate.last_mutation_attempted_label}</div>
            <div>Granica adaptera: {gate.last_mutation_adapter_reached_label}</div>
            <div>Vendor write: {gate.last_external_write_attempted_label}</div>
            <div>System zewnętrzny: {gate.last_mutation_adapter_label}</div>
            <div>Ślad bezpieczeństwa: {gate.last_mutation_audit_trace_label}</div>
          </div>
          <TraceLine
            label="Co blokuje zapis"
            values={[gate.last_mutation_blocker_summary_label]}
            empty="WILQ nie zgłosił dodatkowych blokad zapisu."
          />
        </div>
      ) : null}
      <ActionCreatedDraftReadbackPanel draft={lastCreatedDraft} />
    </div>
  );
}

function ActionCreatedDraftReadbackPanel({
  draft
}: {
  draft?: ActionCreatedWordPressDraftReadback | null;
}) {
  if (!draft) return null;
  const publicHref = safeExternalHref(draft.link);
  const editHref = safeExternalHref(draft.edit_link);
  const digestLabel = draft.verification_status === "verified" ? "zweryfikowany" : "zablokowany";
  const isVerifiedDraft =
    draft.readback_status === "available" &&
    draft.post_status === "draft" &&
    draft.verification_status === "verified";
  const postStatusLabel = draft.post_status || "brak potwierdzonego statusu";

  return (
    <div
      className={`mt-3 rounded-md border p-3 text-slate-700 ${
        isVerifiedDraft ? "border-success/30 bg-success/5" : "border-risk/30 bg-risk/5"
      }`}
    >
      <div className={`font-semibold ${isVerifiedDraft ? "text-success" : "text-risk"}`}>
        {isVerifiedDraft ? "Utworzono szkic" : "Status szkicu wymaga sprawdzenia"}
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <div>post_id: {draft.wordpress_post_id}</div>
        <div>modified_gmt: {draft.modified_gmt || "brak w readbacku"}</div>
        <div>Potwierdzenie digestu: {digestLabel}</div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {publicHref ? (
          <a
            href={publicHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 font-medium text-action hover:bg-slate-50"
          >
            Otwórz link publiczny
          </a>
        ) : null}
        {editHref ? (
          <a
            href={editHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-9 items-center rounded-md bg-action px-3 py-2 font-medium text-white hover:bg-action/90"
          >
            Otwórz w edytorze WordPress
          </a>
        ) : null}
      </div>
      <p className="mt-2 leading-5 text-slate-600">
        {isVerifiedDraft
          ? "Szkic nie jest publicznie widoczny do czasu publikacji (poza zakresem WILQ)."
          : `Szkic ma status: ${postStatusLabel} — sprawdź, zanim założysz, że nie jest publiczny.`}
      </p>
      {!isVerifiedDraft && draft.blocker_label ? (
        <p className="mt-2 leading-5 text-risk">Blokada odczytu: {draft.blocker_label}</p>
      ) : null}
    </div>
  );
}

function safeExternalHref(value: string): string | null {
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    const developmentHosts = new Set([
      "ekologus.dev.proudsite.pl",
      "localhost",
      "127.0.0.1"
    ]);
    const productionHosts = new Set(["www.ekologus.pl", "ekologus.pl"]);
    const isAllowedHost = developmentHosts.has(hostname) || productionHosts.has(hostname);
    const isAllowedProtocol =
      url.protocol === "https:" || (url.protocol === "http:" && developmentHosts.has(hostname));
    if (
      !isAllowedHost ||
      !isAllowedProtocol ||
      url.username.length > 0 ||
      url.password.length > 0
    ) {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
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
