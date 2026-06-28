import { readFileSync } from "node:fs";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ConnectorRefreshRun, ConnectorStatus, Evidence, ExpertRule, Opportunity } from "../lib/api";
import {
  ConnectorGrid,
  ConnectorRefreshRunList,
  EvidenceList,
  ExpertRuleList,
  OpportunityList
} from "./RegistryPanels";

describe("RegistryPanels", () => {
  it("opportunity cards use API summaries instead of raw counts", () => {
    render(
      <OpportunityList
        opportunities={[
          ({
            id: "opp_ads_review",
            type: "ads_review",
            title: "Ocena Google Ads",
            domain: "google_ads",
            domain_label: "Google Ads",
            source_connectors: ["google_ads"],
            source_connector_labels: ["Google Ads"],
            evidence_ids: ["ev_ads_1"],
            evidence_summary_label: "1 dowód źródłowy",
            metric_tiles: {},
            metrics: [],
            human_diagnosis: "WILQ widzi decyzję do sprawdzenia.",
            recommended_action: "Sprawdź akcję w WILQ.",
            risk: "medium",
            risk_label: "średnie ryzyko",
            action_ids: ["act_ads_1"],
            action_summary_label: "1 akcja do sprawdzenia",
            expert_rule_ids: ["ads_rule_v1"],
            playbook_ids: ["ads_playbook_v1"],
            knowledge_summary_label: "2 elementy wiedzy użyte w decyzji",
            is_fixture: false
          } satisfies Opportunity)
        ]}
      />
    );

    expect(screen.getByText("Źródła danych: Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Dowody: 1 dowód źródłowy")).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia: 1 akcja do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Użyta wiedza: 2 elementy wiedzy użyte w decyzji")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("ads_rule_v1")).not.toBeInTheDocument();
    expect(screen.queryByText("ads_playbook_v1")).not.toBeInTheDocument();
  });

  it("connector cards summarize access without raw ids or credential names", () => {
    render(
      <ConnectorGrid
        connectors={[
          ({
            id: "google_ads",
            label: "Google Ads",
            status: "missing_credentials",
            status_label: "brakuje dostępu",
            configured: false,
            missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
            missing_credentials_summary_label: "1 pole",
            available_credential_sources: ["repo_env"],
            credential_source_summary_label: "1 źródło",
            freshness: { state: "missing" },
            supported_actions: []
          } satisfies ConnectorStatus)
        ]}
      />
    );

    expect(screen.getByText("Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Źródło danych sprawdzane przez WILQ.")).toBeInTheDocument();
    expect(screen.getByText("Brakujące ustawienia dostępu")).toBeInTheDocument();
    expect(screen.getByText("1 pole")).toBeInTheDocument();
    expect(screen.getByText("Źródła konfiguracji: 1 źródło")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("GOOGLE_ADS_DEVELOPER_TOKEN")).not.toBeInTheDocument();
    expect(screen.queryByText("repo_env")).not.toBeInTheDocument();
    expect(screen.queryByText("Brakujące credentiale")).not.toBeInTheDocument();

    const source = readFileSync("src/routes/RegistryPanels.tsx", "utf8");
    expect(source).not.toContain("connector.missing_credentials.length, \"pole\"");
    expect(source).not.toContain("connector.available_credential_sources.length,");
  });

  it("evidence cards hide raw source identifiers from the list view", () => {
    render(
      <EvidenceList
        evidenceItems={[
          ({
            id: "ev_connector_google_ads_status",
            title_label: "Dowód z Google Ads",
            source_connector: "google_ads",
            source_connector_label: "Google Ads",
            source_type: "connector_refresh",
            source_type_label: "odczyt źródła danych",
            source_id: "refresh_google_ads_test",
            collected_at: "2026-06-17T10:00:00Z",
            freshness: { state: "fresh" },
            freshness_label: "świeże dane",
            summary: "Google Ads odczytany z sanitizowanym podsumowaniem.",
            trace_summary_label: "Google Ads: odczyt źródła danych, świeże dane",
            raw_ref: null
          } satisfies Evidence)
        ]}
      />
    );

    expect(screen.getByText("Dowód z WILQ")).toBeInTheDocument();
    expect(
      screen.getByText("Zebrany fakt użyty do decyzji. Pełne identyfikatory zostają w śladzie audytu.")
    ).toBeInTheDocument();
    expect(screen.queryByText("ev_connector_google_ads_status")).not.toBeInTheDocument();
    expect(screen.queryByText(/google_ads \/ connector_refresh/)).not.toBeInTheDocument();
  });

  it("connector refresh cards summarize counts instead of raw run details", () => {
    render(
      <ConnectorRefreshRunList
        runs={[
          ({
            id: "refresh_google_ads_test",
            connector_id: "google_ads",
            connector_label: "Google Ads",
            mode: "vendor_read",
            status: "completed",
            status_label: "zakończony",
            summary: "Odczyt Google Ads zakończony.",
            evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
            evidence_summary_label: "2 dowody źródłowe",
            missing_credentials: [],
            checked_credentials: [],
            started_at: "2026-06-17T10:00:00Z",
            completed_at: "2026-06-17T10:01:00Z",
            metric_summary: {
              clicks: 12,
              impressions: 120,
              api: "google_ads_probe"
            },
            vendor_data_collected: true,
            external_call_attempted: true,
            errors: [],
            redacted: true
          } satisfies ConnectorRefreshRun)
        ]}
      />
    );

    expect(screen.getByText("Odczyt źródła danych")).toBeInTheDocument();
    expect(screen.getByText("Dowody: 2 dowody źródłowe")).toBeInTheDocument();
    expect(screen.getByText("Metryki: 3 wartości")).toBeInTheDocument();
    expect(screen.queryByText("refresh_google_ads_test")).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("vendor_read")).not.toBeInTheDocument();
    expect(screen.queryByText(/clicks=12/)).not.toBeInTheDocument();
  });

  it("expert rule cards hide raw rule internals until technical details are opened", () => {
    render(
      <ExpertRuleList
        rules={[
          ({
            id: "ads_search_terms_v1",
            name: "Sprawdzenie wyszukiwanych haseł",
            domain: "ads",
            version: 1,
            source_anchor: "Google Ads raw search terms",
            source_path: "wilq/expert/ads/search_terms.yaml",
            when_to_use: "Gdy trzeba sprawdzić wyszukiwane hasła.",
            required_inputs: ["search_terms"],
            diagnostic_logic: ["segment_by_intent"],
            recommended_actions: ["negative_keyword_candidate", "content_brief_candidate"],
            risk_notes: "External data.",
            output_contract: "WILQ używa reguły tylko z dowodami i blokadami claimów.",
            capabilities: [],
            required_mapping: [],
            requires_evidence: true
          } satisfies ExpertRule)
        ]}
      />
    );

    expect(screen.getByText("Sprawdzenie wyszukiwanych haseł")).toBeInTheDocument();
    expect(screen.getByText("Reguła decyzji używana tylko z dowodami i źródłami danych.")).toBeInTheDocument();
    expect(screen.getByText("WILQ używa reguły tylko z dowodami i blokadami claimów.")).toBeInTheDocument();
    expect(screen.queryByText(/ads \/ v1/)).not.toBeInTheDocument();
    expect(screen.queryByText("Google Ads raw search terms")).not.toBeInTheDocument();
    expect(screen.queryByText(/negative_keyword_candidate/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż szczegóły reguły" }));

    expect(screen.getByText("Źródło reguły: Google Ads raw search terms")).toBeInTheDocument();
    expect(screen.getByText(/negative_keyword_candidate/)).toBeInTheDocument();
  });
});
