import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ContentInventoryCatalogResponse } from "../lib/api";
import {
  compareInventoryItems,
  inventoryWorkItemIdFor,
  inventoryStructureLabel,
  InventoryWorkflowStartingPanel,
  matchesInventoryView
} from "./ContentInventoryCatalogPanel";

const item = {
  catalog_id: "catalog_1",
  work_item_id: "content_work_item_inventory_1",
  url: "https://www.ekologus.pl/artykul/",
  path: "/artykul/",
  title: "Przykładowy artykuł",
  content_type: "posts",
  material_status: "content_summary",
  metrics_status: "available",
  metrics_clicks: 12,
  metrics_impressions: 240,
  metrics_query_count: 4,
  metrics_evidence_ids: ["ev_gsc_1"],
  acf_section_count: 0,
  acf_section_headings: [],
  acf_field_names: [],
  content_summary: "Skrót",
  content_word_count: 180
} as unknown as ContentInventoryCatalogResponse["items"][number];

describe("InventoryWorkflowStartingPanel", () => {
  it("shows the selected page and real catalog signals before binding resolves", () => {
    render(<InventoryWorkflowStartingPanel item={item} isPending error={null} />);

    expect(screen.getByTestId("content-inventory-workflow-starting")).toHaveTextContent(
      "Przygotowuję workflow"
    );
    expect(screen.getByText("240 wyświetleń · 12 kliknięć")).toBeInTheDocument();
    expect(screen.getByText(/Strona jest już wybrana/)).toBeInTheDocument();
  });
});

describe("compareInventoryItems", () => {
  it("keeps existing workflow candidates before material and metric fallbacks", () => {
    const readyWithMetrics = { ...item, url: "https://www.ekologus.pl/ready/", path: "/ready/" };
    const queuedUrlOnly = {
      ...item,
      url: "https://www.ekologus.pl/queued/",
      path: "/queued/",
      material_status: "url_only" as const,
      metrics_status: "missing" as const,
      metrics_impressions: 0
    } as typeof item;

    expect(
      compareInventoryItems(queuedUrlOnly, readyWithMetrics, new Map([["/queued", "work_item_1"]]))
    ).toBeLessThan(0);
  });
});

describe("inventoryWorkItemIdFor", () => {
  it("opens any catalog page directly without a blocking bind read", () => {
    expect(inventoryWorkItemIdFor(item, new Map())).toBe("content_work_item_inventory_1");
    expect(
      inventoryWorkItemIdFor(item, new Map([["/artykul", "content_work_item_queue_1"]]))
    ).toBe("content_work_item_queue_1");
  });
});

describe("matchesInventoryView", () => {
  it("keeps a URL-only page selectable when it has real metrics", () => {
    const metricsOnly = {
      ...item,
      material_status: "url_only" as const,
      metrics_status: "available" as const
    } as typeof item;

    expect(matchesInventoryView(metricsOnly, "ready")).toBe(false);
    expect(matchesInventoryView(metricsOnly, "metrics")).toBe(true);
    expect(matchesInventoryView(metricsOnly, "all")).toBe(true);
  });
});

describe("inventoryStructureLabel", () => {
  it("distinguishes the_content headings from ACF layouts", () => {
    expect(inventoryStructureLabel({ ...item, section_count: 4 })).toBe(
      "4 nagłówków w treści strony"
    );
    expect(
      inventoryStructureLabel({
        ...item,
        acf_section_count: 2,
        acf_section_headings: ["Hero", "CTA"]
      })
    ).toBe("ACF: Hero · CTA");
  });
});
