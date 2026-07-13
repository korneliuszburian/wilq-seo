import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import type { ActionObject } from "../lib/api";
import { ActionsSurface } from "./OperatingRouteSurfaces";

const mockedActions = vi.hoisted(() => [
  {
    id: "act_review_merchant_feed_issues",
    title: "Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
    domain: "merchant",
    connector: "merchant_center",
    mode: "prepare",
    mode_label: "przygotowanie",
    risk: "medium",
    risk_label: "średnie ryzyko",
    status: "needs_validation",
    status_label: "do sprawdzenia",
    evidence_ids: ["ev_merchant_1"],
    evidence_summary_label: "1 dowód źródłowy",
    metrics: [],
    human_diagnosis: "Plik produktowy wymaga sprawdzenia.",
    recommended_reason: "WILQ ma dowód z Merchant Center.",
    validation_status: "not_validated",
    validation_status_label: "niezwalidowana",
    review_gate: {
      apply_allowed: false,
      apply_blocker_labels: ["Brak przeglądu operatora"]
    },
    preview_cards: [],
    payload: { action_type: "prepare" },
    audit_events: []
  },
  {
    id: "act_prepare_content_refresh_queue",
    title: "Przygotuj kolejkę odświeżenia treści ekologus.pl",
    domain: "content",
    connector: "wordpress_ekologus",
    mode: "prepare",
    mode_label: "przygotowanie",
    risk: "low",
    risk_label: "niskie ryzyko",
    status: "ready",
    status_label: "gotowe",
    evidence_ids: ["ev_content_1"],
    evidence_summary_label: "1 dowód źródłowy",
    metrics: [],
    human_diagnosis: "Treść wymaga sprawdzenia przed odświeżeniem.",
    recommended_reason: "WILQ ma dowód z GSC i WordPress.",
    validation_status: "valid",
    validation_status_label: "zwalidowana",
    review_gate: {
      apply_allowed: false,
      apply_blocker_labels: ["Brak zatwierdzonego przekazania do WordPress"]
    },
    preview_cards: [{ label: "Plan", value: "Odświeżenie" }],
    payload: { action_type: "prepare_content_refresh" },
    audit_events: []
  },
  {
    id: "act_review_ga4_tracking_quality",
    title: "Sprawdź jakość pomiaru GA4 przed oceną kampanii",
    domain: "ga4",
    connector: "google_analytics_4",
    mode: "review",
    mode_label: "do sprawdzenia",
    risk: "medium",
    risk_label: "średnie ryzyko",
    status: "needs_validation",
    status_label: "do sprawdzenia",
    evidence_ids: ["ev_ga4_1"],
    evidence_summary_label: "1 dowód źródłowy",
    metrics: [],
    human_diagnosis: "Pomiar wymaga kontroli.",
    recommended_reason: "WILQ ma dowód z GA4.",
    validation_status: "not_validated",
    validation_status_label: "niezwalidowana",
    review_gate: {
      apply_allowed: false,
      apply_blocker_labels: ["Brak audytu działania integracji"]
    },
    preview_cards: [],
    payload: { action_type: "review" },
    audit_events: []
  }
] as unknown as ActionObject[]);

const mockedReadiness = vi.hoisted(() => ({
  first_write_candidate: null,
  first_write_candidate_reason: "Najpierw sprawdź warunki i podgląd.",
  vendor_write_possible_count: 0
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getActions: vi.fn().mockResolvedValue(mockedActions),
    getActionsMutationReadiness: vi.fn().mockResolvedValue(mockedReadiness)
  };
});

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, params }: { children: ReactNode; params?: { actionId?: string } }) => (
    <a href={`/actions/${params?.actionId ?? ""}`}>{children}</a>
  )
}));

describe("ActionsSurface", () => {
  afterEach(() => cleanup());

  it("starts from marketer-facing actions instead of registry dumps", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Akcje" })).toBeInTheDocument();
    expect(screen.getByText(/Bezpieczne przygotowanie zmian/)).toBeInTheDocument();
    expect(screen.getByText("akcji")).toBeInTheDocument();
    expect(screen.getByText("gotowe do review")).toBeInTheDocument();
    expect(screen.getByText("zablokowane")).toBeInTheDocument();
    expect(screen.getByText("dowodów")).toBeInTheDocument();
    expect(screen.getByText("Najbliższa bezpieczna akcja")).toBeInTheDocument();
    expect(screen.getByText("Plan odświeżenia treści")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kolejka akcji" })).toBeInTheDocument();
    expect(screen.getByText("Merchant review produktów")).toBeInTheDocument();
    expect(screen.getByText("Brief SEO: nowy wpis blogowy")).toBeInTheDocument();
    expect(screen.getByText("Przegląd ruchu GA4")).toBeInTheDocument();
    expect(screen.getByText("Przebieg akcji")).toBeInTheDocument();
    expect(screen.getByText("Walidacja")).toBeInTheDocument();
    expect(screen.getByText("Podgląd")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Potwierdzenie")).toBeInTheDocument();
    expect(screen.getByText("Audyt")).toBeInTheDocument();
    expect(screen.queryByText(/rejestru technicznego/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/"action_type"/)).not.toBeInTheDocument();
    expect(screen.queryByText("ev_merchant_1")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Otwórz akcję" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Zobacz podgląd" }).length).toBeGreaterThan(0);
  });
});
