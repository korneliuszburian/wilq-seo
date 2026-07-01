import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentServiceProfile,
  type ContentServiceProfileResponse
} from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentServiceProfile: vi.fn()
  };
});

describe("ServiceProfileSurface", () => {
  beforeEach(() => {
    vi.mocked(getContentServiceProfile).mockResolvedValue(serviceProfileResponse());
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders a read-only Polish service profile without edit controls", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/service-profile", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Profil usług Ekologus")).toBeInTheDocument();
    expect(screen.getByText(/production-depth zablokowane/)).toBeInTheDocument();
    expect(screen.getByText(/źródła są, wymagają review/)).toBeInTheDocument();
    expect(screen.getByText("Polityka zapisu")).toBeInTheDocument();
    expect(screen.getByText(/Edycja kart i promocja faktów wymagają/)).toBeInTheDocument();
    expect(screen.getByText("Brak bezpośredniej karty usługi dla operatu wodnoprawnego"))
      .toBeInTheDocument();
    expect(screen.getByText("BDO i sprawozdawczość środowiskowa")).toBeInTheDocument();
    expect(screen.getByText("Źródła prywatne")).toBeInTheDocument();
    expect(screen.getByText("2 do review")).toBeInTheDocument();
    expect(screen.getByText("ekologus-ai reviewed handoff: Eko-Opieka")).toBeInTheDocument();
    expect(screen.getByText("ekologus-ai reviewed handoff: Audyt zgodności")).toBeInTheDocument();
    expect(screen.getByText("Akcje review")).toBeInTheDocument();
    expect(screen.getByText("Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz"))
      .toBeInTheDocument();
    expect(screen.getByText(/To nie promuje private proposal/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edytuj/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /promuj/i })).not.toBeInTheDocument();
  });
});

function serviceProfileResponse(): ContentServiceProfileResponse {
  return {
    workspace_id: "ekologus",
    workspace_label: "Ekologus",
    generated_at: "2026-07-01T00:00:00Z",
    read_only: true,
    review_policy: {
      can_edit_cards: false,
      can_promote_facts: false,
      can_request_review: true,
      review_required_label:
        "Wiedza review-required może wspierać analizę i UAT, ale nie odblokowuje production-depth treści.",
      blocked_write_reason:
        "Edycja kart i promocja faktów wymagają osobnego ActionObject, review człowieka i audytu."
    },
    production_depth_readiness: {
      status: "source_backed_review_required",
      status_label: "źródła są, wymagają review",
      ready_for_daily_content: false,
      seeded_card_count: 3,
      source_backed_review_required_count: 5,
      production_depth_card_count: 0,
      blocker_labels: ["Brakuje zatwierdzonych production-depth kart usług Ekologus."]
    },
    coverage_summary: {
      card_count: 8,
      service_card_count: 5,
      seeded_contract_proof_count: 3,
      source_backed_review_required_count: 5,
      approved_current_count: 0,
      stale_count: 0,
      rejected_count: 0,
      private_candidate_count: 2,
      missing_required_area_count: 2,
      ready_for_daily_content: false,
      status_label: "źródła są, wymagają review",
      safe_next_step:
        "Przejrzyj karty review-required i luki usługowe z Wilkiem przed użyciem ich jako production-depth."
    },
    service_sections: [
      {
        card_id: "ekologus_service_bdo_reporting",
        title: "BDO i sprawozdawczość środowiskowa",
        status: "source_backed_review_required",
        status_label: "źródło istnieje, wymagane review",
        summary: "Publiczny artykuł Ekologus wspiera edukacyjne tematy o BDO.",
        source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
        source_connector_labels: ["public_site"],
        source_lineage_labels: ["https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"],
        freshness_label: "public_site_review_required_2026-07-01",
        confidence_label: "średnia",
        service_fit_terms: ["bdo", "sprawozdawczość"],
        buyer_problem_terms: ["nie wiem czy dotyczy mnie bdo"],
        buyer_triggers: ["zbliża się termin sprawozdawczy"],
        cta_patterns: ["Sprawdź z ekspertem, jakie dokumenty BDO wymagają weryfikacji."],
        allowed_claims: ["Ekologus publikuje edukacyjne materiały o BDO."],
        claims_needing_review: [],
        forbidden_claims: [],
        evidence_requirements: ["GSC/WordPress evidence is required."],
        usage_notes: [],
        safe_next_step: "Użyj do analizy/UAT, ale poproś o review przed finalnym draftem.",
        review_request_hint: "Poproś Wilka/ownera o decyzję."
      }
    ],
    claim_policy_sections: [],
    evidence_policy_sections: [],
    private_source_proposal_summary: {
      proposal_protocol_available: true,
      proposal_count: 2,
      review_required_count: 2,
      approved_count: 0,
      proposal_source_labels: [
        "ekologus-ai reviewed handoff: Eko-Opieka",
        "ekologus-ai reviewed handoff: Audyt zgodności"
      ],
      review_required_proposal_ids: [
        "private_proposal_ekologus_ai_eko_opieka_2026_07_01",
        "private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01"
      ],
      redacted: true,
      safe_next_step:
        "Użyj protokołu private source proposals dopiero po metadata-only intake i decyzji ownera."
    },
    coverage_gaps: [
      {
        gap_id: "gap_service_operat_wodnoprawny",
        area: "operat wodnoprawny",
        severity: "blocker",
        label: "Brak bezpośredniej karty usługi dla operatu wodnoprawnego",
        reason: "WILQ nie powinien dopasowywać szerokiej karty środowiskowej do usługi bez źródła.",
        needed_source_type: "public_site_or_reviewed_internal_service_fact",
        safe_next_step: "Dodaj publiczny albo reviewed internal source fact.",
        example_work_item_ids: ["content_work_item_operat_wodnoprawny"]
      }
    ],
    review_actions: [
      {
        action_id: "service_profile_review_private_proposal_ekologus_ai_eko_opieka_2026_07_01",
        mode: "review_request",
        label: "Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz",
        reason:
          "ekologus-ai reviewed handoff: Eko-Opieka jest redacted i review-required; może wspierać pytania UAT, ale nie production-depth.",
        blocked_write_claim: "To nie promuje private proposal do source fact ani knowledge card.",
        required_human_role: "Wilku albo owner oferty Ekologus",
        target_card_id: "ekologus_service_eko_opieka"
      }
    ],
    technical_trace: {
      knowledge_card_endpoint: "/api/content/knowledge-cards",
      source_fact_count: 5,
      source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
      private_source_proposal_ids: [
        "private_proposal_ekologus_ai_eko_opieka_2026_07_01",
        "private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01"
      ],
      private_source_protocol_doc: "docs/architecture/private-source-proposal-protocol.md"
    }
  };
}
