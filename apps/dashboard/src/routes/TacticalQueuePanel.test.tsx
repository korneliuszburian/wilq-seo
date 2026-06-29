import { cleanup, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TacticalQueueResponse } from "../lib/api";
import { TacticalQueuePanel } from "./TacticalQueuePanel";

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

const queue: TacticalQueueResponse = {
  generated_at: "2026-06-23T10:00:00Z",
  language: "pl-PL",
  strict_instruction:
    "WILQ pokazuje tylko metryki z danych źródłowych. Brak danych oznacza blocker, nie domysł marketingowy.",
  items: [
    {
      id: "tq_gsc_zielony_lad_a",
      title: "GSC: zielony ład co to -> /europejski-zielony-lad-co-to-takiego/",
      domain: "gsc_seo",
      domain_label: "Treści i GSC",
      intent: "content_create",
      intent_label: "nowa treść",
      priority: 17,
      priority_label: "wysoki priorytet",
      risk: "low",
      risk_label: "niskie ryzyko",
      source_connectors: ["google_search_console"],
      source_connector_labels: ["Google Search Console"],
      evidence_ids: ["ev_refresh_gsc_a"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [],
      dimensions: {
        query: "zielony ład co to",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
        wordpress_match_confidence: "exact_url"
      },
      dimension_labels: {
        query: "zapytanie",
        page: "strona",
        wordpress_match_confidence: "pewność dopasowania"
      },
      dimension_value_labels: {
        query: "zielony ład co to",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
        wordpress_match_confidence: "dokładny adres URL"
      },
      diagnosis: "Raw query/page item.",
      next_step: "Przygotuj plan treści po sprawdzeniu spisu treści.",
      blocked_claims: ["gwarancja pozycji"],
      blocked_claim_labels: ["gwarancja pozycji"],
      action_ids: ["act_prepare_content_refresh_queue"],
      action_summary_label: "1 akcja do sprawdzenia"
    },
    {
      id: "tq_gsc_zielony_lad_b",
      title: "GSC: co to jest zielony ład -> /europejski-zielony-lad-co-to-takiego/",
      domain: "gsc_seo",
      domain_label: "Treści i GSC",
      intent: "content_create",
      intent_label: "nowa treść",
      priority: 18,
      priority_label: "wysoki priorytet",
      risk: "low",
      risk_label: "niskie ryzyko",
      source_connectors: ["google_search_console"],
      source_connector_labels: ["Google Search Console"],
      evidence_ids: ["ev_refresh_gsc_b"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [],
      dimensions: {
        query: "co to jest zielony ład",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
      },
      dimension_labels: {
        query: "zapytanie",
        page: "strona"
      },
      dimension_value_labels: {
        query: "co to jest zielony ład",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
      },
      diagnosis: "Raw query/page item.",
      next_step: "Przygotuj plan treści po sprawdzeniu spisu treści.",
      blocked_claims: ["gwarancja pozycji"],
      blocked_claim_labels: ["gwarancja pozycji"],
      action_ids: ["act_prepare_content_refresh_queue"],
      action_summary_label: "1 akcja do sprawdzenia"
    }
  ],
  compact_groups: [
    {
      id: "gsc_seo:content_create:https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
      title: "SEO: zweryfikuj treść /europejski-zielony-lad-co-to-takiego/ (2 query)",
      meta: "Obszar: Treści i GSC. Zadanie: nowa treść. Priorytet: najpierw.",
      diagnosis:
        "2 powiązane zapytania prowadzą do tej samej strony. Suma widocznych metryk: kliknięcia: 70, wyświetlenia: 1666.",
      next_step: "Najpierw sprawdź duplikaty w WordPress.",
      priority: 17,
      priority_label: "wysoki priorytet",
      risk: "low",
      risk_label: "niskie ryzyko",
      source_connectors: ["google_search_console"],
      source_connector_labels: ["Google Search Console"],
      evidence_ids: ["ev_refresh_gsc_a", "ev_refresh_gsc_b"],
      evidence_summary_label: "2 dowody źródłowe",
      action_ids: ["act_prepare_content_refresh_queue"],
      action_summary_label: "1 akcja do sprawdzenia",
      blocked_claims: ["gwarancja pozycji"],
      blocked_claim_labels: ["gwarancja pozycji"]
    }
  ],
  evidence_ids: ["ev_refresh_gsc_a", "ev_refresh_gsc_b"],
  action_ids: ["act_prepare_content_refresh_queue"]
};

describe("TacticalQueuePanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders full tactical cards with summaries before technical trace IDs", () => {
    render(
      <TacticalQueuePanel
        queue={queue}
        title="Taktyki z WILQ"
        isLoading={false}
        isError={false}
      />
    );

    const section = screen.getByText("Taktyki z WILQ").closest("section");
    expect(section).not.toBeNull();
    const scope = within(section as HTMLElement);

    expect(section?.textContent).toContain("1 dowód źródłowy");
    expect(section?.textContent).toContain("1 akcja do sprawdzenia");
    expect(section?.textContent).toContain("Obszar: Treści i GSC");
    expect(section?.textContent).toContain("Zadanie: nowa treść");
    expect(section?.textContent).toContain("Priorytet: wysoki priorytet");
    expect(section?.textContent).not.toMatch(/[A-Za-zĄ-Żąćęłńóśźż ]+ \/ [A-Za-zĄ-Żąćęłńóśźż ]+ \/ [A-Za-zĄ-Żąćęłńóśźż ]+/);
    expect(scope.getAllByText("Szczegóły techniczne").length).toBeGreaterThan(0);
    expect(section?.textContent).toContain("Dowody źródłowe");
    expect(section?.textContent).toContain("Akcje do sprawdzenia");
    expect(scope.getAllByRole("link", { name: "dowód 1" }).length).toBeGreaterThan(0);
    expect(scope.getAllByRole("link", { name: "akcja 1" }).length).toBeGreaterThan(0);
    expect(section?.textContent).toContain("pewność dopasowania: dokładny adres URL");
    expect(section?.textContent).not.toContain("exact_url");
  });

  it("renders compact decision groups without raw evidence or action IDs", () => {
    render(
      <TacticalQueuePanel
        queue={queue}
        compact
        title="Taktyki z WILQ"
        isLoading={false}
        isError={false}
      />
    );

    const section = screen.getByText("Taktyki z WILQ").closest("section");
    expect(section).not.toBeNull();
    const scope = within(section as HTMLElement);

    expect(
      scope.getByText("SEO: zweryfikuj treść /europejski-zielony-lad-co-to-takiego/ (2 query)")
    ).toBeInTheDocument();
    expect(scope.queryByText(/GSC: zielony ład co to/)).not.toBeInTheDocument();
    expect(scope.queryByText(/ev_refresh_gsc_/)).not.toBeInTheDocument();
    expect(scope.queryByText(/act_prepare_content_refresh_queue/)).not.toBeInTheDocument();
    expect(scope.getAllByText("Dowody").length).toBeGreaterThan(0);
    expect(section?.textContent).toContain("2 dowody źródłowe");
    expect(section?.textContent).toContain("Akcje");
    expect(section?.textContent).toContain("1 akcja do sprawdzenia");
    const routeSource = readFileSync("src/routes/TacticalQueuePanel.tsx", "utf8");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("{item.domain_label} / {item.intent_label} / {item.priority_label}");
  });
});
