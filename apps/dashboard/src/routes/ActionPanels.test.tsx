import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import { ActionFocus, ActionReviewGatePanel } from "./ActionPanels";

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

describe("ActionPanels", () => {
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
              apply_blocker_summary_label: "1 blokada",
              confirmation_required: true,
              apply_allowed: false,
              last_confirmation_summary: null,
              last_mutation_audit_summary: "blocked",
              last_mutation_audit_status: "blocked",
              last_mutation_audit_status_label: "zablokowany",
              last_mutation_attempted: false,
              last_mutation_attempted_label: "nie próbowano zapisu w systemie zewnętrznym",
              last_mutation_adapter: null,
              last_mutation_adapter_label: "brak bezpiecznej ścieżki zapisu",
              last_mutation_audit_event_id: "audit_apply_blocked",
              last_mutation_audit_trace_label: "ślad bezpieczeństwa zapisany",
              last_mutation_blockers: ["vendor_mutation_adapter_required"],
              last_mutation_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"],
              last_mutation_blocker_summary_label: "1 blokada"
            }
          } as ActionObject
        }
      />
    );

    expect(screen.getByText("Ostatni zapis bezpieczeństwa")).toBeInTheDocument();
    expect(
      screen.getByText("Zapisano kontrolę bezpieczeństwa bez zmian w zewnętrznych systemach.")
    ).toBeInTheDocument();
    expect(screen.getByText("Wynik: zablokowany")).toBeInTheDocument();
    expect(
      screen.getByText("Czy próbowano zapisu: nie próbowano zapisu w systemie zewnętrznym")
    ).toBeInTheDocument();
    expect(screen.getByText("System zewnętrzny: brak bezpiecznej ścieżki zapisu")).toBeInTheDocument();
    expect(screen.getByText("Ślad bezpieczeństwa: ślad bezpieczeństwa zapisany")).toBeInTheDocument();
    expect(screen.getAllByText(/1 blokada/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Wynik: brak")).not.toBeInTheDocument();
    expect(screen.queryByText("System zewnętrzny: brak")).not.toBeInTheDocument();
    expect(screen.queryByText("Ślad bezpieczeństwa: brak")).not.toBeInTheDocument();
    expect(screen.queryByText(/vendor_mutation_adapter_required/)).not.toBeInTheDocument();
    expect(screen.queryByText("Ostatni audyt zmiany")).not.toBeInTheDocument();
    expect(screen.queryByText(/Adapter:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Zdarzenie audytu:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Próba zmiany:/)).not.toBeInTheDocument();
  });

  it("uses the action evidence summary as visible proof context", () => {
    renderWithQueryClient(
      <ActionFocus
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
              apply_blocker_summary_label: "1 blokada",
              confirmation_required: true,
              apply_allowed: false,
              last_mutation_blockers: [],
              last_mutation_blocker_labels: [],
              last_mutation_blocker_summary_label: "brak blokad"
            },
            preview_cards: [],
            payload: { raw_debug_value: "wartość tylko do audytu" },
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
    expect(screen.queryByText(/Domyślnie schowany/)).not.toBeInTheDocument();
    expect(screen.queryByText(/wartość tylko do audytu/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż dane techniczne akcji" }));

    expect(screen.getByText(/Domyślnie schowany/)).toBeInTheDocument();
    expect(screen.getByText(/wartość tylko do audytu/)).toBeInTheDocument();
  });

  it("does not join action metadata with slash copy", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).not.toContain("{action.connector_label} / {action.mode_label}");
  });

  it("keeps raw action data drawer named as technical detail, not payload preview", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain("ActionTechnicalDataToggle");
    expect(source).toContain("technicalData={action.payload}");
    expect(source).not.toContain("ActionPayloadPreviewToggle");
    expect(source).not.toContain("payload={action.payload}");
  });

  it("keeps review badge state separate from visible review copy", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain(
      "action.review_gate.last_review_outcome_label ?? action.review_gate.status_label"
    );
    expect(source).toContain(
      "value={action.review_gate.status} label={reviewStatusLabel}"
    );
    expect(source).not.toContain('"brak przeglądu"');
    expect(source).not.toContain('value={lastReviewLabel ?? "brak przeglądu"}');
  });

  it("does not assemble action count copy from action IDs", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain("actionSummaryLabel");
    expect(source).not.toContain("actionIds.length === 1");
    expect(source).not.toContain("`${actionIds.length} akcji do sprawdzenia`");
  });

  it("keeps effect checks in plain comparison language", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain("porównanie wyników sprzed zmiany i po zmianie");
    expect(source).not.toContain("okno efektu");
    expect(source).not.toContain("Zapisuje okno");
    expect(source).not.toContain("Okna:");
  });

  it("uses self-defending empty states instead of bare brak placeholders", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).not.toContain('empty="brak etykiety dowodów z WILQ"');
    expect(source).not.toContain('empty="brak blokad podglądu"');
    expect(source).not.toContain('empty="brak dodatkowych warunków"');
    expect(source).not.toContain('empty="brak błędów"');
    expect(source).not.toContain('empty="brak ostrzeżeń"');
    expect(source).not.toContain('empty="brak blokad potwierdzenia"');
    expect(source).not.toMatch(/empty="brak (źródeł|dowodów)/);
    expect(source).not.toMatch(/"brak dowodów/);
    expect(source).toContain("nie traktuj tej akcji jako gotowej rekomendacji");
    expect(source).toContain("WILQ nie zgłosił blokad podglądu");
    expect(source).toContain("WILQ nie zgłosił błędów sprawdzenia");
    expect(source).toContain("nie oceniaj efektu bez źródła");
  });
});

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
