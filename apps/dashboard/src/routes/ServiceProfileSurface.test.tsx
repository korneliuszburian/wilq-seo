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
    expect(screen.getByText("Wiedza Ekologus: co dziś sprawdzić")).toBeInTheDocument();
    expect(
      screen.getByText("Są źródła i propozycje, ale produkcyjne treści są nadal zablokowane")
    ).toBeInTheDocument();
    expect(screen.getByText("Kolejność review")).toBeInTheDocument();
    expect(screen.getByText("Co blokuje produkcję")).toBeInTheDocument();
    expect(screen.getByText("Najpierw publiczne karty usług Ekologus.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Potem prywatne propozycje ekologus-ai: service, claim-policy i evidence-policy."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("ekologus-ai")).toBeInTheDocument();
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
    expect(screen.getByText("Dowody WILQ")).toBeInTheDocument();
    expect(screen.getByText("ev_content_service_profile_source_facts")).toBeInTheDocument();
    expect(
      screen.getByText("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/")
    ).toBeInTheDocument();
    expect(screen.getByText("Źródła prywatne")).toBeInTheDocument();
    expect(screen.getByText("5 propozycji")).toBeInTheDocument();
    expect(screen.getByText("2 usługowe")).toBeInTheDocument();
    expect(screen.getByText("2 claim-policy")).toBeInTheDocument();
    expect(screen.getByText("1 evidence-policy")).toBeInTheDocument();
    expect(screen.getByText("5 do review")).toBeInTheDocument();
    expect(screen.getByText("promocja zablokowana")).toBeInTheDocument();
    expect(screen.getByText("Warunki przed reviewed source fact")).toBeInTheDocument();
    expect(screen.getAllByText(/Brak zatwierdzenia człowieka/).length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Eko-Opieka").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Audyt zgodności").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Styl marki").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Bezpieczeństwo prawne").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ekologus-ai reviewed handoff: Source trace").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Eko-Opieka / Eko Kalendarz")).toBeInTheDocument();
    expect(screen.getByText("Styl marki i claim policy Ekologus")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczeństwo prawne, poufność i zgody")).toBeInTheDocument();
    expect(screen.getByText("Source trace i evidence pack")).toBeInTheDocument();
    expect(screen.getAllByText("support: partial").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("support: direct").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("risk: medium").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("risk: high").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("freshness: current").length).toBeGreaterThanOrEqual(5);
    expect(screen.getAllByText("audience: company_wide").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("audience: role_restricted").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("bez promocji").length).toBeGreaterThanOrEqual(5);
    expect(screen.getAllByText("Klasy danych").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("service_strategy").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("KB_001_EKO_OPIEKA")).toBeInTheDocument();
    expect(screen.getAllByText(/Retencja: pending_owner_decision/).length)
      .toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("goal_005_private_service_review").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Usuń albo odrzuć redacted proposal.").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Claimy zablokowane").length).toBeGreaterThanOrEqual(5);
    expect(screen.getByText("obietnica stałej zgodności")).toBeInTheDocument();
    expect(screen.getByText("Akcje review")).toBeInTheDocument();
    expect(screen.getByText("13 razem")).toBeInTheDocument();
    expect(screen.getByText("6 publicznych usług")).toBeInTheDocument();
    expect(screen.getByText("2 prywatne service")).toBeInTheDocument();
    expect(screen.getByText("3 prywatne claim-policy")).toBeInTheDocument();
    expect(screen.getByText("12 review request")).toBeInTheDocument();
    expect(screen.getByText("1 prepare")).toBeInTheDocument();
    expect(screen.getAllByText(/Najpierw przejrzyj publiczne karty usług/).length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz"))
      .toBeInTheDocument();
    expect(screen.getByText("Sprawdź prywatną propozycję: Styl marki i claim policy Ekologus"))
      .toBeInTheDocument();
    expect(screen.getByText("private_service_proposal")).toBeInTheDocument();
    expect(screen.getByText("private_claim_policy_proposal")).toBeInTheDocument();
    expect(screen.getByText("private_evidence_policy_proposal")).toBeInTheDocument();
    expect(screen.getAllByText("medium").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("high").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Decyzje: approve, needs_changes, stale, reject").length)
      .toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(/Wymagane pola: action ID z live Service Profile \(action_id\)/)
        .length
    )
      .toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy decyzja retencji została podjęta albo świadomie zablokowana \(retention_decision_confirmed\)/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy aktualność prywatnego źródła została potwierdzona \(freshness_status_confirmed\)/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy zakres dostępu\/audience prywatnego źródła jest poprawny \(audience_scope_confirmed\)/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/follow_up_beads przy blokadzie/).length)
      .toBeGreaterThanOrEqual(2);
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
        evidence_ids: ["ev_content_service_profile_source_facts"],
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
      proposal_count: 5,
      service_proposal_count: 2,
      claim_policy_proposal_count: 2,
      evidence_requirement_proposal_count: 1,
      review_required_count: 5,
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
        "ekologus-ai reviewed handoff: Bezpieczeństwo prawne",
        "ekologus-ai reviewed handoff: Source trace"
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
        freshness_status: "current",
        review_status: "review_required",
        support_level: "partial",
        risk_tier: "medium",
        data_classes: ["service_strategy", "internal_operational"],
        source_block_refs: ["KB_001_EKO_OPIEKA"],
        retention_decision: "pending_owner_decision",
        deletion_path: ["Usuń albo odrzuć redacted proposal."],
        eval_case_ids: ["goal_005_private_service_review"],
        confidence_label: "średnia",
        owner_role: "Wilku albo owner oferty Ekologus",
        audience: "company_wide",
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
        freshness_status: "current",
        review_status: "review_required",
        support_level: "partial",
        risk_tier: "medium",
        data_classes: ["service_strategy", "internal_operational"],
        source_block_refs: ["KB_003_AUDYT_ZGODNOSCI"],
        retention_decision: "pending_owner_decision",
        deletion_path: ["Usuń albo odrzuć redacted proposal."],
        eval_case_ids: ["goal_005_private_service_review"],
        confidence_label: "wysoka",
        owner_role: "Wilku albo owner oferty Ekologus",
        audience: "company_wide",
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
        freshness_status: "current",
        review_status: "review_required",
        support_level: "direct",
        risk_tier: "high",
        data_classes: ["brand_policy", "legal_or_claim_policy", "internal_operational"],
        source_block_refs: ["KB_014_STYL_MARKI"],
        retention_decision: "pending_owner_decision",
        deletion_path: ["Usuń albo odrzuć redacted proposal."],
        eval_case_ids: ["goal_005_private_claim_policy_review"],
        confidence_label: "wysoka",
        owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        audience: "role_restricted",
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
        freshness_status: "current",
        review_status: "review_required",
        support_level: "direct",
        risk_tier: "high",
        data_classes: ["brand_policy", "legal_or_claim_policy", "internal_operational"],
        source_block_refs: ["KB_021_BEZPIECZENSTWO_PRAWNE"],
        retention_decision: "pending_owner_decision",
        deletion_path: ["Usuń albo odrzuć redacted proposal."],
        eval_case_ids: ["goal_005_private_claim_policy_review"],
        confidence_label: "wysoka",
        owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        audience: "role_restricted",
        redacted: true,
        blocked_claims: ["poufne dane klientów w materiale marketingowym"],
        safe_next_step: "Pokaż Wilkowi/reviewerowi zasady claimów.",
        promotion_allowed: false,
        blocked_write_claim:
          "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
      },
      {
        proposal_id:
          "private_proposal_ekologus_ai_evidence_policy_source_trace_review_candidate_2026_07_02",
        source_id: "ekologus_ai_evidence_policy_source_trace_review_candidate_2026_07_02",
        source_type: "reviewed_internal",
        privacy_class: "redacted_only",
        scope: "evidence_requirement",
        target_card_id: "ekologus_evidence_policy_source_trace",
        target_card_title: "Source trace i evidence pack",
        source_class_label: "review-required internal evidence-policy source fact",
        source_locator_label: "ekologus-ai reviewed handoff: Source trace",
        freshness_status: "current",
        review_status: "review_required",
        support_level: "direct",
        risk_tier: "medium",
        data_classes: ["evidence_policy", "internal_operational"],
        source_block_refs: ["KB_EVIDENCE_SOURCE_TRACE"],
        retention_decision: "pending_owner_decision",
        deletion_path: ["Usuń albo odrzuć redacted proposal."],
        eval_case_ids: ["goal_005_private_evidence_policy_review"],
        confidence_label: "wysoka",
        owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        audience: "company_wide",
        redacted: true,
        blocked_claims: ["claim z prywatnego źródła bez evidence pack"],
        safe_next_step: "Pokaż Wilkowi/reviewerowi wymogi source trace.",
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
        decision_options: ["approve", "needs_changes", "stale", "reject"],
        review_requirements: reviewRequirementsFixture(),
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
        decision_options: ["approve", "needs_changes", "stale", "reject"],
        review_requirements: reviewRequirementsFixture(),
        label: "Sprawdź prywatną propozycję: Styl marki i claim policy Ekologus",
        reason:
          "ekologus-ai reviewed handoff: Styl marki jest redacted i review-required; może wspierać pytania UAT, ale nie production-depth.",
        blocked_write_claim: "To nie promuje private proposal do source fact ani knowledge card.",
        required_human_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        target_card_id: "ekologus_claim_policy_brand_voice"
      },
      {
        action_id:
          "service_profile_review_private_proposal_ekologus_ai_evidence_policy_source_trace_review_candidate_2026_07_02",
        mode: "review_request",
        review_scope: "private_evidence_policy_proposal",
        priority: "high",
        decision_options: ["approve", "needs_changes", "stale", "reject"],
        review_requirements: reviewRequirementsFixture(),
        label: "Sprawdź prywatną propozycję: Source trace i evidence pack",
        reason:
          "ekologus-ai reviewed handoff: Source trace jest redacted i review-required; może wspierać pytania UAT, ale nie production-depth.",
        blocked_write_claim: "To nie promuje private proposal do source fact ani knowledge card.",
        required_human_role: "Wilku, owner marki albo reviewer prawny Ekologus",
        target_card_id: "ekologus_evidence_policy_source_trace"
      }
    ],
    review_action_summary: {
      total_count: 13,
      review_request_count: 12,
      prepare_count: 1,
      public_service_review_count: 6,
      private_review_count: 5,
      private_service_review_count: 2,
      private_policy_review_count: 3,
      safe_next_step:
        "Najpierw przejrzyj publiczne karty usług, potem prywatne propozycje service, claim-policy i evidence-policy."
    },
    technical_trace: {
      knowledge_card_endpoint: "/api/content/knowledge-cards",
      source_fact_count: 5,
      source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
      private_source_proposal_ids: [
        "private_proposal_ekologus_ai_eko_opieka_2026_07_01",
        "private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01",
        "private_proposal_ekologus_ai_evidence_policy_source_trace_review_candidate_2026_07_02"
      ],
      private_source_protocol_doc: "docs/architecture/private-source-proposal-protocol.md"
    }
  };
}

