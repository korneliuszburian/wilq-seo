import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createWilqQueryClient } from "../lib/queryClient";
import { CommandCenter } from "./CommandCenterRoute";
import { getCommandCenter, type CommandCenterResponse } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getCommandCenter: vi.fn()
  };
});

const commandCenterFixture: CommandCenterResponse = {
  generated_at: "2026-06-22T18:56:00Z",
  strict_instruction:
    "WILQ pokazuje tylko metryki z danych źródłowych. Brak danych oznacza blokadę, nie domysł marketingowy.",
  primary_next_step: "Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów pliku produktowego.",
  blocker_count: 0,
  tactical_item_count: 4,
  source_connectors: [
    "google_merchant_center",
    "google_search_console",
    "wordpress_ekologus",
    "google_analytics_4"
  ],
  source_connector_labels: [
    "Merchant Center",
    "Google Search Console",
    "WordPress ekologus.pl",
    "GA4"
  ],
  evidence_ids: [
    "ev_refresh_merchant_feed",
    "ev_refresh_gsc",
    "ev_refresh_ga4"
  ],
  evidence_summary: "3 dowody źródłowe",
  action_ids: [
    "act_review_merchant_feed_issues",
    "act_prepare_content_refresh_queue"
  ],
  action_summary: "2 akcje do sprawdzenia",
  daily_decisions: [
    {
      id: "decision_review_merchant_feed_issues",
      title: "Przejrzyj kolejkę problemów Merchant Center",
      domain: "merchant",
      freshness: { state: "fresh" },
      freshness_label: "świeże dane",
      decision_state: "ready",
      decision_state_label: "gotowe",
      route: "/merchant",
      route_label: "Merchant",
      cta_label: "Otwórz Merchant",
      status: "ready",
      priority: 10,
      priority_label: "najpierw",
      metric_tiles: {
        produkty: 10900,
        zgłoszenia: 15
      },
      metric_facts: [
        {
          name: "issue_count",
          metric_label: "Zgłoszenia problemów",
          value: 15,
          period: "connector_refresh",
          source_connector: "google_merchant_center",
          evidence_id: "ev_refresh_merchant_feed",
          dimensions: {},
          dimension_labels: {},
          dimension_value_labels: {}
        }
      ],
      co_widzimy:
        "Merchant Center ma potwierdzone dane problemów pliku produktowego.",
      dlaczego_to_ma_znaczenie:
        "Problemy pliku produktowego mogą blokować widoczność produktów, ale wymagają ręcznego sprawdzenia.",
      bezpieczny_next_step:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
      why_it_matters:
        "Problemy pliku produktowego mogą blokować widoczność produktów, ale wymagają ręcznego sprawdzenia.",
      operator_action:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
      source_connectors: ["google_merchant_center"],
      source_connector_labels: ["Merchant Center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      evidence_summary: "1 potwierdzony ślad w WILQ",
      action_ids: ["act_review_merchant_feed_issues"],
      action_summary: "1 bezpieczna akcja do sprawdzenia",
      blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana pliku produktowego"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "automatyczna zmiana pliku produktowego"],
      skill_id: "wilq-merchant-feed-operator",
      skill_label: "plik produktowy Merchant",
      codex_prompt:
        "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
      codex_context_endpoint: "/api/codex/context-pack",
      expected_codex_output: "Polskie podsumowanie przeglądu problemów pliku produktowego z dowodami źródłowymi.",
      risk: "medium"
    },
    {
      id: "decision_prepare_content_refresh_queue",
      title: "Przejrzyj kolejkę SEO z GSC i WordPress",
      domain: "content",
      freshness: { state: "stale" },
      freshness_label: "dane wymagają odświeżenia",
      decision_state: "stale",
      decision_state_label: "do odświeżenia",
      route: "/content-workflow",
      route_label: "Treści",
      cta_label: "Otwórz Treści",
      status: "ready",
      priority: 12,
      priority_label: "najpierw",
      metric_tiles: {
        "zapytania i adresy z GSC": 10,
        "dopasowania WordPress": 15,
        "ocena Ahrefs": 1,
        "luki linków": 9,
        kliknięcia: 138,
        wyświetlenia: 7852
      },
      metric_facts: [
        {
          name: "clicks",
          metric_label: "Kliknięcia",
          value: 138,
          period: "connector_refresh",
          source_connector: "google_search_console",
          evidence_id: "ev_refresh_gsc",
          dimensions: {},
          dimension_labels: {},
          dimension_value_labels: {}
        }
      ],
      co_widzimy:
        "WILQ ma dane treści: 10 zapytań i adresów z GSC, 15 dopasowań WordPress, 1 ocena Ahrefs, 9 luk linków.",
      dlaczego_to_ma_znaczenie: "120 wyświetleń może uzasadniać sprawdzenie treści.",
      bezpieczny_next_step:
        "Otwórz widok Treści i wybierz odświeżenie, scalenie, utworzenie albo blokadę.",
      why_it_matters: "120 wyświetleń może uzasadniać sprawdzenie treści.",
      operator_action:
        "Otwórz widok Treści i wybierz odświeżenie, scalenie, utworzenie albo blokadę.",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      source_connector_labels: ["Google Search Console", "WordPress ekologus.pl"],
      evidence_ids: ["ev_refresh_gsc"],
      evidence_summary: "1 potwierdzony ślad w WILQ",
      action_ids: ["act_prepare_content_refresh_queue"],
      action_summary: "1 bezpieczna akcja do sprawdzenia",
      blocked_claims: ["wzrost liczby leadów", "gwarancja wzrostu pozycji"],
      blocked_claim_labels: ["wzrost liczby leadów", "gwarancja wzrostu pozycji"],
      skill_id: "wilq-content-strategist",
      skill_label: "strategia treści",
      codex_prompt:
        "Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh.",
      codex_context_endpoint: "/api/codex/context-pack",
      expected_codex_output: "Polski content brief bez obietnic pozycji.",
      risk: "low"
    }
  ],
  work_orders: [
    {
      id: "work_order_decision_review_merchant_feed_issues",
      title: "Przejrzyj kolejkę problemów Merchant Center",
      status: "review_required",
      status_label: "do sprawdzenia",
      owner_role: "product_feed",
      priority: 10,
      domain: "merchant",
      route: "/merchant",
      route_label: "Merchant",
      summary: "Merchant Center ma potwierdzone dane problemów pliku produktowego.",
      why_it_matters:
        "Problemy pliku produktowego mogą blokować widoczność produktów, ale wymagają ręcznego sprawdzenia.",
      next_safe_step:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
      close_condition:
        "Zamknięte po review wskazanej akcji, zapisaniu decyzji i pozostawieniu audytu w WILQ.",
      source_connectors: ["google_merchant_center"],
      source_connector_labels: ["Merchant Center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      evidence_summary: "1 potwierdzony ślad w WILQ",
      action_ids: ["act_review_merchant_feed_issues"],
      action_summary: "1 bezpieczna akcja do sprawdzenia",
      blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana pliku produktowego"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "automatyczna zmiana pliku produktowego"],
      freshness: { state: "fresh" },
      freshness_label: "świeże dane",
      risk: "medium",
      decision_id: "decision_review_merchant_feed_issues"
    },
    {
      id: "work_order_decision_prepare_content_refresh_queue",
      title: "Przejrzyj kolejkę SEO z GSC i WordPress",
      status: "blocked",
      status_label: "blokada danych",
      owner_role: "content_seo",
      priority: 12,
      domain: "content",
      route: "/content-workflow",
      route_label: "Treści",
      summary:
        "WILQ ma dane treści: 10 zapytań i adresów z GSC, 15 dopasowań WordPress, 1 ocena Ahrefs, 9 luk linków.",
      why_it_matters: "120 wyświetleń może uzasadniać sprawdzenie treści.",
      next_safe_step:
        "Otwórz widok Treści i wybierz odświeżenie, scalenie, utworzenie albo blokadę.",
      close_condition:
        "Zamknięte po odświeżeniu źródeł i ponownej ocenie decyzji w WILQ.",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      source_connector_labels: ["Google Search Console", "WordPress ekologus.pl"],
      evidence_ids: ["ev_refresh_gsc"],
      evidence_summary: "1 potwierdzony ślad w WILQ",
      action_ids: ["act_prepare_content_refresh_queue"],
      action_summary: "1 bezpieczna akcja do sprawdzenia",
      blocked_claims: ["wzrost liczby leadów", "gwarancja wzrostu pozycji"],
      blocked_claim_labels: ["wzrost liczby leadów", "gwarancja wzrostu pozycji"],
      freshness: { state: "stale" },
      freshness_label: "dane wymagają odświeżenia",
      risk: "low",
      decision_id: "decision_prepare_content_refresh_queue"
    }
  ],
  operator_brief: [],
  demo_script: [],
  action_plan: [],
  connector_summary: {
    total: 6,
    configured: 6,
    missing_credentials: 0
  },
  sections: {},
  active_actions: [],
  connector_health: [],
  codex_operator_status: {}
};

describe("CommandCenter route", () => {
  beforeEach(() => {
    vi.mocked(getCommandCenter).mockResolvedValue(commandCenterFixture);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  function renderCommandCenter() {
    const client = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });
    return render(
      <QueryClientProvider client={client}>
        <CommandCenter />
      </QueryClientProvider>
    );
  }

  it("renders the Polish daily decision cockpit without raw trace IDs on the first screen", async () => {
    renderCommandCenter();

    await waitFor(() => expect(screen.getByRole("heading", { name: "Dzisiaj" })).toBeInTheDocument());

    expect(screen.getByText("Twoje dzienne centrum operacyjne. Skup się na tym, co ma największy wpływ."))
      .toBeInTheDocument();
    expect(screen.getByText("Wymagają Twojej decyzji")).toBeInTheDocument();
    expect(screen.getByText("Zatrzymują pracę")).toBeInTheDocument();
    expect(screen.getByText("Zadania do wykonania")).toBeInTheDocument();
    expect(screen.getByText("Dane są nieświeże")).toBeInTheDocument();
    expect(screen.getByLabelText("Świeżość źródeł")).toHaveTextContent("Merchantświeże dane");
    expect(screen.getByLabelText("Świeżość źródeł")).toHaveTextContent("Treścidane wymagają odświeżenia");
    expect(screen.getByRole("heading", { name: "Następna najlepsza praca" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Blokady, których nie obchodź" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kolejka dziś" })).toBeInTheDocument();
    expect(screen.getAllByText("Przejrzyj kolejkę problemów Merchant Center").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Przejrzyj kolejkę SEO z GSC i WordPress").length
    ).toBeGreaterThan(0);
    expect(
      screen.getByText("Merchant Center ma potwierdzone dane problemów pliku produktowego.")
    ).toBeInTheDocument();
    expect(screen.queryByText(/WILQ ma dane treści: 10 zapytań i adresów z GSC/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Najpierw sprawdź dopasowania WordPress/)).not.toBeInTheDocument();
    expect(screen.queryByText("120 wyświetleń może uzasadniać sprawdzenie treści."))
      .not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz pracę" })).toHaveAttribute(
      "href",
      "/merchant"
    );
    expect(screen.getByRole("link", { name: "Otwórz Treści" })).toHaveAttribute(
      "href",
      "/content-workflow"
    );
    expect(screen.queryByRole("link", { name: "Otwórz działanie" })).not.toBeInTheDocument();
    expect(screen.getByText("do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("blokada danych")).toBeInTheDocument();
    expect(screen.getByText(/Zamknięte po review wskazanej akcji/)).toBeInTheDocument();
    expect(screen.queryByText("ready")).not.toBeInTheDocument();
    expect(screen.queryByText("stale")).not.toBeInTheDocument();
    expect(screen.queryByText("Prompt do Codex")).not.toBeInTheDocument();
    expect(screen.queryByText("Kopiuj prompt")).not.toBeInTheDocument();
    expect(screen.queryByText("Kopiuj polecenie")).not.toBeInTheDocument();
    expect(screen.queryByText(/^Codex:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Użyj skilla wilq-merchant-feed-operator/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/potwierdzony ślad|potwierdzonych śladów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bezpieczna akcja do sprawdzenia/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ponowne zatwierdzenie produktu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana pliku produktowego/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wzrost liczby leadów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/gwarancja wzrostu pozycji/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/ev_refresh_/)).not.toBeInTheDocument();
    expect(screen.queryByText(/act_review_merchant_feed_issues/)).not.toBeInTheDocument();
    expect(screen.queryByText("Skill: wilq-merchant-feed-operator")).not.toBeInTheDocument();
    expect(screen.queryByText("Context-pack: /api/codex/context-pack")).not.toBeInTheDocument();
    expect(screen.queryByText(/query\/page=/)).not.toBeInTheDocument();
    expect(screen.queryByText(/average_position=/)).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp("lead " + "up" + "lift"))).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp("ranking " + "guarantee"))).not.toBeInTheDocument();
  });

  it("keeps mobile triage compact without hiding blocker and claim overflow", async () => {
    const blocked = commandCenterFixture.work_orders[1]!;
    vi.mocked(getCommandCenter).mockResolvedValue({
      ...commandCenterFixture,
      work_orders: [
        ...commandCenterFixture.work_orders,
        {
          ...blocked,
          id: "work_order_extra_blocker_1",
          title: "Dodatkowa blokada GA4",
          route_label: "GA4"
        },
        {
          ...blocked,
          id: "work_order_extra_blocker_2",
          title: "Dodatkowa blokada Ads",
          route_label: "Ads"
        }
      ]
    });

    renderCommandCenter();

    const mobile = await screen.findByRole("region", { name: "Mobilny triage dnia" });
    expect(within(mobile).getByText("Pozostałe blokady: 1")).toBeInTheDocument();
    expect(within(mobile).getByText("Pozostałe ograniczenia: 2")).toBeInTheDocument();
  });

  it("renders command decisions from API-owned fields instead of route-local copy maps", async () => {
    const { readFileSync } = await import("node:fs");
    const routeSource = readFileSync("src/routes/CommandCenterRoute.tsx", "utf8");

    expect(routeSource).not.toContain("function decisionCopy");
    expect(routeSource).not.toContain("codexSkillLabel");
    expect(routeSource).not.toContain("marketerConnectorLabel");
    expect(routeSource).not.toContain("routeCtaLabel");
    expect(routeSource).not.toContain("marketerMetricLabel");
    expect(routeSource).not.toContain("marketerBlockedClaimLabels");
    expect(routeSource).not.toContain("priorityLabel");
    expect(routeSource).not.toContain("decisionFreshnessLabel");
    expect(routeSource).not.toContain("function decisionStatusBadgeValue");
    expect(routeSource).not.toContain("item.freshness?.state");
    expect(routeSource).not.toContain("Decyzja / {item.priority_label}");
    expect(routeSource).toContain("item.summary");
    expect(routeSource).toContain("item.status_label");
    expect(routeSource).toContain("item.freshness_label");
    expect(routeSource).toContain("item.source_connector_labels");
    expect(routeSource).toContain("item.blocked_claim_labels");
    expect(routeSource).toContain("item.close_condition");
    expect(routeSource).toContain("DenseQueueTable");
    expect(routeSource).toContain("ForbiddenClaimsInline");
    expect(routeSource).not.toContain("ForbiddenClaimsStrip");
  });
});
