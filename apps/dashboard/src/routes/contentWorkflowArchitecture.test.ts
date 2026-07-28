import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const routeSource = readFileSync(resolve(__dirname, "ContentWorkflowSurface.tsx"), "utf8");
const querySource = readFileSync(resolve(__dirname, "contentWorkflowQueries.ts"), "utf8");
const contentApiSource = readFileSync(resolve(__dirname, "../lib/api.ts"), "utf8");
const actionRouteSource = readFileSync(resolve(__dirname, "DetailPanels.tsx"), "utf8");
const actionQuerySource = readFileSync(resolve(__dirname, "actionDetailQueries.ts"), "utf8");

describe("ContentWorkflow architecture boundary", () => {
  it("keeps remote query orchestration in the domain hook", () => {
    expect(routeSource).toContain("useContentWorkflowQueries");
    expect(routeSource).not.toContain('queryKey: ["content-workflow", "queue"]');
    expect(querySource).toContain("useQuery");
    expect(querySource).not.toContain("getContentWorkItemQueue");
    expect(querySource).not.toContain('queryKey: ["content-workflow", "queue"');
    expect(querySource).toContain("useContentTargetDiscovery");
    expect(querySource).toContain("getContentWorkItemTargetDiscovery");
  });

  it("keeps the route's first responsibility as typed state selection", () => {
    expect(routeSource).toContain("<ContentWorkflowRouteState");
    expect(routeSource).toContain("<ContentTextWorkspace");
    expect(routeSource).toContain("<ContentReviewRoute");
    expect(routeSource).not.toContain("<ContentWorkflowQueueReady");
    expect(routeSource).not.toContain("<ContentWorkflowLoaded");
  });

  it("keeps intent-first entry and canonical document presentation in extracted owners", () => {
    expect(routeSource).toContain("<ContentWorkflowEntryPanel");
    expect(routeSource).toContain("<ContentDocumentWorkspaceCanvas");
    expect(routeSource).toContain("<ContentReviewWorkspace");
    expect(routeSource).not.toContain("<ContentPageWorkbenchView");
    expect(routeSource).not.toContain("<WordPressDraftWorkPanelView");
    expect(routeSource).not.toContain("MobileContentTriage");
    expect(routeSource).not.toContain("Treści: praca nad stroną");
    expect(routeSource).not.toContain('<FactTile label="Publikacja"');
  });

  it("does not expose retired snapshot, package-review, or direct WordPress helpers", () => {
    for (const name of [
      "getContentWorkItemSnapshot",
      "postContentWorkItemPreflight",
      "postContentWorkItemSalesBrief",
      "postContentWorkItemDraftPackage",
      "postContentWorkItemQualityReview",
      "postContentWorkItemHumanReview",
      "saveContentWorkItemSnapshotHumanReview",
      "saveContentWorkItemSnapshotAudit",
      "postContentWorkItemWordPressDraftHandoff",
      "postContentWorkItemWordPressDraftExecution"
    ]) {
      expect(contentApiSource).not.toContain(`function ${name}`);
    }
  });

  it("keeps ActionDetail remote queries behind its domain hook", () => {
    expect(actionRouteSource).toContain("useActionDetailQueries");
    expect(actionRouteSource).not.toContain('queryKey: ["actions", actionId]');
    expect(actionQuerySource).toContain("getActionMutationReadiness");
  });
});
