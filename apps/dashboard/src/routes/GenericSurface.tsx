import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { FileJson } from "lucide-react";
import { useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  getConnectors,
  getKnowledgeCards,
  getKnowledgeSourceFacts,
  getKnowledgeSourceMaterials,
  getKnowledgeSourceMaterialReadiness,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  getWorkflowRuns,
  getWorkflows,
  type ConnectorStatus,
  type Workflow,
  type WorkflowRun
} from "../lib/api";
import {
  compactRouteConfig,
  type CompactRouteConfig
} from "./CompactRoutePanel";
import { ErrorState } from "./ErrorStates";
import {
  GenericSurfaceSections,
  type GenericRouteKind
} from "./GenericSurfaceSections";

export { approvedKnowledgeFactCount } from "./KnowledgeSections";

export function GenericSurface({ routeName }: { routeName: string }) {
  const compactRoute = compactRouteConfig(routeName);
  const routeKind = genericRouteKind(routeName, compactRoute);
  const [showKnowledgeMap] = useState(false);
  const [showKnowledgeCards, setShowKnowledgeCards] = useState(false);
  const [showKnowledgePlaybooks, setShowKnowledgePlaybooks] = useState(false);
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
    enabled: routeKind === "settings" || routeKind === "system"
  });
  const workflows = useQuery({
    queryKey: ["workflows"],
    queryFn: getWorkflows,
    enabled: routeKind === "workflow" || routeKind === "system"
  });
  const workflowRuns = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: getWorkflowRuns,
    enabled: routeKind === "workflow" || routeKind === "system"
  });
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-operating-map"],
    queryFn: getKnowledgeOperatingMap,
    enabled: routeKind === "knowledge"
  });
  const knowledgeCards = useQuery({
    queryKey: ["knowledge-cards"],
    queryFn: getKnowledgeCards,
    enabled: routeKind === "knowledge" && showKnowledgeCards
  });
  const knowledgeSourceFacts = useQuery({
    queryKey: ["knowledge-source-facts"],
    queryFn: getKnowledgeSourceFacts,
    enabled: routeKind === "knowledge"
  });
  const knowledgeSourceMaterials = useQuery({
    queryKey: ["knowledge-source-materials"],
    queryFn: getKnowledgeSourceMaterials,
    enabled: routeKind === "knowledge"
  });
  const knowledgeSourceMaterialReadiness = useQuery({
    queryKey: ["knowledge-source-material-readiness"],
    queryFn: getKnowledgeSourceMaterialReadiness,
    enabled: routeKind === "knowledge"
  });
  const playbooks = useQuery({
    queryKey: ["knowledge-playbooks"],
    queryFn: getKnowledgePlaybooks,
    enabled: routeKind === "knowledge" && showKnowledgePlaybooks
  });
  if (isGenericSurfaceLoading(routeKind, connectors, workflows, workflowRuns)) {
    return <LoadingBand />;
  }
  if (hasGenericSurfaceError(routeKind, connectors, workflows, workflowRuns)) {
    return <ErrorState />;
  }

  const header = genericSurfaceHeader(routeKind, compactRoute);
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <SurfaceHeader title={header.title} description={header.description} />
      <GenericSurfaceSections
        routeKind={routeKind}
        compactRoute={compactRoute}
        connectors={connectors.data ?? []}
        workflows={workflows.data ?? []}
        workflowRuns={workflowRuns.data ?? []}
        knowledgeMap={knowledgeMap}
        knowledgeCards={knowledgeCards}
        knowledgeSourceFacts={knowledgeSourceFacts}
        knowledgeSourceMaterials={knowledgeSourceMaterials}
        knowledgeSourceMaterialReadiness={knowledgeSourceMaterialReadiness}
        playbooks={playbooks}
        showKnowledgeMap={showKnowledgeMap}
        showKnowledgeCards={showKnowledgeCards}
        setShowKnowledgeCards={setShowKnowledgeCards}
        showKnowledgePlaybooks={showKnowledgePlaybooks}
        setShowKnowledgePlaybooks={setShowKnowledgePlaybooks}
      />
    </main>
  );
}

function genericRouteKind(
  routeName: string,
  compactRoute: CompactRouteConfig | undefined
): GenericRouteKind {
  if (routeName.startsWith("/knowledge")) return "knowledge";
  if (routeName.startsWith("/workflows")) return "workflow";
  if (routeName.startsWith("/settings")) return "settings";
  if (routeName.startsWith("/system")) return "system";
  if (compactRoute) return "compact";
  return "generic";
}

function isGenericSurfaceLoading(
  routeKind: GenericRouteKind,
  connectors: UseQueryResult<ConnectorStatus[]>,
  workflows: UseQueryResult<Workflow[]>,
  workflowRuns: UseQueryResult<WorkflowRun[]>
) {
  if (routeKind === "settings") return connectors.isLoading;
  if (routeKind === "system") return connectors.isLoading || workflows.isLoading || workflowRuns.isLoading;
  if (routeKind === "workflow") return workflows.isLoading || workflowRuns.isLoading;
  return false;
}

function hasGenericSurfaceError(
  routeKind: GenericRouteKind,
  connectors: UseQueryResult<ConnectorStatus[]>,
  workflows: UseQueryResult<Workflow[]>,
  workflowRuns: UseQueryResult<WorkflowRun[]>
) {
  if (routeKind === "settings") return Boolean(connectors.error);
  if (routeKind === "system") return Boolean(connectors.error || workflows.error || workflowRuns.error);
  if (routeKind === "workflow") return Boolean(workflows.error || workflowRuns.error);
  return false;
}

function genericSurfaceHeader(
  routeKind: GenericRouteKind,
  compactRoute: CompactRouteConfig | undefined
) {
  if (routeKind === "knowledge") {
    return {
      title: "Źródła i wiedza",
      description:
        "Najpierw realne materiały Ekologusa i fakty z ich śladem. Karty operacyjne są wtórne i nie zastępują źródła."
    };
  }
  if (routeKind === "settings") {
    return {
      title: "Źródła",
      description:
        "Zdrowie źródeł, aktualność danych i dostęp wpływają na jakość decyzji."
    };
  }
  if (routeKind === "system") {
    return {
      title: "System",
      description:
        "Przegląd audytowy: status procesów, uruchomienia Codex, historia operatora i reguły bezpieczeństwa."
    };
  }
  return {
    title: compactRoute?.title ?? "Widok WILQ",
    description: "Powierzchnia WILQ z dowodami, źródłami danych i stanem akcji."
  };
}

function SurfaceHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>
      <FileJson aria-hidden="true" className="text-action" size={28} />
    </div>
  );
}
