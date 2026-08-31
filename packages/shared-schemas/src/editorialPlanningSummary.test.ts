import { describe, expect, it } from "vitest";

import { ContentPlanningInputSummarySchema } from "./contentWorkflow";

const sources = [
  "wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs",
  "keyword_planner", "merchant", "localo", "social"
] as const;

const summary = {
  final_canonical_url: "https://www.ekologus.pl/artykul/",
  inventory_status: "available" as const,
  content_inventory_status: "available" as const,
  acf_section_inventory_status: "missing" as const,
  source_assessments: sources.map((source) => ({
    source, status: "not_applicable" as const, reason: "Testowy stan źródła."
  })),
  source_fact_count: 0,
  evidence_id_count: 0,
  knowledge_card_count: 0
};

describe("editorial planning summary", () => {
  it("accepts editorial without a service label", () => {
    expect(ContentPlanningInputSummarySchema.safeParse({
      ...summary, content_kind: "editorial", service_label: null
    }).success).toBe(true);
  });

  it("keeps service summaries label-bound", () => {
    expect(ContentPlanningInputSummarySchema.safeParse({
      ...summary, content_kind: "service", service_label: null
    }).success).toBe(false);
  });
});
