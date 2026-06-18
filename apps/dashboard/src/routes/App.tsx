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
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileJson,
  FileText,
  MapPin,
  Megaphone,
  RefreshCw,
  Search,
  ShieldAlert,
  WalletCards,
  type LucideIcon
} from "lucide-react";

import {
  ActionObject,
  ActionApplyResult,
  ActionValidationResult,
  AdsDiagnosticsResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  ContentDiagnosticsResponse,
  Evidence,
  ExpertRule,
  Ga4DiagnosticsResponse,
  getActions,
  getAdsDiagnostics,
  getCommandCenter,
  getContentDiagnostics,
  getConnectorRefreshRuns,
  getConnectors,
  getEvidence,
  getExpertRules,
  getGa4Diagnostics,
  getKnowledgeCards,
  getKnowledgePlaybooks,
  getMarketingBrief,
  getMerchantDiagnostics,
  getMetricFacts,
  getMetricStoreStatus,
  getOpportunities,
  getTacticalQueue,
  applyAction,
  validateAction,
  getWorkflowRuns,
  getWorkflows,
  KnowledgeCard,
  CommandCenterResponse,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MerchantDiagnosticsResponse,
  MetricFact,
  MetricStoreStatus,
  Opportunity,
  TacticalQueueResponse,
  Workflow,
  WorkflowRun
} from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { Shell } from "../components/Shell";

