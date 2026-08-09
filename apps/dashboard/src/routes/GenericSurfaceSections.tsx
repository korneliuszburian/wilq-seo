import { type UseQueryResult } from "@tanstack/react-query";

import {
  type ConnectorStatus,
  type KnowledgeCard,
  type KnowledgeSourceFactView,
  type KnowledgeSourceMaterialView,
  type KnowledgeSourceMaterialReadiness,
  type KnowledgeOperatingMapResponse,
  type MarketingPlaybook,
  type Workflow,
  type WorkflowRun
} from "../lib/api";
import {
  CompactRoutePanel,
  type CompactRouteConfig
} from "./CompactRoutePanel";
import { KnowledgeSurfaceSections } from "./KnowledgeSections";
import { SettingsSurfaceSections } from "./SettingsSections";
import { SystemSurfaceSections } from "./SystemSections";
import { WorkflowSurfaceSections } from "./WorkflowSections";

export type GenericRouteKind = "knowledge" | "workflow" | "settings" | "system" | "compact" | "generic";

export function GenericSurfaceSections({
  routeKind,
  compactRoute,
  connectors,
  workflows,
  workflowRuns,
  knowledgeMap,
  knowledgeCards,
  knowledgeSourceFacts,
  knowledgeSourceMaterials,
  knowledgeSourceMaterialReadiness,
  playbooks,
  showKnowledgeMap,
  showKnowledgeCards,
  setShowKnowledgeCards,
  showKnowledgePlaybooks,
  setShowKnowledgePlaybooks
}: {
  routeKind: GenericRouteKind;
  compactRoute: CompactRouteConfig | undefined;
  connectors: ConnectorStatus[];
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  knowledgeSourceFacts: UseQueryResult<KnowledgeSourceFactView[]>;
  knowledgeSourceMaterials: UseQueryResult<KnowledgeSourceMaterialView[]>;
  knowledgeSourceMaterialReadiness: UseQueryResult<KnowledgeSourceMaterialReadiness>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
  showKnowledgeMap: boolean;
  showKnowledgeCards: boolean;
  setShowKnowledgeCards: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgePlaybooks: boolean;
  setShowKnowledgePlaybooks: (value: boolean | ((current: boolean) => boolean)) => void;
}) {
  return (
    <div className="grid gap-6">
      {routeKind === "workflow" ? (
        <WorkflowSurfaceSections workflows={workflows} workflowRuns={workflowRuns} />
      ) : null}
      {routeKind === "knowledge" ? (
        <KnowledgeSurfaceSections
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
      ) : null}
      {routeKind === "settings" ? <SettingsSurfaceSections connectors={connectors} /> : null}
      {routeKind === "system" ? (
        <SystemSurfaceSections
          connectors={connectors}
          workflows={workflows}
          workflowRuns={workflowRuns}
        />
      ) : null}
      {compactRoute ? <CompactRoutePanel config={compactRoute} /> : null}
    </div>
  );
}
