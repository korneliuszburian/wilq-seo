import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WorkflowStep } from "./contentWorkflowRuntime";
import { ContentWorkflowTaskMap } from "./ContentWorkflowTaskMap";

const steps: WorkflowStep[] = [
  { id: "scope", title: "Zakres", phase: "current", readiness: "ready", statusLabel: "gotowe", summary: "", canOpen: true, canSubmit: true, blocker: null, safeNextStep: "" },
  { id: "section_map", title: "Plan sekcji", phase: "complete", readiness: "ready", statusLabel: "gotowe", summary: "", canOpen: true, canSubmit: false, blocker: null, safeNextStep: "" },
  { id: "draft", title: "Szkic treści", phase: "pending", readiness: "blocked", statusLabel: "oczekuje", summary: "", canOpen: true, canSubmit: false, blocker: null, safeNextStep: "" },
  { id: "review", title: "Sprawdzenie treści", phase: "pending", readiness: "blocked", statusLabel: "oczekuje", summary: "", canOpen: false, canSubmit: false, blocker: null, safeNextStep: "" },
  { id: "dev_draft", title: "Szkic na devie", phase: "pending", readiness: "blocked", statusLabel: "oczekuje", summary: "", canOpen: false, canSubmit: false, blocker: null, safeNextStep: "" }
];

describe("ContentWorkflowTaskMap", () => {
  it("treats the generated section map as system state, not a marketer step", () => {
    render(
      <ContentWorkflowTaskMap
        currentStepId="section_map"
        selectedStepId="section_map"
        steps={steps}
        onSelectStep={() => undefined}
      />
    );

    const map = screen.getByTestId("content-workflow-task-map");
    expect(within(map).getAllByText("Tekst").length).toBeGreaterThan(0);
    expect(within(map).queryByText("Plan")).not.toBeInTheDocument();
    expect(within(map).getByRole("list", { name: "Stany pracy nad treścią" }).children).toHaveLength(4);
  });
});
