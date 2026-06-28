import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
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
            source_connector_labels: ["Localo"],
            source_connector_summary_label: "Localo",
            evidence_ids: [],
            evidence_summary_label: "brak dowodów źródłowych",
            action_ids: [],
            action_summary_label: "brak akcji do sprawdzenia",
            blocked_claims: ["local_ranking_uplift_claim"],
            blocked_claim_labels: ["obietnica do sprawdzenia"],
            blocked_claim_summary_label: "1 zablokowana obietnica",
            metric_tiles: {},
            missing_contracts: ["local_ranking_rows"],
            missing_contract_labels: ["lokalne pozycje"],
            missing_contract_summary_label: "1 brakujący zakres danych",
            missing_contract_detail_label: "lokalne pozycje",
            risk: "medium",
            risk_label: "średnie ryzyko"
          } satisfies Workflow
        ]}
      />
    );

    expect(screen.getByText("Źródła danych: Localo")).toBeInTheDocument();
    expect(screen.getByText("Dowody: brak dowodów źródłowych")).toBeInTheDocument();
    expect(screen.getByText("Brakujące dane: 1 brakujący zakres danych")).toBeInTheDocument();
    expect(screen.getByText("Granice wniosków: 1 zablokowana obietnica")).toBeInTheDocument();
    expect(screen.queryByText(/^Źródła danych: localo$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_uplift_claim/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż opis procesu" }));

    expect(screen.getByText("Brakujące dane: lokalne pozycje")).toBeInTheDocument();
    expect(screen.getAllByText("Granice wniosków: 1 zablokowana obietnica").length).toBeGreaterThan(0);
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_uplift_claim/)).not.toBeInTheDocument();

    const routeSource = readFileSync("src/routes/WorkflowPanels.tsx", "utf8");
    expect(routeSource).toContain("workflow.missing_contract_detail_label");
    expect(routeSource).toContain("workflow.blocked_claim_summary_label");
    expect(routeSource).not.toContain("workflow.missing_contract_labels.join");
    expect(routeSource).not.toContain("workflow.blocked_claim_labels.join");
  });
});
