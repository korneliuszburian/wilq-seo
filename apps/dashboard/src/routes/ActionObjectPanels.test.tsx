import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import { ActionObjectFocus, ActionReviewGatePanel } from "./ActionObjectPanels";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    params
  }: {
    children: ReactNode;
    params?: { actionId?: string; evidenceId?: string };
  }) => {
    const id = params?.actionId ?? params?.evidenceId ?? "";
    const prefix = params?.actionId ? "/actions/" : "/evidence/";
    return <a href={`${prefix}${id}`}>{children}</a>;
  }
}));

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

  it("uses the ActionObject evidence summary as visible proof context", () => {
    renderWithQueryClient(
      <ActionObjectFocus
        actions={[
          {
            id: "action_merchant_feed_review",
            title: "Sprawdź feed produktowy",
            domain: "merchant",
            connector: "merchant_center",
            connector_label: "Merchant Center",
            mode: "prepare",
            mode_label: "przygotowanie",
            risk: "medium",
            risk_label: "średnie ryzyko",
            status: "pending",
            status_label: "do sprawdzenia",
            evidence_ids: ["evidence_merchant_feed_status", "evidence_merchant_policy_status"],
            evidence_summary_label: "2 dowody źródłowe",
            metrics: [],
            human_diagnosis: "Feed wymaga sprawdzenia przed zmianami.",
            recommended_reason: "WILQ ma dowody z Merchant Center.",
            validation_status: "not_validated",
            validation_status_label: "niezwalidowana",
            review_gate: {
              status: "pending_validation",
              status_label: "wymaga sprawdzenia",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              required_check_labels: [],
              operator_checklist: ["preview_payload_required"],
              operator_checklist_labels: ["sprawdź podgląd zmian"],
              apply_blockers: ["vendor_mutation_adapter_required"],
              apply_blocker_labels: ["brak bezpiecznej ścieżki zapisu"],
              confirmation_required: true,
              apply_allowed: false,
              last_mutation_blockers: [],
              last_mutation_blocker_labels: []
            },
            preview_cards: [],
            payload: {},
            audit_events: []
          } as ActionObject
        ]}
      />
    );

    expect(screen.getByText("2 dowody źródłowe")).toBeInTheDocument();
    expect(screen.getByText("Źródła danych: Merchant Center")).toBeInTheDocument();
    expect(screen.getByText("Tryb pracy: przygotowanie")).toBeInTheDocument();
    expect(screen.queryByText("Merchant Center / przygotowanie")).not.toBeInTheDocument();
    expect(screen.queryByText("evidence_merchant_feed_status")).not.toBeInTheDocument();
    expect(screen.queryByText("evidence_merchant_policy_status")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "dowód 1" })).toHaveAttribute(
      "href",
      "/evidence/evidence_merchant_feed_status"
    );
    expect(screen.getByRole("link", { name: "dowód 2" })).toHaveAttribute(
      "href",
      "/evidence/evidence_merchant_policy_status"
    );
  });

  it("does not join action metadata with slash copy", () => {
    const source = readFileSync("src/routes/ActionObjectPanels.tsx", "utf8");
    expect(source).not.toContain("{action.connector_label} / {action.mode_label}");
  });

  it("keeps review badge state separate from visible review copy", () => {
    const source = readFileSync("src/routes/ActionObjectPanels.tsx", "utf8");
    expect(source).toContain(
      'value={action.review_gate.status} label={lastReviewLabel ?? "brak przeglądu"}'
    );
    expect(source).not.toContain('value={lastReviewLabel ?? "brak przeglądu"}');
  });

  it("does not assemble action count copy from action IDs", () => {
    const source = readFileSync("src/routes/ActionObjectPanels.tsx", "utf8");
    expect(source).toContain("actionSummaryLabel");
    expect(source).not.toContain("actionIds.length === 1");
    expect(source).not.toContain("`${actionIds.length} akcji do sprawdzenia`");
  });
});

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
