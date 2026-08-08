import { CheckCircle2 } from "lucide-react";
import { Link } from "@tanstack/react-router";

import { ActionObject, ConnectorStatus } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";

export function ConnectorGrid({ connectors }: { connectors: ConnectorStatus[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {connectors.map((connector) => (
        <article key={connector.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{connector.label}</h3>
              <p className="mt-1 text-xs text-slate-500">
                Źródło danych sprawdzane przez WILQ.
              </p>
            </div>
            <StatusBadge value={connector.status} label={connector.status_label} />
          </div>
          <div className="mt-4 text-xs text-slate-600">
            <p className="mb-3 font-medium text-ink">
              {connectorCapabilityLabel(connector)}
            </p>
            {connector.risk_notes ? (
              <p className="mb-3 rounded-md border border-line bg-slate-50 p-2 text-slate-600">
                Zakres i bezpieczeństwo: {connector.risk_notes}
              </p>
            ) : null}
            {connector.missing_credentials.length > 0 ? (
              <div>
                <div className="mb-1 font-medium text-wait">Brakujące ustawienia dostępu</div>
                <div>{connector.missing_credentials_summary_label}</div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-signal">
                <CheckCircle2 aria-hidden="true" size={16} />
                Skonfigurowany
              </div>
            )}
            {connector.available_credential_sources.length > 0 ? (
              <div className="mt-2 text-slate-500">
                Źródła konfiguracji: {connector.credential_source_summary_label}
              </div>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}

function connectorCapabilityLabel(connector: ConnectorStatus) {
  if (connector.capabilities.action_scope === "disabled") {
    return "Zakres: integracja wyłączona w bieżącym produkcie.";
  }
  if (connector.capabilities.action_scope === "draft_only") {
    return "Zapis: wyłącznie nowy szkic przez zaimplementowany adapter.";
  }
  if (connector.capabilities.action_scope === "review_only") {
    return connector.capabilities.read
      ? "Akcje: przygotowanie i review, bez zapisu do systemu zewnętrznego."
      : "Akcje: przygotowanie i review z danych WILQ; brak odczytu i publikacji w tym kanale.";
  }
  return "Zakres: wyłącznie odczyt danych.";
}

export function ActionList({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Nie ma akcji dla tej powierzchni; WILQ nie powinien sugerować zapisu zmian.
      </p>
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {actions.map((action) => (
        <article key={action.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{action.title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Otwórz akcję, żeby sprawdzić warunki i bezpieczny zapis zmian.
              </p>
            </div>
            <StatusBadge value={action.status} label={action.status_label} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {action.human_diagnosis}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <StatusBadge value={action.validation_status} label={action.validation_status_label} />
            <StatusBadge value={action.risk} label={action.risk_label} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {action.evidence_summary_label}</div>
            <div>Zapisane sprawdzenia: {action.audit_events.length}</div>
          </div>
          <Link
            to="/actions/$actionId"
            params={{ actionId: action.id }}
            className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
          >
            Otwórz akcję
          </Link>
        </article>
      ))}
    </div>
  );
}
