import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemMeasurement,
  type ContentPublicDeploymentReadResponse
} from "../lib/api";
import { ContentMeasurementPanel } from "./ContentMeasurementPanel";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentWorkItemMeasurement: vi.fn(),
    postContentWorkItemLearningProposal: vi.fn(),
    postContentWorkItemMeasurementOutcome: vi.fn(),
    postContentWorkItemMeasurementWindow: vi.fn()
  };
});

describe("ContentMeasurementPanel", () => {
  beforeEach(() => {
    vi.mocked(getContentWorkItemMeasurement).mockResolvedValue({
      status: "available",
      reason: "Dwa okresy są porównywalne.",
      safe_next_step: "Przeczytaj evidence.",
      work_item_id: "content_work_item_bdo",
      revision_id: "revision_bdo",
      revision_digest: "a".repeat(64),
      deployment_id: "deployment_bdo",
      content_url: "https://www.ekologus.pl/bdo/",
      publication_evidence_id: "ev_publication",
      publication_source_connector: "wordpress_ekologus",
      rows: [{
        source_connector: "google_search_console",
        status: "available",
        reason: "Dwa dokładne okresy mają kompletną lineage.",
        baseline_period: "2026-08-01/2026-08-07",
        observation_period: "2026-08-08/2026-08-14",
        metric_names: ["clicks", "impressions"],
        baseline_values: { clicks: 2, impressions: 92 },
        observation_values: { clicks: 3, impressions: 113 },
        evidence_ids: ["ev_baseline", "ev_observation"]
      }, {
        source_connector: "google_analytics_4",
        status: "not_available",
        reason: "Brakuje drugiego dokładnego okresu.",
        baseline_period: null,
        observation_period: null,
        metric_names: [],
        baseline_values: {},
        observation_values: {},
        evidence_ids: []
      }],
      fact_count: 4,
      source_connectors: ["google_search_console"]
    });
  });

  afterEach(() => cleanup());

  it("renders real exact-revision metrics and the unavailable connector reason", async () => {
    const state = {
      deployment: {
        deployment_id: "deployment_bdo",
        work_item_id: "content_work_item_bdo",
        revision_id: "revision_bdo",
        revision_digest: "a".repeat(64),
        public_url: "https://www.ekologus.pl/bdo/",
        wordpress_post_id: "1234",
        publication_evidence_id: "ev_publication",
        publication_source_connector: "wordpress_ekologus",
        observed_at: "2026-08-01T00:00:00Z",
        confirmed_by: "wilku",
        confirmed_at: "2026-08-01T01:00:00Z"
      },
      publication_observations: [],
      measurement_window: null,
      measurement_outcome: null,
      learning_proposal: null,
      outcome_allowed: false,
      safe_next_step: "Utwórz okno pomiaru."
    } satisfies ContentPublicDeploymentReadResponse;
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentMeasurementPanel
          workItemId="content_work_item_bdo"
          revisionId="revision_bdo"
          state={state}
        />
      </QueryClientProvider>
    );

    expect(await screen.findByText("Rzeczywiste metryki opublikowanej rewizji")).toBeInTheDocument();
    expect(screen.getByText("Wyświetlenia w wyszukiwarce: 92 → 113")).toBeInTheDocument();
    expect(screen.getByText("2026-08-01/2026-08-07 → 2026-08-08/2026-08-14")).toBeInTheDocument();
    expect(screen.getByText("Brakuje drugiego dokładnego okresu.")).toBeInTheDocument();
    expect(getContentWorkItemMeasurement).toHaveBeenCalledWith(
      "content_work_item_bdo",
      "revision_bdo"
    );
    client.clear();
  });
});
