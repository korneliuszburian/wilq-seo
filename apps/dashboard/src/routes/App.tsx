import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClientConfig
} from "@tanstack/react-query";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Link,
  RouterProvider,
  useParams
} from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  FileJson,
  RefreshCw,
  ShieldAlert
} from "lucide-react";

import {
  ActionObject,
  ActionApplyResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  AhrefsDiagnosticsResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  ContentDiagnosticsResponse,
  Evidence,
  ExpertRule,
  Ga4DiagnosticsResponse,
  getActions,
  getAdsDiagnostics,
  getAhrefsDiagnostics,
  getCommandCenter,
  getContentDiagnostics,
  getConnectorRefreshRuns,
  getConnectors,
  getEvidence,
  getExpertRules,
  getGa4Diagnostics,
  getKnowledgeCards,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  getLocaloDiagnostics,
  getMarketingBrief,
  getMerchantDiagnostics,
  getOpportunities,
  getTacticalQueue,
  applyAction,
  validateAction,
  getWorkflowRuns,
  getWorkflows,
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  LocaloDiagnosticsResponse,
  CommandCenterResponse,
  MarketingBriefItem,
  MarketingPlaybook,
  MerchantDiagnosticsResponse,
  MetricFact,
  Opportunity,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun
} from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { Shell } from "../components/Shell";

const WILQ_QUERY_STALE_TIME_MS = 30_000;

export function createWilqQueryClient(config?: QueryClientConfig): QueryClient {
  return new QueryClient({
    ...config,
    defaultOptions: {
      ...config?.defaultOptions,
      queries: {
        staleTime: WILQ_QUERY_STALE_TIME_MS,
        gcTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
        ...config?.defaultOptions?.queries
      },
      mutations: {
        ...config?.defaultOptions?.mutations
      }
    }
  });
}

export const queryClient = createWilqQueryClient();

const operatingRoutes = [
  "/ads-doctor",
  "/ads-doctor/search-terms",
  "/ads-doctor/custom-segments",
  "/ads-doctor/demand-gen",
  "/ads-doctor/scaling",
  "/ads-doctor/seasonality",
  "/ads-doctor/recommendations",
  "/ga4",
  "/seo-gsc",
  "/ahrefs",
  "/localo",
  "/merchant",
  "/content-planner",
  "/content-inventory",
  "/social-publisher",
  "/google-sheets",
  "/knowledge",
  "/codex-runs",
  "/security",
  "/settings"
];

function LoadingBand() {
  return (
    <div className="flex h-32 items-center gap-3 px-6 text-sm text-slate-600">
      <RefreshCw aria-hidden="true" className="animate-spin" size={18} />
      Ładowanie stanu WILQ API
    </div>
  );
}