function reviewRequirementsFixture(): ContentServiceProfileResponse["review_actions"][number]["review_requirements"] {
  return [
    {
      field: "action_id",
      label: "action ID z live Service Profile",
      requirement_type: "text",
      required: true
    },
    {
      field: "target_card_id",
      label: "target card ID zgodny z action_id",
      requirement_type: "text",
      required: true
    },
    {
      field: "decision",
      label: "decyzja review",
      requirement_type: "text",
      required: true
    },
    {
      field: "source_trace_clear",
      label: "czy ślad źródłowy jest czytelny",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "blocked_claims_reviewed",
      label: "czy claimy zablokowane zostały sprawdzone",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "notes",
      label: "notatki review",
      requirement_type: "text",
      required: true
    },
    {
      field: "data_classes_confirmed",
      label: "czy klasy danych prywatnego źródła są poprawne",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "source_block_refs_confirmed",
      label: "czy source block refs są wystarczające do śladu źródłowego",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "freshness_status_confirmed",
      label: "czy aktualność prywatnego źródła została potwierdzona",
      requirement_type: "boolean",
      required: true,
      blocking_rule:
        "Nie wolno promować prywatnej propozycji, gdy freshness_status nie został potwierdzony przez ownera/reviewera."
    },
    {
      field: "audience_scope_confirmed",
      label: "czy zakres dostępu/audience prywatnego źródła jest poprawny",
      requirement_type: "boolean",
      required: true,
      blocking_rule:
        "Nie wolno promować prywatnej propozycji, gdy audience/scope nie został potwierdzony dla użycia marketingowego."
    },
    {
      field: "retention_decision_confirmed",
      label: "czy decyzja retencji została podjęta albo świadomie zablokowana",
      requirement_type: "boolean",
      required: true,
      blocking_rule:
        "Nie wolno promować prywatnej propozycji, gdy retention_decision pozostaje pending_owner_decision bez świadomej decyzji ownera."
    },
    {
      field: "deletion_path_confirmed",
      label: "czy ścieżka usunięcia/odrzucenia proposal jest jasna",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "eval_gates_confirmed",
      label: "czy eval gates blokujące unsafe claimy są wskazane",
      requirement_type: "boolean",
      required: true
    },
    {
      field: "follow_up_beads",
      label: "follow-up Beads",
      requirement_type: "follow_up",
      required: false,
      blocking_rule: "Wymagane przy blokadzie."
    }
  ];
}
