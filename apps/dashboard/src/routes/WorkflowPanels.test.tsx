import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Workflow } from "../lib/api";
import { WorkflowRegistryList } from "./WorkflowPanels";

describe("WorkflowPanels", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders missing data labels instead of raw workflow contract keys", () => {
    render(
      <WorkflowRegistryList
        workflows={[
          {
            id: "localo_visibility_review",
            label: "Widoczność lokalna Localo",
            description: "Proces lokalnej widoczności wymaga jeszcze danych z Localo.",
            steps: [],
            status: "blocked",
            status_label: "zablokowane",
            route: null,
            route_label: "Localo",
            skill_id: "wilq-localo-operator",
            safe_next_step: "Domknij brakujące dane przed oceną lokalnej widoczności.",
            source_connectors: ["localo"],
            evidence_ids: [],
            action_ids: [],
            blocked_claims: ["wzrost lokalnych pozycji"],
            metric_tiles: {},
            missing_contracts: ["local_ranking_rows"],
            missing_contract_labels: ["lokalne pozycje"],
            risk: "medium",
            risk_label: "średnie ryzyko"
          } satisfies Workflow
        ]}
      />
    );

    expect(screen.getByText("Brakujące dane: 1")).toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż opis procesu" }));

    expect(screen.getByText("Brakujące dane: lokalne pozycje")).toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();
  });
});
