import { describe, expect, it } from "vitest";

import {
  activeWorkflowStepIndex,
  blockedWorkflowSteps,
  claimLedgerSummary
} from "./contentWorkflowDecisionModel";
import type { WorkflowStep } from "./contentWorkflowRuntime";

describe("contentWorkflowDecisionModel", () => {
  it("uses typed workflow state instead of Polish status copy", () => {
    const steps: WorkflowStep[] = [
      {
        id: "scope",
        title: "Zakres",
        phase: "complete",
        readiness: "ready",
        statusLabel: "zablokowane, ale ten tekst nie steruje UI",
        summary: "",
        canOpen: true,
        canSubmit: false,
        blocker: null,
        safeNextStep: "Sprawdź mapę."
      },
      {
        id: "draft",
        title: "Szkic",
        phase: "current",
        readiness: "review_required",
        statusLabel: "gotowe, ale readiness wymaga review",
        summary: "",
        canOpen: true,
        canSubmit: false,
        blocker: { code: "revision", label: "Review", reason: "Brak wersji." },
        safeNextStep: "Zapisz wersję."
      },
      {
        id: "review",
        title: "Review",
        phase: "pending",
        readiness: "blocked",
        statusLabel: "wszystko wygląda dobrze",
        summary: "",
        canOpen: false,
        canSubmit: false,
        blocker: { code: "draft", label: "Szkic", reason: "Brak szkicu." },
        safeNextStep: "Zakończ szkic."
      }
    ];
    expect(activeWorkflowStepIndex(steps, "draft")).toBe(1);
    expect(blockedWorkflowSteps(steps).map((step) => step.id)).toEqual(["draft", "review"]);

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