export function createWilqQueryClient(config?: QueryClientConfig): QueryClient {
  return new QueryClient(config);
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
      Loading WILQ API state
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
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Evidence: {opportunity.evidence_ids.join(", ")}</div>
            <div>Source: {opportunity.source_connectors.join(", ")}</div>
            <div>Rules: {opportunity.expert_rule_ids.slice(0, 3).join(", ") || "none"}</div>
            <div>Playbooks: {opportunity.playbook_ids.slice(0, 2).join(", ") || "none"}</div>
          </div>
          {opportunity.is_fixture ? (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
              <AlertCircle aria-hidden="true" size={15} />
              Seed state, not real Ekologus performance data
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function EvidenceList({ evidenceItems }: { evidenceItems: Evidence[] }) {
  if (evidenceItems.length === 0) {
    return <p className="text-sm text-slate-600">No evidence records are available yet.</p>;
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
    return <p className="text-sm text-slate-600">No connector refresh runs yet.</p>;
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
            <div>Vendor data: {run.vendor_data_collected ? "yes" : "no"}</div>
            <div>External call: {run.external_call_attempted ? "yes" : "no"}</div>
            <div>Evidence: {run.evidence_ids.join(", ")}</div>
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
            <div>Evidence: {action.evidence_ids.join(", ")}</div>
            <div>Audit events: {action.audit_events.length}</div>
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
    return <p className="text-sm text-slate-600">No expert rules mapped to this surface yet.</p>;
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
            {rule.requires_evidence ? <StatusBadge value="evidence required" /> : null}
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{rule.output_contract}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Anchor: {rule.source_anchor}</div>
            <div>Actions: {rule.recommended_actions.slice(0, 3).join(", ") || "none"}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

function WorkflowRunList({ runs }: { runs: WorkflowRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-600">No persisted workflow runs yet.</p>;
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
            <div>Evidence: {run.output.evidence_ids.length}</div>
            <div>Actions: {run.output.action_ids.length}</div>
            <div>Errors: {run.output.errors.length}</div>
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
    return <p className="text-sm text-slate-600">No machine-readable playbooks yet.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {playbooks.map((playbook) => (
        <article key={playbook.id} className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold">{playbook.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{playbook.output_contract}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Evidence: {playbook.required_evidence.slice(0, 4).join(", ")}</div>
            <div>Actions: {playbook.maps_to_action_types.slice(0, 3).join(", ")}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

type OperatingDecisionSection = {
  key: string;
  title: string;
  description: string;
  emptyMessage: string;
  icon: LucideIcon;
};

const operatingDecisionSections: OperatingDecisionSection[] = [
  {
    key: "money_leaks",
    title: "Budżet i ryzyko wydatków",
    description: "Ads, Merchant i kampanie, które mogą palić budżet albo wymagają świeżych danych.",
    emptyMessage: "Brak potwierdzonych money leaks. WILQ potrzebuje live Ads/Merchant evidence.",
    icon: WalletCards
  },
  {
    key: "traffic_wins",
    title: "Szanse na ruch",
    description: "GSC, GA4 i SEO okazje, które mogą podnieść wartościowy ruch.",
    emptyMessage: "Brak potwierdzonych traffic wins. Uruchom read-only refresh GSC/GA4/Ahrefs.",
    icon: Search
  },
  {
    key: "content_to_rewrite",
    title: "Treści do poprawy",
    description: "Strony i wpisy, które mają dostać refresh, merge albo zmianę intentu.",
    emptyMessage: "Brak kolejki rewrite. Potrzebne są GSC query/page, GA4 landing i WordPress inventory.",
    icon: FileText
  },
  {
    key: "content_to_create",
    title: "Treści do stworzenia",
    description: "Nowe landing pages, artykuły i tematy wynikające z Ads/GSC/Ahrefs/Merchant.",
    emptyMessage: "Brak evidence-backed briefów. WILQ nie tworzy tematów bez danych źródłowych.",
    icon: ClipboardCheck
  },
  {
    key: "local_visibility_moves",
    title: "Widoczność lokalna",
    description: "Localo/GBP ruchy i blockery widoczności lokalnej.",
    emptyMessage: "Brak lokalnych rekomendacji. Potrzebne są świeże dane Localo/GBP.",
    icon: MapPin
  },
  {
    key: "social_queue",
    title: "Social queue",
    description: "LinkedIn/Facebook kandydaci i permission blockery.",
    emptyMessage: "Brak postów do przygotowania. Social wymaga evidence-backed claimów i uprawnień.",
    icon: Megaphone
  }
];

function DecisionSection({
  section,
  opportunities
}: {
  section: OperatingDecisionSection;
  opportunities: Opportunity[];
}) {
  const Icon = section.icon;

  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <Icon aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            {section.title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">{section.description}</p>
        </div>
      </div>
      {opportunities.length === 0 ? (
        <BlockerNotice message={section.emptyMessage} />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {opportunities.map((opportunity) => (
            <DecisionOpportunityCard key={opportunity.id} opportunity={opportunity} />
          ))}
        </div>
      )}
    </section>
  );
}

function DecisionOpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const readinessOnly =
    opportunity.metrics.length === 0 ||
    opportunity.metrics.every((metric) => metric.name === "connector_configured");

  return (
    <article className="rounded-md border border-line bg-white p-4">
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
      <p className="mt-3 text-sm font-medium text-ink">{opportunity.recommended_action}</p>
      {readinessOnly ? (
        <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-wait">
          To jeszcze nie jest rekomendacja performance. WILQ ma tylko readiness/status i czeka na
          vendor_read z realnymi metrykami.
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine label="Evidence" values={opportunity.evidence_ids} />
        <TraceLine label="Źródła" values={opportunity.source_connectors} />
        <TraceLine label="Reguły" values={opportunity.expert_rule_ids.slice(0, 3)} />
        <TraceLine label="Akcje" values={opportunity.action_ids} empty="brak gotowej akcji" />
      </div>
      {opportunity.metrics.length > 0 ? (
        <MetricFactChips facts={opportunity.metrics.slice(0, 4)} />
      ) : null}
    </article>
  );
}

function ActionQueue({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak kandydatów ActionObject. Najpierw potrzebne są evidence-backed opportunities." />
    );
  }

  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ShieldAlert aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Kandydaci działań API
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Każdy write path wymaga walidacji ActionObject i audytu przed wykonaniem.
          </p>
        </div>
      </div>
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
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={action.validation_status} />
              <StatusBadge value={action.risk} />
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <TraceLine label="ActionObject" values={[action.id]} />
              <TraceLine label="Evidence" values={action.evidence_ids} />
            </div>
          </article>
        ))}
      </div>
    </section>
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
      <SectionHeading title="ActionObject focus" />
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
                Apply zablokowany: ten ActionObject jest prepare-only. Najpierw walidacja,
                payload preview i jawna zgoda operatora.
              </div>
            ) : null}
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <LinkedTraceLine label="ActionObject" values={[action.id]} kind="actions" />
              <LinkedTraceLine label="Evidence" values={action.evidence_ids} kind="evidence" />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionValidationControls action={action} />
            <div className="mt-3">
              <div className="mb-1 text-xs font-semibold uppercase tracking-normal text-slate-500">
                Payload preview
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

function ConnectorBlockers({ connectors }: { connectors: ConnectorStatus[] }) {
  const blockers = connectors.filter(
    (connector) => connector.status !== "configured" || connector.freshness.state !== "fresh"
  );

  return (
    <section>
      <SectionHeading title="Blockery i świeżość źródeł" />
      {blockers.length === 0 ? (
        <div className="rounded-md border border-signal/30 bg-signal/10 p-4 text-sm text-signal">
          Brak znanych blockerów connectorów.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {blockers.slice(0, 9).map((connector) => (
            <article key={connector.id} className="rounded-md border border-line bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">{connector.label}</h3>
                  <p className="mt-1 text-xs text-slate-500">{connector.id}</p>
                </div>
                <StatusBadge value={connector.status} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-600">
                Freshness: {connector.freshness.state}
                {connector.freshness.notes ? ` - ${connector.freshness.notes}` : ""}
              </p>
              {connector.missing_credentials.length > 0 ? (
                <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
                  Brakuje: {connector.missing_credentials.join(", ")}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function MetricInventory({
  facts,
  status,
  isLoading,
  isError
}: {
  facts: MetricFact[];
  status?: MetricStoreStatus;
  isLoading: boolean;
  isError: boolean;
}) {
  const visibleFacts = [...facts].sort((a, b) => {
    const aDimensions = Object.keys(a.dimensions ?? {}).length;
    const bDimensions = Object.keys(b.dimensions ?? {}).length;
    return bDimensions - aDimensions;
  });

  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <Database aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Realne metric facts zapisane lokalnie
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Dane z connector refreshy w DuckDB; to nie zastępuje freshness ani evidence IDs.
          </p>
        </div>
      </div>
      {isError ? (
        <BlockerNotice message="Nie udało się odczytać /api/metrics. Dashboard nie może udawać lokalnych metryk." />
      ) : isLoading ? (
        <div className="rounded-md border border-line bg-white p-4 text-sm text-slate-600">
          Ładowanie metric store...
        </div>
      ) : facts.length === 0 ? (
        <BlockerNotice message="Brak metric facts. Uruchom vendor_read dla skonfigurowanych connectorów." />
      ) : (
        <div className="rounded-md border border-line bg-white p-4">
          <div className="mb-4 grid gap-3 text-sm sm:grid-cols-3">
            <MetricTile label="Facts" value={status?.metric_fact_count ?? facts.length} />
            <MetricTile label="Connectors" value={status?.connector_count ?? 0} />
            <MetricTile label="Refresh runs" value={status?.refresh_run_count ?? 0} />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {visibleFacts.slice(0, 8).map((fact, index) => (
              <div key={`${fact.evidence_id}-${fact.name}-${index}`} className="rounded border border-line p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{fact.name}</span>
                  <span className="text-sm font-semibold">{formatMetricFactValue(fact)}</span>
                </div>
                <div className="mt-2 text-xs text-slate-600">
                  {fact.source_connector} / {fact.period}
                </div>
                {Object.keys(fact.dimensions ?? {}).length > 0 ? (
                  <div className="mt-1 text-xs text-slate-600">
                    Wymiar: {formatMetricDimensions(fact)}
                  </div>
                ) : null}
                <div className="mt-1 text-xs text-slate-600">
                  {formatMetricDelta(fact)} / {fact.freshness_label ?? fact.freshness_state ?? "unknown"}
                </div>
                <div className="mt-1 break-words text-xs text-slate-500">
                  Evidence: {fact.evidence_id}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function MetricFactChips({ facts }: { facts: MetricFact[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {facts.map((fact) => (
        <span
          key={`${fact.name}-${fact.evidence_id}`}
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

function MarketingBriefPanel({
  brief,
  isLoading,
  isError
}: {
  brief?: MarketingBrief;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isError) {
    return (
      <BlockerNotice message="Nie udało się odczytać /api/marketing/brief. Command Center nie może udawać briefu." />
    );
  }
  if (isLoading || !brief) {
    return (
      <div className="rounded-md border border-line bg-white p-4 text-sm text-slate-600">
        Ładowanie dzisiejszego briefu WILQ...
      </div>
    );
  }

  const visibleItems = brief.sections.flatMap((section) => section.items).slice(0, 6);

  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dzisiejszy brief WILQ
          </h2>
          <p className="mt-1 text-sm text-slate-600">{brief.strict_instruction}</p>
        </div>
      </div>
      <div className="rounded-md border border-line bg-white p-4">
        <div className="mb-4 grid gap-3 text-sm sm:grid-cols-4">
          <MetricTile label="Rekomendacje" value={brief.recommendation_count} />
          <MetricTile label="Blockery" value={brief.blocker_count} />
          <MetricTile label="Evidence IDs" value={brief.evidence_ids.length} />
          <MetricTile label="ActionObjects" value={brief.action_ids.length} />
        </div>
        {visibleItems.length === 0 ? (
          <BlockerNotice message="Brief nie ma jeszcze itemów. Uruchom read-only vendor_read dla skonfigurowanych connectorów." />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {visibleItems.map((item) => (
              <MarketingBriefCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function MarketingBriefCard({ item }: { item: MarketingBriefItem }) {
  return (
    <article className="rounded-md border border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {item.kind} / priority {item.priority}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.summary}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      {item.blocker_reason ? (
        <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
          Blocker: {item.blocker_reason}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Evidence" values={item.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
      </div>
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

type TacticalQueueItem = TacticalQueueResponse["items"][number];
type CommandCenterBriefItem = CommandCenterResponse["operator_brief"][number];
type CommandCenterDemoStep = CommandCenterResponse["demo_script"][number];
type CommandCenterActionPlanItem = CommandCenterResponse["action_plan"][number];

function TacticalQueuePanel({
  queue,
  connectorIds,
  limit = 8,
  title = "Kolejka taktyczna WILQ",
  isLoading,
  isError
}: {
  queue?: TacticalQueueResponse;
  connectorIds?: string[];
  limit?: number;
  title?: string;
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

  const items = queue.items
    .filter((item) =>
      connectorIds
        ? item.source_connectors.some((connector) => connectorIds.includes(connector))
        : true
    )
    .slice(0, limit);

  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            {title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">{queue.strict_instruction}</p>
        </div>
      </div>
      {items.length === 0 ? (
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

function TacticalQueueCard({ item }: { item: TacticalQueueItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {item.intent} / priority {item.priority}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Evidence" values={item.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
        <TraceLine label="Blokady claimów" values={item.blocked_claims} />
      </div>
      {Object.keys(item.dimensions).length > 0 ? (
        <div className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-700">
          Wymiar:{" "}
          {Object.entries(item.dimensions)
            .map(([key, value]) => `${key}=${value}`)
            .join(", ")}
        </div>
      ) : null}
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

function DailyOperatorBrief({ data }: { data: CommandCenterResponse }) {
  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dzisiejszy panel operatora
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{data.primary_next_step}</p>
        </div>
      </div>

      <div className="mb-4 grid gap-3 text-sm sm:grid-cols-3">
        <MetricTile label="Taktyki" value={data.tactical_item_count} />
        <MetricTile label="Blockery" value={data.blocker_count} />
        <MetricTile label="Akcje" value={data.active_actions.length} />
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        {data.operator_brief.map((item) => (
          <DailyOperatorBriefCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

function DailyOperatorBriefCard({ item }: { item: CommandCenterBriefItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            priority {item.priority}
          </div>
          <h3 className="mt-1 text-base font-semibold tracking-normal">{item.title}</h3>
        </div>
        <StatusBadge value={item.status} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.summary}</p>
      <p className="mt-2 text-sm font-medium text-ink">{item.next_step}</p>

      {Object.keys(item.metric_tiles).length > 0 ? (
        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
          {Object.entries(item.metric_tiles).map(([label, value]) => (
            <div key={label} className="rounded-md border border-line bg-slate-50 p-2">
              <div className="uppercase tracking-normal text-slate-500">{label}</div>
              <div className="mt-1 font-semibold text-ink">{String(value)}</div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Evidence" values={item.evidence_ids} kind="evidence" />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
        <TraceLine label="Zablokowane claimy" values={item.blocked_claims} />
      </div>

      <a
        href={item.route}
        className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
      >
        Otwórz widok
      </a>
    </article>
  );
}

function MarketerActionPlan({ items }: { items: CommandCenterActionPlanItem[] }) {
  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Plan działań marketera
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Konkretne kroki z WILQ API. Ready oznacza źródło z evidence; blocked oznacza,
            że WILQ celowo blokuje claimy i pokazuje repair path.
          </p>
        </div>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  {item.category} / priority {item.priority}
                </div>
                <h3 className="mt-1 text-base font-semibold tracking-normal">{item.title}</h3>
              </div>
              <StatusBadge value={item.status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{item.why_it_matters}</p>
            <p className="mt-2 text-sm font-medium text-ink">{item.operator_action}</p>
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Źródła" values={item.source_connectors} />
              <LinkedTraceLine label="Evidence" values={item.evidence_ids} kind="evidence" />
              <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
              <TraceLine label="Zablokowane claimy" values={item.blocked_claims} />
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

function MarketerDemoScript({ steps }: { steps: CommandCenterDemoStep[] }) {
  return (
    <section>
      <div className="mb-3 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Demo dla marketera
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Kolejność pokazu z WILQ API: co ekran udowadnia, jaki prompt ma sens i gdzie
            są evidence IDs oraz ActionObjecty.
          </p>
        </div>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {steps.map((step, index) => (
          <article key={step.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  krok {index + 1}
                </div>
                <h3 className="mt-1 text-base font-semibold tracking-normal">{step.label}</h3>
              </div>
              <StatusBadge value={step.status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{step.what_it_proves}</p>
            <p className="mt-2 text-sm font-medium text-ink">{step.operator_prompt}</p>
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Źródłowe karty" values={step.source_item_ids} />
              <LinkedTraceLine label="Evidence" values={step.evidence_ids} kind="evidence" />
              <LinkedTraceLine label="Akcje" values={step.action_ids} kind="actions" empty="brak" />
            </div>
            <a
              href={step.route}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
            >
              Otwórz krok
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function CommandCenter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });
  const marketingBrief = useQuery({
    queryKey: ["marketing-brief"],
    queryFn: getMarketingBrief
  });
  const metricFacts = useQuery({
    queryKey: ["metric-facts", 80],
    queryFn: () => getMetricFacts(80)
  });
  const metricStoreStatus = useQuery({
    queryKey: ["metric-store-status"],
    queryFn: getMetricStoreStatus
  });
  const tacticalQueue = useQuery({
    queryKey: ["tactical-queue"],
    queryFn: getTacticalQueue
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Command Center</h1>
          <p className="mt-1 text-sm text-slate-600">{data.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Connectors" value={data.connector_summary.total} />
          <MetricTile label="Configured" value={data.connector_summary.configured} />
          <MetricTile label="Missing" value={data.connector_summary.missing_credentials} />
        </div>
      </div>

      <div className="grid gap-8">
        <DailyOperatorBrief data={data} />

        <MarketerActionPlan items={data.action_plan} />

        <MarketerDemoScript steps={data.demo_script} />

        <MarketingBriefPanel
          brief={marketingBrief.data}
          isLoading={marketingBrief.isLoading}
          isError={Boolean(marketingBrief.error)}
        />

        <section>
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
              <BarChart3 aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                Priorytety dnia
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Najważniejsze karty z WILQ API. Readiness nie jest jeszcze rekomendacją
                marketingową.
              </p>
            </div>
          </div>
          <OpportunityList opportunities={data.sections.todays_moves ?? []} />
        </section>

        {operatingDecisionSections.map((section) => (
          <DecisionSection
            key={section.key}
            section={section}
            opportunities={data.sections[section.key] ?? []}
          />
        ))}

        <ActionQueue actions={data.active_actions} />

        <TacticalQueuePanel
          queue={tacticalQueue.data}
          isLoading={tacticalQueue.isLoading}
          isError={Boolean(tacticalQueue.error)}
        />

        <MetricInventory
          facts={metricFacts.data ?? []}
          status={metricStoreStatus.data}
          isLoading={metricFacts.isLoading || metricStoreStatus.isLoading}
          isError={Boolean(metricFacts.error || metricStoreStatus.error)}
        />

        <ConnectorBlockers connectors={data.connector_health} />
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
          <h1 className="text-2xl font-semibold tracking-normal">Opportunities</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Lista decyzji z WILQ API. Każda karta musi mieć evidence IDs, źródła i reguły;
            readiness albo seed data nie są jeszcze rekomendacją marketingową.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Karty" value={items.length} />
          <MetricTile label="Live" value={liveItems.length} />
          <MetricTile label="Evidence" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Kolejka decyzji" />
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
          <SectionHeading title="Evidence użyte przez opportunities" />
          <EvidenceList
            evidenceItems={(evidence.data ?? []).filter((item) => evidenceIds.has(item.id)).slice(0, 12)}
          />
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
  const completedRuns = runs.filter((run) => run.status === "completed");
  const workflowEvidenceIds = new Set(runs.flatMap((run) => run.output.evidence_ids));
  const workflowActionIds = new Set(runs.flatMap((run) => run.output.action_ids));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Workflows</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Rejestr automatyzacji WILQ. Workflows uruchamiają API-backed operacje,
            zapisują run state i oddają evidence/action IDs do dashboardu oraz skillsów.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Workflowy" value={(workflows.data ?? []).length} />
          <MetricTile label="Runy" value={runs.length} />
          <MetricTile label="Gotowe" value={completedRuns.length} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Rejestr workflowów" />
          <WorkflowRegistryList workflows={workflows.data ?? []} />
        </section>
        <section>
          <SectionHeading title="Ostatnie uruchomienia" />
          <WorkflowRunList runs={runs} />
        </section>
        <section>
          <SectionHeading title="Wyniki workflowów" />
          <div className="grid gap-3 xl:grid-cols-2">
            <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
              <h3 className="font-semibold text-ink">Evidence z workflowów</h3>
              <LinkedTraceLine
                label="Evidence"
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
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {workflows.map((workflow) => (
        <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold">{workflow.label}</h3>
          <p className="mt-1 break-words text-xs text-slate-500">{workflow.id}</p>
          <p className="mt-3 text-sm leading-6 text-slate-700">{workflow.description}</p>
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
};

const briefSurfaceConfigs: Record<string, BriefSurfaceConfig> = {
  "/ads-doctor": {
    title: "Ads Doctor",
    description:
      "Widok Google Ads oparty o WILQ MarketingBrief. Najpierw pokazuje OAuth/blockery, evidence i ActionObject, dopiero potem diagnozę spendu.",
    focusTitle: "Ads Focus",
    emptyMessage:
      "Brak Google Ads evidence w /api/marketing/brief. WILQ nie pokaże spend/campaign rekomendacji bez odczytu Ads API.",
    safetyTitle: "Spend Safety Gate",
    safetyText:
      "Zmiany kampanii, budżetu, wykluczeń i segmentów wymagają payload preview, walidacji ActionObject i audytu. Do czasu naprawy OAuth widok pokazuje blocker, nie performance claims.",
    connectorIds: ["google_ads"],
    textNeedles: []
  },
  "/ga4": {
    title: "GA4",
    description:
      "Widok analityki zachowania i konwersji oparty o WILQ MarketingBrief. Pokazuje tylko metryki GA4 z evidence IDs.",
    focusTitle: "GA4 Quality Focus",
    emptyMessage:
      "Brak GA4 evidence w /api/marketing/brief. Uruchom read-only refresh GA4, zanim WILQ oceni landing pages albo jakość ruchu.",
    safetyTitle: "Analytics Safety Gate",
    safetyText:
      "GA4 służy do diagnozy jakości ruchu i tracking gaps. WILQ nie traktuje braku danych jako spadku marketingowego bez evidence.",
    connectorIds: ["google_analytics_4"],
    textNeedles: []
  },
  "/seo-gsc": {
    title: "SEO / GSC",
    description:
      "Widok SEO oparty o GSC evidence z WILQ MarketingBrief. Ma prowadzić do kolejki treści, nie do zgadywania tematów.",
    focusTitle: "Search Console Content Focus",
    emptyMessage:
      "Brak GSC evidence w /api/marketing/brief. Uruchom read-only refresh Search Console przed rekomendacją treści.",
    safetyTitle: "SEO Evidence Gate",
    safetyText:
      "Rekomendacje contentowe wymagają query/page evidence, źródła i jasnego następnego kroku. Bez CTR/impressions/clicks WILQ pokazuje blocker.",
    connectorIds: ["google_search_console"],
    textNeedles: []
  },
  "/localo": {
    title: "Localo",
    description:
      "Widok lokalnej widoczności oparty o WILQ readiness i przyszłe Localo MCP evidence. Aktualnie pokazuje blocker OAuth, jeśli brakuje dostępu.",
    focusTitle: "Local Visibility Focus",
    emptyMessage:
      "Brak Localo evidence w /api/marketing/brief. WILQ nie pokaże lokalnych rankingów ani GBP rekomendacji bez Localo access token.",
    safetyTitle: "Local Visibility Safety Gate",
    safetyText:
      "GBP posty i lokalne działania wymagają evidence, payload preview, walidacji ActionObject i audytu. Brak LOCALO_ACCESS_TOKEN jest blockerem, nie metryką.",
    connectorIds: ["localo"],
    textNeedles: []
  },
  "/social-publisher": {
    title: "Social Publisher",
    description:
      "Widok publikacji social oparty o WILQ evidence i permission state. Przy brakach LinkedIn/Facebook pokazuje blockery, nie gotowe posty.",
    focusTitle: "Social Publishing Focus",
    emptyMessage:
      "Brak social evidence w /api/marketing/brief. Skonfiguruj LinkedIn/Facebook credentials przed przygotowaniem post candidates.",
    safetyTitle: "Publishing Safety Gate",
    safetyText:
      "Posty LinkedIn/Facebook muszą bazować na evidence-backed claims i pozostać prepare-only, dopóki permission state, payload preview i audit nie są gotowe.",
    connectorIds: ["linkedin", "facebook"],
    textNeedles: []
  },
  "/content-planner": {
    title: "Content Planner",
    description:
      "Widok planowania treści łączy GSC, GA4, Ahrefs, WordPress i Merchant evidence w jedną kolejkę działań dla polskiego marketera.",
    focusTitle: "Content Growth Focus",
    emptyMessage:
      "Brak content evidence w /api/marketing/brief. WILQ potrzebuje GSC/GA4/Ahrefs/WordPress inventory przed planem treści.",
    safetyTitle: "Content Safety Gate",
    safetyText:
      "Briefy, rewrites i drafty wymagają źródeł, evidence IDs i zgodności z realną ofertą. WILQ nie generuje claimów bez pokrycia w danych.",
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
      "Widok feed/product oparty o WILQ MarketingBrief. Nie pokazuje rekomendacji, jeżeli brakuje evidence z Merchant Center albo zweryfikowanego ActionObject.",
    focusTitle: "Feed/Product Focus",
    emptyMessage:
      "Brak Merchant evidence w /api/marketing/brief. Uruchom read-only refresh Merchant Center, zanim WILQ zaproponuje zmiany feedu albo produktu.",
    safetyTitle: "Feed Safety Gate",
    safetyText:
      "Zmiana feedu wymaga payload preview, walidacji ActionObject i audit eventu. Ten ekran jest read-only, dopóki WILQ API nie wystawi poprawnego action candidate.",
    connectorIds: ["google_merchant_center", "merchant_center"],
    textNeedles: []
  }
};

type AdsDiagnosticSection = AdsDiagnosticsResponse["sections"][number];
type AdsBlockedHandoff = NonNullable<AdsDiagnosticsResponse["blocked_handoff"]>;

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
        <BlockerNotice message="Nie udało się odczytać /api/actions. Ads Doctor nie może pokazać walidacji ani payload preview." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;
  const liveLabel = data.live_data_available ? "live metryki" : "blokada danych";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ads Doctor</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Google Ads z WILQ API. Pokazuje live campaign facts dopiero
            po udanym vendor_read; przy OAuth blockerze pokazuje dokładny powód i bezpieczny
            ActionObject zamiast zmyślać spend, CPA albo ROAS.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Stan" value={data.blocker_count} />
          <MetricTile label="Sekcje" value={data.sections.length} />
          <MetricTile label="Evidence" value={data.evidence_ids.length} />
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
            <StatusBadge value={data.connector.status} />
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {liveLabel}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni refresh: {latestRefresh.status}
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

      <div className="grid gap-4 xl:grid-cols-2">
        {data.sections.map((section) => (
          <AdsDiagnosticCard key={section.id} section={section} />
        ))}
      </div>

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

    </main>
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
        <StatusBadge value={handoff.status} />
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
        <LinkedTraceLine label="Evidence" values={handoff.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={handoff.source_connectors} />
        <LinkedTraceLine label="Akcje" values={handoff.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={handoff.blocked_claims} />
      </div>
    </section>
  );
}

function AdsDiagnosticCard({ section }: { section: AdsDiagnosticSection }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {section.status}
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{section.title}</h2>
        </div>
        <StatusBadge value={section.status} />
      </div>
      <p className="text-sm leading-6 text-slate-700">{section.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{section.diagnosis}</p>
      <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700">
        {section.next_step}
      </div>
      {section.metric_facts.length > 0 ? <MetricFactChips facts={section.metric_facts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Evidence" values={section.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={section.source_connectors} />
        <LinkedTraceLine label="Akcje" values={section.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={section.blocked_claims} />
      </div>
    </section>
  );
}

type MerchantDiagnosticSection = MerchantDiagnosticsResponse["sections"][number];

type ContentDiagnosticSection = ContentDiagnosticsResponse["sections"][number];

type Ga4DiagnosticSection = Ga4DiagnosticsResponse["sections"][number];

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
        <BlockerNotice message="Nie udało się odczytać /api/actions. GA4 route nie może pokazać walidacji ani payload preview." />
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
            Dedykowany widok GA4 z WILQ API. Pokazuje landing/source/campaign behavior,
            WordPress match i tracking blockers bez udawania konwersji, ROAS albo revenue.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Landing groups" value={data.landing_group_count} />
          <MetricTile label="Low engagement" value={data.low_engagement_count} />
          <MetricTile label="WP match" value={data.wordpress_match_count} />
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
            <StatusBadge value={data.connector.status} />
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "live GA4 facts" : "brak live GA4 facts"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni refresh: {latestRefresh.status}
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

      <div className="grid gap-4 xl:grid-cols-2">
        {data.sections.map((section) => (
          <Ga4DiagnosticCard key={section.id} section={section} />
        ))}
      </div>

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
              Analytics Safety Gate
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              GA4 route jest read-only. WILQ może przygotować review jakości ruchu i
              tracking-gap checklist, ale nie może uznać wyniku za problem kampanii bez
              konwersji, kosztów i ActionObject validation.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={data.sections.flatMap((section) => section.blocked_claims)}
        />
      </section>
    </main>
  );
}

function Ga4DiagnosticCard({ section }: { section: Ga4DiagnosticSection }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {section.status}
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{section.title}</h2>
        </div>
        <StatusBadge value={section.status} />
      </div>
      <p className="text-sm leading-6 text-slate-700">{section.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{section.diagnosis}</p>
      <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700">
        {section.next_step}
      </div>
      {section.metric_facts.length > 0 ? <MetricFactChips facts={section.metric_facts} /> : null}
      {section.tactical_items.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {section.tactical_items.slice(0, 4).map((item) => (
            <div key={item.id} className="rounded-md border border-line bg-white p-3 text-xs">
              <div className="font-semibold text-ink">{item.title}</div>
              <div className="mt-1 text-slate-600">{item.diagnosis}</div>
              <TraceLine
                label="Landing"
                values={[
                  item.dimensions.landing_page,
                  item.dimensions.source_medium,
                  item.dimensions.campaign_name
                ].filter(Boolean)}
              />
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Evidence" values={section.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={section.source_connectors} />
        <LinkedTraceLine label="Akcje" values={section.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={section.blocked_claims} />
      </div>
    </section>
  );
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
        <BlockerNotice message="Nie udało się odczytać /api/actions. Content route nie może pokazać walidacji ani payload preview." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestStatuses = data.latest_refreshes.map(
    (refresh) => `${refresh.connector_id}: ${refresh.status}`
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok SEO/content z WILQ API. Łączy GSC query-page matrix,
            WordPress inventory i ActionObjecty, żeby marketer wiedział co odświeżyć,
            połączyć, utworzyć albo zablokować bez duplikowania treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Query/page" value={data.query_page_count} />
          <MetricTile label="WP match" value={data.matched_inventory_count} />
          <MetricTile label="Evidence" value={data.evidence_ids.length} />
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
              {data.live_data_available ? "live content facts" : "brak live content facts"}
            </span>
            {data.connectors.map((connector) => (
              <StatusBadge key={connector.id} value={connector.status} />
            ))}
          </div>
        </div>
        <TraceLine label="Ostatnie refresh" values={latestStatuses} />
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        {data.sections.map((section) => (
          <ContentDiagnosticCard key={section.id} section={section} />
        ))}
      </div>

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
              Content Safety Gate
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować brief, refresh queue i payload preview, ale nie
              publikuje ani nie zmienia WordPress bez walidacji ActionObject, jawnej
              zgody operatora i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={data.sections.flatMap((section) => section.blocked_claims)}
        />
      </section>
    </main>
  );
}

function ContentDiagnosticCard({ section }: { section: ContentDiagnosticSection }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {section.status}
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{section.title}</h2>
        </div>
        <StatusBadge value={section.status} />
      </div>
      <p className="text-sm leading-6 text-slate-700">{section.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{section.diagnosis}</p>
      <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700">
        {section.next_step}
      </div>
      {section.metric_facts.length > 0 ? <MetricFactChips facts={section.metric_facts} /> : null}
      {section.tactical_items.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {section.tactical_items.slice(0, 4).map((item) => (
            <div key={item.id} className="rounded-md border border-line bg-white p-3 text-xs">
              <div className="font-semibold text-ink">{item.title}</div>
              <div className="mt-1 text-slate-600">{item.diagnosis}</div>
              <TraceLine label="Intent" values={[item.intent]} />
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Evidence" values={section.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={section.source_connectors} />
        <LinkedTraceLine label="Akcje" values={section.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={section.blocked_claims} />
      </div>
    </section>
  );
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
        <BlockerNotice message="Nie udało się odczytać /api/actions. Merchant route nie może pokazać walidacji ani payload preview." />
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
            Dedykowany widok feed/product oparty o Merchant Diagnostics z WILQ API.
            Pokazuje live product facts, issue queue i bezpieczne ActionObjecty bez raw
            product dumps i bez obietnic naprawy produktów.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Issues" value={data.issue_count ?? 0} />
          <MetricTile label="Evidence" value={data.evidence_ids.length} />
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
            <StatusBadge value={data.connector.status} />
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "live feed facts" : "brak live feed facts"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni refresh: {latestRefresh.status}
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        {data.sections.map((section) => (
          <MerchantDiagnosticCard key={section.id} section={section} />
        ))}
      </div>

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
              Feed Safety Gate
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Merchant Center pozostaje w trybie review/prepare. WILQ może pokazać
              issue queue, evidence i payload preview, ale nie może zmienić feedu,
              obiecać approval recovery ani wykonać apply bez walidacji i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={data.sections.flatMap((section) => section.blocked_claims)}
        />
      </section>
    </main>
  );
}

function MerchantDiagnosticCard({ section }: { section: MerchantDiagnosticSection }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {section.status}
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{section.title}</h2>
        </div>
        <StatusBadge value={section.status} />
      </div>
      <p className="text-sm leading-6 text-slate-700">{section.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{section.diagnosis}</p>
      <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700">
        {section.next_step}
      </div>
      {section.metric_facts.length > 0 ? <MetricFactChips facts={section.metric_facts} /> : null}
      {section.tactical_items.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {section.tactical_items.slice(0, 3).map((item) => (
            <div key={item.id} className="rounded-md border border-line bg-white p-3 text-xs">
              <div className="font-semibold text-ink">{item.title}</div>
              <div className="mt-1 text-slate-600">{item.diagnosis}</div>
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Evidence" values={section.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={section.source_connectors} />
        <LinkedTraceLine label="Akcje" values={section.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={section.blocked_claims} />
      </div>
    </section>
  );
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
          <MetricTile label="Metric facts" value={metricFacts.length} />
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

        <TacticalQueuePanel
          queue={tacticalQueue.data}
          connectorIds={config.connectorIds}
          limit={6}
          title="Taktyki z WILQ API"
          isLoading={tacticalQueue.isLoading}
          isError={Boolean(tacticalQueue.error)}
        />

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
              label="Evidence"
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
  const isKnowledgeLoading = isKnowledgeRoute && (knowledgeCards.isLoading || playbooks.isLoading);
  const hasKnowledgeError = isKnowledgeRoute && (knowledgeCards.error || playbooks.error);

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

  const title = routeName
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
            API-backed operating surface with evidence, connector and action state.
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
              <SectionHeading title="Knowledge Cards" />
              <KnowledgeCardList cards={knowledgeCards.data ?? []} />
            </section>
            <section>
              <SectionHeading title="Machine-Readable Playbooks" />
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
        <SectionHeading title="Evidence And Diagnosis" />
        <p className="text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
        <div className="mt-4 text-xs text-slate-600">
          <LinkedTraceLine label="Evidence" values={action.evidence_ids} kind="evidence" />
        </div>
        <ActionValidationControls action={action} />
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Payload Preview" />
        <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Audit Timeline" />
        {action.audit_events.length === 0 ? (
          <p className="text-sm text-slate-600">No audit events recorded yet.</p>
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
        <SectionHeading title="Evidence Summary" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Source connector: {evidence.source_connector}</div>
          <div>Source type: {evidence.source_type}</div>
          <div>Source ID: {evidence.source_id}</div>
          <div>Collected at: {evidence.collected_at}</div>
          <div>Freshness: {evidence.freshness.state}</div>
          <div>Raw ref: {evidence.raw_ref ?? "brak"}</div>
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
        <SectionHeading title="Diagnosis" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Evidence: {opportunity.evidence_ids.join(", ")}</div>
          <div>Sources: {opportunity.source_connectors.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Raw Metrics" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">No real metric facts are available yet.</p>
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

function MetricTile({ label, value }: { label: string; value: number }) {
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
  component: () => <GenericSurface routeName="/actions" />
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
