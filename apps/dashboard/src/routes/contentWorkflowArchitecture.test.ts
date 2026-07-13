import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const routeSource = readFileSync(resolve(__dirname, "ContentWorkflowSurface.tsx"), "utf8");
const querySource = readFileSync(resolve(__dirname, "contentWorkflowQueries.ts"), "utf8");

describe("ContentWorkflow architecture boundary", () => {
  it("keeps remote query orchestration in the domain hook", () => {
    expect(routeSource).toContain("useContentWorkflowQueries");
    expect(routeSource).not.toContain('queryKey: ["content-workflow", "queue"]');
    expect(querySource).toContain("useQuery");
    expect(querySource).toContain("getContentWorkItemQueue");
  });

  it("keeps the route's first responsibility as typed state selection", () => {
    expect(routeSource).toContain("<ContentWorkflowRouteState");
    expect(routeSource).toContain("<ContentWorkflowQueueReady");
    expect(routeSource).toContain("<ContentWorkflowLoaded");
  });
});
