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
});
