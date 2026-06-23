import { AlertCircle, CheckCircle2 } from "lucide-react";
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
              <p className="mt-1 text-xs text-slate-500">{connector.id}</p>
            </div>
            <StatusBadge value={connector.status} />
          </div>
          <div className="mt-4 text-xs text-slate-600">
            {connector.missing_credentials.length > 0 ? (
              <div>
                <div className="mb-1 font-medium text-wait">Missing credentials</div>
                <div className="break-words">{connector.missing_credentials.join(", ")}</div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-signal">
                <CheckCircle2 aria-hidden="true" size={16} />
                Configured
              </div>
            )}
            {connector.available_credential_sources.length > 0 ? (
              <div className="mt-2 break-words text-slate-500">
                Source: {connector.available_credential_sources.join(", ")}
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
      <BlockerNotice message="Brak opportunities z WILQ API. Dashboard nie generuje rekomendacji bez evidence IDs." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {opportunities.map((opportunity) => (
        <article key={opportunity.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{opportunity.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {opportunity.domain} / {opportunity.type}
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
            <div>Dowody: {opportunity.evidence_ids.join(", ")}</div>
            <div>Źródła: {opportunity.source_connectors.join(", ")}</div>
            <div>Reguły: {opportunity.expert_rule_ids.slice(0, 3).join(", ") || "brak"}</div>
            <div>Playbooki: {opportunity.playbook_ids.slice(0, 2).join(", ") || "brak"}</div>
          </div>
          {opportunity.is_fixture ? (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
              <AlertCircle aria-hidden="true" size={15} />
              Dane seed, nie realny performance Ekologus
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export function EvidenceList({ evidenceItems }: { evidenceItems: Evidence[] }) {
  if (evidenceItems.length === 0) {
    return <p className="text-sm text-slate-600">Brak zapisanych dowodów w WILQ API.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {evidenceItems.map((evidence) => (
        <article key={evidence.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{evidence.id}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {evidence.source_connector} / {evidence.source_type}
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
    return <p className="text-sm text-slate-600">Brak zapisanych odczytów connectorów.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {runs.map((run) => (
        <article key={run.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{run.connector_id}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">{run.id}</p>
            </div>
            <StatusBadge value={run.status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{run.summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Mode: {run.mode}</div>
            <div>Dane vendora: {run.vendor_data_collected ? "tak" : "nie"}</div>
            <div>Zewnętrzny odczyt: {run.external_call_attempted ? "tak" : "nie"}</div>
            <div>Dowody: {run.evidence_ids.join(", ")}</div>
          </div>
          {Object.keys(run.metric_summary).length > 0 ? (
            <pre className="mt-3 max-h-32 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
              {JSON.stringify(run.metric_summary, null, 2)}
            </pre>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export function ActionList({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return <p className="text-sm text-slate-600">Brak ActionObjectów dla tej powierzchni.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {actions.map((action) => (
        <article key={action.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{action.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {action.connector} / {action.mode}
              </p>
            </div>
            <StatusBadge value={action.status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <StatusBadge value={action.validation_status} />
            <StatusBadge value={action.risk} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {action.evidence_ids.join(", ")}</div>
            <div>Zdarzenia audytu: {action.audit_events.length}</div>
          </div>
          <RegistryActionPayloadToggle action={action} />
        </article>
      ))}
    </div>
  );
}

function RegistryActionPayloadToggle({ action }: { action: ActionObject }) {
  const [showPayload, setShowPayload] = useState(false);
  const payloadKeys = Object.keys(action.payload);
  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Payload ActionObject
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Schowany na wejściu. Klucze: {payloadKeys.slice(0, 5).join(", ") || "brak"}
            {payloadKeys.length > 5 ? ` +${payloadKeys.length - 5}` : ""}.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPayload((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showPayload ? "Ukryj payload ActionObject" : "Pokaż payload ActionObject"}
        </button>
      </div>
      {showPayload ? (
        <pre className="mt-3 max-h-40 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export function ExpertRuleList({ rules }: { rules: ExpertRule[] }) {
  if (rules.length === 0) {
    return <p className="text-sm text-slate-600">Brak reguł eksperckich dla tej powierzchni.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {rules.map((rule) => (
        <article key={rule.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{rule.name}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {rule.domain} / v{rule.version}
              </p>
            </div>
            {rule.requires_evidence ? <StatusBadge value="wymaga dowodów" /> : null}
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{rule.output_contract}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Źródło reguły: {rule.source_anchor}</div>
            <div>Akcje: {rule.recommended_actions.slice(0, 3).join(", ") || "brak"}</div>
          </div>
        </article>
      ))}
    </div>
  );
}