function ConnectorGrid({ connectors }: { connectors: ConnectorStatus[] }) {
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

function OpportunityList({ opportunities }: { opportunities: Opportunity[] }) {
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

function EvidenceList({ evidenceItems }: { evidenceItems: Evidence[] }) {
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

function ConnectorRefreshRunList({ runs }: { runs: ConnectorRefreshRun[] }) {
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

function ActionList({ actions }: { actions: ActionObject[] }) {
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
          <pre className="mt-3 max-h-40 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(action.payload, null, 2)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function ExpertRuleList({ rules }: { rules: ExpertRule[] }) {
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

function WorkflowRunList({ runs }: { runs: WorkflowRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-600">Brak zapisanych uruchomień workflow.</p>;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {runs.map((run) => (
        <article key={run.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{run.workflow_id.replaceAll("_", " ")}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">{run.id}</p>
            </div>
            <StatusBadge value={run.status} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Dowody: {run.output.evidence_ids.length}</div>
            <div>Akcje: {run.output.action_ids.length}</div>
            <div>Błędy: {run.output.errors.length}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

function KnowledgeCardList({ cards }: { cards: KnowledgeCard[] }) {
  if (cards.length === 0) {
    return <p className="text-sm text-slate-600">No compiled knowledge cards yet.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {cards.map((card) => (
        <article key={card.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{card.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {card.card_type} / {card.source_type}
              </p>
            </div>
            <StatusBadge value={`confidence ${Math.round(card.confidence * 100)}%`} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{card.summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Source: {card.source_url_or_path}</div>
            <div>Lineage: {card.source_lineage.slice(0, 4).join(", ")}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

function PlaybookList({ playbooks }: { playbooks: MarketingPlaybook[] }) {
  if (playbooks.length === 0) {
    return <p className="text-sm text-slate-600">Brak maszynowych playbooków.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {playbooks.map((playbook) => (
        <article key={playbook.id} className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold">{playbook.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{playbook.output_contract}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Wymagane dowody: {playbook.required_evidence.slice(0, 4).join(", ")}</div>
            <div>Akcje: {playbook.maps_to_action_types.slice(0, 3).join(", ")}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

function KnowledgeOperatingMapPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak mapy wiedzy do decyzji. WILQ nie powinien pokazywać reguł bez powiązania z evidence i workflowem." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {map.bindings.map((binding) => (
        <article key={binding.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{binding.title}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">
                {binding.id} / {binding.route}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={binding.status} />
              <StatusBadge value={binding.risk} />
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{binding.summary}</p>
          {Object.keys(binding.metric_tiles).length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
              {Object.entries(binding.metric_tiles).map(([label, value]) => (
                <MetricTile key={`${binding.id}-${label}`} label={label} value={value} />
              ))}
            </div>
          ) : null}
          <p className="mt-3 text-sm font-medium text-ink">{binding.next_step}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Skill: {binding.skill_id ?? "brak"}</div>
            <div>Źródła: {binding.source_connectors.join(", ") || "brak"}</div>
            <div>Dowody: {binding.evidence_ids.length || "brak"}</div>
            <div>ActionObjecty: {binding.action_ids.length || "brak"}</div>
            <div>Karty wiedzy: {binding.knowledge_card_ids.join(", ") || "brak"}</div>
            <div>Playbooki: {binding.playbook_ids.join(", ") || "brak"}</div>
            <div>Reguły: {binding.expert_rule_ids.join(", ") || "brak"}</div>
            <div>Wymagane dowody: {binding.required_evidence.slice(0, 4).join(", ") || "brak"}</div>
            <div>Brakujące kontrakty: {binding.missing_contracts.join(", ") || "brak"}</div>
          </div>
          {binding.blocked_claims.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Zablokowane claimy: {binding.blocked_claims.slice(0, 4).join(", ")}
            </p>
          ) : null}
          {binding.source_lineage.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Lineage: {binding.source_lineage.slice(0, 5).join(", ")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function ActionObjectFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak ActionObject dla tego workflow. WILQ może pokazać evidence, ale nie powinien sugerować wykonania bez payload preview." />
    );
  }

  return (
    <section>
      <SectionHeading title="ActionObjecty do walidacji" />
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
              <StatusBadge value={action.validation_status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={action.status} />
              <StatusBadge value={action.risk} />
            </div>
            {action.mode !== "apply" ? (
              <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-wait">
                Apply zablokowany: ten ActionObject jest w trybie przygotowania.
                Najpierw walidacja, podgląd payloadu i jawna zgoda operatora.
              </div>
            ) : null}
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <LinkedTraceLine label="ActionObject" values={[action.id]} kind="actions" />
              <LinkedTraceLine label="Dowody" values={action.evidence_ids} kind="evidence" />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionValidationControls action={action} />
            <div className="mt-3">
              <div className="mb-1 text-xs font-semibold uppercase tracking-normal text-slate-500">
                Podgląd payloadu
              </div>
              <pre className="max-h-56 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(action.payload, null, 2)}
              </pre>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ActionValidationControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const validationMutation = useMutation({
    mutationFn: () => validateAction(action.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const applyMutation = useMutation({
    mutationFn: () =>
      applyAction(action.id, {
        confirm: true,
        confirmed_by: "operator_local_dashboard"
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const validation = validationMutation.data;

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
            Walidacja ActionObject
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Walidacja sprawdza payload, connector, evidence IDs i tryb działania. Nie wykonuje
            apply.
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
          {validationMutation.isPending ? "Waliduję" : "Waliduj"}
        </button>
      </div>
      <ActionValidationResultPanel
        validation={validation}
        error={validationMutation.error instanceof Error ? validationMutation.error.message : null}
      />
      <div className="mt-3 rounded-md border border-wait/30 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
          Jawne potwierdzenie apply
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Apply wymaga requestu z <code>confirm=true</code> i <code>confirmed_by</code>.
          Dla obecnych ActionObjectów prepare-only endpoint nadal zwróci blocker i zapisze
          audit event.
        </p>
        <button
          type="button"
          onClick={() => applyMutation.mutate()}
          disabled={applyMutation.isPending}
          className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-md border border-wait bg-white px-3 py-2 text-xs font-medium text-wait hover:bg-wait/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {applyMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ShieldAlert aria-hidden="true" size={15} />
          )}
          {applyMutation.isPending ? "Sprawdzam apply gate" : "Potwierdź apply"}
        </button>
        <ActionApplyResultPanel
          result={applyMutation.data}
          error={applyMutation.error instanceof Error ? applyMutation.error.message : null}
        />
      </div>
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
    return <div className="mt-3 text-xs leading-5 text-risk">Błąd walidacji: {error}</div>;
  }
  if (!validation) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Wynik: <span className="font-semibold">{validation.valid ? "valid" : "invalid"}</span>
      </div>
      <TraceLine label="Błędy" values={validation.errors} empty="brak" />
      <TraceLine label="Ostrzeżenia" values={validation.warnings} empty="brak" />
    </div>
  );
}

function ActionApplyResultPanel({
  result,
  error
}: {
  result?: ActionApplyResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Apply zablokowany: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Apply: <span className="font-semibold">{result.status}</span>
      </div>
      <TraceLine label="Błędy apply" values={result.errors} empty="brak" />
      <div>Audit event: {result.audit_event.event_type}</div>
    </div>
  );
}

function MetricFactChips({ facts }: { facts: MetricFact[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {facts.map((fact, index) => (
        <span
          key={metricFactKey(fact, index)}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {fact.name}: {formatMetricFactValue(fact)}
          {Object.keys(fact.dimensions ?? {}).length > 0 ? ` / ${formatMetricDimensions(fact)}` : ""}
          {fact.delta !== null && fact.delta !== undefined ? ` (${formatMetricDelta(fact)})` : ""}
          {fact.freshness_label ? ` / ${fact.freshness_label}` : ""}
        </span>
      ))}
    </div>
  );
}

function metricFactKey(fact: MetricFact, index: number) {
  const dimensions = Object.entries(fact.dimensions ?? {})
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join("|");
  return [
    fact.source_connector,
    fact.period,
    fact.name,
    fact.evidence_id,
    dimensions,
    index,
  ].join("::");
}

function TraceLine({
  label,
  values,
  empty = "brak"
}: {
  label: string;
  values: string[];
  empty?: string;
}) {
  return (
    <div className="break-words">
      {label}: {values.length > 0 ? values.join(", ") : empty}
    </div>
  );
}

function LinkedTraceLine({
  label,
  values,
  kind,
  empty = "brak"
}: {
  label: string;
  values: string[];
  kind: "actions" | "evidence";
  empty?: string;
}) {
  return (
    <div className="break-words">
      {label}:{" "}
      {values.length > 0
        ? values.map((value, index) => (
            <span key={value}>
              {index > 0 ? ", " : ""}
              <Link
                to={kind === "actions" ? "/actions/$actionId" : "/evidence/$evidenceId"}
                params={kind === "actions" ? { actionId: value } : { evidenceId: value }}
                className="font-medium text-action underline-offset-2 hover:underline"
              >
                {value}
              </Link>
            </span>
          ))
        : empty}
    </div>
  );
}

function marketerBlockedClaimLabels(claims: string[]) {
  return uniqueValues(claims.map(marketerBlockedClaimLabel));
}

function marketerBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    ROAS: "ROAS",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "approval restored": "ponowne zatwierdzenie produktu",
    "automatic approval fix": "automatyczna naprawa zatwierdzenia",
    "automatic feed edit": "automatyczna zmiana feedu",
    "automatic recommendation accept": "automatyczne przyjęcie rekomendacji",
    "audience size": "rozmiar odbiorców",
    "budget apply": "wdrożenie zmiany budżetu",
    "budget scaling": "skalowanie budżetu",
    "campaign mutation": "zmiana kampanii",
    "campaign performance": "wynik kampanii",
    "conversion drop": "spadek konwersji",
    "conversion loss": "utrata konwersji",
    "conversion rate": "conversion rate",
    "conversion uplift": "wzrost konwersji",
    "feed fix candidate": "kandydat naprawy feedu",
    "feed write": "zapis do feedu",
    "GBP performance": "wynik Google Business Profile",
    "lead quality": "jakość leadów",
    "lead uplift": "wzrost leadów",
    "local ranking": "lokalne pozycje",
    "local visibility uplift": "wzrost lokalnej widoczności",
    "negative keyword apply": "wdrożenie wykluczeń",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "new article without inventory check": "nowy artykuł bez sprawdzenia inventory",
    profitability: "opłacalność",
    "product data mutation": "zmiana danych produktu",
    "product fix applied": "naprawa produktu wdrożona",
    "ranking guarantee": "gwarancja pozycji",
    "recommendation apply": "wdrożenie rekomendacji",
    "revenue impact": "wpływ na przychód",
    "revenue recovered": "odzyskany przychód",
    "search-term waste": "waste na zapytaniach",
    "targeting applied": "targetowanie wdrożone",
    "tracking fixed": "pomiar naprawiony",
    "wasted budget": "zmarnowany budżet"
  };
  return labels[value] ?? value;
}

function BlockerNotice({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-wait/30 bg-wait/10 p-4 text-sm leading-6 text-wait">
      <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
      <span>{message}</span>
    </div>
  );
}

function formatMetricFactValue(fact: MetricFact) {
  const suffix = fact.unit ? ` ${fact.unit}` : "";
  return `${fact.value}${suffix}`;
}

function formatMetricDelta(fact: MetricFact) {
  if (fact.delta === null || fact.delta === undefined || !fact.trend || fact.trend === "unknown") {
    return "delta: brak";
  }
  const sign = fact.delta > 0 ? "+" : "";
  const percent =
    fact.delta_percent === null || fact.delta_percent === undefined
      ? ""
      : ` (${sign}${fact.delta_percent.toFixed(1)}%)`;
  return `delta: ${sign}${fact.delta}${percent}`;
}

function formatMetricDimensions(fact: MetricFact) {
  return Object.entries(fact.dimensions ?? {})
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
}

function MarketingBriefCard({ item }: { item: MarketingBriefItem }) {
  return (
    <article className="rounded-md border border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {item.kind} / {priorityLabel(item.priority)}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.summary}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      {item.blocker_reason ? (
        <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
          Blokada: {item.blocker_reason}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={item.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
      </div>
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

type TacticalQueueItem = TacticalQueueResponse["items"][number];

const tacticalIntentLabels: Record<TacticalQueueItem["intent"], string> = {
  content_refresh: "odświeżenie treści",
  content_create: "nowa treść",
  content_merge: "scalenie treści",
  content_block: "blokada treści",
  landing_page_quality: "jakość landing page",
  tracking_gap: "problem pomiaru",
  merchant_feed_triage: "triage feedu",
  traffic_quality_review: "jakość ruchu"
};

const tacticalDomainLabels: Record<string, string> = {
  gsc_seo: "SEO / GSC",
  ga4: "GA4",
  merchant: "Merchant",
  content: "Content"
};

const tacticalDimensionLabels: Record<string, string> = {
  query: "Query",
  page: "Strona",
  landing_page: "Landing",
  source_medium: "Źródło",
  campaign_name: "Kampania",
  issue_type: "Issue",
  affected_attribute: "Atrybut",
  country: "Kraj",
  reporting_context: "Kontekst",
  wordpress_match: "WordPress",
  wordpress_match_confidence: "Dopasowanie WP",
  gsc_page_query_count: "Liczba query"
};

function TacticalQueuePanel({
  queue,
  connectorIds,
  limit = 8,
  title = "Konkretne zadania z danych",
  hideTrackingGaps = false,
  compact = false,
  isLoading,
  isError
}: {
  queue?: TacticalQueueResponse;
  connectorIds?: string[];
  limit?: number;
  title?: string;
  hideTrackingGaps?: boolean;
  compact?: boolean;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isError) {
    return (
      <BlockerNotice message="Nie udało się odczytać /api/marketing/tactical-queue. Dashboard nie może udawać kolejki działań." />
    );
  }
  if (isLoading || !queue) {
    return (
      <div className="rounded-md border border-line bg-white p-4 text-sm text-slate-600">
        Ładowanie kolejki taktycznej...
      </div>
    );
  }

  const filteredItems = queue.items
    .filter((item) =>
      connectorIds
        ? item.source_connectors.some((connector) => connectorIds.includes(connector))
        : true
    )
    .filter((item) => !(hideTrackingGaps && item.intent === "tracking_gap"));
  const compactGroups = compact ? compactTacticalGroups(filteredItems).slice(0, limit) : [];
  const items = compact ? [] : filteredItems.slice(0, limit);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {compact
              ? "Skondensowana kolejka decyzji z WILQ API. Duplikaty zapytań i URL-i są zgrupowane; pełny drilldown jest w dedykowanych widokach."
              : "Gotowe taktyki z wymiarowych metric facts. Każda karta pokazuje źródła, dowody, ActionObjecty i claimy, których WILQ nie wolno dopowiadać."}
          </p>
          <p className="mt-1 text-xs text-slate-500">{queue.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile
            label={compact ? "Decyzje" : "Taktyki"}
            value={compact ? compactGroups.length : filteredItems.length}
          />
          <MetricTile label="Dowody" value={uniqueValues(filteredItems.flatMap((item) => item.evidence_ids)).length} />
          <MetricTile label="Akcje" value={uniqueValues(filteredItems.flatMap((item) => item.action_ids)).length} />
        </div>
      </div>
      {compact && compactGroups.length > 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {compactGroups.map((group) => (
            <CompactTacticalCard key={group.id} group={group} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <BlockerNotice message="Brak taktyk dla tej trasy. Potrzebne są wymiarowe metric facts z WILQ API." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {items.map((item) => (
            <TacticalQueueCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

type CompactTacticalGroup = {
  id: string;
  title: string;
  meta: string;
  diagnosis: string;
  nextStep: string;
  sourceConnectors: string[];
  evidenceIds: string[];
  actionIds: string[];
  blockedClaims: string[];
  risk: TacticalQueueItem["risk"];
};

function CompactTacticalCard({ group }: { group: CompactTacticalGroup }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{group.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">{group.meta}</p>
        </div>
        <StatusBadge value={group.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{group.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{group.nextStep}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={group.evidenceIds.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={group.sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={group.actionIds} kind="actions" empty="brak" />
        <TraceLine label="Blokady claimów" values={marketerBlockedClaimLabels(group.blockedClaims)} />
      </div>
    </article>
  );
}

function compactTacticalGroups(items: TacticalQueueItem[]): CompactTacticalGroup[] {
  const groups = new Map<string, TacticalQueueItem[]>();
  for (const item of items) {
    const key = compactTacticalGroupKey(item);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return Array.from(groups.values())
    .map((groupItems) => compactTacticalGroup(groupItems))
    .sort((left, right) => prioritySortValue(left.meta) - prioritySortValue(right.meta));
}

function compactTacticalGroupKey(item: TacticalQueueItem) {
  if (item.domain === "gsc_seo" && item.dimensions.page) {
    return `${item.domain}:${item.intent}:${item.dimensions.page}`;
  }
  if (item.domain === "ga4") {
    return `${item.domain}:${item.intent}:${item.dimensions.landing_page ?? ""}:${item.dimensions.source_medium ?? ""}`;
  }
  if (item.domain === "merchant") {
    return `${item.domain}:${item.intent}:${item.dimensions.issue_type ?? ""}:${item.dimensions.affected_attribute ?? ""}:${item.dimensions.country ?? ""}`;
  }
  return item.id;
}

function compactTacticalGroup(items: TacticalQueueItem[]): CompactTacticalGroup {
  const first = items[0];
  const facts = items.flatMap((item) => item.metric_facts);
  const queries = uniqueValues(items.map((item) => item.dimensions.query).filter(Boolean));
  const clicks = sumMetricFacts(facts, "clicks");
  const impressions = sumMetricFacts(facts, "impressions");
  return {
    id: compactTacticalGroupKey(first),
    title: compactTacticalTitle(first, items.length),
    meta: `${tacticalDomainLabels[first.domain] ?? first.domain} / ${tacticalIntentLabels[first.intent]} / ${priorityLabel(first.priority)}`,
    diagnosis: compactTacticalDiagnosis(first, queries, clicks, impressions, items.length),
    nextStep: first.next_step,
    sourceConnectors: uniqueValues(items.flatMap((item) => item.source_connectors)),
    evidenceIds: uniqueValues(items.flatMap((item) => item.evidence_ids)),
    actionIds: uniqueValues(items.flatMap((item) => item.action_ids)),
    blockedClaims: uniqueValues(items.flatMap((item) => item.blocked_claims)),
    risk: first.risk
  };
}

function compactTacticalTitle(item: TacticalQueueItem, groupSize: number) {
  if (item.domain === "gsc_seo" && item.dimensions.page) {
    const action = item.intent === "content_refresh" ? "odśwież" : "zweryfikuj treść";
    return `SEO: ${action} ${shortPath(item.dimensions.page)} (${groupSize} ${polishQueryLabel(groupSize)})`;
  }
  if (item.domain === "ga4") {
    return `GA4: sprawdź ${item.dimensions.landing_page ?? "landing"} / ${item.dimensions.source_medium ?? "źródło"}`;
  }
  if (item.domain === "merchant") {
    return `Merchant: sprawdź ${merchantDimensionLabel(item.dimensions.issue_type ?? "problem feedu")} / ${merchantDimensionLabel(item.dimensions.affected_attribute ?? "atrybut")}`;
  }
  return item.title;
}

function merchantDimensionLabel(value: string) {
  const labels: Record<string, string> = {
    availability_updated: "zmiana dostępności",
    missing_potentially_required_attribute: "brak potencjalnie wymaganego atrybutu",
    "n:availability": "dostępność",
    "n:unit_pricing_measure": "miara ceny jednostkowej",
    "problem feedu": "problem feedu",
    atrybut: "atrybut"
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function compactTacticalDiagnosis(
  item: TacticalQueueItem,
  queries: string[],
  clicks: number | null,
  impressions: number | null,
  groupSize: number
) {
  if (item.domain === "gsc_seo") {
    const queryText = queries.length > 0 ? ` Query: ${queries.slice(0, 4).join(", ")}.` : "";
    const metrics = [
      clicks === null ? null : `clicks=${formatCompactNumber(clicks)}`,
      impressions === null ? null : `impressions=${formatCompactNumber(impressions)}`
    ]
      .filter(Boolean)
      .join(", ");
    return `${groupSize} powiązanych zapytań prowadzi do tej samej strony.${queryText}${metrics ? ` Suma widocznych metryk: ${metrics}.` : ""}`;
  }
  return item.diagnosis;
}

function sumMetricFacts(facts: MetricFact[], name: string) {
  const values = facts
    .filter((fact) => fact.name === name && typeof fact.value === "number")
    .map((fact) => Number(fact.value));
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0);
}

function formatCompactNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function shortPath(value: string) {
  try {
    const parsed = new URL(value);
    return parsed.pathname === "/" ? parsed.hostname : parsed.pathname;
  } catch {
    return value;
  }
}

function polishQueryLabel(count: number) {
  if (count === 1) return "zapytanie";
  if (count >= 2 && count <= 4) return "zapytania";
  return "zapytań";
}

function prioritySortValue(meta: string) {
  if (meta.includes("najpierw")) return 0;
  if (meta.includes("wysoki priorytet")) return 1;
  if (meta.includes("do sprawdzenia")) return 2;
  return 3;
}

function TacticalQueueCard({ item }: { item: TacticalQueueItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {tacticalDomainLabels[item.domain] ?? item.domain} /{" "}
            {tacticalIntentLabels[item.intent]} / {priorityLabel(item.priority)}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={item.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
        <TraceLine label="Blokady claimów" values={marketerBlockedClaimLabels(item.blocked_claims)} />
      </div>
      {tacticalContextPairs(item).length > 0 ? (
        <div className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-700">
          <div className="font-semibold text-ink">Kontekst</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {tacticalContextPairs(item).map(([key, value]) => (
              <span key={key} className="rounded border border-line bg-white px-2 py-1">
                {tacticalDimensionLabels[key] ?? key}: {value}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

function tacticalContextPairs(item: TacticalQueueItem): Array<[string, string]> {
  const priorityKeys = [
    "query",
    "page",
    "landing_page",
    "source_medium",
    "campaign_name",
    "issue_type",
    "affected_attribute",
    "country",
    "reporting_context",
    "wordpress_match",
    "wordpress_match_confidence",
    "gsc_page_query_count"
  ];
  return priorityKeys
    .filter((key) => item.dimensions[key])
    .slice(0, 6)
    .map((key) => [key, item.dimensions[key]]);
}

function priorityLabel(priority: number) {
  if (priority <= 12) return "najpierw";
  if (priority <= 25) return "wysoki priorytet";
  if (priority <= 45) return "do sprawdzenia";
  return "niżej w kolejce";
}

function DailyDecisionBoard({ data }: { data: CommandCenterResponse }) {
  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dzisiejsze decyzje marketera
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {data.primary_next_step}
          </p>
        </div>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {data.daily_decisions.map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Decyzja / {priorityLabel(item.priority)}
                </div>
                <h3 className="mt-1 text-base font-semibold tracking-normal">{item.title}</h3>
              </div>
              <StatusBadge value={item.status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{item.co_widzimy}</p>
            {Object.keys(item.metric_tiles ?? {}).length > 0 ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-3">
                {Object.entries(item.metric_tiles).map(([label, value]) => (
                  <MetricTile key={label} label={label} value={value} />
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {item.dlaczego_to_ma_znaczenie}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">{item.bezpieczny_next_step}</p>
            {item.skill_id && item.codex_prompt ? (
              <div className="mt-3 rounded-md border border-action/25 bg-action/5 p-3 text-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-action">
                  <Copy aria-hidden="true" size={15} />
                  Jak Codex może pomóc
                </div>
                <p className="mt-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Prompt do Codex
                </p>
                <p className="mt-2 leading-6 text-slate-700">{item.codex_prompt}</p>
                <TraceLine label="Skill" values={[item.skill_id]} />
                <TraceLine
                  label="Context-pack"
                  values={item.codex_context_endpoint ? [item.codex_context_endpoint] : []}
                />
                {item.expected_codex_output ? (
                  <p className="mt-2 leading-6 text-slate-700">
                    Oczekiwany wynik: {item.expected_codex_output}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Źródła" values={item.source_connectors} />
              <div>
                Dowody: {item.evidence_ids.length} ID
                {item.evidence_ids.length === 1 ? "" : "s"}
              </div>
              <LinkedTraceLine
                label="Przykładowe dowody"
                values={item.evidence_ids.slice(0, 2)}
                kind="evidence"
                empty="brak"
              />
              <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
              <TraceLine label="Zablokowane claimy" values={marketerBlockedClaimLabels(item.blocked_claims)} />
            </div>
            <a
              href={item.route}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
            >
              Otwórz działanie
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function SourceHealthSummary({ data }: { data: CommandCenterResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Źródła i ograniczenia
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            To jest tylko skrót zdrowia źródeł. Pełne statusy connectorów, braki
            uprawnień i etykiety źródeł dostępu są w ustawieniach, nie w planie dnia.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Źródła" value={data.connector_summary.total} />
          <MetricTile label="Aktywne" value={data.connector_summary.configured} />
          <MetricTile label="Do naprawy" value={data.connector_summary.missing_credentials} />
        </div>
      </div>
      <a
        href="/settings"
        className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
      >
        Otwórz ustawienia
      </a>
    </section>
  );
}

function CommandCenter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;
  const sourceCount = uniqueValues(
    data.daily_decisions.flatMap((item) => item.source_connectors)
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Command Center</h1>
          <p className="mt-1 text-sm text-slate-600">{data.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.daily_decisions.length} />
          <MetricTile label="Blockery" value={data.blocker_count} />
          <MetricTile label="Źródła" value={sourceCount} />
        </div>
      </div>

      <div className="grid gap-8">
        <DailyDecisionBoard data={data} />

        <SourceHealthSummary data={data} />
      </div>
    </main>
  );
}

function OpportunitiesSurface() {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (opportunities.isLoading || actions.isLoading || evidence.isLoading) return <LoadingBand />;
  if (opportunities.error || actions.error || evidence.error) return <ErrorState />;

  const items = opportunities.data ?? [];
  const evidenceIds = new Set(items.flatMap((item) => item.evidence_ids));
  const actionEvidenceIds = new Set((actions.data ?? []).flatMap((action) => action.evidence_ids));
  const liveItems = items.filter((item) => !item.is_fixture);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Szanse i decyzje</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Kolejka szans z WILQ API oparta o te same decyzje, które widzi Command Center.
            Każda karta musi mieć dowody, źródła, liczby i bezpieczny następny krok.
            Sama gotowość connectora albo dane testowe nie są rekomendacją marketingową.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={items.length} />
          <MetricTile label="Aktywne" value={liveItems.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Kolejka decyzji z WILQ API" />
          <OpportunityList opportunities={items} />
        </section>
        <section>
          <SectionHeading title="Powiązane ActionObjecty" />
          <ActionList
            actions={(actions.data ?? []).filter(
              (action) =>
                actionEvidenceIds.size === 0 ||
                action.evidence_ids.some((id) => evidenceIds.has(id))
            )}
          />
        </section>
        <section>
          <SectionHeading title="Dowody użyte przez karty" />
          <EvidenceList
            evidenceItems={(evidence.data ?? []).filter((item) => evidenceIds.has(item.id)).slice(0, 12)}
          />
        </section>
      </div>
    </main>
  );
}

function ActionsSurface() {
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (actions.isLoading || evidence.isLoading) return <LoadingBand />;
  if (actions.error || evidence.error) return <ErrorState />;

  const items = actions.data ?? [];
  const evidenceIds = new Set(items.flatMap((action) => action.evidence_ids));
  const relatedEvidence = (evidence.data ?? [])
    .filter((item) => evidenceIds.has(item.id))
    .slice(0, 12);
  const needsValidation = items.filter(
    (action) => action.validation_status !== "valid"
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Actions</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            ActionObjecty z WILQ API. To jest kolejka bezpiecznych kandydatów działań:
            każda karta ma dowody, tryb, ryzyko, status walidacji i payload preview.
            Apply pozostaje zablokowany bez walidacji, jawnej zgody i audytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="ActionObjects" value={items.length} />
          <MetricTile label="Do walidacji" value={needsValidation.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="ActionObjecty do przeglądu" />
          <ActionList actions={items} />
        </section>
        <section>
          <SectionHeading title="Dowody powiązane z akcjami" />
          <EvidenceList evidenceItems={relatedEvidence} />
        </section>
      </div>
    </main>
  );
}

function WorkflowsSurface() {
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });
  const workflowRuns = useQuery({ queryKey: ["workflow-runs"], queryFn: getWorkflowRuns });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (workflows.isLoading || workflowRuns.isLoading || actions.isLoading || evidence.isLoading) {
    return <LoadingBand />;
  }
  if (workflows.error || workflowRuns.error || actions.error || evidence.error) {
    return <ErrorState />;
  }

  const runs = workflowRuns.data ?? [];
  const workflowItems = workflows.data ?? [];
  const readyWorkflows = workflowItems.filter((workflow) => workflow.status === "ready");
  const workflowEvidenceIds = new Set([
    ...runs.flatMap((run) => run.output.evidence_ids),
    ...workflowItems.flatMap((workflow) => workflow.evidence_ids)
  ]);
  const workflowActionIds = new Set([
    ...runs.flatMap((run) => run.output.action_ids),
    ...workflowItems.flatMap((workflow) => workflow.action_ids)
  ]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Workflowy WILQ</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Mapa workflowów operatora oparta o WILQ API. Gotowe workflowy prowadzą do
            decyzji, dowodów i ActionObjectów; planowane pokazują brakujące kontrakty
            zamiast udawać automatyzację.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Workflowy" value={workflowItems.length} />
          <MetricTile label="Gotowe workflowy" value={readyWorkflows.length} />
          <MetricTile label="Runy" value={runs.length} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Workflowy decyzyjne" />
          <WorkflowRegistryList workflows={workflowItems} />
        </section>
        <section>
          <SectionHeading title="Ostatnie uruchomienia" />
          <WorkflowRunList runs={runs} />
        </section>
        <section>
          <SectionHeading title="Wyniki workflowów" />
          <div className="grid gap-3 xl:grid-cols-2">
            <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
              <h3 className="font-semibold text-ink">Dowody z workflowów</h3>
              <LinkedTraceLine
                label="Dowody"
                values={[...workflowEvidenceIds].slice(0, 12)}
                kind="evidence"
                empty="brak"
              />
            </article>
            <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
              <h3 className="font-semibold text-ink">ActionObjecty z workflowów</h3>
              <LinkedTraceLine
                label="Akcje"
                values={[...workflowActionIds].slice(0, 12)}
                kind="actions"
                empty="brak"
              />
            </article>
          </div>
        </section>
        <section>
          <SectionHeading title="Powiązane ActionObjecty" />
          <ActionList
            actions={(actions.data ?? []).filter((action) => workflowActionIds.has(action.id))}
          />
        </section>
      </div>
    </main>
  );
}

function WorkflowRegistryList({ workflows }: { workflows: Workflow[] }) {
  if (workflows.length === 0) {
    return (
      <BlockerNotice message="Brak workflowów w WILQ API. Nie pokazujemy automatyzacji, której API nie zna." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {workflows.map((workflow) => (
        <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{workflow.label}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">{workflow.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={workflow.status} />
              <StatusBadge value={workflow.risk} />
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{workflow.description}</p>
          {Object.keys(workflow.metric_tiles).length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
              {Object.entries(workflow.metric_tiles).map(([label, value]) => (
                <MetricTile key={`${workflow.id}-${label}`} label={label} value={value} />
              ))}
            </div>
          ) : null}
          {workflow.safe_next_step ? (
            <p className="mt-3 text-sm font-medium text-ink">{workflow.safe_next_step}</p>
          ) : null}
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Skill: {workflow.skill_id ?? "brak"}</div>
            <div>
              Widok:{" "}
              {workflow.route ? (
                <Link className="font-medium text-brand" to={workflow.route}>
                  {workflow.route}
                </Link>
              ) : (
                "brak"
              )}
            </div>
            <div>Źródła: {workflow.source_connectors.join(", ") || "brak"}</div>
            <div>Akcje: {workflow.action_ids.length || "brak"}</div>
            <div>Dowody: {workflow.evidence_ids.length || "brak"}</div>
            <div>Brakujące kontrakty: {workflow.missing_contracts.join(", ") || "brak"}</div>
          </div>
          {workflow.blocked_claims.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Zablokowane claimy: {workflow.blocked_claims.join(", ")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

type BriefSurfaceConfig = {
  title: string;
  description: string;
  focusTitle: string;
  emptyMessage: string;
  safetyTitle: string;
  safetyText: string;
  connectorIds: string[];
  textNeedles: string[];
  showTacticalQueue?: boolean;
};

const briefSurfaceConfigs: Record<string, BriefSurfaceConfig> = {
  "/ads-doctor": {
    title: "Ads Doctor",
    description:
      "Widok Google Ads oparty o WILQ API. Pokazuje dowody, decyzje i blokady claimów; jeśli Ads jest zablokowany, pokazuje blocker zamiast diagnozy spendu.",
    focusTitle: "Decyzje Ads",
    emptyMessage:
      "Brak dowodów Google Ads w /api/marketing/brief. WILQ nie pokaże rekomendacji o spendzie ani kampaniach bez odczytu Ads API.",
    safetyTitle: "Brama bezpieczeństwa Ads",
    safetyText:
      "Zmiany kampanii, budżetu, wykluczeń i segmentów wymagają podglądu akcji, walidacji ActionObject i audytu. Brak dowodów na zapytania, CPA albo ROAS oznacza zakres blokad, nie powód do zgadywania.",
    connectorIds: ["google_ads"],
    textNeedles: []
  },
  "/ga4": {
    title: "GA4",
    description:
      "Widok analityki zachowania i konwersji oparty o WILQ MarketingBrief. Pokazuje tylko metryki GA4 z dowodami.",
    focusTitle: "Jakość ruchu GA4",
    emptyMessage:
      "Brak dowodów GA4 w /api/marketing/brief. Uruchom odczyt GA4, zanim WILQ oceni landing pages albo jakość ruchu.",
    safetyTitle: "Brama bezpieczeństwa GA4",
    safetyText:
      "GA4 służy do diagnozy jakości ruchu i problemów pomiaru. WILQ nie traktuje braku danych jako spadku marketingowego bez evidence.",
    connectorIds: ["google_analytics_4"],
    textNeedles: []
  },
  "/seo-gsc": {
    title: "SEO / GSC",
    description:
      "Widok SEO oparty o dowody GSC z WILQ MarketingBrief. Ma prowadzić do kolejki treści, nie do zgadywania tematów.",
    focusTitle: "Search Console Content Focus",
    emptyMessage:
      "Brak dowodów GSC w /api/marketing/brief. Uruchom odczyt Search Console przed rekomendacją treści.",
    safetyTitle: "Brama dowodów SEO",
    safetyText:
      "Rekomendacje contentowe wymagają metryk zapytań i URL-i, źródła i jasnego następnego kroku. Bez CTR/impressions/clicks WILQ pokazuje blocker.",
    connectorIds: ["google_search_console"],
    textNeedles: []
  },
  "/localo": {
    title: "Localo",
    description:
      "Widok lokalnej widoczności oparty o gotowość WILQ i dowody Localo MCP. Dostęp OAuth może działać, ale lokalne rekomendacje wymagają jeszcze konkretnych faktów o rankingach i GBP.",
    focusTitle: "Local Visibility Focus",
    emptyMessage:
      "Brak konkretnych faktów Localo o rankingach i GBP w /api/marketing/brief. WILQ może pokazać status dostępu, ale nie dopowiada lokalnych wyników bez dowodów.",
    safetyTitle: "Local Visibility Safety Gate",
    safetyText:
      "Posty GBP i lokalne działania wymagają dowodów, podglądu akcji, walidacji ActionObject i audytu. MCP initialize=200 potwierdza dostęp, ale nie zastępuje rankingów, wyniku GBP ani danych konkurencji.",
    connectorIds: ["localo"],
    textNeedles: [],
    showTacticalQueue: false
  },
  "/social-publisher": {
    title: "Social Publisher",
    description:
      "Widok publikacji social oparty o dowody WILQ i stan uprawnień. Przy brakach LinkedIn/Facebook pokazuje blockery, nie gotowe posty.",
    focusTitle: "Social Publishing Focus",
    emptyMessage:
      "Brak dowodów social w /api/marketing/brief. Skonfiguruj credentials LinkedIn/Facebook przed przygotowaniem kandydatów postów.",
    safetyTitle: "Publishing Safety Gate",
    safetyText:
      "Posty LinkedIn/Facebook muszą bazować na claimach z dowodami i pozostać tylko do przygotowania, dopóki stan uprawnień, podgląd akcji i audyt nie są gotowe.",
    connectorIds: ["linkedin", "facebook"],
    textNeedles: []
  },
  "/content-planner": {
    title: "Content Planner",
    description:
      "Widok planowania treści łączy dowody GSC, GA4, Ahrefs, WordPress i Merchant w jedną kolejkę działań dla polskiego marketera.",
    focusTitle: "Content Growth Focus",
    emptyMessage:
      "Brak dowodów contentowych w /api/marketing/brief. WILQ potrzebuje GSC/GA4/Ahrefs/WordPress inventory przed planem treści.",
    safetyTitle: "Content Safety Gate",
    safetyText:
      "Briefy, rewrites i drafty wymagają źródeł, dowodów i zgodności z realną ofertą. WILQ nie generuje claimów bez pokrycia w danych.",
    connectorIds: [
      "google_search_console",
      "google_analytics_4",
      "ahrefs",
      "wordpress_ekologus",
      "wordpress_sklep",
      "google_merchant_center"
    ],
    textNeedles: ["content", "treści", "wordpress", "gsc", "ahrefs", "merchant"]
  },
  "/merchant": {
    title: "Merchant Center",
    description:
      "Widok feed/product oparty o WILQ MarketingBrief. Nie pokazuje rekomendacji, jeżeli brakuje dowodów z Merchant Center albo zweryfikowanego ActionObject.",
    focusTitle: "Feed/Product Focus",
    emptyMessage:
      "Brak dowodów Merchant w /api/marketing/brief. Uruchom odczyt Merchant Center, zanim WILQ zaproponuje zmiany feedu albo produktu.",
    safetyTitle: "Feed Safety Gate",
    safetyText:
      "Zmiana feedu wymaga podglądu akcji, walidacji ActionObject i audit eventu. Ten ekran jest tylko do odczytu, dopóki WILQ API nie wystawi poprawnego kandydata akcji.",
    connectorIds: ["google_merchant_center", "merchant_center"],
    textNeedles: []
  }
};

type AdsBlockedHandoff = NonNullable<AdsDiagnosticsResponse["blocked_handoff"]>;
type AdsDecisionItem = AdsDiagnosticsResponse["decision_queue"][number];
type AdsCampaignMetricRow = AdsDiagnosticsResponse["campaign_read_contract"]["campaign_rows"][number];
type AdsDerivedKpiRow = AdsDiagnosticsResponse["derived_kpi_read_contract"]["kpi_rows"][number];
type AdsBudgetPacingRow =
  AdsDiagnosticsResponse["budget_pacing_read_contract"]["budget_rows"][number];
type AdsRecommendationRow =
  AdsDiagnosticsResponse["recommendations_read_contract"]["recommendation_rows"][number];
type AdsImpressionShareRow =
  AdsDiagnosticsResponse["impression_share_read_contract"]["impression_share_rows"][number];
type AdsChangeHistoryRow =
  AdsDiagnosticsResponse["change_history_read_contract"]["change_history_rows"][number];
type AdsSearchTermMetricRow =
  AdsDiagnosticsResponse["search_terms_read_contract"]["search_term_rows"][number];
type AdsSearchTermSafetyRow =
  AdsDiagnosticsResponse["search_term_safety_read_contract"]["safety_rows"][number];
type AdsKeywordMatchContextRow =
  AdsDiagnosticsResponse["keyword_match_context_read_contract"]["context_rows"][number];
type AdsCustomSegmentCandidate =
  AdsDiagnosticsResponse["custom_segments_read_contract"]["candidates"][number];
type AdsNegativeKeywordCandidate =
  AdsDiagnosticsResponse["negative_keywords_read_contract"]["candidates"][number];

function AdsDoctorSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics"],
    queryFn: getAdsDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ads/diagnostics. Ads Doctor nie może udawać diagnozy bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Ads Doctor nie może pokazać walidacji ani podglądu akcji." />
      </main>
    );
  }

  const data = diagnostics.data;
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;
  const blockedDecisionCount = data.decision_queue.filter(
    (decision) => decision.status === "blocked"
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ads Doctor</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Google Ads z WILQ API. Pokazuje, co marketer może
            uczciwie sprawdzić na podstawie kampanii i zapytań oraz które claimy
            pozostają zablokowane bez kolejnych kontraktów odczytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Blockery" value={blockedDecisionCount} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
          <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Google Ads
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {adsConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki Ads dostępne" : "brak metryk Ads"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {adsRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      {data.blocked_handoff ? <AdsBlockedHandoffPanel handoff={data.blocked_handoff} /> : null}

      <AdsOperatorSummary data={data} />

      <AdsMetricEvidencePanel data={data} currencyCode={currencyCode} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

    </main>
  );
}

function AdsOperatorSummary({ data }: { data: AdsDiagnosticsResponse }) {
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const decisions = data.decision_queue
    .slice()
    .sort((left, right) => adsDecisionSortValue(left) - adsDecisionSortValue(right));
  const allowedMetrics = uniqueValues(
    decisions.flatMap((decision) => decision.allowed_metrics).map(adsAllowedMetricLabel)
  );
  const missingReadContracts = uniqueValues(
    decisions.flatMap((decision) => decision.missing_read_contracts).map(adsMissingReadContractLabel)
  );
  const operatorReviewGates = uniqueValues(
    decisions.flatMap((decision) => decision.operator_review_gates).map(adsOperatorReviewGateLabel)
  );
  const blockedClaims = uniqueValues(
    decisions.flatMap((decision) => decision.blocked_claims).map(adsBlockedClaimLabel)
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co marketer ma sprawdzić teraz w Google Ads
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ pokazuje tylko decyzje, które wynikają z odczytu Google Ads.
            Kampanie i zapytania można przeglądać, ale optymalizacje CPA, ROAS,
            budżetów i wykluczeń wymagają kolejnych kontraktów oraz ActionObject.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Kampanie" value={data.campaign_read_contract.campaign_rows.length} />
          <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
          <MetricTile
            label="Rekom."
            value={data.recommendations_read_contract.recommendation_rows.length}
          />
          <MetricTile
            label="Udział"
            value={data.impression_share_read_contract.impression_share_rows.length}
          />
          <MetricTile
            label="Zmiany"
            value={data.change_history_read_contract.change_history_rows.length}
          />
          <MetricTile
            label="Zapytania"
            value={data.search_terms_read_contract.search_term_rows.length}
          />
          <MetricTile
            label="Waluta"
            value={data.account_currency_read_contract.currency_code ?? "brak"}
          />
          <MetricTile
            label="Biznes"
            value={data.business_context_read_contract.status === "ready" ? "gotowe" : "blokada"}
          />
          <MetricTile
            label="90 dni"
            value={data.search_term_safety_read_contract.safety_rows.length}
          />
          <MetricTile
            label="Keywords"
            value={data.keyword_match_context_read_contract.context_rows.length}
          />
          <MetricTile label="Decyzje" value={decisions.length} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {decisions.length > 0 ? (
            decisions.map((decision) => (
              <AdsDecisionCard
                key={decision.id}
                decision={decision}
                currencyCode={currencyCode}
              />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji Ads. Najpierw uruchom odczyt Google Ads." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb Ads</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Metryki dostępne" values={allowedMetrics} empty="brak" />
            <TraceLine
              label="Waluta konta"
              values={[data.account_currency_read_contract.currency_code ?? "brak"]}
              empty="brak"
            />
            <TraceLine label="Brakujące kontrakty" values={missingReadContracts} empty="brak" />
            <TraceLine label="Wymagany review" values={operatorReviewGates} empty="brak" />
            <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObjecty" values={data.action_ids} kind="actions" />
            <TraceLine label="Nie wolno twierdzić" values={blockedClaims} empty="brak" />
          </div>
        </div>
      </div>
    </section>
  );
}

function AdsDecisionCard({
  decision,
  currencyCode
}: {
  decision: AdsDecisionItem;
  currencyCode?: string;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {adsDecisionTypeLabel(decision.decision_type)} / {adsDecisionStatusLabel(decision.status)}
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          ryzyko: {adsRiskLabel(decision.risk)}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      {decision.negative_keyword_candidates.length > 0 ? (
        <AdsNegativeKeywordCandidatesPanel
          candidates={decision.negative_keyword_candidates}
          currencyCode={currencyCode}
          compact
        />
      ) : null}
      {decision.custom_segment_candidates.length > 0 ? (
        <AdsCustomSegmentCandidatesPanel candidates={decision.custom_segment_candidates} compact />
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <LinkedTraceLine label="ActionObjecty" values={decision.action_ids} kind="actions" />
        {decision.knowledge_card_ids.length > 0 ? (
          <TraceLine label="Karty wiedzy" values={decision.knowledge_card_ids} />
        ) : null}
        {decision.expert_rule_ids.length > 0 ? (
          <TraceLine label="Reguły" values={decision.expert_rule_ids} />
        ) : null}
        {decision.operator_review_gates.length > 0 ? (
          <TraceLine
            label="Wymagany review"
            values={decision.operator_review_gates.map(adsOperatorReviewGateLabel)}
          />
        ) : null}
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claims.map(adsBlockedClaimLabel)} />
      </div>
    </article>
  );
}

function AdsMetricEvidencePanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode?: string;
}) {
  const campaignRows = data.campaign_read_contract.campaign_rows;
  const derivedKpiRows = data.derived_kpi_read_contract.kpi_rows;
  const budgetRows = data.budget_pacing_read_contract.budget_rows;
  const recommendationRows = data.recommendations_read_contract.recommendation_rows;
  const impressionShareRows = data.impression_share_read_contract.impression_share_rows;
  const changeHistoryRows = data.change_history_read_contract.change_history_rows;
  const searchTermRows = data.search_terms_read_contract.search_term_rows;
  const searchTermSafetyRows = data.search_term_safety_read_contract.safety_rows;
  const keywordContextRows = data.keyword_match_context_read_contract.context_rows;
  const customSegmentCandidates = data.custom_segments_read_contract.candidates;
  const negativeKeywordCandidates = data.negative_keywords_read_contract.candidates;
  const missingReadContracts = uniqueValues([
    ...data.account_currency_read_contract.missing_read_contracts,
    ...data.business_context_read_contract.missing_read_contracts,
    ...data.campaign_read_contract.missing_read_contracts,
    ...data.derived_kpi_read_contract.missing_read_contracts,
    ...data.budget_pacing_read_contract.missing_read_contracts,
    ...data.recommendations_read_contract.missing_read_contracts,
    ...data.impression_share_read_contract.missing_read_contracts,
    ...data.change_history_read_contract.missing_read_contracts,
    ...data.search_terms_read_contract.missing_read_contracts,
    ...data.search_term_safety_read_contract.missing_read_contracts,
    ...data.keyword_match_context_read_contract.missing_read_contracts,
    ...data.custom_segments_read_contract.missing_read_contracts,
    ...data.negative_keywords_read_contract.missing_read_contracts
  ]).map(adsMissingReadContractLabel);
  const blockedClaims = uniqueValues([
    ...data.account_currency_read_contract.blocked_claims,
    ...data.business_context_read_contract.blocked_claims,
    ...data.campaign_read_contract.blocked_claims,
    ...data.derived_kpi_read_contract.blocked_claims,
    ...data.budget_pacing_read_contract.blocked_claims,
    ...data.recommendations_read_contract.blocked_claims,
    ...data.impression_share_read_contract.blocked_claims,
    ...data.change_history_read_contract.blocked_claims,
    ...data.search_terms_read_contract.blocked_claims,
    ...data.search_term_safety_read_contract.blocked_claims,
    ...data.keyword_match_context_read_contract.blocked_claims,
    ...data.custom_segments_read_contract.blocked_claims,
    ...data.negative_keywords_read_contract.blocked_claims,
    ...data.sections.flatMap((section) => section.blocked_claims)
  ]).map(adsBlockedClaimLabel);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
            tutaj widać kampanie, zapytania i blokady claimów.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile label="Kampanie" value={campaignRows.length} />
          <MetricTile label="KPI" value={derivedKpiRows.length} />
          <MetricTile label="Budżety" value={budgetRows.length} />
          <MetricTile label="Rekom." value={recommendationRows.length} />
          <MetricTile label="Udział" value={impressionShareRows.length} />
          <MetricTile label="Zmiany" value={changeHistoryRows.length} />
          <MetricTile label="Zapytania" value={searchTermRows.length} />
          <MetricTile label="Safety 90d" value={searchTermSafetyRows.length} />
          <MetricTile label="Keywords" value={keywordContextRows.length} />
          <MetricTile label="Review wykl." value={negativeKeywordCandidates.length} />
          <MetricTile label="Segmenty" value={customSegmentCandidates.length} />
          <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
          <MetricTile
            label="Biznes"
            value={data.business_context_read_contract.status === "ready" ? "gotowe" : "blokada"}
          />
        </div>
      </div>

      <div className="grid gap-4">
        <AdsCampaignRowsTable rows={campaignRows} currencyCode={currencyCode} />
        <AdsDerivedKpiRowsTable rows={derivedKpiRows} currencyCode={currencyCode} />
        <AdsBudgetPacingRowsTable rows={budgetRows} currencyCode={currencyCode} />
        <AdsRecommendationRowsPanel
          rows={recommendationRows}
          currencyCode={currencyCode}
        />
        <AdsImpressionShareRowsTable rows={impressionShareRows} />
        <AdsChangeHistoryRowsTable rows={changeHistoryRows} />
        <AdsSearchTermRowsTable rows={searchTermRows} currencyCode={currencyCode} />
        <AdsSearchTermSafetyRowsTable
          rows={searchTermSafetyRows}
          currencyCode={currencyCode}
        />
        <AdsKeywordMatchContextRowsTable rows={keywordContextRows} />
        <AdsNegativeKeywordCandidatesPanel
          candidates={negativeKeywordCandidates}
          currencyCode={currencyCode}
        />
        <AdsCustomSegmentCandidatesPanel candidates={customSegmentCandidates} />
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Brakujące kontrakty" values={missingReadContracts} />
        <TraceLine label="Nie wolno twierdzić" values={blockedClaims} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine
          label="Sekcje źródłowe"
          values={data.sections.map((section) => adsSectionLabel(section.id))}
        />
      </div>
    </section>
  );
}

function AdsCampaignRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsCampaignMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wymiarowych wierszy kampanii. Ads Doctor nie może analizować kampanii bez odczytu Google Ads." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-4 font-semibold">Wartość konw.</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversion_value)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsDerivedKpiRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsDerivedKpiRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wyliczalnych KPI kampanii. WILQ potrzebuje kosztu, kliknięć, konwersji i wartości konwersji w campaign facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">CTR</th>
            <th className="py-2 pr-4 font-semibold">Śr. CPC</th>
            <th className="py-2 pr-4 font-semibold">Conv. rate</th>
            <th className="py-2 pr-4 font-semibold">CPA</th>
            <th className="py-2 pr-4 font-semibold">Target CPA</th>
            <th className="py-2 pr-4 font-semibold">Różnica CPA</th>
            <th className="py-2 pr-4 font-semibold">ROAS</th>
            <th className="py-2 pr-4 font-semibold">Target ROAS</th>
            <th className="py-2 pr-4 font-semibold">Różnica ROAS</th>
            <th className="py-2 pr-4 font-semibold">Triage</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-kpi`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.ctr)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.average_cpc_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.conversion_rate)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_per_conversion_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.target_cpa_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsSignedCost(row.cpa_vs_target_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.target_roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsSignedNumber(row.roas_vs_target)}</td>
              <td className="py-2 pr-4 text-xs">
                <span className={adsTargetStatusClass(row.target_status)}>
                  {row.target_status_label}
                </span>
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsBudgetPacingRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsBudgetPacingRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kontekstu budżetu kampanii. WILQ potrzebuje campaign_budget.amount_micros z Google Ads, żeby pokazać koszt względem budżetu dziennego." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Budżet</th>
            <th className="py-2 pr-4 font-semibold">Koszt 7 dni</th>
            <th className="py-2 pr-4 font-semibold">7-dniowy budżet</th>
            <th className="py-2 pr-4 font-semibold">Wydanie</th>
            <th className="py-2 pr-4 font-semibold">Rekomendacja Google</th>
            <th className="py-2 pr-4 font-semibold">Preview apply</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.budget_id ?? row.budget_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                <div>{row.campaign_name}</div>
                <div className="text-xs font-normal text-slate-500">
                  {row.advertising_channel_type ?? "kanał: brak"} /{" "}
                  {row.budget_period ?? "okres: brak"}
                </div>
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.budget_amount_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_7d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.seven_day_budget_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.spend_to_budget_ratio_7d)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.has_recommended_budget
                  ? adsCost(row.recommended_budget_amount_micros, currencyCode)
                  : "brak"}
              </td>
              <td className="min-w-48 py-2 pr-4 text-xs text-slate-600">
                {row.payload_preview ? (
                  <div>
                    <div className="font-semibold text-ink">
                      {adsCost(
                        row.payload_preview.proposed_budget_amount_micros,
                        currencyCode
                      )}
                    </div>
                    <div>
                      {row.payload_preview.operation_type} /{" "}
                      {row.payload_preview.apply_allowed ? "apply możliwy" : "apply zablokowany"}
                    </div>
                  </div>
                ) : (
                  "brak"
                )}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsRecommendationRowsPanel({
  rows,
  currencyCode
}: {
  rows: AdsRecommendationRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak aktywnych rekomendacji Google Ads w ostatnim read-only odczycie albo brak kontraktu recommendations. WILQ nie przyjmuje rekomendacji bez review." />
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Rekomendacje Google Ads</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Read-only lista typów rekomendacji do review. Apply pozostaje zablokowany.
          </p>
        </div>
        <MetricTile label="Do review" value={rows.length} />
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <article
            key={`${row.recommendation_id ?? row.recommendation_type}-${row.campaign_id ?? "account"}`}
            className="rounded-md border border-line bg-white p-3"
          >
            <div className="text-sm font-semibold text-ink">{row.recommendation_type}</div>
            <div className="mt-1 text-xs leading-5 text-slate-600">
              Kampania: {row.campaign_id ?? "brak"} / budżet:{" "}
              {row.campaign_budget_id ?? "brak"} / zakres kampanii:{" "}
              {row.campaign_count ?? 0}
            </div>
            {row.impact_available ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                <MetricTile label="Klik. delta" value={adsSignedNumber(row.delta_clicks)} />
                <MetricTile
                  label="Wyśw. delta"
                  value={adsSignedNumber(row.delta_impressions)}
                />
                <MetricTile
                  label="Koszt delta"
                  value={adsSignedCost(row.delta_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt bazowy"
                  value={adsCost(row.base_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt po"
                  value={adsCost(row.potential_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Konw. delta"
                  value={adsSignedNumber(row.delta_conversions)}
                />
              </div>
            ) : (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                Google Ads nie zwrócił impact metrics dla tego typu rekomendacji.
              </div>
            )}
            <TraceLine
              label="Nie wolno twierdzić"
              values={row.blocked_claims.map(adsBlockedClaimLabel)}
            />
            <LinkedTraceLine
              label="Dowody"
              values={row.evidence_ids.slice(0, 2)}
              kind="evidence"
            />
            {row.payload_preview ? (
              <div className="mt-3 rounded-md border border-line bg-slate-50 px-2 py-2 text-xs text-slate-700">
                <div className="font-semibold text-ink">Podgląd apply: zablokowany</div>
                <div className="mt-1">
                  Operacja: {row.payload_preview.operation_type}. Wdrożenie:{" "}
                  {row.payload_preview.apply_allowed
                    ? "dozwolone"
                    : "niedozwolone bez review i audytu"}.
                </div>
                <div className="mt-1">
                  Walidacje: {row.payload_preview.required_validation.slice(0, 4).join(", ")}
                </div>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsImpressionShareRowsTable({ rows }: { rows: AdsImpressionShareRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wierszy udziału w wyświetleniach. WILQ nie może ocenić utraconej ekspozycji przez budżet albo ranking bez impression share facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Search IS</th>
            <th className="py-2 pr-4 font-semibold">Lost IS budget</th>
            <th className="py-2 pr-4 font-semibold">Lost IS rank</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-impression-share`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_budget_lost_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_rank_lost_impression_share)}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsChangeHistoryRowsTable({ rows }: { rows: AdsChangeHistoryRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wierszy historii zmian. WILQ nie może łączyć performance ze zmianami kampanii bez change_event facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Data zmiany</th>
            <th className="py-2 pr-4 font-semibold">Zasób</th>
            <th className="py-2 pr-4 font-semibold">Operacja</th>
            <th className="py-2 pr-4 font-semibold">Klient</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-3 font-semibold">Pola</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.change_event_id ?? "unknown"}-${row.change_date_time ?? "no-date"}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                {row.change_date_time ?? "brak daty"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.change_resource_type ?? "brak"} / {row.change_resource_id ?? "brak ID"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.resource_change_operation ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{row.client_type ?? "brak"}</td>
              <td className="py-2 pr-4 text-slate-700">{row.campaign_id ?? "brak"}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.changed_fields.length > 0
                  ? row.changed_fields.slice(0, 4).join(", ")
                  : `${row.changed_field_count ?? 0} pól`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsSearchTermRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wymiarowych wierszy zapytań. Ads Doctor nie może analizować zapytań ani waste bez danych z search_term_view." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Zapytanie</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsSearchTermSafetyRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermSafetyRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak 90-dniowego safety read dla zapytań. WILQ nie powinien zdejmować blokady z review wykluczeń bez tego odczytu." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Safety 90 dni</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`90d-${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_90d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions_90d)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsKeywordMatchContextRowsTable({ rows }: { rows: AdsKeywordMatchContextRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kontekstu istniejących keywords/match types. WILQ nie powinien zdejmować blokady z review wykluczeń bez odczytu ad_group_criterion." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Keyword</th>
            <th className="py-2 pr-4 font-semibold">Match type</th>
            <th className="py-2 pr-4 font-semibold">Status</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`kw-${row.criterion_id ?? row.keyword_text}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.keyword_text}</td>
              <td className="py-2 pr-4 text-slate-700">{row.match_type}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.negative ? "negative" : row.criterion_status ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_ids.length} ID
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsNegativeKeywordCandidatesPanel({
  candidates,
  currencyCode,
  compact = false
}: {
  candidates: AdsNegativeKeywordCandidate[];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak kolejki review wykluczeń. WILQ potrzebuje search terms z aktywnością i zerową konwersją, a potem 90-dniowego safety checku." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Review wykluczeń z search terms
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kolejka bezpieczeństwa. WILQ pokazuje terminy do sprawdzenia,
            ale blokuje wdrożenie wykluczeń bez kontekstu dopasowania, 90-dniowej
            historii i walidacji ActionObject.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.search_term}</h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {candidate.campaign_name ?? candidate.campaign_id ?? "kampania"} /{" "}
                  {candidate.ad_group_name ?? candidate.ad_group_id ?? "grupa reklam"}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {candidate.safety_status === "needs_90_day_review"
                  ? "wymaga 90 dni"
                  : candidate.safety_status === "read_ready_needs_human_review"
                    ? "90 dni odczytane"
                    : "blocked"}
              </span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <MetricTile label="Kliknięcia" value={adsNumber(candidate.clicks)} />
              <MetricTile
                label="Koszt"
                value={adsCost(candidate.cost_micros, currencyCode)}
              />
              <MetricTile label="Konwersje" value={adsNumber(candidate.conversions)} />
              <MetricTile label="Klik. 90d" value={adsNumber(candidate.clicks_90d)} />
              <MetricTile
                label="Koszt 90d"
                value={adsCost(candidate.cost_micros_90d, currencyCode)}
              />
              <MetricTile label="Konw. 90d" value={adsNumber(candidate.conversions_90d)} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{candidate.next_step}</p>
            {candidate.payload_preview ? (
              <div className="mt-2 rounded-md border border-blue-100 bg-blue-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-blue-700">
                  Podgląd wykluczenia
                </div>
                <div>
                  `{candidate.payload_preview.negative_keyword_text}` /{" "}
                  {candidate.payload_preview.match_type} /{" "}
                  {adsNegativeKeywordLevelLabel(candidate.payload_preview.level)}
                </div>
                <div className="text-slate-600">
                  Wdrożenie:{" "}
                  {candidate.payload_preview.apply_allowed
                    ? "wymaga walidacji"
                    : "zablokowany"}
                  . {candidate.payload_preview.reason}
                </div>
              </div>
            ) : null}
            {candidate.keyword_context_rows.length > 0 ? (
              <div className="mt-2 rounded-md border border-line bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-slate-600">
                  Istniejące keywords w tej grupie
                </div>
                {candidate.keyword_context_rows.slice(0, 4).map((row) => (
                  <div key={`${row.criterion_id ?? row.keyword_text}-${row.match_type}`}>
                    {row.keyword_text} / {row.match_type}
                    {row.negative ? " / negative" : ""}
                  </div>
                ))}
              </div>
            ) : null}
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine label="Wymagane checki" values={candidate.required_checks.map(adsMissingReadContractLabel)} />
              <LinkedTraceLine
                label="Dowody"
                values={uniqueValues([
                  ...candidate.evidence_ids,
                  ...candidate.safety_evidence_ids
                ]).slice(0, 3)}
                kind="evidence"
              />
              <TraceLine label="Nie wolno twierdzić" values={candidate.blocked_claims.map(adsBlockedClaimLabel)} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsCustomSegmentCandidatesPanel({
  candidates,
  compact = false
}: {
  candidates: AdsCustomSegmentCandidate[];
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak kandydatów custom segments. WILQ potrzebuje realnych search terms i walidacji Keyword Planner, zanim przygotuje payload." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Kandydaci custom segments z search terms
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest prepare-only kolejka. WILQ nie twierdzi, że segment ma zasięg,
            ROAS albo wpływ na kampanię bez osobnego forecastu i walidacji.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.name}</h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {candidate.intent} / pewność: {candidate.confidence}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {candidate.validation_status === "pending_validation"
                  ? "do walidacji"
                  : "blocked"}
              </span>
            </div>
            <p className="mt-2 text-sm font-medium text-ink">{candidate.next_step}</p>
            {candidate.payload_preview ? (
              <div className="mt-2 rounded-md border border-blue-100 bg-blue-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-blue-700">
                  Podgląd segmentu
                </div>
                <div>{candidate.payload_preview.custom_segment_name}</div>
                <div className="text-slate-600">
                  Typ wejścia: {candidate.payload_preview.member_type}. Wdrożenie:{" "}
                  {candidate.payload_preview.apply_allowed
                    ? "wymaga walidacji"
                    : "zablokowany"}
                  .
                </div>
              </div>
            ) : null}
            <div className="mt-2 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Source terms" values={candidate.source_terms.slice(0, 8)} />
              <TraceLine label="Odrzucone" values={candidate.rejected_terms.slice(0, 6)} />
              <LinkedTraceLine
                label="Dowody"
                values={candidate.evidence_ids.slice(0, 4)}
                kind="evidence"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={candidate.blocked_claims.map(adsBlockedClaimLabel)}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsBlockedHandoffPanel({ handoff }: { handoff: AdsBlockedHandoff }) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Handoff blockera Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{handoff.title}</h2>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {adsDecisionStatusLabel(handoff.status)}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-700">{handoff.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{handoff.marketer_message}</p>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Ścieżka naprawy</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.repair_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Co wolno pokazać w demo</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.allowed_demo_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={handoff.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={handoff.source_connectors} />
        <LinkedTraceLine label="ActionObjecty" values={handoff.action_ids} kind="actions" />
        <TraceLine label="Nie wolno twierdzić" values={handoff.blocked_claims.map(adsBlockedClaimLabel)} />
      </div>
    </section>
  );
}

function adsDecisionTypeLabel(decisionType: AdsDecisionItem["decision_type"]) {
  if (decisionType === "review_campaign_activity") return "przegląd kampanii";
  if (decisionType === "review_business_context") return "kontekst biznesowy";
  if (decisionType === "review_derived_kpi") return "wyliczone KPI";
  if (decisionType === "review_budget_context") return "kontekst budżetu";
  if (decisionType === "review_recommendations") return "rekomendacje do review";
  if (decisionType === "review_impression_share") return "udział w wyświetleniach";
  if (decisionType === "review_change_history") return "historia zmian";
  if (decisionType === "review_search_term_safety") return "safety 90 dni";
  if (decisionType === "review_search_terms") return "przegląd zapytań";
  if (decisionType === "review_negative_keyword_safety") return "review wykluczeń";
  if (decisionType === "prepare_custom_segments") return "kandydaci segmentów";
  if (decisionType === "block_write_actions") return "blokada zmian";
  return "naprawa dostępu";
}

function adsDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function adsNegativeKeywordLevelLabel(level: string) {
  if (level === "ad_group") return "grupa reklam";
  if (level === "campaign_review_required") return "poziom do decyzji";
  return level;
}

function adsRiskLabel(risk: AdsDecisionItem["risk"]) {
  if (risk === "critical") return "krytyczne";
  if (risk === "high") return "wysokie";
  if (risk === "medium") return "średnie";
  return "niskie";
}

function adsDecisionSortValue(decision: AdsDecisionItem) {
  const statusRank: Record<AdsDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  return statusRank[decision.status] * 100 + decision.priority;
}

function adsConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function adsRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function adsSectionLabel(sectionId: string) {
  if (sectionId === "ads_live_data_status") return "Status odczytu Google Ads";
  if (sectionId === "ads_campaign_overview") return "Aktywność kampanii";
  if (sectionId === "ads_business_context") return "Kontekst biznesowy";
  if (sectionId === "ads_derived_kpi") return "Wyliczone KPI";
  if (sectionId === "ads_budget_pacing") return "Kontekst budżetu";
  if (sectionId === "ads_recommendations") return "Rekomendacje Google Ads";
  if (sectionId === "ads_impression_share") return "Udział w wyświetleniach";
  if (sectionId === "ads_change_history") return "Historia zmian";
  if (sectionId === "ads_search_terms") return "Zapytania użytkowników";
  if (sectionId === "ads_search_term_safety") return "Safety 90 dni";
  if (sectionId === "ads_keyword_match_context") return "Kontekst keywords";
  if (sectionId === "ads_negative_keyword_safety") return "Review wykluczeń";
  if (sectionId === "ads_custom_segments") return "Custom segments";
  if (sectionId === "ads_action_safety") return "Bezpieczeństwo akcji Ads";
  if (sectionId === "ads_oauth_blocker") return "Dostęp Google Ads";
  return sectionId;
}

function adsAllowedMetricLabel(value: string) {
  const labels: Record<string, string> = {
    clicks: "kliknięcia",
    impressions: "wyświetlenia",
    cost_micros: "koszt",
    conversions: "konwersje",
    conversion_value: "wartość konwersji",
    account_currency_code: "waluta konta",
    profit_margin: "marża",
    business_goal: "cel biznesowy",
    human_budget_goal: "cel budżetu",
    target_roas: "target ROAS",
    target_cpa_micros: "target CPA",
    budget_amount_micros: "budżet",
    cost_micros_7d: "koszt 7 dni",
    seven_day_budget_micros: "budżet 7 dni",
    spend_to_budget_ratio_7d: "wydanie względem budżetu",
    budget_has_recommended_budget: "sygnał recommended budget",
    budget_recommended_amount_micros: "rekomendowany budżet",
    recommendation_available: "rekomendacja dostępna",
    recommendation_campaign_count: "kampanie w rekomendacji",
    recommendation_impact_base_clicks: "bazowe kliknięcia rekomendacji",
    recommendation_impact_potential_clicks: "potencjalne kliknięcia rekomendacji",
    recommendation_impact_base_impressions: "bazowe wyświetlenia rekomendacji",
    recommendation_impact_potential_impressions:
      "potencjalne wyświetlenia rekomendacji",
    recommendation_impact_base_cost_micros: "bazowy koszt rekomendacji",
    recommendation_impact_potential_cost_micros: "potencjalny koszt rekomendacji",
    recommendation_impact_base_conversions: "bazowe konwersje rekomendacji",
    recommendation_impact_potential_conversions:
      "potencjalne konwersje rekomendacji",
    recommendation_impact_base_conversion_value:
      "bazowa wartość konwersji rekomendacji",
    recommendation_impact_potential_conversion_value:
      "potencjalna wartość konwersji rekomendacji",
    search_impression_share: "udział w wyświetleniach",
    search_budget_lost_impression_share: "utracony udział przez budżet",
    search_rank_lost_impression_share: "utracony udział przez ranking",
    change_event_available: "historia zmian dostępna",
    change_event_changed_field_count: "liczba zmienionych pól",
    search_term: "zapytanie",
    search_term_90d_clicks: "kliknięcia 90 dni",
    search_term_90d_impressions: "wyświetlenia 90 dni",
    search_term_90d_cost_micros: "koszt 90 dni",
    search_term_90d_conversions: "konwersje 90 dni",
    search_term_90d_conversion_value: "wartość konwersji 90 dni",
    keyword_text: "keyword",
    keyword_match_type: "typ dopasowania keyworda",
    criterion_status: "status keyworda",
    keyword_negative: "keyword negative",
    campaign: "kampania",
    ad_group: "grupa reklam",
    status: "status zapytania"
  };
  return labels[value] ?? value;
}

function adsMissingReadContractLabel(value: string) {
  const labels: Record<string, string> = {
    recommendations: "rekomendacje Google Ads",
    recommendation_impact_preview: "impact preview rekomendacji",
    recommendation_apply_preview: "podgląd apply rekomendacji",
    human_strategy_review: "review strategii przez człowieka",
    change_history: "historia zmian",
    budget_pacing: "tempo wydawania budżetu",
    campaign_budget: "budżet kampanii",
    shared_budget_distribution: "podział shared budget",
    budget_target_or_seasonality: "cel budżetowy lub sezonowość",
    business_goal: "cel biznesowy",
    target_roas_or_cpa: "target ROAS albo CPA",
    profit_margin: "marża albo model rentowności",
    human_budget_goal: "cel budżetu od człowieka",
    account_currency: "waluta konta",
    pre_change_performance_window: "okno wyników przed zmianą",
    post_change_performance_window: "okno wyników po zmianie",
    human_change_impact_review: "ręczny review wpływu zmian",
    apply_preview: "podgląd wdrożenia",
    impression_share: "udział w wyświetleniach",
    "keyword match context": "kontekst dopasowania słów kluczowych",
    keyword_match_context_read: "odczyt istniejących keywords i match types",
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    search_term_90d_read: "90-dniowy odczyt zapytań",
    human_intent_review: "ręczny review intencji",
    review_search_term_context: "sprawdzenie intencji zapytania",
    check_existing_keywords_and_match_types: "sprawdzenie słów i typów dopasowania",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem",
    negative_keyword_payload_preview: "podgląd payloadu wykluczeń",
    negative_keyword_action_validation: "walidacja ActionObject dla wykluczeń",
    "campaign activity": "aktywność kampanii",
    search_term_view: "widok zapytań użytkowników",
    zero_conversion_search_terms: "terminy z zerową konwersją"
  };
  return labels[value] ?? value;
}

function adsOperatorReviewGateLabel(value: string) {
  const labels: Record<string, string> = {
    human_strategy_review: "review strategii przez człowieka",
    review_recommendation_type: "sprawdzenie typu rekomendacji",
    review_impact_metrics: "sprawdzenie impact metrics",
    review_change_history: "sprawdzenie historii zmian",
    review_business_goal: "sprawdzenie celu biznesowego",
    recommendation_apply_preview: "podgląd apply rekomendacji",
    google_ads_rmf_compliance_review: "review Google Ads RMF/compliance",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem"
  };
  return labels[value] ?? value;
}

function adsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    ROAS: "ROAS",
    "search-term waste": "waste na zapytaniach",
    "wasted budget": "zmarnowany budżet",
    "wasted spend": "zmarnowany spend",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "negative keyword apply": "wdrożenie wykluczeń",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "budget apply": "zmiana budżetu",
    "margin verdict": "werdykt marży",
    "currency-formatted cost": "koszt w walucie konta",
    "budget mutation": "zmiana budżetu",
    "campaign mutation": "zmiana kampanii",
    "change history": "historia zmian",
    "change impact": "wpływ zmian",
    "campaign creation": "tworzenie kampanii",
    "impression share": "udział w wyświetleniach",
    "recommendation apply": "wdrożenie rekomendacji",
    "automatic recommendation accept": "automatyczne przyjęcie rekomendacji",
    "performance uplift": "wzrost performance",
    "budget scaling": "skalowanie budżetu",
    "budget amount": "kwota budżetu",
    "budget pacing": "tempo wydawania budżetu",
    "conversion drop": "spadek konwersji",
    "conversion loss": "utrata konwersji",
    "search terms": "zapytania użytkowników",
    "campaign scaling": "skalowanie kampanii"
  };
  return labels[value] ?? value;
}

function adsNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 }).format(value);
}

function adsCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "brak";
  const accountUnits = value / 1_000_000;
  if (currencyCode) {
    return new Intl.NumberFormat("pl-PL", {
      currency: currencyCode,
      maximumFractionDigits: 2,
      style: "currency"
    }).format(accountUnits);
  }
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    accountUnits
  )} jedn. konta`;
}

function adsSignedCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "brak";
  const formatted = adsCost(Math.abs(value), currencyCode);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

function adsSignedNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  if (value > 0) return `+${adsNumber(value)}`;
  return adsNumber(value);
}

function adsTargetStatusClass(status: string | null | undefined) {
  const base = "inline-flex whitespace-nowrap rounded border px-2 py-1 font-semibold";
  if (status === "spend_without_conversions") {
    return `${base} border-amber-200 bg-amber-50 text-amber-800`;
  }
  if (status === "outside_target") {
    return `${base} border-rose-200 bg-rose-50 text-rose-800`;
  }
  if (status === "within_target") {
    return `${base} border-emerald-200 bg-emerald-50 text-emerald-800`;
  }
  return `${base} border-slate-200 bg-slate-50 text-slate-600`;
}

function adsPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    value * 100
  )}%`;
}

type ContentDecisionItem = ContentDiagnosticsResponse["decision_queue"][number];

type Ga4DecisionItem = Ga4DiagnosticsResponse["decision_queue"][number];

type LocaloDecisionItem = LocaloDiagnosticsResponse["decision_queue"][number];

type AhrefsDecisionItem = AhrefsDiagnosticsResponse["decision_queue"][number];

type MerchantDecisionItem = MerchantDiagnosticsResponse["decision_queue"][number];

function Ga4DiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ga4-diagnostics"],
    queryFn: getGa4Diagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ga4/diagnostics. GA4 route nie może udawać behavior ani conversion insightów bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. GA4 route nie może pokazać walidacji ani podglądu payloadu." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">GA4</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok GA4 z WILQ API. Pokazuje jakość ruchu z landingów,
            dopasowanie WordPress i problemy pomiaru bez udawania konwersji, ROAS
            albo revenue.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Do pomiaru" value={data.low_engagement_count} />
          <MetricTile label="Dopasowania WP" value={data.wordpress_match_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status GA4 / Landing Quality
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {ga4ConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki GA4 dostępne" : "brak metryk GA4"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {ga4RefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <Ga4OperatorSummary data={data} />

      <Ga4DiagnosticProof data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa GA4
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować review jakości ruchu i checklistę pomiaru, ale
              nie może uznać wyniku za problem kampanii bez konwersji, kosztów i
              walidacji ActionObject.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

function Ga4OperatorSummary({ data }: { data: Ga4DiagnosticsResponse }) {
  const decisions = data.decision_queue;
  const topDecisions = decisions
    .slice()
    .sort((left, right) => ga4DecisionSortValue(left) - ga4DecisionSortValue(right))
    .slice(0, 4);
  const measurementIssueCount = decisions.filter(
    (decision) => decision.decision_type === "fix_measurement"
  ).length;
  const wordpressMissingCount = decisions.filter(
    (decision) => decision.wordpress_match === "missing"
  ).length;
  const trackingSection = data.sections.find((section) => section.id === "ga4_tracking_readiness");
  const actionIds = data.action_ids.length ? data.action_ids : ["act_review_ga4_tracking_quality"];

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator GA4
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co marketer ma sprawdzić teraz w jakości ruchu
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ pokazuje grupy ruchu do kontroli landingów, źródeł i kampanii.
            Brak metryk konwersji oznacza, że nie wolno wyciągać wniosków o ROAS,
            revenue, spadku konwersji ani winie kampanii.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Pomiar" value={measurementIssueCount} />
          <MetricTile label="Brak WP" value={wordpressMissingCount} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <Ga4DecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji GA4. Najpierw uruchom odczyt GA4." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb analityki</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Gotowość pomiaru"
              values={
                trackingSection
                  ? [ga4SectionStatusLabel(trackingSection.status), trackingSection.summary]
                  : []
              }
              empty="brak"
            />
            <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObject" values={actionIds} kind="actions" />
            <TraceLine
              label="Nie wolno twierdzić"
              values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
            />
          </div>
          <a
            href={`/actions/${actionIds[0]}`}
            className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
          >
            Waliduj ActionObject
          </a>
        </div>
      </div>
    </section>
  );
}

function Ga4DecisionCard({ decision }: { decision: Ga4DecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {ga4DecisionTypeLabel(decision.decision_type)}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge value={ga4DecisionStatusLabel(decision.status)} />
          <StatusBadge value={decision.risk} />
        </div>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.landing_page ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Landing: {decision.landing_page}
          </span>
        ) : null}
        {decision.source_medium ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Źródło: {decision.source_medium}
          </span>
        ) : null}
        {decision.campaign_name ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kampania: {decision.campaign_name}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {wordpressMatchLabel(decision.wordpress_match)}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {wordpressMatchConfidenceLabel(decision.wordpress_match_confidence)}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <LinkedTraceLine label="Akcje" values={decision.action_ids} kind="actions" />
        <TraceLine label="Nie wolno twierdzić" values={ga4BlockedClaimLabels(decision.blocked_claims)} />
      </div>
      {decision.metric_facts.length > 0 ? <MetricFactChips facts={decision.metric_facts.slice(0, 5)} /> : null}
    </article>
  );
}

function Ga4DiagnosticProof({ data }: { data: Ga4DiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.decision_queue.flatMap((decision) => decision.source_connectors)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
        </div>
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => ga4SectionLabel(section.id))} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine
          label="Zablokowane claimy"
          values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </div>
    </section>
  );
}

function ga4DecisionTypeLabel(decisionType: Ga4DecisionItem["decision_type"]) {
  if (decisionType === "fix_measurement") return "problem pomiaru";
  if (decisionType === "review_landing_mapping") return "sprawdzenie mapowania landingu";
  return "kontrola jakości ruchu";
}

function ga4DecisionStatusLabel(status: Ga4DecisionItem["status"]) {
  if (status === "blocked") return "zablokowane";
  return "gotowe";
}

function ga4DecisionSortValue(decision: Ga4DecisionItem) {
  return decision.priority;
}

function ga4SectionLabel(sectionId: string) {
  if (sectionId === "ga4_landing_behavior") return "Jakość ruchu z landingów";
  if (sectionId === "ga4_tracking_readiness") return "Gotowość pomiaru konwersji";
  if (sectionId === "ga4_action_safety") return "Bezpieczeństwo akcji GA4";
  return sectionId;
}

function ga4SectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak metryk konwersji";
  return status;
}

function ga4ConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function ga4RefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function ga4BlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "attribution verdict": "werdykt atrybucji",
    "campaign quality": "jakość kampanii",
    "conversion drop": "spadek konwersji",
    "conversion rate": "conversion rate",
    "conversion setup applied": "konfiguracja konwersji wdrożona",
    "funnel diagnosis": "diagnoza lejka",
    "funnel dropoff": "spadek w lejku",
    "GA4 write": "zapis do GA4",
    "landing page quality": "jakość landing page",
    "message match": "message match",
    "profitability": "opłacalność",
    "revenue": "revenue",
    "ROAS": "ROAS",
    "tracking fixed": "pomiar naprawiony",
    "tracking gap": "problem pomiaru"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function LocaloDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["localo-diagnostics"],
    queryFn: getLocaloDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/localo/diagnostics. Localo route nie może udawać rankingów, GBP ani lokalnej widoczności bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Localo</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Localo z WILQ API. Oddziela dostęp MCP od lokalnych
            rankingów, GBP, konkurencji i reviews, żeby marketer nie dostał
            fałszywej rekomendacji lokalnego SEO.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="MCP" value={data.access_probe.mcp_initialize_status ?? "brak"} />
          <MetricTile label="Fakty" value={data.visibility_fact_count} />
          <MetricTile label="Blokady" value={data.blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Localo / MCP access
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {localoConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {localoAccessStatusLabel(data.access_probe.status)}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {localoRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700">{data.access_probe.summary}</p>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <LocaloOperatorSummary data={data} />
      <LocaloDiagnosticProof data={data} />

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa Localo/GBP
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              MCP initialize potwierdza tylko dostęp adaptera. WILQ nie publikuje
              postów GBP, nie zmienia profilu i nie obiecuje poprawy widoczności
              bez ranking/GBP evidence, ActionObject, walidacji i audytu.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <LinkedTraceLine label="Dowody" values={data.evidence_ids} kind="evidence" />
          <TraceLine label="Źródła" values={["localo"]} />
          <TraceLine
            label="Zablokowane claimy"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.blocked_claims.map(localoBlockedClaimLabel)
              )
            )}
          />
          <TraceLine
            label="Brakujące kontrakty"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.missing_read_contracts.map(localoMissingContractLabel)
              )
            )}
          />
        </div>
      </section>
    </main>
  );
}

function LocaloOperatorSummary({ data }: { data: LocaloDiagnosticsResponse }) {
  const decisions = [...data.decision_queue].sort(localoDecisionSortValue);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co marketer ma wiedzieć o Localo
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Ten widok nie jest listą connectorów. Pokazuje, czy Localo może już
            wspierać decyzje lokalnego SEO, i co WILQ musi jeszcze zebrać.
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Localo z WILQ API. Widok nie wygeneruje lokalnej rekomendacji z pustego stanu." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {decisions.map((decision) => (
            <LocaloDecisionCard key={decision.id} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}

function LocaloDecisionCard({ decision }: { decision: LocaloDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Localo / {localoDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {localoDecisionStatusLabel(decision.status)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles ?? {}).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine label="Access" values={[localoAccessStatusLabel(decision.access_status)]} />
        <TraceLine
          label="Dozwolone evidence"
          values={decision.allowed_evidence.map(localoAllowedEvidenceLabel)}
        />
        <TraceLine
          label="Brakujące kontrakty"
          values={decision.missing_read_contracts.map(localoMissingContractLabel)}
        />
        <TraceLine
          label="Blokady claimów"
          values={decision.blocked_claims.map(localoBlockedClaimLabel)}
        />
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids} kind="evidence" />
      </div>
      {decision.metric_facts.length > 0 ? (
        <MetricFactChips facts={decision.metric_facts.slice(0, 6)} />
      ) : null}
    </article>
  );
}

function LocaloDiagnosticProof({ data }: { data: LocaloDiagnosticsResponse }) {
  const probe = data.access_probe;
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Dowody i ograniczenia Localo
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          WILQ pokazuje access proof osobno od lokalnych facts. Brak facts oznacza
          brak diagnozy rankingów, nie zaproszenie do zgadywania.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="MCP initialize" value={probe.mcp_initialize_status ?? "brak"} />
        <MetricTile label="OAuth code" value={localoBooleanLabel(probe.authorization_code_supported)} />
        <MetricTile label="PKCE S256" value={localoBooleanLabel(probe.pkce_s256_supported)} />
        <MetricTile label="Token" value={localoTokenPresenceLabel(probe.access_token_present)} />
      </div>
      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        {data.sections.map((section) => (
          <article key={section.id} className="rounded-md border border-line p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{section.title}</h3>
              <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                {localoSectionStatusLabel(section.status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
            <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
          </article>
        ))}
      </div>
      {data.visibility_fact_count === 0 ? (
        <BlockerNotice message="Brak Localo ranking/GBP/competitor facts. Ten ekran celowo blokuje lokalne rekomendacje marketingowe." />
      ) : null}
    </section>
  );
}

function localoDecisionSortValue(decision: LocaloDecisionItem) {
  const statusRank: Record<LocaloDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  return statusRank[decision.status] * 1000 + decision.priority;
}

function localoDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function localoSectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak facts";
  return status;
}

function localoDecisionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    access_ready_wait_for_visibility_facts: "status źródła",
    fix_access: "napraw dostęp",
    review_local_visibility: "przejrzyj widoczność",
    block_visibility_claims: "blokada claimów"
  };
  return labels[value] ?? value;
}

function localoConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function localoRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  return status;
}

function localoAccessStatusLabel(status: string) {
  if (status === "access_ready") return "access działa";
  if (status === "access_blocked") return "access zablokowany";
  return "access niepewny";
}

function localoBooleanLabel(value: boolean | null | undefined) {
  if (value === true) return "tak";
  if (value === false) return "nie";
  return "brak";
}

function localoTokenPresenceLabel(value: boolean | null | undefined) {
  if (value === true) return "obecny";
  if (value === false) return "brak";
  return "brak danych";
}

function localoAllowedEvidenceLabel(value: string) {
  const labels: Record<string, string> = {
    access_token_presence: "obecność tokenu",
    competitor_visibility: "widoczność konkurencji",
    gbp_visibility: "widoczność GBP",
    local_rankings: "rankingi lokalne",
    mcp_initialize: "MCP initialize",
    oauth_metadata: "OAuth metadata",
    place_inventory: "lista lokalizacji",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}

function localoMissingContractLabel(value: string) {
  const labels: Record<string, string> = {
    competitor_visibility: "widoczność konkurencji",
    gbp_visibility: "widoczność GBP",
    local_rankings: "rankingi lokalne",
    local_tasks: "zadania lokalne",
    mcp_initialize: "MCP initialize",
    place_inventory: "lista lokalizacji",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}

function localoBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    "competitor visibility": "widoczność konkurencji",
    "GBP performance": "wyniki GBP",
    "GBP post published": "publikacja posta GBP",
    "GBP write": "zmiana GBP",
    "local ranking": "pozycje lokalne",
    "local task completed": "wykonanie zadania lokalnego",
    "local visibility uplift": "wzrost widoczności lokalnej",
    "profile edit applied": "zmiana profilu",
    "review velocity": "tempo opinii",
    "visibility uplift guaranteed": "gwarancja wzrostu widoczności"
  };
  return labels[value] ?? value;
}

function AhrefsDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ahrefs-diagnostics"],
    queryFn: getAhrefsDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ahrefs/diagnostics. Ahrefs route nie może udawać luki treści, luki backlinków ani przewagi konkurencji bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ahrefs</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Ahrefs z WILQ API. Oddziela kontekst autorytetu od
            prawdziwych rekordów luk treści, backlinków i konkurencji, żeby marketer nie
            dostał generycznej rekomendacji SEO z samego DR.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Autorytet" value={data.authority_fact_count} />
          <MetricTile label="Luki SEO" value={data.gap_fact_count} />
          <MetricTile label="Blockery" value={data.blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Ahrefs / dowody SEO
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {ahrefsConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki Ahrefs dostępne" : "brak metryk Ahrefs"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {ahrefsRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <AhrefsOperatorSummary data={data} />
      <AhrefsDiagnosticProof data={data} />
    </main>
  );
}

function AhrefsOperatorSummary({ data }: { data: AhrefsDiagnosticsResponse }) {
  const decisions = [...data.decision_queue].sort(ahrefsDecisionSortValue);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co marketer ma wiedzieć o Ahrefs
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Ten widok nie jest listą connectorów. Pokazuje, czy Ahrefs może już
            wesprzeć decyzje SEO i które claimy nadal są zablokowane.
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Ahrefs z WILQ API. Widok nie wygeneruje analizy luk z pustego stanu." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {decisions.map((decision) => (
            <AhrefsDecisionCard key={decision.id} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}

function AhrefsDecisionCard({ decision }: { decision: AhrefsDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Ahrefs / {ahrefsDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {ahrefsDecisionStatusLabel(decision.status)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Dozwolone evidence"
          values={decision.allowed_evidence.map(ahrefsAllowedEvidenceLabel)}
        />
        <TraceLine
          label="Brakujące kontrakty"
          values={decision.missing_read_contracts.map(ahrefsMissingContractLabel)}
        />
        <TraceLine
          label="Blokady claimów"
          values={decision.blocked_claims.map(ahrefsBlockedClaimLabel)}
        />
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids} kind="evidence" />
      </div>
      {decision.metric_facts.length > 0 ? (
        <MetricFactChips facts={decision.metric_facts.slice(0, 6)} />
      ) : null}
    </article>
  );
}

function AhrefsDiagnosticProof({ data }: { data: AhrefsDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Dowody i ograniczenia Ahrefs
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          WILQ pokazuje fakty autorytetu osobno od rekordów luk SEO. Brak rekordów luk
          oznacza brak diagnozy luk konkurencji, nie zaproszenie do zgadywania.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {data.sections.map((section) => (
          <article key={section.id} className="rounded-md border border-line p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{section.title}</h3>
              <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                {ahrefsSectionStatusLabel(section.status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
            <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
          </article>
        ))}
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine label="Źródła" values={["ahrefs"]} />
        <TraceLine
          label="Zablokowane claimy"
          values={uniqueValues(
            data.decision_queue.flatMap((decision) =>
              decision.blocked_claims.map(ahrefsBlockedClaimLabel)
            )
          )}
        />
      </div>
    </section>
  );
}

function ahrefsDecisionSortValue(decision: AhrefsDecisionItem) {
  const statusRank: Record<AhrefsDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  return statusRank[decision.status] * 1000 + decision.priority;
}

function ahrefsDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function ahrefsSectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak facts";
  return status;
}

function ahrefsDecisionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    block_gap_claims: "blokada luk",
    review_authority_context: "kontekst autorytetu",
    run_authority_read: "odczyt autorytetu"
  };
  return labels[value] ?? value;
}

function ahrefsConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function ahrefsRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  return status;
}

function ahrefsAllowedEvidenceLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs_rank: "Ahrefs Rank",
    authority_summary: "kontekst autorytetu",
    domain_rating: "Domain Rating"
  };
  return labels[value] ?? value;
}

function ahrefsMissingContractLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs_backlink_gap_records: "rekordy luk backlinków",
    ahrefs_competitor_pages: "strony konkurencji",
    ahrefs_content_gap_records: "rekordy luk treści",
    ahrefs_organic_keywords_by_url: "organiczne słowa per URL",
    ahrefs_top_pages_by_competitor: "top pages konkurencji",
    domain_rating: "Domain Rating"
  };
  return labels[value] ?? value;
}

function ahrefsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    "authority improvement": "poprawa autorytetu",
    "backlink gap": "luka backlinków",
    "competitor gap": "przewaga konkurencji",
    "content gap": "luka treści",
    "ranking opportunity": "okazja rankingowa",
    "traffic uplift": "wzrost ruchu"
  };
  return labels[value] ?? value;
}

function ContentDiagnosticSurface({ title }: { title: string }) {
  const diagnostics = useQuery({
    queryKey: ["content-diagnostics"],
    queryFn: getContentDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/content/diagnostics. Content route nie może udawać SEO ani content insightów bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Content route nie może pokazać walidacji ani podglądu payloadu." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestStatuses = data.latest_refreshes.map(
    (refresh) => `${refresh.connector_id}: ${contentRefreshStatusLabel(refresh.status)}`
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok SEO i treści z WILQ API. Łączy zapytania i URL-e z GSC,
            inventory WordPress i ActionObjecty, żeby marketer wiedział co odświeżyć,
            połączyć, utworzyć albo zablokować bez duplikowania treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="Dopasowania WP" value={data.matched_inventory_count} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status SEO / Content
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki treści dostępne" : "brak metryk treści"}
            </span>
            {data.connectors.map((connector) => (
              <span
                key={connector.id}
                className="rounded-md border border-line px-2 py-1 text-slate-600"
              >
                {connector.id}: {contentConnectorStatusLabel(connector.status)}
              </span>
            ))}
          </div>
        </div>
        <TraceLine label="Ostatnie odczyty" values={latestStatuses} />
      </section>

      <ContentOperatorSummary data={data} />

      <ContentDiagnosticProof data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa treści
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować brief, kolejkę odświeżenia i podgląd payloadu,
              ale nie publikuje ani nie zmienia WordPress bez walidacji ActionObject,
              jawnej zgody operatora i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

function ContentOperatorSummary({ data }: { data: ContentDiagnosticsResponse }) {
  const decisions = data.decision_queue;
  const topDecisions = decisions
    .slice()
    .sort((left, right) => contentDecisionSortValue(left) - contentDecisionSortValue(right))
    .slice(0, 4);
  const matchedCount = decisions.filter((decision) => decision.wordpress_match === "found").length;
  const missingCount = decisions.filter((decision) => decision.wordpress_match === "missing").length;
  const decisionTypeLabels = Array.from(
    new Set(decisions.map((decision) => contentDecisionTypeLabel(decision.decision_type)))
  );
  const actionIds = data.action_ids.length ? data.action_ids : ["act_prepare_content_refresh_queue"];

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Content
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co marketer ma zrobić teraz z treściami
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ łączy zapytania i URL-e z GSC z inventory WordPress. Najpierw obsłuż
            istniejące URL-e i klastry zapytań, potem dopiero twórz nowe treści. Bez
            dowodów nie wolno twierdzić, że wzrosną leady, pozycje albo konwersje.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="Dopasowania WP" value={data.matched_inventory_count} />
          <MetricTile label="Decyzje" value={decisions.length} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <ContentDecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji contentowych. Najpierw uruchom odczyt GSC i WordPress." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb treści</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Tryby decyzji" values={decisionTypeLabels} empty="brak" />
            <TraceLine
              label="Dopasowania WordPress"
              values={[
                `potwierdzone: ${matchedCount}`,
                `brak potwierdzenia: ${missingCount}`
              ]}
            />
            <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObject" values={actionIds} kind="actions" />
            <TraceLine
              label="Nie wolno twierdzić"
              values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
            />
          </div>
          <a
            href={`/actions/${actionIds[0]}`}
            className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
          >
            Waliduj ActionObject
          </a>
        </div>
      </div>
    </section>
  );
}

function ContentDecisionCard({ decision }: { decision: ContentDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{contentDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {contentDecisionTypeLabel(decision.decision_type)}
          </p>
        </div>
        <StatusBadge value={decision.status} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.summary ?? decision.rationale}
      </p>
      {decision.summary ? (
        <p className="mt-1 text-xs leading-5 text-slate-500">{decision.rationale}</p>
      ) : null}
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.page ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Strona: {shortPath(decision.page)}
          </span>
        ) : null}
        {decision.queries.length > 0 ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Zapytania: {decision.queries.slice(0, 4).join(", ")}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {wordpressMatchLabel(decision.wordpress_match)}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {wordpressMatchConfidenceLabel(decision.wordpress_match_confidence)}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <LinkedTraceLine label="Akcje" values={decision.action_ids} kind="actions" />
        <TraceLine label="Nie wolno twierdzić" values={contentBlockedClaimLabels(decision.blocked_claims)} />
      </div>
      {decision.metric_facts.length > 0 ? <MetricFactChips facts={decision.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

function ContentDiagnosticProof({ data }: { data: ContentDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.decision_queue.flatMap((decision) => decision.source_connectors)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Content
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
        </div>
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => contentSectionLabel(section.id))} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine
          label="Zablokowane claimy"
          values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </div>
    </section>
  );
}

function contentDecisionTitle(decision: ContentDecisionItem) {
  return decision.title;
}

function contentDecisionTypeLabel(decisionType: ContentDecisionItem["decision_type"]) {
  if (decisionType === "refresh_or_merge") return "odświeżenie albo scalenie";
  if (decisionType === "merge_create_after_inventory_check") {
    return "scalenie lub utworzenie po kontroli inventory";
  }
  if (decisionType === "inventory_check_before_create") return "kontrola inventory przed briefem";
  return "blokada zadania contentowego";
}

function contentDecisionSortValue(decision: ContentDecisionItem) {
  const statusRank: Record<ContentDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  const riskRank: Record<ContentDecisionItem["risk"], number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3
  };
  return statusRank[decision.status] * 1000 + decision.priority * 10 + riskRank[decision.risk];
}

function contentSectionLabel(sectionId: string) {
  if (sectionId === "content_query_page_matrix") return "Zapytania i URL-e z GSC";
  if (sectionId === "content_inventory_match") return "Dopasowanie WordPress";
  if (sectionId === "content_action_safety") return "Bezpieczeństwo akcji";
  return sectionId;
}

function contentConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function contentRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function wordpressMatchLabel(value: string) {
  if (value === "found") return "potwierdzony";
  if (value === "missing") return "brak potwierdzenia";
  return value;
}

function wordpressMatchConfidenceLabel(value: string) {
  if (value === "exact_url") return "dokładny URL";
  if (value === "host_alias_sitemap") return "alias hosta z sitemap";
  if (value === "path_fallback") return "dopasowanie ścieżki";
  if (value === "missing") return "brak dopasowania";
  return value;
}

function contentBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "auto publish": "automatyczna publikacja",
    "content rewrite": "rewrite treści bez dowodu",
    "conversion uplift": "wzrost konwersji",
    "duplicate avoidance": "uniknięcie duplikacji",
    "duplicate-free guarantee": "gwarancja braku duplikatów",
    "lead uplift": "wzrost leadów",
    "merge plan": "plan scalenia",
    "new article without inventory check": "nowy artykuł bez kontroli inventory",
    "ranking guarantee": "gwarancja pozycji",
    "ranking win": "wygrana pozycji",
    "refresh plan": "plan odświeżenia",
    "revenue impact": "wpływ na przychód",
    "ROAS": "ROAS",
    "wordpress write": "zapis do WordPress"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function MerchantDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["merchant-diagnostics"],
    queryFn: getMerchantDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/merchant/diagnostics. Merchant route nie może udawać feed insightów bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Merchant route nie może pokazać walidacji ani podglądu payloadu." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Merchant Center</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok feedu i produktów oparty o Merchant Diagnostics z WILQ API.
            Pokazuje metryki produktów, kolejkę problemów i bezpieczne ActionObjecty
            bez surowych dumpów produktów i bez obietnic naprawy feedu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Problemy" value={data.issue_count ?? 0} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Merchant Center
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {merchantConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki feedu dostępne" : "brak metryk feedu"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {merchantRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <MerchantOperatorSummary data={data} />

      <MerchantDiagnosticProof data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa feedu
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Merchant Center pozostaje w trybie przeglądu i przygotowania. WILQ może pokazać
              kolejkę problemów, dowody i podgląd payloadu, ale nie może zmienić feedu,
              obiecać ponownego zatwierdzenia produktu ani wykonać zmiany bez walidacji i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={merchantBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

function merchantConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function merchantRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function MerchantOperatorSummary({ data }: { data: MerchantDiagnosticsResponse }) {
  const decisions = data.decision_queue;
  const topDecisions = decisions
    .slice()
    .sort((left, right) => merchantDecisionSortValue(left) - merchantDecisionSortValue(right))
    .slice(0, 4);
  const issueItems = data.sections.flatMap((section) => section.tactical_items);
  const topIssueClusters = data.issue_clusters.slice(0, 4);
  const topIssueItems = issueItems
    .slice()
    .sort((left, right) => right.priority - left.priority)
    .slice(0, 3);
  const issueMetricFacts = data.sections
    .flatMap((section) => section.metric_facts)
    .filter((fact) => fact.name === "issue_product_count");
  const reportedIssueOccurrences = data.issue_clusters.length
    ? data.issue_clusters.reduce((sum, cluster) => sum + cluster.product_count, 0)
    : issueMetricFacts.reduce((sum, fact) => {
        return sum + (typeof fact.value === "number" ? fact.value : 0);
      }, 0);
  const issueTypes = Array.from(
    new Set([
      ...data.issue_clusters.map((cluster) => cluster.issue_type),
      ...issueItems.map((item) => item.dimensions.issue_type).filter(Boolean)
    ])
  );
  const actionIds = data.action_ids.length ? data.action_ids : ["act_review_merchant_feed_issues"];

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Merchant
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co marketer ma zrobić teraz z feedem
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ grupuje problemy Merchant po typie i atrybucie. To jest kolejka
            przeglądu: można przygotować decyzje i podgląd payloadu, ale nie wolno
            obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać feedu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Decyzje" value={decisions.length} />
          <MetricTile label="Zgłoszenia" value={reportedIssueOccurrences} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <MerchantDecisionCard key={decision.id} decision={decision} />
            ))
          ) : topIssueClusters.length > 0 ? (
            topIssueClusters.map((cluster) => (
              <article key={cluster.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      {cluster.issue_type}
                      {cluster.affected_attribute ? ` / ${cluster.affected_attribute}` : ""}
                      {` / ${merchantReportingContextLabel(cluster.reporting_context)}`}
                    </h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {cluster.severity} / {cluster.resolution ?? "brak resolution"}
                    </p>
                  </div>
                  <StatusBadge value={cluster.risk} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Raport pokazuje{" "}
                  {formatPolishCount(
                    cluster.product_count,
                    "zgłoszenie",
                    "zgłoszenia",
                    "zgłoszeń"
                  )}{" "}
                  tego problemu
                  {cluster.country ? ` w kraju ${cluster.country}` : ""}
                  {cluster.reporting_context
                    ? ` / ${merchantReportingContextLabel(cluster.reporting_context)}`
                    : " / wszystkie konteksty"}.
                </p>
                {cluster.sample_unavailable_reason ? (
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {cluster.sample_unavailable_reason}
                  </p>
                ) : null}
                <p className="mt-2 text-sm font-medium text-ink">{cluster.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  <span className="rounded border border-line bg-white px-2 py-1">
                    zgłoszenia: {cluster.product_count}
                  </span>
                  {cluster.country ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      kraj: {cluster.country}
                    </span>
                  ) : null}
                  <span className="rounded border border-line bg-white px-2 py-1">
                    kontekst: {merchantReportingContextLabel(cluster.reporting_context)}
                  </span>
                  {cluster.resolution ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      rozwiązanie: {cluster.resolution}
                    </span>
                  ) : null}
                  {cluster.action_id ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      ActionObject: {cluster.action_id}
                    </span>
                  ) : null}
                </div>
              </article>
            ))
          ) : topIssueItems.length > 0 ? (
            topIssueItems.map((item) => (
              <article key={item.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {tacticalIntentLabels[item.intent]} / {priorityLabel(item.priority)}
                    </p>
                  </div>
                  <StatusBadge value={item.risk} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
                <p className="mt-2 text-sm font-medium text-ink">{item.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  {tacticalContextPairs(item).map(([key, value]) => (
                    <span key={key} className="rounded border border-line bg-white px-2 py-1">
                      {tacticalDimensionLabels[key] ?? key}: {value}
                    </span>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <BlockerNotice message="Brak Merchant tactical items. Najpierw uruchom read-only Merchant vendor_read." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb pracy</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Typy problemów" values={issueTypes} empty="brak" />
            <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObject" values={actionIds} kind="actions" />
            <TraceLine
              label="Nie wolno twierdzić"
              values={merchantBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
            />
          </div>
          <a
            href={`/actions/${actionIds[0]}`}
            className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
          >
            Waliduj ActionObject
          </a>
        </div>
      </div>
    </section>
  );
}

function MerchantDecisionCard({ decision }: { decision: MerchantDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {merchantDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
        </div>
        <StatusBadge value={decision.risk} />
      </div>
      {decision.summary ? (
        <p className="mt-2 text-sm leading-6 text-slate-700">{decision.summary}</p>
      ) : null}
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles ?? {}).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.issue_type ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            problem: {decision.issue_type}
          </span>
        ) : null}
        {decision.affected_attribute ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            atrybut: {decision.affected_attribute}
          </span>
        ) : null}
        {decision.country ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kraj: {decision.country}
          </span>
        ) : null}
        <span className="rounded border border-line bg-white px-2 py-1">
          kontekst: {merchantReportingContextLabel(decision.reporting_context)}
        </span>
      </div>
      <div className="mt-2 grid gap-1.5 text-xs text-slate-600">
        <LinkedTraceLine
          label="Dowody"
          values={decision.evidence_ids.slice(0, 4)}
          kind="evidence"
        />
        <LinkedTraceLine label="ActionObject" values={decision.action_ids} kind="actions" />
        <TraceLine
          label="Nie wolno twierdzić"
          values={merchantBlockedClaimLabels(decision.blocked_claims)}
        />
      </div>
    </article>
  );
}

function merchantDecisionTypeLabel(decisionType: MerchantDecisionItem["decision_type"]) {
  if (decisionType === "review_issue_cluster") return "przegląd problemu feedu";
  if (decisionType === "review_feed_status") return "przegląd statusu feedu";
  return "blocker odczytu Merchant";
}

function merchantDecisionSortValue(decision: MerchantDecisionItem) {
  const statusRank: Record<MerchantDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1,
    missing: 2
  };
  return statusRank[decision.status] * 1000 + decision.priority;
}

function merchantReportingContextLabel(value: string | null | undefined) {
  if (!value) return "wszystkie konteksty";
  return value;
}

function formatPolishCount(count: number, one: string, few: string, many: string) {
  const absolute = Math.abs(count);
  const lastDigit = absolute % 10;
  const lastTwoDigits = absolute % 100;
  if (absolute === 1) {
    return `${count} ${one}`;
  }
  if (
    lastDigit >= 2 &&
    lastDigit <= 4 &&
    !(lastTwoDigits >= 12 && lastTwoDigits <= 14)
  ) {
    return `${count} ${few}`;
  }
  return `${count} ${many}`;
}

function MerchantDiagnosticProof({ data }: { data: MerchantDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const blockedClaims = merchantBlockedClaimLabels(
    data.sections.flatMap((section) => section.blocked_claims)
  );
  const sectionTitles = data.sections.map((section) => merchantSectionLabel(section.id));
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.issue_clusters.flatMap((cluster) => cluster.source_connectors)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Merchant
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót technicznego kontraktu WILQ API. Pełna kolejka pracy
            jest powyżej; tutaj widać, z jakich sekcji i dowodów wynika przegląd.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Klastry" value={data.issue_clusters.length} />
        </div>
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={sectionTitles} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={blockedClaims} />
      </div>
    </section>
  );
}

function merchantSectionLabel(sectionId: string) {
  if (sectionId === "merchant_feed_health") return "Metryki produktów";
  if (sectionId === "merchant_issue_queue") return "Kolejka problemów feedu";
  if (sectionId === "merchant_action_safety") return "Bezpieczeństwo akcji";
  return sectionId;
}

function merchantBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "approval restored": "produkt zatwierdzony ponownie",
    "automatic approval fix": "automatyczna naprawa zatwierdzenia",
    "automatic feed edit": "automatyczna zmiana feedu",
    "feed fix candidate": "kandydat naprawy feedu",
    "feed health": "ocena stanu feedu",
    "feed write": "zapis do feedu",
    "primary feed overwrite": "nadpisanie głównego feedu",
    "product approval": "zatwierdzenie produktu",
    "product data mutation": "zmiana danych produktu",
    "product-level fix": "naprawa pojedynczego produktu",
    "profit uplift": "wzrost zysku",
    "revenue recovered": "odzyskany przychód"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function BriefWorkflowSurface({ config }: { config: BriefSurfaceConfig }) {
  const marketingBrief = useQuery({
    queryKey: ["marketing-brief"],
    queryFn: getMarketingBrief
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  const tacticalQueue = useQuery({
    queryKey: ["tactical-queue"],
    queryFn: getTacticalQueue
  });

  if (marketingBrief.isLoading || actions.isLoading || tacticalQueue.isLoading) return <LoadingBand />;
  if (marketingBrief.error || !marketingBrief.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message={`Nie udało się odczytać /api/marketing/brief. ${config.title} nie może pokazać rekomendacji bez WILQ API.`} />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message={`Nie udało się odczytać /api/actions. ${config.title} nie może pokazać payload preview ani walidacji ActionObject.`} />
      </main>
    );
  }

  const brief = marketingBrief.data;
  const allItems = brief.sections.flatMap((section) => section.items);
  const routeItems = allItems
    .filter((item) => itemMatchesBriefSurface(item, config))
    .sort((left, right) => right.priority - left.priority);
  const recommendations = routeItems.filter((item) => item.kind === "recommendation");
  const blockers = routeItems.filter((item) => item.kind === "blocker");
  const metricFacts = brief.top_metric_facts.filter((fact) =>
    config.connectorIds.includes(fact.source_connector)
  );
  const routeActionIds = uniqueValues(routeItems.flatMap((item) => item.action_ids));
  const routeActions = actions.data.filter((action) => routeActionIds.includes(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{config.title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{config.description}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Rekomendacje" value={recommendations.length} />
          <MetricTile label="Blockery" value={blockers.length} />
          <MetricTile label="Fakty" value={metricFacts.length} />
        </div>
      </div>

      <div className="grid gap-6">
        {routeItems.length === 0 ? (
          <BlockerNotice message={config.emptyMessage} />
        ) : (
          <section>
            <SectionHeading title={config.focusTitle} />
            <div className="grid gap-3 xl:grid-cols-2">
              {routeItems.map((item) => (
                <MarketingBriefCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        )}

        {routeActionIds.length > 0 ? <ActionObjectFocus actions={routeActions} /> : null}

        {config.showTacticalQueue === false ? null : (
          <TacticalQueuePanel
            queue={tacticalQueue.data}
            connectorIds={config.connectorIds}
            limit={6}
            title="Taktyki z WILQ API"
            isLoading={tacticalQueue.isLoading}
            isError={Boolean(tacticalQueue.error)}
          />
        )}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
              <ShieldAlert aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                {config.safetyTitle}
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">{config.safetyText}</p>
            </div>
          </div>
          <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <LinkedTraceLine
              label="Dowody"
              values={uniqueValues(routeItems.flatMap((item) => item.evidence_ids))}
              kind="evidence"
            />
            <TraceLine
              label="Źródła"
              values={uniqueValues(routeItems.flatMap((item) => item.source_connectors))}
            />
            <LinkedTraceLine
              label="Akcje"
              values={uniqueValues(routeItems.flatMap((item) => item.action_ids))}
              kind="actions"
            />
          </div>
          {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 6)} /> : null}
        </section>
      </div>
    </main>
  );
}

function itemMatchesBriefSurface(item: MarketingBriefItem, config: BriefSurfaceConfig) {
  const searchable = `${item.id} ${item.title} ${item.summary} ${item.next_step}`.toLowerCase();
  return (
    item.source_connectors.some((connector) => config.connectorIds.includes(connector)) ||
    config.textNeedles.some((needle) => searchable.includes(needle))
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}

function GenericSurface({ routeName }: { routeName: string }) {
  const connectors = useQuery({ queryKey: ["connectors"], queryFn: getConnectors });
  const connectorRefreshRuns = useQuery({
    queryKey: ["connector-refresh-runs"],
    queryFn: getConnectorRefreshRuns
  });
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });
  const workflowRuns = useQuery({ queryKey: ["workflow-runs"], queryFn: getWorkflowRuns });
  const expertRules = useQuery({ queryKey: ["expert-rules"], queryFn: getExpertRules });
  const isKnowledgeRoute = routeName.startsWith("/knowledge");
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-operating-map"],
    queryFn: getKnowledgeOperatingMap,
    enabled: isKnowledgeRoute
  });
  const knowledgeCards = useQuery({
    queryKey: ["knowledge-cards"],
    queryFn: getKnowledgeCards,
    enabled: isKnowledgeRoute
  });
  const playbooks = useQuery({
    queryKey: ["knowledge-playbooks"],
    queryFn: getKnowledgePlaybooks,
    enabled: isKnowledgeRoute
  });
  const isWorkflowRoute = routeName.startsWith("/workflows");
  const isWorkflowLoading = isWorkflowRoute && (workflows.isLoading || workflowRuns.isLoading);
  const hasWorkflowError = isWorkflowRoute && (workflows.error || workflowRuns.error);
  const isKnowledgeLoading =
    isKnowledgeRoute && (knowledgeMap.isLoading || knowledgeCards.isLoading || playbooks.isLoading);
  const hasKnowledgeError =
    isKnowledgeRoute && (knowledgeMap.error || knowledgeCards.error || playbooks.error);

  if (
    connectors.isLoading ||
    connectorRefreshRuns.isLoading ||
    opportunities.isLoading ||
    actions.isLoading ||
    evidence.isLoading ||
    expertRules.isLoading ||
    isWorkflowLoading ||
    isKnowledgeLoading
  ) {
    return <LoadingBand />;
  }
  if (
    connectors.error ||
    connectorRefreshRuns.error ||
    opportunities.error ||
    actions.error ||
    evidence.error ||
    expertRules.error ||
    hasWorkflowError ||
    hasKnowledgeError
  ) {
    return <ErrorState />;
  }

  const title = isKnowledgeRoute
    ? "Baza wiedzy WILQ"
    : routeName
        .replace(/^\//, "")
        .replaceAll("/", " / ")
        .replaceAll("-", " ")
        .replace(/\b\w/g, (match) => match.toUpperCase());
  const mappedRules = expertRulesForRoute(routeName, expertRules.data ?? []).slice(0, 6);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title || "Command Center"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {isKnowledgeRoute
              ? "Źródła, playbooki i expert rules powiązane z decyzjami, workflowami i dowodami WILQ API."
              : "API-backed operating surface with evidence, connector and action state."}
          </p>
        </div>
        <FileJson aria-hidden="true" className="text-action" size={28} />
      </div>
      <div className="grid gap-6">
        {isWorkflowRoute ? (
          <>
            <section>
              <SectionHeading title="Workflow Registry" />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {(workflows.data ?? []).map((workflow) => (
                  <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
                    <h3 className="text-sm font-semibold">{workflow.label}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{workflow.description}</p>
                  </article>
                ))}
              </div>
            </section>
            <section>
              <SectionHeading title="Workflow Runs" />
              <WorkflowRunList runs={workflowRuns.data ?? []} />
            </section>
          </>
        ) : null}
        {isKnowledgeRoute ? (
          <>
            <section>
              <div className="mb-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
                <MetricTile label="Powiązania" value={knowledgeMap.data?.binding_count ?? 0} />
                <MetricTile label="Karty wiedzy" value={knowledgeMap.data?.source_card_count ?? 0} />
                <MetricTile label="Playbooki" value={knowledgeMap.data?.playbook_count ?? 0} />
                <MetricTile label="Reguły" value={knowledgeMap.data?.expert_rule_count ?? 0} />
              </div>
              <SectionHeading title="Mapa wiedzy do decyzji" />
              <KnowledgeOperatingMapPanel
                map={
                  knowledgeMap.data ?? {
                    generated_at: "",
                    source_card_count: 0,
                    playbook_count: 0,
                    expert_rule_count: 0,
                    binding_count: 0,
                    bindings: []
                  }
                }
              />
            </section>
            <section>
              <SectionHeading title="Karty źródłowe" />
              <KnowledgeCardList cards={knowledgeCards.data ?? []} />
            </section>
            <section>
              <SectionHeading title="Playbooki maszynowe" />
              <PlaybookList playbooks={playbooks.data ?? []} />
            </section>
          </>
        ) : null}
        <section>
          <SectionHeading title="Opportunities" />
          <OpportunityList opportunities={opportunities.data ?? []} />
        </section>
        <section>
          <SectionHeading title="Evidence Registry" />
          <EvidenceList evidenceItems={(evidence.data ?? []).slice(0, 8)} />
        </section>
        <section>
          <SectionHeading title="Connector Refresh Runs" />
          <ConnectorRefreshRunList runs={(connectorRefreshRuns.data ?? []).slice(0, 8)} />
        </section>
        <section>
          <SectionHeading title="Actions" />
          <ActionList actions={actions.data ?? []} />
        </section>
        <section>
          <SectionHeading title="Expert Rules" />
          <ExpertRuleList rules={mappedRules} />
        </section>
        <section>
          <SectionHeading title="Connector Status" />
          <ConnectorGrid connectors={connectors.data ?? []} />
        </section>
      </div>
    </main>
  );
}

function expertRulesForRoute(routeName: string, rules: ExpertRule[]): ExpertRule[] {
  const domains = routeExpertDomains(routeName);
  if (domains.length === 0) return rules;
  return rules.filter((rule) => domains.includes(rule.domain));
}

function routeExpertDomains(routeName: string): string[] {
  if (routeName.includes("ads-doctor")) return ["ads", "analytics", "merchant"];
  if (routeName.includes("seo-gsc")) return ["seo", "analytics", "content"];
  if (routeName.includes("ahrefs")) return ["seo", "content"];
  if (routeName.includes("localo")) return ["local"];
  if (routeName.includes("merchant")) return ["merchant", "ads"];
  if (routeName.includes("content")) return ["content", "seo"];
  if (routeName.includes("social")) return ["social", "content"];
  if (routeName.includes("ga4")) return ["analytics"];
  return [];
}

function DetailSurface({ kind }: { kind: "actions" | "opportunities" | "workflows" | "evidence" }) {
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const id = params.actionId ?? params.opportunityId ?? params.workflowId ?? params.evidenceId ?? "";
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (actions.isLoading || opportunities.isLoading || evidence.isLoading) return <LoadingBand />;
  if (actions.error || opportunities.error || evidence.error) return <ErrorState />;

  if (kind === "actions") {
    const action = (actions.data ?? []).find((item) => item.id === id);
    if (action) return <ActionDetail action={action} />;
  }
  if (kind === "opportunities") {
    const opportunity = (opportunities.data ?? []).find((item) => item.id === id);
    if (opportunity) return <OpportunityDetail opportunity={opportunity} />;
  }
  if (kind === "evidence") {
    const evidenceItem = (evidence.data ?? []).find((item) => item.id === id);
    if (evidenceItem) return <EvidenceDetail evidence={evidenceItem} />;
  }
  return <GenericSurface routeName={`/${kind}/${id}`} />;
}

function ActionDetail({ action }: { action: ActionObject }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{action.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={action.status} />
        <StatusBadge value={action.validation_status} />
        <StatusBadge value={action.risk} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Dowody i diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
        <div className="mt-4 text-xs text-slate-600">
          <LinkedTraceLine label="Dowody" values={action.evidence_ids} kind="evidence" />
        </div>
        <ActionValidationControls action={action} />
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd payloadu" />
        <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Historia audytu" />
        {action.audit_events.length === 0 ? (
          <p className="text-sm text-slate-600">Brak zapisanych zdarzeń audytu.</p>
        ) : (
          <div className="grid gap-3">
            {action.audit_events.map((event) => (
              <div key={event.id} className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium">{event.event_type}</div>
                <div className="mt-1 text-slate-600">{event.summary}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function EvidenceDetail({ evidence }: { evidence: Evidence }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="break-words text-2xl font-semibold tracking-normal">{evidence.id}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={evidence.source_connector} />
        <StatusBadge value={evidence.source_type} />
        <StatusBadge value={evidence.freshness.state} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podsumowanie dowodu" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Źródło: {evidence.source_connector}</div>
          <div>Typ źródła: {evidence.source_type}</div>
          <div>ID źródła: {evidence.source_id}</div>
          <div>Zebrano: {evidence.collected_at}</div>
          <div>Świeżość: {evidence.freshness.state}</div>
          <div>Referencja raw: {evidence.raw_ref ?? "brak"}</div>
        </div>
      </section>
    </main>
  );
}

function OpportunityDetail({ opportunity }: { opportunity: Opportunity }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{opportunity.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={opportunity.domain} />
        <StatusBadge value={opportunity.risk} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Dowody: {opportunity.evidence_ids.join(", ")}</div>
          <div>Źródła: {opportunity.source_connectors.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Surowe metryki" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">Brak realnych metric facts.</p>
        ) : (
          <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(opportunity.metrics, null, 2)}
          </pre>
        )}
      </section>
    </main>
  );
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function MetricTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="min-w-24 rounded-md border border-line bg-white px-3 py-2">
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-slate-500">{label}</div>
    </div>
  );
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        WILQ API is not reachable.
      </div>
    </main>
  );
}

const rootRoute = createRootRoute({ component: Shell });
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: CommandCenter
});
const commandCenterRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/command-center",
  component: CommandCenter
});
const opportunitiesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/opportunities",
  component: OpportunitiesSurface
});
const opportunityDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/opportunities/$opportunityId",
  component: () => <DetailSurface kind="opportunities" />
});
const actionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/actions",
  component: ActionsSurface
});
const workflowsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workflows",
  component: WorkflowsSurface
});
const actionDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/actions/$actionId",
  component: () => <DetailSurface kind="actions" />
});
const workflowDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workflows/$workflowId",
  component: () => <DetailSurface kind="workflows" />
});
const evidenceDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/evidence/$evidenceId",
  component: () => <DetailSurface kind="evidence" />
});

const generatedRoutes = operatingRoutes.map((path) =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => {
      if (path === "/ads-doctor") {
        return <AdsDoctorSurface />;
      }
      if (path === "/ga4") {
        return <Ga4DiagnosticSurface />;
      }
      if (path === "/localo") {
        return <LocaloDiagnosticSurface />;
      }
      if (path === "/ahrefs") {
        return <AhrefsDiagnosticSurface />;
      }
      if (path === "/merchant") {
        return <MerchantDiagnosticSurface />;
      }
      if (path === "/seo-gsc" || path === "/content-planner") {
        return <ContentDiagnosticSurface title={briefSurfaceConfigs[path].title} />;
      }
      const briefConfig = briefSurfaceConfigs[path];
      return briefConfig ? (
        <BriefWorkflowSurface config={briefConfig} />
      ) : (
        <GenericSurface routeName={path} />
      );
    }
  })
);

const routeTree = rootRoute.addChildren([
  indexRoute,
  commandCenterRoute,
  opportunitiesRoute,
  opportunityDetailRoute,
  actionsRoute,
  workflowsRoute,
  actionDetailRoute,
  workflowDetailRoute,
  evidenceDetailRoute,
  ...generatedRoutes
]);

export function createWilqRouter({
  initialPath,
  defaultPendingMinMs
}: {
  initialPath?: string;
  defaultPendingMinMs?: number;
} = {}) {
  return createRouter({
    routeTree,
    ...(initialPath
      ? { history: createMemoryHistory({ initialEntries: [initialPath] }) }
      : {}),
    ...(defaultPendingMinMs === undefined ? {} : { defaultPendingMinMs })
  });
}

export const router = createWilqRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function App({
  client = queryClient,
  appRouter = router
}: {
  client?: QueryClient;
  appRouter?: typeof router;
}) {
  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={appRouter} />
    </QueryClientProvider>
  );
}
