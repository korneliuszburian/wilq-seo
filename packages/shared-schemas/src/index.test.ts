import { describe, expect, it } from "vitest";

import {
  ContentWorkItemDraftPackageResponseSchema,
  ContentWorkItemHumanReviewResponseSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  ContentWorkItemPreflightResponseSchema,
  ContentWorkItemSalesBriefResponseSchema,
  ContentWorkItemSnapshotAuditRequestSchema,
  ContentWorkItemSnapshotHumanReviewRequestSchema,
  ContentWorkItemStructuredDraftGenerationResponseSchema,
  ContentWorkItemStructuredDraftPreviewResponseSchema,
  ContentWorkItemStructuredDraftRuntimeResponseSchema,
  ContentWorkItemWordPressDraftExecutionRequestSchema,
  ContentWorkItemWordPressDraftExecutionResponseSchema,
  ContentWorkItemWordPressDraftHandoffResponseSchema,
  ContentWorkItemWorkflowSnapshotResponseSchema,
  ContentPreflightResponseSchema,
  MerchantDiagnosticsResponseSchema
} from "./index";

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
      canonical_gate_status: "public_canonical_confirmed",
      duplicate_gate_status: "existing_public_content_requires_refresh_or_merge",
      claim_gate_status: "needs_claim_review",
      service_fit_status: "ready_for_service_review",
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

