import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

const actionFixture: ActionObject = {
  id: "act_1",
  title: "Odnow Google Ads OAuth refresh token",
  domain: "google_ads",
  connector: "google_ads",
  mode: "prepare",
  risk: "low",
  status: "needs_validation",
  evidence_ids: ["ev_1"],
  metrics: [],
  validation_status: "not_validated",
  human_diagnosis: "Google Ads refresh token returns oauth_error=invalid_grant.",
  recommended_reason: "OAuth repair unlocks reads.",
  payload: { action_type: "repair_google_ads_oauth" },
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

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/actions/act_1")) {
        return Promise.resolve(Response.json(actionFixture));
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

  function renderActionDetail() {
    return render(
      <App
        appRouter={createWilqRouter({ initialPath: "/actions/act_1", defaultPendingMinMs: 0 })}
        client={testQueryClient}
      />
    );
  }

  it("renders the selected ActionObject detail", async () => {
    renderActionDetail();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Odnow Google Ads OAuth refresh token" })
      ).toBeInTheDocument()
    );
  });
});
