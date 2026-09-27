import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import type { ActionObject } from "../lib/api";
import { getActions } from "../lib/api";
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
const mockedReadinessState = vi.hoisted(() => ({
  current: Promise.resolve(mockedReadiness)
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getActions: vi.fn().mockResolvedValue(mockedActions),
    getActionsMutationReadiness: vi.fn().mockImplementation(() => mockedReadinessState.current)
  };
});

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, params }: { children: ReactNode; params?: { actionId?: string } }) => (
    <a href={`/actions/${params?.actionId ?? ""}`}>{children}</a>
  )
}));

describe("ActionsSurface", () => {
  afterEach(() => {
    cleanup();
    vi.mocked(getActions).mockResolvedValue(mockedActions as never);
    mockedReadinessState.current = Promise.resolve(mockedReadiness);
  });

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
    expect(screen.getByText("Przygotuj kolejkę przeglądu pliku produktowego Merchant Center")).toBeInTheDocument();
    expect(screen.getAllByText("Przygotuj kolejkę odświeżenia treści ekologus.pl").length).toBeGreaterThan(0);
    expect(screen.getByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")).toBeInTheDocument();
    expect(screen.queryByText("Merchant review produktów")).not.toBeInTheDocument();
    expect(screen.queryByText("Brief SEO: nowy wpis blogowy")).not.toBeInTheDocument();
    expect(screen.queryByText("Przegląd ruchu GA4")).not.toBeInTheDocument();
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

  it("shows only the blockers the API returns", async () => {
    vi.mocked(getActions).mockResolvedValue([
      {
        ...mockedActions[0],
        review_gate: { apply_allowed: false, apply_blocker_labels: [] }
      } as unknown as ActionObject
    ]);
    mockedReadinessState.current = Promise.resolve({
      first_write_candidate: {
        action_id: "act_review_merchant_feed_issues",
        title: "Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
        connector: "merchant_center",
        mode: "prepare",
        mode_label: "przygotowanie",
        ready_to_request_apply: false,
        blockers: [],
        operator_next_step: "Sprawdź plik produktowy.",
        apply_contract: {
          draft_only: false,
          allowed_operation: "MerchantIssueClusterReview"
        }
      },
      first_write_candidate_reason: "Sprawdź plik produktowy.",
      vendor_write_possible_count: 0
    } as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    await screen.findByText("Co nadal blokuje zapis");
    expect(screen.queryByText("Brak potwierdzenia operatora")).not.toBeInTheDocument();
  });

  it("still shows a blocker label the API returns", async () => {
    vi.mocked(getActions).mockResolvedValue([
      {
        ...mockedActions[0],
        review_gate: { apply_allowed: false, apply_blocker_labels: ["Brak podpisu operatora"] }
      } as unknown as ActionObject
    ]);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByText("Brak podpisu operatora")).toBeInTheDocument();
  });

  it("keeps the first action useful while mutation readiness is loading", async () => {
    let resolveReadiness!: (value: typeof mockedReadiness) => void;
    mockedReadinessState.current = new Promise((resolve) => {
      resolveReadiness = resolve;
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    try {
      render(
        <QueryClientProvider client={queryClient}>
          <ActionsSurface />
        </QueryClientProvider>
      );

      await waitFor(() =>
        expect(
          screen.getAllByText("Przygotuj kolejkę odświeżenia treści ekologus.pl").length
        ).toBeGreaterThan(0)
      );
      expect(screen.getByText("sprawdzam gotowość")).toBeInTheDocument();
      expect(screen.getByText("zapis zablokowany do czasu sprawdzenia")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Otwórz akcję" })).toBeInTheDocument();
      expect(screen.queryByText("podgląd gotowy")).not.toBeInTheDocument();

      resolveReadiness(mockedReadiness);
      await waitFor(() => expect(screen.getByText("podgląd gotowy")).toBeInTheDocument());
    } finally {
      mockedReadinessState.current = Promise.resolve(mockedReadiness);
    }
  });

  it("does not call an unprepared preview ready after readiness completes", async () => {
    mockedReadinessState.current = Promise.resolve({
      first_write_candidate: {
        action_id: "act_review_merchant_feed_issues",
        title: "Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
        connector: "merchant_center",
        mode: "prepare",
        mode_label: "przygotowanie",
        ready_to_request_apply: false,
        blockers: [],
        operator_next_step: "Sprawdź podgląd pliku produktowego.",
        apply_contract: {
          draft_only: false,
          allowed_operation: "MerchantIssueClusterReview"
        }
      },
      first_write_candidate_reason: "Sprawdź podgląd pliku produktowego.",
      vendor_write_possible_count: 0
    } as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    await waitFor(() =>
      expect(
        screen.getAllByText("Przygotuj kolejkę przeglądu pliku produktowego Merchant Center").length
      ).toBeGreaterThan(0)
    );
    expect(screen.queryByText("sprawdzam gotowość")).not.toBeInTheDocument();
    expect(screen.queryByText("podgląd gotowy")).not.toBeInTheDocument();
  });

  it("does not claim a preview for a fallback action when the candidate is missing", async () => {
    mockedReadinessState.current = Promise.resolve({
      first_write_candidate: {
        action_id: "act_missing_from_list",
        title: "Akcja spoza listy",
        connector: "merchant_center",
        mode: "prepare",
        mode_label: "przygotowanie",
        ready_to_request_apply: false,
        blockers: [],
        operator_next_step: "Sprawdź akcję.",
        apply_contract: {
          draft_only: false,
          allowed_operation: "MerchantIssueClusterReview"
        }
      },
      first_write_candidate_reason: "Sprawdź akcję.",
      vendor_write_possible_count: 0
    } as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    await waitFor(() =>
      expect(screen.getAllByText("Akcja spoza listy").length).toBeGreaterThan(0)
    );
    expect(screen.queryByText("podgląd gotowy")).not.toBeInTheDocument();
  });

  it("keeps the preview label when the candidate matches the prepared action", async () => {
    mockedReadinessState.current = Promise.resolve({
      first_write_candidate: {
        action_id: "act_prepare_content_refresh_queue",
        title: "Przygotuj kolejkę odświeżenia treści ekologus.pl",
        connector: "wordpress_ekologus",
        mode: "prepare",
        mode_label: "przygotowanie",
        ready_to_request_apply: false,
        blockers: [],
        operator_next_step: "Sprawdź podgląd odświeżenia.",
        apply_contract: {
          draft_only: true,
          allowed_operation: "content_refresh"
        }
      },
      first_write_candidate_reason: "Sprawdź podgląd odświeżenia.",
      vendor_write_possible_count: 0
    } as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ActionsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByText("podgląd gotowy")).toBeInTheDocument();
  });
});
