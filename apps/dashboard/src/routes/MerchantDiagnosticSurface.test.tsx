import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("MerchantDiagnosticSurface", () => {
  it("keeps the Merchant operator contract typed and disclosure-safe", () => {
    const routeSource = readFileSync("src/routes/MerchantDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("summary.action_summary_label");
    expect(routeSource).toContain("decision.action_summary_label");
    expect(routeSource).toContain("merchantDecisionQueueTitle");
    expect(routeSource).not.toContain("sample_titles.slice(0, 2).join");
    expect(routeSource).toContain("cluster.reported_issue_summary_label");
    expect(routeSource).toContain("row.ads_clicks_label");
    expect(routeSource).toContain("row.ga4_ecommerce_purchases_label");
    expect(routeSource).toContain("row.ga4_purchase_revenue_label");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain('empty="brak');
    expect(routeSource).not.toContain('row.ads_clicks ?? "brak"');
    expect(routeSource).not.toContain('row.ga4_ecommerce_purchases ?? "brak"');
    expect(routeSource).not.toContain('row.ga4_purchase_revenue ?? "brak"');
    expect(routeSource).toContain("nie oceniaj gotowości połączenia");
    expect(routeSource).toContain("bez odczytu Merchant");
    expect(routeSource).not.toContain("{decision.decision_type_label} /");
    expect(routeSource).not.toContain(" / ${cluster.reporting_context_label}");
    expect(routeSource).not.toContain("formatMerchantIdCount");
    expect(routeSource).not.toContain("function formatPolishCount");
    expect(routeSource).not.toContain("cluster.product_count,");
    expect(routeSource).not.toContain("{item.intent_label} / {item.priority_label}");
  });
});
