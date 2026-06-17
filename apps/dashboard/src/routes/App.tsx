import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  useParams
} from "@tanstack/react-router";
import { AlertCircle, CheckCircle2, FileJson, RefreshCw } from "lucide-react";

import {
  ActionObject,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  getActions,
  getCommandCenter,
  getConnectors,
  getEvidence,
  getExpertRules,
  getKnowledgeCards,
  getKnowledgePlaybooks,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows,
  KnowledgeCard,
  MarketingPlaybook,
  Opportunity,
  WorkflowRun
} from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { Shell } from "../components/Shell";

const queryClient = new QueryClient();

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

function CommandCenter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;

  const todaysMoves = data.sections.todays_moves ?? [];

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

      <section className="mb-8">
        <SectionHeading title="Today's Moves" />
        <OpportunityList opportunities={todaysMoves} />
      </section>

      <section className="mb-8">
        <SectionHeading title="Connector Health" />
        <ConnectorGrid connectors={data.connector_health} />
      </section>

      <section>
        <SectionHeading title="Active Actions" />
        <ActionList actions={data.active_actions} />
      </section>
    </main>
  );
}

function GenericSurface({ routeName }: { routeName: string }) {
  const connectors = useQuery({ queryKey: ["connectors"], queryFn: getConnectors });
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

function DetailSurface({ kind }: { kind: "actions" | "opportunities" | "workflows" }) {
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const id = params.actionId ?? params.opportunityId ?? params.workflowId ?? "";
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });

  if (actions.isLoading || opportunities.isLoading) return <LoadingBand />;
  if (actions.error || opportunities.error) return <ErrorState />;

  if (kind === "actions") {
    const action = (actions.data ?? []).find((item) => item.id === id);
    if (action) return <ActionDetail action={action} />;
  }
  if (kind === "opportunities") {
    const opportunity = (opportunities.data ?? []).find((item) => item.id === id);
    if (opportunity) return <OpportunityDetail opportunity={opportunity} />;
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
        <div className="mt-4 text-xs text-slate-600">Evidence: {action.evidence_ids.join(", ")}</div>
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

const generatedRoutes = operatingRoutes.map((path) =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => <GenericSurface routeName={path} />
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
  ...generatedRoutes
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
