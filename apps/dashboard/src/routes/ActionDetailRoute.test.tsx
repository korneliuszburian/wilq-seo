import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

const actionFixture: ActionObject = {
  id: "act_1",
  title: "Przygotuj kolejkę przeglądu feedu Merchant Center",
  domain: "merchant",
  connector: "google_merchant_center",
  mode: "prepare",
  risk: "medium",
  status: "needs_validation",
  evidence_ids: ["ev_refresh_merchant_feed"],
  metrics: [],
  validation_status: "not_validated",
  human_diagnosis: "Merchant Center ma issue facts i próbki produktów do review.",
  recommended_reason: "Przejrzyj preview bez mutacji feedu.",
  payload: {
    action_type: "merchant_feed_issue",
    preview_contract: "merchant_feed_issue_review_preview_v1",
    payload_preview: [
      ...Array.from({ length: 4 }, (_, index) => ({
        id: `merchant_feed_issue_review_empty_${index}`,
        preview_contract: "merchant_feed_issue_review_preview_v1",
        operation_type: "MerchantIssueClusterReview",
        issue_type: "landing_page_error",
        affected_attribute: "n:link",
        metric_snapshot: { issue_product_count: 2 },
        sample_products_available: false,
        sample_product_ids: [],
        sample_titles: [],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      })),
      {
        id: "merchant_feed_issue_review_1",
        preview_contract: "merchant_feed_issue_review_preview_v1",
        operation_type: "MerchantIssueClusterReview",
        issue_type: "availability_updated",
        affected_attribute: "n:availability",
        metric_snapshot: { issue_product_count: 23 },
        sample_products_available: true,
        sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
        sample_titles: ["Sorbent chemiczny 10 kg"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }
    ]
  },
  review_gate: {
    status: "pending_validation",
    summary: "Wymaga walidacji ActionObject; apply pozostaje zablokowany.",
    required_checks: ["validate_action_object", "human_confirm_before_apply"],
    operator_checklist: ["validate_action_object", "human_confirm_before_apply"],
    apply_blockers: [
      "action_mode_prepare_only",
      "action_validation_required",
      "payload_apply_allowed_false",
      "human_confirm_before_apply"
    ],
    confirmation_required: true,
    apply_allowed: false,
    last_confirmation_by: null,
    last_confirmation_at: null,
    last_confirmation_summary: null,
    last_review_outcome: null,
    last_reviewed_by: null,
    last_reviewed_at: null,
    last_review_summary: null,
    last_impact_check_status: null,
    last_impact_checked_by: null,
    last_impact_checked_at: null,
    last_impact_check_summary: null,
    last_mutation_audit_id: null,
    last_mutation_audit_status: null,
    last_mutation_audit_actor: null,
    last_mutation_audit_at: null,
    last_mutation_audit_summary: null,
    last_mutation_attempted: null,
    last_mutation_adapter: null,
    last_mutation_audit_event_id: null,
    last_mutation_blockers: []
  },
  audit_events: []
};

const adsActionFixture: ActionObject = {
  ...actionFixture,
  id: "act_ads",
  title: "Przygotuj kolejkę przeglądu kampanii Google Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Google Ads ma kampanie i budżety do review.",
  recommended_reason: "Przejrzyj budżet bez mutacji kampanii.",
  payload: {
    action_type: "campaign_change_review",
    preview_contract: "budget_apply_preview_v1",
    budget_payload_preview: [
      {
        id: "budget_apply_preview_23704710371_15473121355",
        campaign_id: "23704710371",
        campaign_name: "(2026) Ekologus Ogólna",
        campaign_budget_id: "15473121355",
        campaign_budget_name: "(2026) Ekologus Ogólna",
        operation_type: "CampaignBudgetOperation",
        current_budget_amount_micros: 10000000,
        proposed_budget_amount_micros: null,
        proposed_budget_delta_micros: null,
        reason:
          "Review-only podgląd CampaignBudgetOperation. Google Ads nie zwrócił recommended budget.",
        evidence_ids: ["ev_refresh_google_ads"],
        required_validation: [
          "review_campaign_activity",
          "human_budget_goal",
          "campaign_budget_apply_safety"
        ],
        blocked_claims: ["budget scaling", "budget apply", "wasted budget"],
        safety_review: {
          safety_contract: "campaign_budget_apply_safety_v1",
          status: "blocked",
          reason: "Budget apply zablokowany: brak proponowanej kwoty.",
          missing_requirements: ["human_budget_goal", "recommended_budget_missing"],
          apply_allowed: false,
          api_mutation_ready: false,
          destructive: false
        },
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const adsRecommendationActionFixture: ActionObject = {
  ...actionFixture,
  id: "act_ads_recommendation",
  title: "Przygotuj ocenę rekomendacji Google Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Google Ads ma rekomendacje do review, ale apply jest zablokowany.",
  recommended_reason: "Przejrzyj typ rekomendacji bez akceptowania jej w Google Ads.",
  payload: {
    action_type: "google_ads_recommendation_review",
    preview_contract: "recommendation_apply_preview_v1",
    payload_preview: [
      {
        id: "recommendation_apply_preview_display",
        recommendation_type: "DISPLAY_EXPANSION_OPT_IN",
        campaign_id: "23848569273",
        campaign_budget_id: "15587163334",
        operation_type: "ApplyRecommendationOperation",
        required_validation: [
          "review_recommendation_type",
          "review_impact_metrics",
          "review_change_history",
          "review_business_goal"
        ],
        blocked_claims: [
          "recommendation apply",
          "automatic recommendation accept",
          "performance uplift"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const customSegmentActionFixture: ActionObject = {
  ...actionFixture,
  id: "act_custom_segments",
  title: "Przygotuj kandydatów segmentów z wyszukiwanych haseł",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Search terms mogą zasilić review-only custom segment.",
  recommended_reason: "Przejrzyj źródłowe hasła i safety przed targetowaniem.",
  payload: {
    action_type: "custom_segment_review",
    preview_contract: "custom_segment_apply_preview_v1",
    payload_preview: [
      {
        id: "custom_segment_preview_google_ads_search_terms",
        custom_segment_name: "WILQ search-term intent review",
        member_type: "KEYWORD",
        source_terms: [
          "alba czeladź",
          "asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a",
          "bdo szkolenia stacjonarne"
        ],
        required_validation: [
          "review_source_terms",
          "reject_brand_or_low_intent_terms",
          "keyword_planner_enrichment",
          "forecast_or_audience_size"
        ],
        blocked_claims: ["audience size", "conversion uplift", "targeting applied"],
        targeting_preview: [
          {
            campaign_id: "23848569273",
            campaign_name: "Kompendium PPWR",
            operation_type: "custom_segment_targeting_review",
            apply_allowed: false,
            api_mutation_ready: false
          }
        ],
        safety_review: {
          status: "blocked",
          reason: "Custom segment apply zablokowany.",
          missing_requirements: ["forecast_or_audience_size", "keyword_planner_enrichment"]
        },
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const negativeKeywordActionFixture: ActionObject = {
  ...actionFixture,
  id: "act_negative_keywords",
  title: "Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Search terms mogą wymagać review wykluczeń, ale apply jest zablokowany.",
  recommended_reason: "Przejrzyj kontekst wyszukiwanego hasła i safety przed wykluczeniem.",
  payload: {
    action_type: "negative_keyword_review",
    preview_contract: "negative_keyword_review_preview_v1",
    payload_preview: [
      {
        id: "negative_keyword_preview_23848569273_alba",
        search_term: "alba czeladź",
        negative_keyword_text: "alba czeladź",
        match_type: "EXACT",
        level: "ad_group",
        campaign_id: "23848569273",
        campaign_name: "Kompendium PPWR",
        ad_group_id: "203360679544",
        ad_group_name: "Grupa reklam 1",
        required_validation: [
          "review_search_term_context",
          "check_existing_keywords_and_match_types",
          "90_day_safety_check",
          "human_confirm_before_apply"
        ],
        blocked_claims: ["negative keyword apply", "search-term waste", "CPA", "ROAS"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const contentActionFixture: ActionObject = {
  ...actionFixture,
  id: "act_content",
  title: "Przygotuj kolejkę odświeżenia treści ekologus.pl",
  domain: "content",
  connector: "wordpress_ekologus",
  risk: "medium",
  evidence_ids: ["ev_refresh_gsc"],
  human_diagnosis: "GSC i WordPress wskazują kandydatów content review.",
  recommended_reason: "Przejrzyj brief i draft preview bez publikacji.",
  payload: {
    action_type: "content_refresh_queue",
    preview_contract: "content_brief_preview_v1",
    content_brief_preview: [
      {
        preview_contract: "content_brief_preview_v1",
        candidate_id: "content_brief_gsc_bdo",
        source_type: "gsc_query_page",
        mode: "inventory_check",
        topic: "bdo co to",
        target_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        wordpress_inventory_match: "missing",
        decision_options: ["merge", "create", "block"],
        metric_snapshot: {
          queries: 1,
          clicks: 4,
          impressions: 4429,
          ctr: 0.0009031384059607134,
          average_position: 9.441183111311808
        },
        brief_goal:
          "Sprawdź inventory i duplikaty przed briefem dla `bdo co to`. Bez potwierdzenia URL nie twórz nowej strony.",
        brief_outline: [
          {
            section: "intent",
            instruction: "Opisz intencję użytkownika dla `bdo co to`."
          },
          {
            section: "cta",
            instruction: "Dopasuj CTA do usługi Ekologus."
          }
        ],
        required_validation: [
          "wordpress_inventory_check",
          "duplicate_or_cannibalization_check",
          "human_confirm_before_wordpress_write"
        ],
        blocked_claims: ["lead uplift", "revenue impact", "automatic WordPress publish"],
        source_connectors: ["google_search_console"],
        evidence_ids: ["ev_refresh_gsc"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      },
      ...Array.from({ length: 4 }, (_, index) => ({
        preview_contract: "content_brief_preview_v1",
        candidate_id: `content_brief_extra_${index}`,
        source_type: "gsc_query_page",
        mode: "inventory_check",
        topic: `temat dodatkowy ${index}`,
        target_url: `https://www.ekologus.pl/extra-${index}/`,
        wordpress_inventory_match: "missing",
        decision_options: ["merge", "create", "block"],
        metric_snapshot: {
          queries: 1,
          clicks: index,
          impressions: 100 + index
        },
        brief_goal: "Dodatkowy brief do testu limitu kart.",
        required_validation: ["wordpress_inventory_check"],
        blocked_claims: ["lead uplift"],
        source_connectors: ["google_search_console"],
        evidence_ids: ["ev_refresh_gsc"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }))
    ],
    wordpress_draft_payload_preview: [
      {
        preview_contract: "wordpress_draft_payload_preview_v1",
        candidate_id: "content_brief_gsc_bdo",
        operation_type: "prepare_new_content_draft_review",
        post_status: "draft",
        topic: "bdo co to",
        draft_payload: {
          post_status: "draft",
          post_title: "Brief: bdo co to",
          post_excerpt_direction: "Sprawdź inventory i duplikaty przed briefem.",
          content_blocks: []
        },
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }
    ]
  }
};

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/actions/act_1")) {
        return Promise.resolve(Response.json(actionFixture));
      }
      if (url.endsWith("/api/actions/act_ads")) {
        return Promise.resolve(Response.json(adsActionFixture));
      }
      if (url.endsWith("/api/actions/act_ads_recommendation")) {
        return Promise.resolve(Response.json(adsRecommendationActionFixture));
      }
      if (url.endsWith("/api/actions/act_custom_segments")) {
        return Promise.resolve(Response.json(customSegmentActionFixture));
      }
      if (url.endsWith("/api/actions/act_negative_keywords")) {
        return Promise.resolve(Response.json(negativeKeywordActionFixture));
      }
      if (url.endsWith("/api/actions/act_content")) {
        return Promise.resolve(Response.json(contentActionFixture));
      }
      return Promise.resolve(Response.json({}));
    })
  );
}

describe("Action detail route", () => {
  let testQueryClient: QueryClient;

  beforeEach(() => {
    mockFetch();
    testQueryClient = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });
  });

  afterEach(() => {
    cleanup();
    testQueryClient.clear();
    vi.unstubAllGlobals();
  });

  function renderActionDetail(actionId = "act_1") {
    return render(
      <App
        appRouter={createWilqRouter({
          initialPath: `/actions/${actionId}`,
          defaultPendingMinMs: 0
        })}
        client={testQueryClient}
      />
    );
  }

  it("renders the selected ActionObject detail", async () => {
    renderActionDetail();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę przeglądu feedu Merchant Center"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getAllByText("Review-only podgląd").length).toBeGreaterThan(0);
    expect(screen.getByText("availability_updated / n:availability")).toBeInTheDocument();
    expect(screen.getAllByText(/online~pl~PL~SKU-001/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Sorbent chemiczny 10 kg/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders Google Ads budget payload preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę przeglądu kampanii Google Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Budżet kampanii do review")).toBeInTheDocument();
    expect(screen.getByText("CampaignBudgetOperation")).toBeInTheDocument();
    expect(screen.getByText(/Kampania: \(2026\) Ekologus Ogólna/)).toBeInTheDocument();
    expect(screen.getByText(/Obecny budżet: 10 PLN/)).toBeInTheDocument();
    expect(screen.getByText(/Propozycja: brak/)).toBeInTheDocument();
    expect(screen.getByText(/Safety: blocked/)).toBeInTheDocument();
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders Google Ads recommendation payload preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads_recommendation");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj ocenę rekomendacji Google Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Rekomendacja Google Ads do review")).toBeInTheDocument();
    expect(screen.getByText("ApplyRecommendationOperation")).toBeInTheDocument();
    expect(screen.getByText(/Typ: DISPLAY_EXPANSION_OPT_IN/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania: 23848569273/)).toBeInTheDocument();
    expect(screen.getByText(/Budżet kampanii: 15587163334/)).toBeInTheDocument();
    expect(screen.getByText(/Walidacje: review_recommendation_type/)).toBeInTheDocument();
    expect(screen.getByText(/Blokady: recommendation apply/)).toBeInTheDocument();
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders custom segment payload preview without requiring raw JSON", async () => {
    renderActionDetail("act_custom_segments");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kandydatów segmentów z wyszukiwanych haseł"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Custom segment do review")).toBeInTheDocument();
    expect(screen.getByText(/Nazwa: WILQ search-term intent review/)).toBeInTheDocument();
    expect(screen.getByText(/Typ członków: KEYWORD/)).toBeInTheDocument();
    expect(screen.getByText(/Hasła źródłowe: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania do review: Kompendium PPWR/)).toBeInTheDocument();
    expect(screen.getByText(/Safety: blocked/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: forecast_or_audience_size/)).toBeInTheDocument();
    expect(screen.getByText(/Blokady: audience size/)).toBeInTheDocument();
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders negative keyword payload preview without requiring raw JSON", async () => {
    renderActionDetail("act_negative_keywords");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Wykluczenie słowa do review")).toBeInTheDocument();
    expect(screen.getByText(/Hasło: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Wykluczenie: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Dopasowanie: EXACT/)).toBeInTheDocument();
    expect(screen.getByText(/Poziom: ad_group/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania: Kompendium PPWR/)).toBeInTheDocument();
    expect(screen.getByText(/Grupa reklam: Grupa reklam 1/)).toBeInTheDocument();
    expect(screen.getByText(/Walidacje: review_search_term_context/)).toBeInTheDocument();
    expect(screen.getByText(/Blokady: negative keyword apply/)).toBeInTheDocument();
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders content brief and WordPress draft preview without requiring raw JSON", async () => {
    renderActionDetail("act_content");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę odświeżenia treści ekologus.pl"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getAllByText("Brief treści do review").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Temat: bdo co to/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Tryb: inventory_check/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Kliknięcia: 4/)).toBeInTheDocument();
    expect(screen.getByText(/Wyświetlenia: 4429/)).toBeInTheDocument();
    expect(screen.getAllByText(/Opcje: merge, create, block/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Walidacje: wordpress_inventory_check/).length).toBeGreaterThan(0);
    expect(screen.getByText("Draft WordPress do review")).toBeInTheDocument();
    expect(screen.getByText(/Tytuł draftu: Brief: bdo co to/)).toBeInTheDocument();
    expect(screen.getAllByText(/Apply zablokowany/).length).toBeGreaterThan(0);
  });
});
