import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TacticalQueueResponse } from "../lib/api";
import { TacticalQueuePanel } from "./TacticalQueuePanel";

const queue: TacticalQueueResponse = {
  generated_at: "2026-06-23T10:00:00Z",
  language: "pl-PL",
  strict_instruction:
    "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, nie domysł marketingowy.",
  items: [
    {
      id: "tq_gsc_zielony_lad_a",
      title: "GSC: zielony ład co to -> /europejski-zielony-lad-co-to-takiego/",
      domain: "gsc_seo",
      intent: "content_create",
      priority: 17,
      risk: "low",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc_a"],
      metric_facts: [],
      dimensions: {
        query: "zielony ład co to",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
      },
      diagnosis: "Raw query/page item.",
      next_step: "Przygotuj brief po sprawdzeniu inventory.",
      blocked_claims: ["ranking guarantee"],
      action_ids: ["act_prepare_content_refresh_queue"]
    },
    {
      id: "tq_gsc_zielony_lad_b",
      title: "GSC: co to jest zielony ład -> /europejski-zielony-lad-co-to-takiego/",
      domain: "gsc_seo",
      intent: "content_create",
      priority: 18,
      risk: "low",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc_b"],
      metric_facts: [],
      dimensions: {
        query: "co to jest zielony ład",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
      },
      diagnosis: "Raw query/page item.",
      next_step: "Przygotuj brief po sprawdzeniu inventory.",
      blocked_claims: ["ranking guarantee"],
      action_ids: ["act_prepare_content_refresh_queue"]
    }
  ],
  compact_groups: [
    {
      id: "gsc_seo:content_create:https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
      title: "SEO: zweryfikuj treść /europejski-zielony-lad-co-to-takiego/ (2 query)",
      meta: "SEO / nowa treść / najpierw",
      diagnosis:
        "2 powiązane zapytania prowadzą do tej samej strony. Suma widocznych metryk: clicks=70, impressions=1666.",
      next_step: "Najpierw sprawdź duplikaty w WordPress.",
      priority: 17,
      risk: "low",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc_a", "ev_refresh_gsc_b"],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["ranking guarantee"]
    }
  ],
  evidence_ids: ["ev_refresh_gsc_a", "ev_refresh_gsc_b"],
  action_ids: ["act_prepare_content_refresh_queue"]
};

describe("TacticalQueuePanel", () => {
  it("renders compact decision groups without raw evidence or action IDs", () => {
    render(
      <TacticalQueuePanel
        queue={queue}
        compact
        title="Taktyki z WILQ API"
        isLoading={false}
        isError={false}
      />
    );

    const section = screen.getByText("Taktyki z WILQ API").closest("section");
    expect(section).not.toBeNull();
    const scope = within(section as HTMLElement);

    expect(
      scope.getByText("SEO: zweryfikuj treść /europejski-zielony-lad-co-to-takiego/ (2 query)")
    ).toBeInTheDocument();
    expect(scope.queryByText(/GSC: zielony ład co to/)).not.toBeInTheDocument();
    expect(scope.queryByText(/ev_refresh_gsc_/)).not.toBeInTheDocument();
    expect(scope.queryByText(/act_prepare_content_refresh_queue/)).not.toBeInTheDocument();
    expect(scope.getAllByText("Dowody").length).toBeGreaterThan(0);
    expect(section?.textContent).toContain("2 ID");
    expect(section?.textContent).toContain("Akcje");
  });
});
