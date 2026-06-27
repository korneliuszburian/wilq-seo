import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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
    "WILQ pokazuje tylko metryki z danych źródłowych. Brak danych oznacza blocker, nie domysł marketingowy.",
  primary_next_step: "Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów feedu.",
  blocker_count: 0,
  tactical_item_count: 4,
  daily_decisions: [
    {
      id: "decision_review_merchant_feed_issues",
      title: "Przejrzyj kolejkę problemów Merchant Center",
      domain: "merchant",
      freshness: { state: "fresh" },
      decision_state: "ready",
      route: "/merchant",
      status: "ready",
      priority: 10,
      metric_tiles: {
        produkty: 10900,
        zgłoszenia: 15
      },
      metric_facts: [
        {
          name: "issue_count",
          value: 15,
          period: "connector_refresh",
          source_connector: "google_merchant_center",
          evidence_id: "ev_refresh_merchant_feed",
          dimensions: {}
        }
      ],
      co_widzimy:
        "Merchant Center ma potwierdzone dane problemów feedu.",
      dlaczego_to_ma_znaczenie:
        "Problemy feedu mogą blokować widoczność produktów, ale wymagają ręcznego review.",
      bezpieczny_next_step:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
      why_it_matters:
        "Problemy feedu mogą blokować widoczność produktów, ale wymagają ręcznego review.",
      operator_action:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana feedu"],
      skill_id: "wilq-merchant-feed-operator",
      codex_prompt:
        "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
      codex_context_endpoint: "/api/codex/context-pack",
      expected_codex_output: "Polski brief przeglądu problemów feedu z evidence IDs.",
      risk: "medium"
    },
    {
      id: "decision_prepare_content_refresh_queue",
      title: "Przejrzyj kolejkę SEO z GSC i WordPress",
      domain: "content",
      freshness: { state: "stale" },
      decision_state: "stale",
      route: "/content-planner",
      status: "ready",
      priority: 12,
      metric_tiles: {
        "zapytania/URL": 10,
        "dopasowania WordPress": 15,
        "ocena Ahrefs": 1,
        "luki linków": 9,
        kliknięcia: 138,
        wyświetlenia: 7852
      },
      metric_facts: [
        {
          name: "clicks",
          value: 138,
          period: "connector_refresh",
          source_connector: "google_search_console",
          evidence_id: "ev_refresh_gsc",
          dimensions: {}
        }
      ],
      co_widzimy:
        "Content evidence jest gotowe: zapytania/URL=10, dopasowania WordPress=15, ocena Ahrefs=1, luki linków=9.",
      dlaczego_to_ma_znaczenie: "120 wyświetleń może uzasadniać review treści.",
      bezpieczny_next_step:
        "Otwórz widok Treści i wybierz odświeżenie, scalenie, utworzenie albo blokadę.",
      why_it_matters: "120 wyświetleń może uzasadniać review treści.",
      operator_action:
        "Otwórz widok Treści i wybierz odświeżenie, scalenie, utworzenie albo blokadę.",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      evidence_ids: ["ev_refresh_gsc"],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["wzrost liczby leadów", "gwarancja wzrostu pozycji"],
      skill_id: "wilq-content-strategist",
      codex_prompt:
        "Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh.",
      codex_context_endpoint: "/api/codex/context-pack",
      expected_codex_output: "Polski content brief bez obietnic pozycji.",
      risk: "low"
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

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument()
    );

    expect(screen.getByText("Dzisiejsze decyzje marketera")).toBeInTheDocument();
    expect(
      screen.getByText("Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów feedu.")
    ).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj problemy produktów w Merchant Center")).toBeInTheDocument();
    expect(
      screen.getByText("Ułóż kolejkę odświeżenia i scalania treści SEO")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/WILQ widzi 10\s?900 produktów i 15 zgłoszeń problemów feedu/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/WILQ ma 10 par zapytanie-URL z GSC, 138 kliknięć i 7852 wyświetleń/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Najpierw sprawdź dopasowania WordPress/)).not.toBeInTheDocument();
    expect(screen.getByText(/To jest materiał do decyzji: odświeżyć, scalić, utworzyć albo zablokować/))
      .toBeInTheDocument();
    expect(screen.getByText("10900")).toBeInTheDocument();
    expect(screen.getByText("zapytania/URL")).toBeInTheDocument();
    expect(screen.getByText("dopasowania WordPress")).toBeInTheDocument();
    expect(screen.getByText("ocena Ahrefs")).toBeInTheDocument();
    expect(screen.getByText("luki linków")).toBeInTheDocument();
    expect(screen.getByText("Polecenie: feed Merchant")).toBeInTheDocument();
    expect(screen.getByText("Polecenie: strategia treści")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Kopiuj polecenie" })).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Otwórz Merchant" })).toHaveAttribute(
      "href",
      "/merchant"
    );
    expect(screen.getByRole("link", { name: "Otwórz Content Planner" })).toHaveAttribute(
      "href",
      "/content-planner"
    );
    expect(screen.queryByRole("link", { name: "Otwórz działanie" })).not.toBeInTheDocument();
    expect(screen.getByText("gotowe")).toBeInTheDocument();
    expect(screen.getByText("do odświeżenia")).toBeInTheDocument();
    expect(screen.getByText(/Świeżość źródeł: świeże/)).toBeInTheDocument();
    expect(screen.getByText(/Świeżość źródeł: do odświeżenia/)).toBeInTheDocument();
    expect(screen.queryByText("Prompt do Codex")).not.toBeInTheDocument();
    expect(screen.queryByText("Kopiuj prompt")).not.toBeInTheDocument();
    expect(screen.queryByText(/^Codex:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Użyj skilla wilq-merchant-feed-operator/)).not.toBeInTheDocument();
    expect(screen.getByText("Źródła i ograniczenia")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz ustawienia" })).toBeInTheDocument();
    expect(screen.getAllByText(/potwierdzony ślad|potwierdzonych śladów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bezpieczna akcja do sprawdzenia/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ponowne zatwierdzenie produktu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana feedu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wzrost liczby leadów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/gwarancja wzrostu pozycji/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/ev_refresh_/)).not.toBeInTheDocument();
    expect(screen.queryByText(/act_review_merchant_feed_issues/)).not.toBeInTheDocument();
    expect(screen.queryByText("Skill: wilq-merchant-feed-operator")).not.toBeInTheDocument();
    expect(screen.queryByText("Context-pack: /api/codex/context-pack")).not.toBeInTheDocument();
    expect(screen.queryByText(/query\/page=/)).not.toBeInTheDocument();
    expect(screen.queryByText(/average_position=/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Content evidence jest gotowe/)).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp("lead " + "uplift"))).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp("ranking " + "guarantee"))).not.toBeInTheDocument();
  });
});
