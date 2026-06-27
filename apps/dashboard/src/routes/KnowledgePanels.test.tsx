import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { KnowledgeCard, MarketingPlaybook } from "../lib/api";
import { KnowledgeCardList, PlaybookList } from "./KnowledgePanels";

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
            summary: "Jak oceniać wyszukiwane hasła bez zmyślania skuteczności.",
            card_type: "ads_pattern_card",
            source_type: "marketing_playbook",
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
            expert_rule_ids: ["ads_search_terms_v1"],
            output_contract: "Evidence-backed search-term review.",
            card_type: "ads_pattern_card",
            family: "ads",
            source_anchors: ["Google Ads search terms"],
            required_evidence: ["search_terms", "campaign_rows"],
            maps_to_opportunity_types: ["ads_review"],
            maps_to_action_types: ["negative_keyword_candidate"],
            source_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
            compact_playbook: "Review search terms without claiming CPA/zwrotu z reklam.",
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
});