describe("Content work item workflow schemas", () => {
  const item = {
    id: "content_work_item_bdo",
    topic: "BDO dla firm",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    inventory_status: "resolved",
    canonical_status: "resolved",
    duplicate_status: "checked",
    preflight_status: "handoff_allowed",
    preserve_first_plan_status: "approved",
    sales_brief_status: "approved",
    sales_brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_status: "approved",
    claim_ledger_id: "claim_ledger_bdo",
    draft_package_status: "ready",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_status: "approved",
    human_review_id: "human_review_bdo",
    wordpress_handoff_status: "prepared",
    wordpress_post_id: null,
    measurement_window_status: "planned",
    measurement_window_id: "measurement_window_content_work_item_bdo",
    audit_status: "recorded",
    audit_id: "audit_bdo"
  };

  const blocker = {
    code: "measurement_window_not_ready",
    label: "Nie wolno jeszcze oceniać efektu",
    reason: "Okno obserwacji jeszcze trwa.",
    next_step: "Wróć po earliest_verdict_date."
  };

  it("accepts Goal 002 work item workflow API response shapes", () => {
    expect(
      ContentWorkItemPreflightResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "plan_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: false,
          draft_allowed: false,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Zatwierdź preserve-first plan."
        }
      }).success
    ).toBe(true);

    const brief = {
      id: "sales_brief_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      topic: "BDO dla firm",
      target_reader: "właściciel firmy",
      buyer_problem: "nie wie, jak podejść do BDO",
      buyer_trigger: "zbliża się kontrola",
      search_intent: "informacyjno-usługowy",
      service_fit: "obsługa środowiskowa",
      source_public_url: "https://ekologus.pl/bdo/",
      final_canonical_url: "https://ekologus.pl/bdo/",
      intended_final_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      existing_content_plan: "Zacznij od istniejącej treści.",
      h1_direction: "BDO dla firm",
      h2_direction: ["Kogo dotyczy BDO"],
      faq_direction: ["Czy każda firma musi mieć BDO?"],
      cta_direction: "Skontaktuj się z Ekologus.",
      internal_link_direction: ["https://ekologus.pl/kontakt/"],
      source_facts: [
        {
          evidence_id: "ev_gsc_bdo",
          source_connector: "google_search_console",
          summary: "GSC pokazuje popyt na temat BDO."
        }
      ],
      forbidden_claims: [],
      missing_evidence: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      measurement_plan: {
        measurement_window_id: "measurement_window_content_work_item_bdo",
        metrics_to_watch: ["GSC clicks"],
        earliest_verdict_note: "Nie oceniaj przed końcem okna.",
        success_claim_rule: "Nie claimuj sukcesu bez danych."
      },
      human_review_required: true,
      draft_allowed: false
    };

    expect(
      ContentWorkItemSalesBriefResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "brief_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: true,
          draft_allowed: false,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Przygotuj Sales Brief."
        },
        sales_brief_result: { brief, blockers: [] }
      }).success
    ).toBe(true);

    const draftPackage = {
      id: "draft_package_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      brief_id: "sales_brief_content_work_item_bdo",
      claim_ledger_id: "claim_ledger_bdo",
      draft_kind: "outline",
      title: "BDO dla firm",
      sections: [],
      section_to_evidence_map: [],
      claims_used: [],
      claims_removed_or_blocked: [],
      human_review_questions: ["Czy to brzmi jak Ekologus?"],
      publish_ready: false
    };

    expect(
      ContentWorkItemDraftPackageResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "draft_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: true,
          draft_allowed: true,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Przygotuj Draft Package."
        },
        sales_brief_result: { brief, blockers: [] },
        draft_package_result: { draft_package: draftPackage, blockers: [] }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftGenerationResponseSchema.safeParse({
        item,
        structured_generation_result: {
          contract: {
            schema_name: "wilq_content_structured_draft_v1",
            strict_schema: true,
            model_input: {
              work_item_id: "content_work_item_bdo",
              language: "pl-PL",
              draft_kind: "section_draft",
              title: "BDO dla firm",
              final_canonical_url: "https://ekologus.pl/bdo/",
              source_public_url: "https://ekologus.pl/bdo/",
              preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
              target_reader: "właściciel firmy",
              buyer_problem: "nie wie, jak podejść do BDO",
              buyer_trigger: "zbliża się kontrola",
              search_intent: "informacyjno-usługowy",
              service_fit: "obsługa środowiskowa",
              cta_direction: "Skontaktuj się z Ekologus.",
              sections: [
                {
                  heading: "Kogo dotyczy BDO",
                  purpose: "Sekcja konspektu do napisania po sprawdzeniu planu.",
                  evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
                  draft_notes: ["Zachowaj kierunek H1"]
                }
              ],
              source_facts: [
                {
                  evidence_id: "ev_gsc_bdo",
                  source_connector: "google_search_console",
                  summary: "GSC pokazuje popyt na temat BDO."
                }
              ],
              claims_allowed: ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
              claims_removed_or_blocked: [],
              human_review_questions: ["Czy to brzmi jak Ekologus?"]
            },
            output_schema: {
              type: "object",
              additionalProperties: false,
              properties: { sections: { type: "array" } }
            },
            system_instruction: "Pisz wyłącznie z przekazanych faktów.",
            user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
            publish_ready: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftRuntimeResponseSchema.safeParse({
        runtime_result: {
          status: "dry_run_ready",
          request_payload: {
            model: "gpt-5",
            input: [
              {
                role: "system",
                content: "Pisz wyłącznie z przekazanych faktów."
              },
              {
                role: "user",
                content: "Przygotuj ustrukturyzowany szkic treści dla WILQ."
              }
            ],
            text: {
              format: {
                type: "json_schema",
                name: "wilq_content_structured_draft_v1",
                strict: true,
                schema: {
                  type: "object",
                  additionalProperties: false,
                  properties: { sections: { type: "array" } }
                }
              }
            },
            temperature: 0.2,
            max_output_tokens: 4000
          },
          output: null,
          external_call_attempted: false,
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemHumanReviewResponseSchema.safeParse({
        item,
        reviewed_item: item,
        review: null,
        blockers: [
          {
            code: "missing_human_review",
            label: "Brakuje decyzji człowieka",
            reason: "Snapshot nie może udawać zatwierdzonego review.",
            next_step: "Zatwierdź brief, claimy i paczkę szkicu."
          }
        ],
        wordpress_handoff_allowed: false
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemHumanReviewResponseSchema.safeParse({
        item,
        reviewed_item: item,
        review: {
          id: "human_review_bdo",
          work_item_id: "content_work_item_bdo",
          stage: "draft_package",
          reviewed_by: "wilku",
          decision: "approved",
          notes: "Może iść dalej.",
          checked_items: ["claimy sprawdzone"],
          evidence_ids: ["ev_gsc_bdo"],
          blocked_claims_handled: [],
          draft_package_id: "draft_package_content_work_item_bdo"
        },
        blockers: [],
        wordpress_handoff_allowed: true
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftPreviewResponseSchema.safeParse({
        preview_result: {
          preview: {
            title: "BDO dla firm",
            meta_title: "BDO dla firm",
            meta_description: "Sprawdź, kiedy warto skonsultować BDO.",
            h1: "BDO dla firm",
            sections: [
              {
                heading: "Kogo dotyczy BDO",
                body_markdown: "BDO warto sprawdzić na podstawie sytuacji firmy.",
                evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
                claims_used: ["Ekologus pomaga firmom uporządkować obowiązki BDO."]
              }
            ],
            faq: ["Czy każda firma musi mieć BDO?"],
            cta: "Skontaktuj się z Ekologus, żeby omówić sytuację firmy.",
            internal_links: ["https://ekologus.pl/kontakt/"],
            source_facts_used: ["ev_gsc_bdo", "ev_wp_bdo"],
            forbidden_claims_avoided: ["Ta treść zwiększy liczbę leadów."],
            human_review_checklist: ["Czy to brzmi jak Ekologus?"],
            publish_ready: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemSnapshotHumanReviewRequestSchema.safeParse({
        review: {
          id: "human_review_bdo",
          work_item_id: "content_work_item_bdo",
          stage: "draft_package",
          reviewed_by: "wilku",
          decision: "approved",
          notes: "Może iść dalej.",
          checked_items: ["claimy sprawdzone"],
          evidence_ids: ["ev_gsc_bdo"],
          blocked_claims_handled: [],
          draft_package_id: "draft_package_content_work_item_bdo"
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemSnapshotAuditRequestSchema.safeParse({
        audit: {
          audit_id: "audit_bdo",
          actor: "wilku",
          reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
          evidence_ids: ["ev_gsc_bdo"],
          human_review_id: "human_review_bdo"
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftHandoffResponseSchema.safeParse({
        item,
        handoff_result: {
          handoff: {
            id: "wordpress_draft_handoff_content_work_item_bdo",
            work_item_id: "content_work_item_bdo",
            draft_package_id: "draft_package_content_work_item_bdo",
            human_review_id: "human_review_bdo",
            audit_id: "audit_bdo",
            connector: "wordpress_ekologus",
            operation_type: "create_wordpress_draft",
            status: "prepared",
            post_status: "draft",
            title: "BDO dla firm",
            final_canonical_url: "https://ekologus.pl/bdo/",
            intended_final_url: "https://ekologus.pl/bdo/",
            preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            publish_allowed: false,
            destructive_update_allowed: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftExecutionRequestSchema.safeParse({
        handoff: {
          id: "wordpress_draft_handoff_content_work_item_bdo",
          work_item_id: "content_work_item_bdo",
          draft_package_id: "draft_package_content_work_item_bdo",
          human_review_id: "human_review_bdo",
          audit_id: "audit_bdo",
          connector: "wordpress_ekologus",
          operation_type: "create_wordpress_draft",
          status: "prepared",
          post_status: "draft",
          title: "BDO dla firm",
          final_canonical_url: "https://ekologus.pl/bdo/",
          intended_final_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          publish_allowed: false,
          destructive_update_allowed: false
        },
        draft_package: draftPackage,
        mode: "dry_run"
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftExecutionResponseSchema.safeParse({
        execution_result: {
          status: "dry_run_ready",
          mode: "dry_run",
          payload: {
            connector: "wordpress_ekologus",
            endpoint_kind: "posts",
            post_status: "draft",
            title: "BDO dla firm",
            content_markdown: "# BDO dla firm",
            final_canonical_url: "https://ekologus.pl/bdo/",
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            publish_allowed: false,
            destructive_update_allowed: false
          },
          wordpress_post_id: null,
          external_write_attempted: false,
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemMeasurementWindowResponseSchema.safeParse({
        item,
        updated_item: item,
        measurement_window_result: {
          window: {
            id: "measurement_window_content_work_item_bdo",
            work_item_id: "content_work_item_bdo",
            content_url: "https://ekologus.pl/bdo/",
            baseline_period: { start: "2026-05-01", end: "2026-05-31" },
            observation_period: { start: "2026-07-01", end: "2026-07-31" },
            earliest_verdict_date: "2026-08-01",
            allowed_metrics: ["gsc_clicks"],
            source_connectors: ["google_search_console"],
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            status: "planned",
            handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
            success_claim_allowed: false
          },
          blockers: []
        },
        outcome_blockers: [blocker]
      }).success
    ).toBe(true);

    const inventoryResolution = {
      status: "resolved",
      recommended_mode: "preserve",
      records: [],
      similar_existing_urls: ["https://ekologus.pl/bdo/"],
      blockers: [],
      evidence_ids: ["ev_wp_bdo"],
      source_connectors: ["wordpress_ekologus"],
      next_step: "Zacznij od preserve-first."
    };
    const preflightVerdict = {
      status: "plan_allowed",
      recommended_mode: "preserve",
      create_allowed: false,
      sales_brief_allowed: false,
      draft_allowed: false,
      wordpress_draft_allowed: false,
      similar_existing_urls: ["https://ekologus.pl/bdo/"],
      blockers: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      next_step: "Zatwierdź preserve-first plan."
    };
    const humanReview = {
      id: "human_review_bdo",
      work_item_id: "content_work_item_bdo",
      stage: "draft_package",
      reviewed_by: "wilku",
      decision: "approved",
      notes: "Może iść dalej.",
      checked_items: ["claimy sprawdzone"],
      evidence_ids: ["ev_gsc_bdo"],
      blocked_claims_handled: [],
      draft_package_id: "draft_package_content_work_item_bdo"
    };
    const wordpressHandoff = {
      id: "wordpress_draft_handoff_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      draft_package_id: "draft_package_content_work_item_bdo",
      human_review_id: "human_review_bdo",
      audit_id: "audit_bdo",
      connector: "wordpress_ekologus",
      operation_type: "create_wordpress_draft",
      status: "prepared",
      post_status: "draft",
      title: "BDO dla firm",
      final_canonical_url: "https://ekologus.pl/bdo/",
      intended_final_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      publish_allowed: false,
      destructive_update_allowed: false
    };
    const measurementWindow = {
      id: "measurement_window_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      content_url: "https://ekologus.pl/bdo/",
      baseline_period: { start: "2026-05-01", end: "2026-05-31" },
      observation_period: { start: "2026-07-01", end: "2026-07-31" },
      earliest_verdict_date: "2026-08-01",
      allowed_metrics: ["gsc_clicks"],
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      status: "planned",
      handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
      success_claim_allowed: false
    };
    const structuredContract = {
      schema_name: "wilq_content_structured_draft_v1",
      strict_schema: true,
      model_input: {
        work_item_id: "content_work_item_bdo",
        language: "pl-PL",
        draft_kind: "section_draft",
        title: "BDO dla firm",
        final_canonical_url: "https://ekologus.pl/bdo/",
        source_public_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        target_reader: "właściciel firmy",
        buyer_problem: "nie wie, jak podejść do BDO",
        buyer_trigger: "zbliża się kontrola",
        search_intent: "informacyjno-usługowy",
        service_fit: "obsługa środowiskowa",
        cta_direction: "Skontaktuj się z Ekologus.",
        sections: [],
        source_facts: [],
        claims_allowed: [],
        claims_removed_or_blocked: [],
        human_review_questions: ["Czy to brzmi jak Ekologus?"]
      },
      output_schema: { type: "object", additionalProperties: false },
      system_instruction: "Pisz wyłącznie z przekazanych faktów.",
      user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
      publish_ready: false
    };

    expect(
      ContentWorkItemWorkflowSnapshotResponseSchema.safeParse({
        preflight: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict
        },
        sales_brief: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict,
          sales_brief_result: { brief, blockers: [] }
        },
        draft_package: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict,
          sales_brief_result: { brief, blockers: [] },
          draft_package_result: { draft_package: draftPackage, blockers: [] }
        },
        structured_generation: {
          item,
          structured_generation_result: { contract: structuredContract, blockers: [] }
        },
        human_review: {
          item,
          reviewed_item: item,
          review: humanReview,
          blockers: [],
          wordpress_handoff_allowed: true
        },
        wordpress_handoff: {
          item,
          handoff_result: { handoff: wordpressHandoff, blockers: [] }
        },
        measurement_window: {
          item,
          updated_item: item,
          measurement_window_result: { window: measurementWindow, blockers: [] },
          outcome_blockers: [blocker]
        },
        operator_steps: [
          {
            id: "content_preflight",
            title: "Sprawdzenie pisania",
            status_label: "można planować",
            summary: "Zatwierdź preserve-first plan."
          },
          {
            id: "sales_brief",
            title: "Plan sprzedażowy",
            status_label: "gotowy do sprawdzenia",
            summary: "nie wie, jak podejść do BDO"
          }
        ]
      }).success
    ).toBe(true);
  });
});
