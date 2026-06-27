import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { KnowledgeCard, KnowledgeOperatingMapResponse, MarketingPlaybook } from "../lib/api";
import { KnowledgeCardList, KnowledgeOperatingMapPanel, PlaybookList } from "./KnowledgePanels";

describe("KnowledgePanels", () => {
  afterEach(() => {
    cleanup();
  });

  it("knowledge cards translate playbook source type into plain Polish", () => {
    render(
      <KnowledgeCardList
        cards={[
          ({
            id: "card_google_ads_search_playbook",
            source_id: "google_ads_search_playbook",
            title: "Google Ads search terms",
            display_title: "Diagnostyka wyszukiwanych haseł Google Ads",
            summary: "Jak oceniać wyszukiwane hasła bez zmyślania skuteczności.",
            card_type: "ads_pattern_card",
            card_type_label: "wzorzec Ads",
            source_type: "marketing_playbook",
            source_type_label: "zasada pracy",
            source_url_or_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
            extracted_at: "2026-06-17T10:00:00Z",
            last_seen_at: "2026-06-17T10:00:00Z",
            source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml"],
            confidence: 0.9
          } satisfies KnowledgeCard)
        ]}
      />
    );

    expect(screen.getByText(/wzorzec Ads \/ zasada pracy/)).toBeInTheDocument();
    expect(screen.getByText("Źródło: zasada pracy")).toBeInTheDocument();
    expect(screen.queryByText(/playbook marketingowy/i)).not.toBeInTheDocument();
  });

  it("playbook list uses marketer-facing wording", () => {
    render(
      <PlaybookList
        playbooks={[
          ({
            id: "google_ads_search_playbook",
            title: "Google Ads search terms",
            display_title: "Diagnostyka wyszukiwanych haseł Google Ads",
            expert_rule_ids: ["ads_search_terms_v1"],
            output_contract: "Evidence-backed search-term review.",
            card_type: "ads_pattern_card",
            card_type_label: "wzorzec Ads",
            source_type_label: "zasada pracy",
            family: "ads",
            source_anchors: ["Google Ads search terms"],
            required_evidence: ["search_terms", "campaign_rows"],
            maps_to_opportunity_types: ["ads_review"],
            maps_to_action_types: ["negative_keyword_candidate"],
            source_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
            compact_playbook: "Review search terms without claiming kosztu pozyskania celu ani zwrotu z reklam.",
            refusal_rules: ["No evidence, no recommendation."]
          } satisfies MarketingPlaybook)
        ]}
      />
    );

    expect(screen.getByText("Diagnostyka wyszukiwanych haseł Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia: 1 typ")).toBeInTheDocument();
    expect(screen.queryByText(/playbook/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Powiązane działania/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż zasady" }));
    expect(screen.getAllByText("Akcje do sprawdzenia: 1 typ").length).toBeGreaterThan(1);
    expect(screen.queryByText(/Powiązane typy działań/)).not.toBeInTheDocument();
  });

  it("empty playbook list uses plain Polish", () => {
    render(<PlaybookList playbooks={[]} />);

    expect(screen.getByText("Brak skompilowanych zasad pracy.")).toBeInTheDocument();
    expect(screen.queryByText(/playbook/i)).not.toBeInTheDocument();
  });

  it("operating map uses API labels for status, risk and route", () => {
    render(
      <KnowledgeOperatingMapPanel
        map={
          {
            generated_at: "2026-06-17T10:00:00Z",
            source_card_count: 1,
            playbook_count: 1,
            expert_rule_count: 1,
            binding_count: 1,
            bindings: [
              {
                id: "knowledge_ads_daily_check",
                title: "Ocena Ads",
                status: "ready",
                status_label: "gotowe z API",
                route: "/ads-doctor",
                route_label: "Ads z API",
                skill_id: "wilq-ads-doctor",
                summary: "Decyzja oparta o karty wiedzy i dowody.",
                next_step: "Otwórz Ads i sprawdź decyzję z dowodami.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_google_ads"],
                action_ids: ["act_prepare_ads"],
                metric_tiles: {},
                knowledge_card_ids: ["card_google_ads_search_playbook"],
                playbook_ids: ["google_ads_search_playbook"],
                expert_rule_ids: ["ads_search_terms_v1"],
                required_evidence: ["search_terms"],
                missing_contracts: [],
                blocked_claims: [],
                source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml"],
                risk: "low",
                risk_label: "ryzyko z API"
              }
            ]
          } satisfies KnowledgeOperatingMapResponse
        }
      />
    );

    expect(screen.getByText("Widok: Ads z API")).toBeInTheDocument();
    expect(screen.getByText("gotowe z API")).toBeInTheDocument();
    expect(screen.getByText("ryzyko z API")).toBeInTheDocument();
    expect(screen.queryByText("widok Google Ads")).not.toBeInTheDocument();
  });
});
