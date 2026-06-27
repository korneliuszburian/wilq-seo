import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useState } from "react";

import {
  ActionObject,
  ConnectorRefreshRun,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  Opportunity
} from "../lib/api";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
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
            <StatusBadge value={connector.status} />
          </div>
          <div className="mt-4 text-xs text-slate-600">
            {connector.missing_credentials.length > 0 ? (
              <div>
                <div className="mb-1 font-medium text-wait">Brakujące ustawienia dostępu</div>
                <div>{formatPolishCount(connector.missing_credentials.length, "pole", "pola", "pól")}</div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-signal">
                <CheckCircle2 aria-hidden="true" size={16} />
                Skonfigurowany
              </div>
            )}
            {connector.available_credential_sources.length > 0 ? (
              <div className="mt-2 text-slate-500">
                Źródła konfiguracji:{" "}
                {formatPolishCount(
                  connector.available_credential_sources.length,
                  "źródło",
                  "źródła",
                  "źródeł"
                )}
              </div>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}

export function OpportunityList({ opportunities }: { opportunities: Opportunity[] }) {
  if (opportunities.length === 0) {
    return (
      <BlockerNotice message="Brak decyzji w WILQ. Dashboard nie generuje rekomendacji bez dowodów." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {opportunities.map((opportunity) => (
        <article key={opportunity.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{opportunity.title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Decyzja z dowodami i bezpiecznym następnym krokiem.
              </p>
            </div>
            <StatusBadge value={opportunity.risk} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
          {Object.keys(opportunity.metric_tiles).length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
              {Object.entries(opportunity.metric_tiles).map(([label, value]) => (
                <MetricTile key={`${opportunity.id}-${label}`} label={label} value={value} />
              ))}
            </div>
          ) : null}
          <p className="mt-3 text-sm font-medium text-ink">{opportunity.recommended_action}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {formatEvidenceCount(opportunity.evidence_ids.length)}</div>
            <div>
              Źródła danych:{" "}
              {formatPolishCount(opportunity.source_connectors.length, "źródło", "źródła", "źródeł")}
            </div>
            <div>Akcje do sprawdzenia: {opportunity.action_ids.length}</div>
            <div>
              Użyta wiedza: {opportunity.expert_rule_ids.length + opportunity.playbook_ids.length}
            </div>
          </div>
          {opportunity.is_fixture ? (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
              <AlertCircle aria-hidden="true" size={15} />
              Dane testowe, nie realne wyniki Ekologus
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export function EvidenceList({ evidenceItems }: { evidenceItems: Evidence[] }) {
  if (evidenceItems.length === 0) {
    return <p className="text-sm text-slate-600">Brak zapisanych dowodów w WILQ.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {evidenceItems.map((evidence) => (
        <article key={evidence.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Dowód z WILQ</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Zebrany fakt użyty do decyzji. Pełne identyfikatory zostają w śladzie audytu.
              </p>
            </div>
            <StatusBadge value={evidence.freshness.state} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{evidence.summary}</p>
        </article>
      ))}
    </div>
  );
}

export function ConnectorRefreshRunList({ runs }: { runs: ConnectorRefreshRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-600">Brak zapisanych odczytów źródeł danych.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {runs.map((run) => (
        <article key={run.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Odczyt źródła danych</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Skrót ostatniego pobrania danych. Pełny ślad techniczny zostaje w audycie.
              </p>
            </div>
            <StatusBadge value={run.status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{run.summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dane z zewnętrznego systemu: {run.vendor_data_collected ? "tak" : "nie"}</div>
            <div>Zewnętrzny odczyt: {run.external_call_attempted ? "tak" : "nie"}</div>
            <div>Dowody: {formatEvidenceCount(run.evidence_ids.length)}</div>
          </div>
          {formatMetricCount(run.metric_summary) ? (
            <p className="mt-3 text-xs leading-5 text-slate-600">
              Metryki: {formatMetricCount(run.metric_summary)}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export function ActionList({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return <p className="text-sm text-slate-600">Brak akcji dla tej powierzchni.</p>;
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
            <StatusBadge value={action.status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {action.human_diagnosis}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <StatusBadge value={action.validation_status} />
            <StatusBadge value={action.risk} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {formatEvidenceCount(action.evidence_ids.length)}</div>
            <div>Zdarzenia audytu: {action.audit_events.length}</div>
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

function formatEvidenceCount(count: number) {
  return formatPolishCount(count, "dowód źródłowy", "dowody źródłowe", "dowodów źródłowych");
}

function formatPolishCount(count: number, singular: string, few: string, many: string) {
  const absolute = Math.abs(count);
  const lastTwo = absolute % 100;
  const last = absolute % 10;
  if (absolute === 1) return `${count} ${singular}`;
  if (last >= 2 && last <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) {
    return `${count} ${few}`;
  }
  return `${count} ${many}`;
}

function formatMetricCount(metricSummary: Record<string, unknown>) {
  const count = Object.keys(metricSummary).length;
  return count > 0 ? formatPolishCount(count, "wartość", "wartości", "wartości") : "";
}

export function ExpertRuleList({ rules }: { rules: ExpertRule[] }) {
  if (rules.length === 0) {
    return <p className="text-sm text-slate-600">Brak reguł eksperckich dla tej powierzchni.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {rules.map((rule) => (
        <ExpertRuleCard key={rule.id} rule={rule} />
      ))}
    </div>
  );
}

function ExpertRuleCard({ rule }: { rule: ExpertRule }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{rule.name}</h3>
          <p className="mt-1 text-xs text-slate-500">
            Reguła decyzji używana tylko z dowodami i źródłami danych.
          </p>
        </div>
        {rule.requires_evidence ? <StatusBadge value="wymaga dowodów" /> : null}
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{rule.output_contract}</p>
      <button
        type="button"
        className="mt-3 min-h-8 rounded-md border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? "Ukryj szczegóły reguły" : "Pokaż szczegóły reguły"}
      </button>
      {showDetails ? (
        <div className="mt-3 grid gap-2 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-600 sm:grid-cols-2">
          <div>Domena: {rule.domain}</div>
          <div>Wersja: {rule.version}</div>
          <div>Źródło reguły: {rule.source_anchor}</div>
          <div>Typy akcji: {rule.recommended_actions.slice(0, 3).join(", ") || "brak"}</div>
        </div>
      ) : null}
    </article>
  );
}
