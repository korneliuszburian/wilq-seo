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
    expect(screen.getByText("Źródła i review")).toBeInTheDocument();
    expect(screen.getByText("Poproś Wilka/ownera o decyzję.")).toBeInTheDocument();
    expect(screen.getByText("public_site")).toBeInTheDocument();
    expect(screen.getByText("ekologus_public_bdo_faq_2026_07_01")).toBeInTheDocument();
    expect(
      screen.getByText("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/")
    ).toBeInTheDocument();
    expect(screen.getByText("Źródła prywatne")).toBeInTheDocument();
    expect(screen.getByText("4 propozycji")).toBeInTheDocument();
    expect(screen.getByText("2 usługowe")).toBeInTheDocument();
    expect(screen.getByText("2 claim-policy")).toBeInTheDocument();
    expect(screen.getByText("4 do review")).toBeInTheDocument();
    expect(screen.getByText("promocja zablokowana")).toBeInTheDocument();
    expect(screen.getByText("Warunki przed reviewed source fact")).toBeInTheDocument();
    expect(screen.getByText(/Brak zatwierdzenia człowieka/)).toBeInTheDocument();
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Eko-Opieka").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Audyt zgodności").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Styl marki").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Bezpieczeństwo prawne").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Eko-Opieka / Eko Kalendarz")).toBeInTheDocument();
    expect(screen.getByText("Styl marki i claim policy Ekologus")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczeństwo prawne, poufność i zgody")).toBeInTheDocument();
    expect(screen.getAllByText("support: partial").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("support: direct").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("risk: medium").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("risk: high").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("bez promocji").length).toBeGreaterThanOrEqual(4);
    expect(screen.getAllByText("Claimy zablokowane").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("obietnica stałej zgodności")).toBeInTheDocument();
    expect(screen.getByText("Akcje review")).toBeInTheDocument();
    expect(screen.getByText("12 razem")).toBeInTheDocument();
    expect(screen.getByText("6 publicznych usług")).toBeInTheDocument();
    expect(screen.getByText("2 prywatne service")).toBeInTheDocument();
    expect(screen.getByText("2 prywatne claim-policy")).toBeInTheDocument();
    expect(screen.getByText("11 review request")).toBeInTheDocument();
    expect(screen.getByText("1 prepare")).toBeInTheDocument();
    expect(screen.getByText(/Najpierw przejrzyj publiczne karty usług/)).toBeInTheDocument();
    expect(screen.getByText("Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz"))
      .toBeInTheDocument();
    expect(screen.getByText("Sprawdź prywatną propozycję: Styl marki i claim policy Ekologus"))
      .toBeInTheDocument();
    expect(screen.getByText("private_service_proposal")).toBeInTheDocument();
    expect(screen.getByText("private_claim_policy_proposal")).toBeInTheDocument();
    expect(screen.getAllByText("medium").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("high").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/To nie promuje private proposal/).length)
      .toBeGreaterThanOrEqual(2);
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
        "Edycja kart i promocja faktów wymagają osobnej zatwierdzonej akcji, review człowieka i audytu."
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
      proposal_count: 4,
      service_proposal_count: 2,
      claim_policy_proposal_count: 2,
      evidence_requirement_proposal_count: 0,
      review_required_count: 4,
      approved_count: 0,
      promotion_ready: false,
      promotion_checklist: [
        "Wilku albo owner potwierdza, że propozycja opisuje realną ofertę Ekologus.",
        "Źródło zostaje streszczone jako redacted/source-safe fact bez raw private text."
      ],
      promotion_blocked_reason:
        "Brak zatwierdzenia człowieka i reviewed source fact; Service Profile pokazuje tylko propozycje review.",
      proposal_source_labels: [
        "ekologus-ai reviewed handoff: Eko-Opieka",
        "ekologus-ai reviewed handoff: Audyt zgodności",
        "ekologus-ai reviewed handoff: Styl marki",
        "ekologus-ai reviewed handoff: Bezpieczeństwo prawne"
      ],
      review_required_proposal_ids: [
        "private_proposal_ekologus_ai_eko_opieka_2026_07_01",
        "private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01",
        "private_proposal_ekologus_ai_brand_voice_2026_07_01",
        "private_proposal_ekologus_ai_legal_safety_2026_07_01"
      ],
      redacted: true,
      safe_next_step:
        "Użyj protokołu private source proposals dopiero po metadata-only intake i decyzji ownera."
    },
    private_source_proposals: [
      {
        proposal_id:
          "private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
        source_id: "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
        source_type: "reviewed_internal",
        privacy_class: "redacted_only",
        scope: "service",
        target_card_id: "ekologus_service_eko_opieka_calendar",
        target_card_title: "Eko-Opieka / Eko Kalendarz",
        source_class_label: "review-required internal service context",
        source_locator_label: "ekologus-ai reviewed handoff: Eko-Opieka",
        review_status: "review_required",
        support_level: "partial",
        risk_tier: "medium",
        confidence_label: "średnia",
        owner_role: "Wilku albo owner oferty Ekologus",
        redacted: true,
        blocked_claims: ["obietnica stałej zgodności"],
        safe_next_step: "Pokazać Wilkowi zwykły handoff i zdecydować o review.",
        promotion_allowed: false,
        blocked_write_claim:
          "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
      },
      {
        proposal_id:
          "private_proposal_ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01",
        source_id: "ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01",
        source_type: "reviewed_internal",
        privacy_class: "redacted_only",
        scope: "service",
        target_card_id: "ekologus_service_environmental_compliance_audit",
        target_card_title: "Audyt zgodności środowiskowej",
        source_class_label: "review-required internal service context",
        source_locator_label: "ekologus-ai reviewed handoff: Audyt zgodności",
        review_status: "review_required",
        support_level: "partial",
        risk_tier: "medium",
        confidence_label: "wysoka",
        owner_role: "Wilku albo owner oferty Ekologus",
        redacted: true,
        blocked_claims: ["gwarancja braku kar"],
        safe_next_step: "Pokazać Wilkowi zwykły handoff i zdecydować o review.",
        promotion_allowed: false,
        blocked_write_claim:
          "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
      },
      {
        proposal_id:
          "private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01",
        source_id: "ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01",
        source_type: "reviewed_internal",
        privacy_class: "redacted_only",
        scope: "claim_policy",
        target_card_id: "ekologus_claim_policy_brand_voice",
        target_card_title: "Styl marki i claim policy Ekologus",
        source_class_label: "review-required internal claim-policy source fact",
        source_locator_label: "ekologus-ai reviewed handoff: Styl marki",
        review_status: "review_required",
        support_level: "direct",
        risk_tier: "high",
        confidence_label: "wysoka",
        owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        redacted: true,
        blocked_claims: ["puste slogany agencyjne", "gwarantowany wynik"],
        safe_next_step: "Pokaż Wilkowi/reviewerowi zasady claimów.",
        promotion_allowed: false,
        blocked_write_claim:
          "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
      },
      {
        proposal_id:
          "private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
        source_id: "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
        source_type: "reviewed_internal",
        privacy_class: "redacted_only",
        scope: "claim_policy",
        target_card_id: "ekologus_claim_policy_legal_safety",
        target_card_title: "Bezpieczeństwo prawne, poufność i zgody",
        source_class_label: "review-required internal claim-policy source fact",
        source_locator_label: "ekologus-ai reviewed handoff: Bezpieczeństwo prawne",
        review_status: "review_required",
        support_level: "direct",
        risk_tier: "high",
        confidence_label: "wysoka",
        owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        redacted: true,
        blocked_claims: ["poufne dane klientów w materiale marketingowym"],
        safe_next_step: "Pokaż Wilkowi/reviewerowi zasady claimów.",
        promotion_allowed: false,
        blocked_write_claim:
          "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
      }
    ],
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
        review_scope: "private_service_proposal",
        priority: "medium",
        label: "Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz",
        reason:
          "ekologus-ai reviewed handoff: Eko-Opieka jest redacted i review-required; może wspierać pytania UAT, ale nie production-depth.",
        blocked_write_claim: "To nie promuje private proposal do source fact ani knowledge card.",
        required_human_role: "Wilku albo owner oferty Ekologus",
        target_card_id: "ekologus_service_eko_opieka"
      },
      {
        action_id: "service_profile_review_private_proposal_ekologus_ai_brand_voice_2026_07_01",
        mode: "review_request",
        review_scope: "private_claim_policy_proposal",
        priority: "high",
        label: "Sprawdź prywatną propozycję: Styl marki i claim policy Ekologus",
        reason:
          "ekologus-ai reviewed handoff: Styl marki jest redacted i review-required; może wspierać pytania UAT, ale nie production-depth.",
        blocked_write_claim: "To nie promuje private proposal do source fact ani knowledge card.",
        required_human_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        target_card_id: "ekologus_claim_policy_brand_voice"
      }
    ],
    review_action_summary: {
      total_count: 12,
      review_request_count: 11,
      prepare_count: 1,
      public_service_review_count: 6,
      private_review_count: 4,
      private_service_review_count: 2,
      private_policy_review_count: 2,
      safe_next_step:
        "Najpierw przejrzyj publiczne karty usług, potem prywatne propozycje service i claim-policy."
    },
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
