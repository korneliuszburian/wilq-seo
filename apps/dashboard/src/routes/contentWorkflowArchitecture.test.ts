import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const routeSource = readFileSync(resolve(__dirname, "ContentWorkflowSurface.tsx"), "utf8");
const querySource = readFileSync(resolve(__dirname, "contentWorkflowQueries.ts"), "utf8");
const actionRouteSource = readFileSync(resolve(__dirname, "DetailPanels.tsx"), "utf8");
const actionQuerySource = readFileSync(resolve(__dirname, "actionDetailQueries.ts"), "utf8");

describe("ContentWorkflow architecture boundary", () => {
  it("keeps remote query orchestration in the domain hook", () => {
    expect(routeSource).toContain("useContentWorkflowQueries");
    expect(routeSource).not.toContain('queryKey: ["content-workflow", "queue"]');
    expect(querySource).toContain("useQuery");
    expect(querySource).toContain("getContentWorkItemQueue");
    expect(querySource).toContain('queryKey: ["content-workflow", "queue", "catalog"]');
    expect(querySource).toContain('queryKey: ["content-workflow", "queue", "selected", selectedWorkItemId]');
  });

  it("keeps the route's first responsibility as typed state selection", () => {
    expect(routeSource).toContain("<ContentWorkflowRouteState");
    expect(routeSource).toContain("<ContentWorkflowQueueReady");
    expect(routeSource).toContain("<ContentWorkflowLoaded");
  });

  it("keeps first-screen and draft presentation in extracted owners", () => {
    expect(routeSource).toContain("<ContentWorkflowJourneyContext");
    expect(routeSource).toContain("<ContentWorkflowTaskMap");
    expect(routeSource).toContain("<ContentPageWorkbenchView");
    expect(routeSource).toContain("<WordPressDraftWorkPanelView");
    expect(routeSource).toContain("<WorkflowStepsList");
    expect(routeSource).toContain('viewMode === "marketer"');
    expect(routeSource).not.toContain("<details");
    expect(routeSource).not.toContain("MobileContentTriage");
    expect(routeSource).not.toContain("Treści: praca nad stroną");
    expect(routeSource).not.toContain('<FactTile label="Publikacja"');
  });

  it("keeps ActionDetail remote queries behind its domain hook", () => {
    expect(actionRouteSource).toContain("useActionDetailQueries");
    expect(actionRouteSource).not.toContain('queryKey: ["actions", actionId]');
    expect(actionQuerySource).toContain("getActionMutationReadiness");
  });
});
