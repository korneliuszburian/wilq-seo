import { describe, expect, it } from "vitest";

import { ContentPreflightResponseSchema, MerchantDiagnosticsResponseSchema } from "./index";

describe("MerchantDiagnosticsResponseSchema", () => {
  it("accepts Merchant price-impact readiness decisions returned by the API", () => {
    const response = {
      generated_at: "2026-06-24T03:12:30Z",
      language: "pl-PL",
      strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
      connector: {
        id: "google_merchant_center",
        label: "Merchant Center",
        status: "configured",
        configured: true,
        missing_credentials: [],
        available_credential_sources: ["repo_env"],
        freshness: { state: "fresh" },
        supported_actions: ["merchant_feed_issue"]
      },
      latest_refresh: {
        id: "refresh_google_merchant_center_live",
        connector_id: "google_merchant_center",
        mode: "vendor_read",
        status: "completed",
        started_at: "2026-06-24T03:04:00Z",
        completed_at: "2026-06-24T03:04:08Z",
        evidence_ids: ["ev_refresh_merchant_feed"],
        missing_credentials: [],
        checked_credentials: ["GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"],
        external_call_attempted: true,
        vendor_data_collected: true,
        metric_summary: { total_products: 10776 },
        summary: "Merchant Center vendor read completed.",
        errors: [],
        redacted: true
      },
      live_data_available: true,
      product_count: 10776,
      issue_count: 19,
      freshness_assessment: {
        state: "fresh",
        checked_at: "2026-06-24T03:12:30Z",
        latest_refresh_id: "refresh_google_merchant_center_live",
        latest_refresh_completed_at: "2026-06-24T03:04:08Z",
        age_hours: 0.14,
        stale_after_hours: 48,
        requires_refresh: false,
        summary: "Merchant data is fresh.",
        next_step: "Use review queue."
      },
      unknowns: [],
      product_sample_readiness: {
        status: "ready",
        sample_products_available: true,
        sample_count: 1,
        sample_product_ids: ["pl~PL~gla_107394"],
        sample_product_titles: ["Produkt testowy"],
        current_read_contract: "merchant_aggregate_product_statuses",
        required_read_contracts: ["merchant_products_list_product_status"],
        source_endpoint: "aggregateProductStatuses",
        summary: "Samples are available.",
        next_step: "Review samples.",
        blocked_claims: ["feed write"]
      },
      product_performance_readiness: {
        id: "merchant_product_performance_readiness",
        status: "blocked",
        joined_product_count: 0,
        merchant_sample_count: 1,
        ads_product_fact_count: 0,
        ga4_product_fact_count: 0,
        current_read_contracts: ["merchant_aggregate_product_statuses"],
        required_read_contracts: ["google_ads_shopping_product_performance"],
        missing_read_contracts: ["google_ads_shopping_product_performance"],
        join_key_candidates: ["product_id"],
        sample_product_ids: ["pl~PL~gla_107394"],
        performance_rows: [],
        source_connectors: ["google_merchant_center"],
        evidence_ids: ["ev_refresh_merchant_feed"],
        summary: "Product performance is blocked.",
        next_step: "Collect product performance facts.",
        blocked_claims: ["product ROAS"]
      },
      price_impact_readiness: {
        id: "merchant_price_impact_readiness",
        status: "blocked",
        products_with_current_price: 1,
        products_with_previous_price: 1,
        products_with_price_change: 0,
        products_with_unchanged_price_history: 1,
        products_with_performance_metrics: 0,
        current_read_contracts: ["google_ads_shopping_product_current_price"],
        required_read_contracts: ["merchant_price_change_event_or_snapshot"],
        missing_read_contracts: ["merchant_price_change_event_or_snapshot"],
        payload_preview: [],
        source_connectors: ["google_merchant_center", "google_ads"],
        evidence_ids: ["ev_refresh_merchant_feed", "ev_refresh_google_ads_products"],
        summary: "Price impact is blocked.",
        next_step: "Collect price change event and performance window.",
        blocked_claims: ["price change impact"]
      },
      operator_summary: {
        id: "merchant_operator_summary",
        title: "Merchant operator summary",
        summary: "Review only.",
        next_step: "Review decision queue.",
        top_decision_ids: ["merchant_decision_review_price_impact_readiness"],
        top_issue_cluster_ids: [],
        top_tactical_item_ids: [],
        reported_issue_occurrences: 0,
        decision_source: "decision_queue",
        drilldown_source: "issue_clusters",
        count_semantics: "reported_issue_occurrences",
        issue_types: [],
        source_connectors: ["google_merchant_center"],
        evidence_ids: ["ev_refresh_merchant_feed"],
        action_ids: ["act_review_merchant_feed_issues"],
        blocked_claims: ["feed write"]
      },
      issue_clusters: [],
      decision_queue: [
        {
          id: "merchant_decision_review_price_impact_readiness",
          decision_type: "review_price_impact_readiness",
          status: "blocked",
          title: "Merchant: sprawdz gotowosc price impact",
          summary: "Price impact remains blocked until required read contracts exist.",
          priority: 30,
          metric_tiles: { produkty: 1 },
          source_connectors: ["google_merchant_center", "google_ads"],
          evidence_ids: ["ev_refresh_merchant_feed", "ev_refresh_google_ads_products"],
          metric_facts: [],
          action_ids: ["act_review_merchant_feed_issues"],
          blocked_claims: ["price change impact"],
          rationale: "This is a readiness decision, not a product mutation.",
          next_step: "Show missing read contracts before any recommendation.",
          risk: "medium"
        }
      ],
      sections: [],
      evidence_ids: ["ev_refresh_merchant_feed"],
      action_ids: ["act_review_merchant_feed_issues"],
      blocker_count: 0
    };

    const result = MerchantDiagnosticsResponseSchema.safeParse(response);

    expect(result.success).toBe(true);
  });
});

describe("ContentPreflightResponseSchema", () => {
  it("accepts first-class content preflight contracts", () => {
    const item = {
      id: "preflight_content_decision_bdo",
      technical_decision_id: "content_decision_bdo",
      recommended_mode: "refresh",
      status: "review_required",
      create_allowed: false,
      draft_allowed: false,
      wordpress_draft_allowed: false,
      sales_brief_allowed: true,
      source_public_url: "https://www.ekologus.pl/bdo/",
      preview_url: null,
      intended_final_url: "https://www.ekologus.pl/bdo/",
      final_canonical_url: "https://www.ekologus.pl/bdo/",
      inventory_gate_status: "confirmed_current_inventory",
      canonical_gate_status: "current_url_confirmed",
      duplicate_gate_status: "refresh_or_merge_required",
      claim_gate_status: "needs_claim_review",
      service_mapping_status: "ready_for_service_review",
      similar_existing_urls: ["https://www.ekologus.pl/bdo/"],
      query_overlap_summary: "1 zapytań z GSC; główne zapytanie: bdo.",
      blocked_claims: ["ranking guarantee"],
      missing_inputs: [],
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      next_step: "Przygotuj sales brief odświeżenia dopiero po sprawdzeniu claimów."
    };
    const response = {
      generated_at: "2026-06-26T08:00:00Z",
      language: "pl-PL",
      strict_instruction: "ContentPreflight is required before writing.",
      primary_item: item,
      items: [item],
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      blocker_count: 0
    };

    const result = ContentPreflightResponseSchema.safeParse(response);

    expect(result.success).toBe(true);
  });
});
