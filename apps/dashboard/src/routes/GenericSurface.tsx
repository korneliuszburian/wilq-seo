import { useQuery } from "@tanstack/react-query";
import { FileJson } from "lucide-react";

import {
  ExpertRule,
  getActions,
  getConnectorRefreshRuns,
  getConnectors,
  getEvidence,
  getExpertRules,
  getKnowledgeCards,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows
} from "../lib/api";
import { LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import {
  KnowledgeCardList,
  KnowledgeOperatingMapPanel,
  PlaybookList
} from "./KnowledgePanels";
import {
  ActionList,
  ConnectorGrid,
  ConnectorRefreshRunList,
  EvidenceList,
  ExpertRuleList,
  OpportunityList
} from "./RegistryPanels";
import { WorkflowRunList } from "./WorkflowPanels";

export function GenericSurface({ routeName }: { routeName: string }) {
  const isKnowledgeRoute = routeName.startsWith("/knowledge");
  const isWorkflowRoute = routeName.startsWith("/workflows");
  const isSettingsRoute = routeName.startsWith("/settings");
  const shouldLoadGenericRegistries = !isKnowledgeRoute && !isSettingsRoute;
  const shouldLoadConnectorStatus = shouldLoadGenericRegistries || isSettingsRoute;
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
    enabled: shouldLoadConnectorStatus
  });
  const connectorRefreshRuns = useQuery({
    queryKey: ["connector-refresh-runs"],
    queryFn: getConnectorRefreshRuns,
    enabled: shouldLoadGenericRegistries
  });
  const opportunities = useQuery({
    queryKey: ["opportunities"],
    queryFn: getOpportunities,
    enabled: shouldLoadGenericRegistries
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
    enabled: shouldLoadGenericRegistries
  });
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: getEvidence,
    enabled: shouldLoadGenericRegistries
  });
  const workflows = useQuery({
    queryKey: ["workflows"],
    queryFn: getWorkflows,
    enabled: shouldLoadGenericRegistries || isWorkflowRoute
  });
  const workflowRuns = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: getWorkflowRuns,
    enabled: shouldLoadGenericRegistries || isWorkflowRoute
  });
  const expertRules = useQuery({
    queryKey: ["expert-rules"],
    queryFn: getExpertRules,
    enabled: shouldLoadGenericRegistries
  });
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
    : isSettingsRoute
      ? "Ustawienia"
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
              : isSettingsRoute
                ? "Status dostępu do źródeł WILQ. Braki credentiali pokazujemy nazwami pól, bez wartości sekretów."
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
        {isSettingsRoute ? (
          <section>
            <SectionHeading title="Status connectorów" />
            <ConnectorGrid connectors={connectors.data ?? []} />
          </section>
        ) : null}
        {shouldLoadGenericRegistries ? (
          <>
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
          </>
        ) : null}
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

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
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
