import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { KnowledgeCard, KnowledgeOperatingMapResponse, MarketingPlaybook } from "../lib/api";
import {
  KnowledgeCardList,
  KnowledgeDecisionImpactPanel,
  KnowledgeOperatingMapPanel,
  PlaybookList
} from "./KnowledgePanels";
import routeSource from "./KnowledgePanels.tsx?raw";

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
            source_lineage_summary_label: "1 ślad źródłowy",
            confidence: 0.9
          } satisfies KnowledgeCard)
        ]}
      />
    );

    expect(screen.getByText("Typ: wzorzec Ads")).toBeInTheDocument();
    expect(screen.getAllByText("Źródło: zasada pracy").length).toBeGreaterThan(0);
    expect(screen.getByText("Źródła wiedzy: 1 ślad źródłowy")).toBeInTheDocument();
    expect(screen.getByText("Pewność 90%")).toBeInTheDocument();
    expect(screen.queryByText(/wzorzec Ads \/ zasada pracy/)).not.toBeInTheDocument();
    expect(routeSource).not.toContain("{card.card_type_label} / {card.source_type_label}");
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
            output_contract: "Przegląd wyszukiwanych haseł oparty o dowody.",
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
            refusal_rules: ["Brak dowodów oznacza brak rekomendacji."],
            required_evidence_summary_label: "2 wymagane dowody",
            mapped_action_type_summary_label: "1 typ akcji do sprawdzenia"
          } satisfies MarketingPlaybook)
        ]}
      />
    );

    expect(screen.getByText("Diagnostyka wyszukiwanych haseł Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Wymagane dowody: 2 wymagane dowody")).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia: 1 typ akcji do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText(/playbook/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Powiązane działania/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż zasady" }));
    expect(screen.getAllByText("Akcje do sprawdzenia: 1 typ akcji do sprawdzenia").length).toBeGreaterThan(1);
    expect(screen.queryByText(/Powiązane typy działań/)).not.toBeInTheDocument();
    expect(routeSource).not.toContain("function formatCount");
    expect(routeSource).not.toContain("function formatPolishCount");
    expect(routeSource).not.toContain("playbook.required_evidence.length");
    expect(routeSource).not.toContain("playbook.maps_to_action_types.length");
  });

  it("empty playbook list uses plain Polish", () => {
    render(<PlaybookList playbooks={[]} />);

    expect(screen.getByText("Brak skompilowanych zasad pracy.")).toBeInTheDocument();
    expect(screen.queryByText(/playbook/i)).not.toBeInTheDocument();
  });

  it("renders card confidence as a neutral label instead of a status value", () => {
    render(
      <KnowledgeCardList
        cards={[
          ({
            id: "card_content_quality",
            source_id: "content_quality",
            title: "Content quality",
            display_title: "Jakość treści",
            summary: "Jak sprawdzać jakość treści bez zmyślania efektu.",
            card_type: "content_pattern_card",
            card_type_label: "wzorzec treści",
            source_type: "marketing_playbook",
            source_type_label: "zasada pracy",
            source_url_or_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
            extracted_at: "2026-06-17T10:00:00Z",
            last_seen_at: "2026-06-17T10:00:00Z",
            source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml"],
            source_lineage_summary_label: "1 ślad źródłowy",
            confidence: 0.82
          } satisfies KnowledgeCard)
        ]}
      />
    );

    const confidence = screen.getByText("Pewność 82%");
    expect(confidence).toBeInTheDocument();
    expect(confidence.className).not.toContain("text-signal");
    expect(confidence.className).not.toContain("text-risk");
  });

  it("operating map uses API labels for status, risk and route", () => {
    const manyKnowledgeCards = Array.from({ length: 13 }, (_, index) => `card_${index + 1}`);
    render(
      <KnowledgeOperatingMapPanel
        map={
          {
            generated_at: "2026-06-17T10:00:00Z",
            source_card_count: 1,
            playbook_count: 1,
            expert_rule_count: 1,
            binding_count: 1,
            blocked_binding_summary_label: "brak zablokowanych decyzji",
            missing_contract_summary_label: "brak brakujących danych",
            blocked_claim_count_summary_label: "brak zablokowanych obietnic",
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
                source_connector_labels: ["Google Ads"],
                source_connector_summary_label: "Google Ads",
                evidence_ids: ["ev_refresh_google_ads"],
                evidence_summary_label: "1 dowód źródłowy",
                action_ids: ["act_prepare_ads"],
                action_summary_label: "1 akcja do sprawdzenia",
                metric_tiles: {},
                knowledge_card_ids: manyKnowledgeCards,
                playbook_ids: ["google_ads_search_playbook"],
                expert_rule_ids: ["ads_search_terms_v1"],
                knowledge_summary_label: "15 elementów wiedzy użytych w decyzji",
                required_evidence: ["search_terms"],
                required_evidence_summary_label: "1 wymagany dowód",
                missing_contracts: [],
                missing_contract_labels: [],
                missing_contract_summary_label: "brak brakujących danych",
                missing_contract_detail_label: "brak",
                has_missing_contracts: false,
                blocked_claims: [],
                blocked_claim_labels: [],
                blocked_claim_summary_label: "brak zakazanych obietnic",
                blocked_claim_count_summary_label: "brak zablokowanych obietnic",
                has_blocked_claims: false,
                source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml"],
                source_lineage_summary_label: "1 ślad źródłowy",
                risk: "low",
                risk_label: "ryzyko z API"
              }
            ]
          } satisfies KnowledgeOperatingMapResponse
        }
      />
    );

    expect(screen.getByText("Widok: Ads z API")).toBeInTheDocument();
    expect(screen.getByText("Dowody: 1 dowód źródłowy")).toBeInTheDocument();
    expect(screen.getByText("Źródła danych: Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Wiedza użyta w decyzji: 15 elementów wiedzy użytych w decyzji")).toBeInTheDocument();
    expect(screen.getByText("gotowe z API")).toBeInTheDocument();
    expect(screen.getByText("ryzyko z API")).toBeInTheDocument();
    expect(screen.queryByText("widok Google Ads")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż szczegóły techniczne" }));
    expect(screen.getAllByText("Źródła: Google Ads").length).toBeGreaterThan(0);
    expect(screen.queryByText(/google_ads/)).not.toBeInTheDocument();
  });

  it("decision impact panel renders API summary labels instead of local counts", () => {
    render(
      <KnowledgeDecisionImpactPanel
        map={
          {
            generated_at: "2026-06-17T10:00:00Z",
            source_card_count: 1,
            playbook_count: 1,
            expert_rule_count: 1,
            binding_count: 1,
            blocked_binding_summary_label: "brak zablokowanych decyzji",
            missing_contract_summary_label: "brak brakujących danych",
            blocked_claim_count_summary_label: "1 zablokowana obietnica",
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
                source_connector_labels: ["Google Ads"],
                source_connector_summary_label: "Google Ads",
                evidence_ids: ["ev_refresh_google_ads"],
                evidence_summary_label: "1 dowód źródłowy",
                action_ids: ["act_prepare_ads"],
                action_summary_label: "1 akcja do sprawdzenia",
                metric_tiles: {},
                knowledge_card_ids: ["card_google_ads_search_playbook"],
                playbook_ids: ["google_ads_search_playbook"],
                expert_rule_ids: ["ads_search_terms_v1"],
                knowledge_summary_label: "3 elementy wiedzy użyte w decyzji",
                required_evidence: ["search_terms"],
                required_evidence_summary_label: "1 wymagany dowód",
                missing_contracts: [],
                missing_contract_labels: [],
                missing_contract_summary_label: "brak brakujących danych",
                missing_contract_detail_label: "brak",
                has_missing_contracts: false,
                blocked_claims: ["ranking_guarantee"],
                blocked_claim_labels: ["gwarancja pozycji"],
                blocked_claim_summary_label: "gwarancja pozycji",
                blocked_claim_count_summary_label: "1 zablokowana obietnica",
                has_blocked_claims: true,
                source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml"],
                source_lineage_summary_label: "1 ślad źródłowy",
                risk: "low",
                risk_label: "ryzyko z API"
              }
            ]
          } satisfies KnowledgeOperatingMapResponse
        }
      />
    );

    expect(screen.getByText("Źródła danych: Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia: 1 akcja do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Zakazane obietnice: 1 zablokowana obietnica")).toBeInTheDocument();
    expect(screen.getByText("Blokady")).toBeInTheDocument();
    expect(screen.getByText("1 zablokowana obietnica")).toBeInTheDocument();
    expect(screen.queryByText("Akcje do sprawdzenia: 1 akcja")).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(routeSource).toContain("binding.blocked_claim_count_summary_label");
    expect(routeSource).toContain("binding.has_blocked_claims");
    expect(routeSource).toContain("map.blocked_claim_count_summary_label");
    expect(routeSource).not.toContain("binding.missing_contract_labels.join");
    expect(routeSource).not.toContain("binding.knowledge_card_ids.length");
    expect(routeSource).not.toContain("binding.playbook_ids.length");
    expect(routeSource).not.toContain("binding.expert_rule_ids.length");
    expect(routeSource).not.toContain("binding.blocked_claim_labels.join");
    expect(routeSource).not.toContain("binding.blocked_claims.length}");
  });
});
