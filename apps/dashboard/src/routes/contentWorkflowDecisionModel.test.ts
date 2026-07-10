import { describe, expect, it } from "vitest";

import {
  activeWorkflowStepIndex,
  blockedWorkflowSteps,
  claimLedgerSummary
} from "./contentWorkflowDecisionModel";

describe("contentWorkflowDecisionModel", () => {
  it("prioritizes blocked work and preserves claim-ledger statuses", () => {
    const steps = [
      { id: "plan", title: "Plan", statusLabel: "gotowe", summary: "" },
      { id: "review", title: "Review", statusLabel: "wymaga review", summary: "" },
      { id: "publish", title: "Publikacja", statusLabel: "zablokowane", summary: "" }
    ];
    expect(activeWorkflowStepIndex(steps)).toBe(2);
    expect(blockedWorkflowSteps(steps).map((step) => step.id)).toEqual(["review", "publish"]);

    expect(
      claimLedgerSummary({
        claimLedger: {
          entries: [
            { status: "allowed", strength: "strong" },
            { status: "needs_human_review", strength: "strong" },
            { status: "allowed", strength: "weak" },
            { status: "blocked_until_measurement", strength: "strong" }
          ]
        }
      } as never)
    ).toEqual({ allowed: 2, review: 2, blocked: 1 });
  });
});
