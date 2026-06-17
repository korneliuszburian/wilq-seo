import {
  QueryClient,
  QueryClientProvider,
  useQuery,
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
  ConnectorRefreshRun,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  getActions,
  getCommandCenter,
  getConnectorRefreshRuns,
  getConnectors,
  getEvidence,
  getExpertRules,
  getKnowledgeCards,
  getKnowledgePlaybooks,
  getMarketingBrief,
  getMetricFacts,
  getMetricStoreStatus,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows,
  KnowledgeCard,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MetricFact,
  MetricStoreStatus,
  Opportunity,
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
            {facts.slice(0, 8).map((fact, index) => (
              <div key={`${fact.evidence_id}-${fact.name}-${index}`} className="rounded border border-line p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{fact.name}</span>
                  <span className="text-sm font-semibold">{formatMetricFactValue(fact)}</span>
                </div>
                <div className="mt-2 text-xs text-slate-600">
                  {fact.source_connector} / {fact.period}
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
    queryKey: ["metric-facts", 24],
    queryFn: () => getMetricFacts(24)
  });
  const metricStoreStatus = useQuery({
    queryKey: ["metric-store-status"],
    queryFn: getMetricStoreStatus
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

const merchantConnectorIds = ["google_merchant_center", "merchant_center"];

function MerchantSurface() {
  const marketingBrief = useQuery({
    queryKey: ["marketing-brief"],
    queryFn: getMarketingBrief
  });

  if (marketingBrief.isLoading) return <LoadingBand />;
  if (marketingBrief.error || !marketingBrief.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/marketing/brief. Merchant nie może pokazać rekomendacji bez WILQ API." />
      </main>
    );
  }

  const brief = marketingBrief.data;
  const allItems = brief.sections.flatMap((section) => section.items);
  const merchantItems = allItems
    .filter((item) => itemTouchesMerchant(item))
    .sort((left, right) => right.priority - left.priority);
  const merchantRecommendations = merchantItems.filter((item) => item.kind === "recommendation");
  const merchantBlockers = merchantItems.filter((item) => item.kind === "blocker");
  const merchantMetricFacts = brief.top_metric_facts.filter((fact) =>
    merchantConnectorIds.includes(fact.source_connector)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Merchant Center</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Widok feed/product oparty o WILQ MarketingBrief. Nie pokazuje rekomendacji, jeżeli
            brakuje evidence z Merchant Center albo zweryfikowanego ActionObject.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Rekomendacje" value={merchantRecommendations.length} />
          <MetricTile label="Blockery" value={merchantBlockers.length} />
          <MetricTile label="Metric facts" value={merchantMetricFacts.length} />
        </div>
      </div>

      <div className="grid gap-6">
        {merchantItems.length === 0 ? (
          <BlockerNotice message="Brak Merchant evidence w /api/marketing/brief. Uruchom read-only refresh Merchant Center, zanim WILQ zaproponuje zmiany feedu albo produktu." />
        ) : (
          <section>
            <SectionHeading title="Feed/Product Focus" />
            <div className="grid gap-3 xl:grid-cols-2">
              {merchantItems.map((item) => (
                <MarketingBriefCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        )}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
              <ShieldAlert aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                Safety Gate
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Zmiana feedu wymaga payload preview, walidacji ActionObject i audit eventu. Ten
                ekran jest read-only, dopóki WILQ API nie wystawi poprawnego action candidate.
              </p>
            </div>
          </div>
          <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <TraceLine label="Evidence" values={uniqueValues(merchantItems.flatMap((item) => item.evidence_ids))} />
            <TraceLine label="Źródła" values={uniqueValues(merchantItems.flatMap((item) => item.source_connectors))} />
            <TraceLine label="Akcje" values={uniqueValues(merchantItems.flatMap((item) => item.action_ids))} />
          </div>
          {merchantMetricFacts.length > 0 ? <MetricFactChips facts={merchantMetricFacts.slice(0, 6)} /> : null}
        </section>
      </div>
    </main>
  );
}

function itemTouchesMerchant(item: MarketingBriefItem) {
  return (
    item.source_connectors.some((connector) => merchantConnectorIds.includes(connector)) ||
    item.id.includes("merchant") ||
    item.title.toLowerCase().includes("merchant")
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
  component: () => <GenericSurface routeName="/opportunities" />
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
  component: () => <GenericSurface routeName="/workflows" />
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
    component: () => (path === "/merchant" ? <MerchantSurface /> : <GenericSurface routeName={path} />)
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
