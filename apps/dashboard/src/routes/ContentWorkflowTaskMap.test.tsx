import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

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
  afterEach(cleanup);

  it("treats the generated section map as system state, not a marketer step", () => {
    render(
      <ContentWorkflowTaskMap
        currentStepId="section_map"
        selectedStepId="section_map"
        steps={steps}
        sectionMapCurrent={true}
        onSelectStep={() => undefined}
      />
    );

    const map = screen.getByTestId("content-workflow-task-map");
    expect(within(map).getAllByText("Tekst").length).toBeGreaterThan(0);
    expect(within(map).queryByText("Plan")).not.toBeInTheDocument();
    expect(within(map).getByRole("list", { name: "Stany pracy nad treścią" }).children).toHaveLength(4);
  });

  it("keeps an unready section map in context instead of opening text", () => {
    render(
      <ContentWorkflowTaskMap
        currentStepId="section_map"
        selectedStepId="section_map"
        steps={steps}
        sectionMapCurrent={false}
        onSelectStep={() => undefined}
      />
    );

    const map = screen.getByTestId("content-workflow-task-map");
    expect(within(map).getByRole("button", { name: /Kontekst/ })).toHaveAttribute("aria-current", "step");
    expect(within(map).getByRole("button", { name: /Kontekst/ })).toHaveAttribute("aria-pressed", "true");
  });
});
