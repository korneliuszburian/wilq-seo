import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ActionObject } from "../lib/api";
import { ActionReviewGatePanel } from "./ActionObjectPanels";

describe("ActionObjectPanels", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows the safety record without audit or adapter jargon", () => {
    render(
      <ActionReviewGatePanel
        action={
          {
            review_gate: {
              status: "pending_validation",
              operator_checklist: ["preview_payload_required"],
              operator_checklist_labels: ["sprawdź podgląd zmian"],
              apply_blockers: ["vendor_mutation_adapter_required"],
              apply_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"],
              confirmation_required: true,
              apply_allowed: false,
              last_confirmation_summary: null,
              last_mutation_audit_summary: "blocked",
              last_mutation_audit_status: "blocked",
              last_mutation_attempted: false,
              last_mutation_adapter: null,
              last_mutation_audit_event_id: "audit_apply_blocked",
              last_mutation_blockers: ["vendor_mutation_adapter_required"],
              last_mutation_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"]
            }
          } as ActionObject
        }
      />
    );

    expect(screen.getByText("Ostatni zapis bezpieczeństwa")).toBeInTheDocument();
    expect(
      screen.getByText("Zapisano kontrolę bezpieczeństwa bez zmian w zewnętrznych systemach.")
    ).toBeInTheDocument();
    expect(screen.getByText("Czy próbowano zapisu: nie")).toBeInTheDocument();
    expect(screen.getByText("System zewnętrzny: brak")).toBeInTheDocument();
    expect(screen.getByText("Ślad bezpieczeństwa: zapisany")).toBeInTheDocument();
    expect(screen.getAllByText(/brak bezpiecznej ścieżki zapisu/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Ostatni audyt zmiany")).not.toBeInTheDocument();
    expect(screen.queryByText(/Adapter:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Zdarzenie audytu:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Próba zmiany:/)).not.toBeInTheDocument();
  });
});
