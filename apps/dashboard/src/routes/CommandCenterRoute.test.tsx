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
    "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, nie domysł marketingowy.",
  primary_next_step: "Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu.",
  blocker_count: 0,
  tactical_item_count: 4,
  daily_decisions: [
    {
      id: "decision_review_merchant_feed_issues",
      title: "Przejrzyj kolejkę problemów Merchant Center",
      route: "/merchant",
      status: "ready",
      priority: 10,
      metric_tiles: {
        produkty: 10900,
        issues: 15
      },
      co_widzimy:
        "Merchant Center ma evidence `ev_refresh_merchant_feed` i ActionObject `act_review_merchant_feed_issues`.",
      dlaczego_to_ma_znaczenie:
        "Problemy feedu mogą blokować widoczność produktów, ale wymagają ręcznego review.",
      bezpieczny_next_step:
        "Otwórz /merchant, sprawdź issue queue i waliduj `act_review_merchant_feed_issues`.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["approval restored", "automatic feed edit"],
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
      route: "/content-planner",
      status: "ready",
      priority: 12,
      metric_tiles: {
        "query/page": 10,
        "WP match": 15
      },
      co_widzimy: "Content evidence jest gotowe.",
      dlaczego_to_ma_znaczenie: "120 wyświetleń może uzasadniać review treści.",
      bezpieczny_next_step: "Otwórz /content-planner i wybierz refresh, merge, create albo block.",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      evidence_ids: ["ev_refresh_gsc"],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["lead uplift", "ranking guarantee"],
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
      screen.getByText("Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu.")
    ).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj kolejkę problemów Merchant Center")).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj kolejkę SEO z GSC i WordPress")).toBeInTheDocument();
    expect(screen.getByText("10900")).toBeInTheDocument();
    expect(screen.getAllByText("Prompt do Codex")).toHaveLength(2);
    expect(screen.getByText("Tryb Codexa: Merchant Feed Operator")).toBeInTheDocument();
    expect(screen.getByText("Źródła i ograniczenia")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz ustawienia" })).toBeInTheDocument();
    expect(screen.getAllByText(/potwierdzony ślad|potwierdzonych śladów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bezpieczna akcja do walidacji/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ponowne zatwierdzenie produktu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana feedu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wzrost leadów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/gwarancja pozycji/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/ev_refresh_/)).not.toBeInTheDocument();
    expect(screen.queryByText(/act_review_merchant_feed_issues/)).not.toBeInTheDocument();
    expect(screen.queryByText("Skill: wilq-merchant-feed-operator")).not.toBeInTheDocument();
    expect(screen.queryByText("Context-pack: /api/codex/context-pack")).not.toBeInTheDocument();
    expect(screen.queryByText(/approval restored/)).not.toBeInTheDocument();
    expect(screen.queryByText(/automatic feed edit/)).not.toBeInTheDocument();
    expect(screen.queryByText(/lead uplift/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ranking guarantee/)).not.toBeInTheDocument();
  });
});
