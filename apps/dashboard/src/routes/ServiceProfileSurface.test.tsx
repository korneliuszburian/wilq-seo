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
    expect(screen.getByText("Gotowość zatwierdzenia wiedzy")).toBeInTheDocument();
    expect(screen.getByText("wniosek o zatwierdzenie zablokowany")).toBeInTheDocument();
    expect(screen.getByText("wniosek zablokowany")).toBeInTheDocument();
    expect(screen.getByText("bez mutacji")).toBeInTheDocument();
    expect(screen.getByText("wymaga wyniku review")).toBeInTheDocument();
    expect(
      screen.getByText("Publiczne karty usług sprawdzone przez człowieka")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Osobny wniosek o zatwierdzenie jest gotowy do przygotowania")
    ).toBeInTheDocument();
    expect(screen.getByText("Audyt pokrycia wiedzy")).toBeInTheDocument();
    expect(screen.getByText("Production-depth")).toBeInTheDocument();
    expect(screen.getByText("Usługi zatwierdzone")).toBeInTheDocument();
    expect(screen.getByText("Fakty zatwierdzone")).toBeInTheDocument();
    expect(screen.getByText("Wartość ekologus-ai")).toBeInTheDocument();
    expect(screen.getByText("9/10")).toBeInTheDocument();
    expect(screen.getByText("Co to znaczy teraz")).toBeInTheDocument();
    expect(screen.getByText("audyt spójny")).toBeInTheDocument();
    expect(screen.getByText("14 faktów źródłowych")).toBeInTheDocument();
    expect(screen.getByText("13 akcji review")).toBeInTheDocument();
    expect(screen.getByText("5 prywatnych do review")).toBeInTheDocument();
    expect(screen.getByText("Pytania do Wilka")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?"
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Następne review")).toBeInTheDocument();
    expect(screen.getByText(/Zacznij od:/)).toBeInTheDocument();
    expect(screen.getByText("Liczby techniczne")).toBeInTheDocument();
    expect(screen.getByText("Najpierw publiczne karty usług Ekologus.")).toBeInTheDocument();
    expect(screen.getByText("Pierwszy review item")).toBeInTheDocument();
    expect(
      screen.getAllByText("Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa")
        .length
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Wymagane pola review")).toBeInTheDocument();
    expect(screen.getAllByText("source_trace_clear").length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(
        "Potem prywatne propozycje ekologus-ai: usługi, polityki twierdzeń i wymagania dowodowe."
      )
    ).toBeInTheDocument();
    expect(screen.getAllByText("Zatwierdzone").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("ekologus-ai")).toBeInTheDocument();
    expect(screen.getAllByText(/production-depth zablokowane/).length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/źródła są, wymagają review/)).toBeInTheDocument();
    expect(screen.getByText("Polityka zapisu")).toBeInTheDocument();
    expect(screen.getByText(/Edycja kart i promocja faktów wymagają/)).toBeInTheDocument();
    expect(screen.getByText("Brak bezpośredniej karty usługi dla operatu wodnoprawnego"))
      .toBeInTheDocument();
    expect(screen.getAllByText("BDO i sprawozdawczość środowiskowa").length)
      .toBeGreaterThanOrEqual(1);
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
    expect(screen.getByText("2 polityki twierdzeń")).toBeInTheDocument();
    expect(screen.getByText("1 wymagania dowodowe")).toBeInTheDocument();
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
    expect(screen.getAllByText("Styl marki i claim policy Ekologus").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Bezpieczeństwo prawne, poufność i zgody").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Source trace i evidence pack").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("częściowe wsparcie").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("wsparcie bezpośrednie").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("średnie ryzyko").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("wysokie ryzyko").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("aktualność: aktualne").length).toBeGreaterThanOrEqual(5);
    expect(screen.getAllByText("odbiorcy: dla całej firmy").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("odbiorcy: dla wybranej roli").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("bez promocji").length).toBeGreaterThanOrEqual(5);
    expect(screen.getAllByText("Klasy danych").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("service_strategy").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Bloki źródła").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("KB_001_EKO_OPIEKA")).toBeInTheDocument();
    expect(screen.getAllByText(/Retencja: decyzja właściciela wymagana/).length)
      .toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Bramki ewaluacji").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("goal_005_private_service_review").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Usuń albo odrzuć zredagowaną propozycję.").length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/Retencja: pending_owner_decision/)).not.toBeInTheDocument();
    expect(screen.queryByText("Source block refs")).not.toBeInTheDocument();
    expect(screen.queryByText("Eval gates")).not.toBeInTheDocument();
    expect(screen.getAllByText("Twierdzenia zablokowane").length).toBeGreaterThanOrEqual(5);
    expect(screen.getByText("obietnica stałej zgodności")).toBeInTheDocument();
    expect(screen.getByText("Akcje review")).toBeInTheDocument();
    expect(screen.getByText("13 razem")).toBeInTheDocument();
    expect(screen.getByText("6 publicznych usług")).toBeInTheDocument();
    expect(screen.getByText("2 prywatne usługi")).toBeInTheDocument();
    expect(screen.getByText("3 prywatne polityki twierdzeń")).toBeInTheDocument();
    expect(screen.getByText("12 prośby o review")).toBeInTheDocument();
    expect(screen.getByText("1 przygotowań")).toBeInTheDocument();
    expect(screen.getAllByText(/Najpierw przejrzyj publiczne karty usług/).length)
      .toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Sprawdź prywatną propozycję: Eko-Opieka / Eko Kalendarz"))
      .toBeInTheDocument();
    expect(screen.getByText("Sprawdź prywatną propozycję: Styl marki i claim policy Ekologus"))
      .toBeInTheDocument();
    expect(screen.getByText("prywatna propozycja usługi")).toBeInTheDocument();
    expect(screen.getByText("prywatna propozycja polityki twierdzeń")).toBeInTheDocument();
    expect(screen.getByText("prywatna propozycja wymagań dowodowych")).toBeInTheDocument();
    expect(screen.getAllByText("średni priorytet").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("wysoki priorytet").length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText(
        "Decyzje: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne, odrzuć"
      ).length
    )
      .toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(/Wymagane pola: action ID z live Service Profile/).length
    )
      .toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy decyzja retencji została podjęta albo świadomie zablokowana/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy aktualność prywatnego źródła została potwierdzona/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(
        /czy zakres dostępu\/audience prywatnego źródła jest poprawny/
      ).length
    ).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText("Decyzje: approve, needs_changes, stale, reject"))
      .not.toBeInTheDocument();
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
    private_review_value: {
      proposal_count: 5,
      promotion_allowed_count: 0,
      blocked_claim_proposal_count: 5,
      cta_pattern_proposal_count: 1,
      buyer_trigger_proposal_count: 2,
      operator_value_score: 9,
      value_summary:
        "Prywatne propozycje ekologus-ai dają materiał do review i mogą poprawić konkretność Service Profile, ale nie odblokowują production-depth, publikacji ani gotowych twierdzeń bez decyzji człowieka.",
      review_value_points: [
        "Prywatne propozycje dodają CTA albo kierunek rozmowy do oceny przez Wilka.",
        "Prywatne propozycje doprecyzowują problemy i triggery kupującego.",
        "Żadna prywatna propozycja nie może wejść do production-depth bez review człowieka."
      ],
      review_questions: [
        "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?",
        "Czy opisany problem kupującego faktycznie pasuje do rozmów z klientami Ekologus?"
      ]
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
      first_review_action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
      first_review_action_label: "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa",
      first_review_action_reason:
        "Karta ma publiczne źródło, ale wymaga decyzji człowieka zanim stanie się approved-current.",
      first_review_action_scope: "public_service_card",
      first_review_action_priority: "medium",
      first_review_action_target_card_id: "ekologus_service_bdo_reporting",
      first_review_action_gap_id: null,
      first_review_required_fields: [
        "action_id",
        "target_card_id",
        "decision",
        "source_trace_clear",
        "blocked_claims_reviewed",
        "notes"
      ],
      first_review_safe_next_step:
        "Weź tę publiczną kartę jako pierwszą: sprawdź źródło, zablokowane claimy i dopiero potem zdecyduj approve/needs_changes/stale/reject.",
      safe_next_step:
        "Najpierw przejrzyj publiczne karty usług, potem prywatne propozycje service, claim-policy i evidence-policy."
    },
    source_fact_coverage: {
      pass_state: true,
      knowledge_status: "source_backed_review_required",
      ready_for_daily_content: false,
      production_depth_percent: 0,
      approved_service_percent: 0,
      reviewed_fact_percent: 0,
      fact_count: 14,
      fact_review_counts: { review_required: 14 },
      fact_scope_counts: { claim_policy: 2, cta: 1, evidence_requirement: 2, service: 9 },
      fact_connector_counts: { ekologus_ai_private_source_catalog: 5, public_site: 9 },
      service_card_count: 8,
      coverage_gap_count: 1,
      review_action_count: 13,
      first_review_action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
      first_review_action_label: "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa",
      private_proposal_count: 5,
      private_review_required_count: 5,
      private_review_value: {
        proposal_count: 5,
        promotion_allowed_count: 0,
        blocked_claim_proposal_count: 5,
        cta_pattern_proposal_count: 1,
        buyer_trigger_proposal_count: 2,
        operator_value_score: 9,
        value_summary:
          "Prywatne propozycje ekologus-ai dają materiał do review i mogą poprawić konkretność Service Profile, ale nie odblokowują production-depth, publikacji ani gotowych twierdzeń bez decyzji człowieka.",
        review_value_points: [
          "Prywatne propozycje dodają CTA albo kierunek rozmowy do oceny przez Wilka.",
          "Prywatne propozycje doprecyzowują problemy i triggery kupującego.",
          "Żadna prywatna propozycja nie może wejść do production-depth bez review człowieka."
        ],
        review_questions: [
          "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?",
          "Czy opisany problem kupującego faktycznie pasuje do rozmów z klientami Ekologus?"
        ]
      },
      private_review_queue: [
        {
          proposal_id:
            "private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
          source_id: "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
          scope: "claim_policy",
          target_card_id: "ekologus_claim_policy_legal_safety",
          target_card_title: "Bezpieczeństwo prawne, poufność i zgody",
          risk_tier: "high",
          freshness_status: "current",
          audience: "role_restricted",
          review_status: "review_required",
          promotion_allowed: false,
          blocked_claim_count: 1,
          data_classes: ["brand_policy", "legal_or_claim_policy", "internal_operational"],
          source_block_refs: ["KB_021_BEZPIECZENSTWO_PRAWNE"],
          retention_decision: "pending_owner_decision",
          deletion_path: ["Usuń albo odrzuć redacted proposal."],
          eval_case_ids: ["goal_005_private_claim_policy_review"],
          source_locator_label: "ekologus-ai reviewed handoff: Bezpieczeństwo prawne",
          owner_role: "Wilku, owner marki albo reviewer prawny Ekologus",
          redacted: true,
          source_trace_ready: true,
          safe_next_step: "Pokaż Wilkowi/reviewerowi zasady claimów."
        }
      ],
      review_action_queue: [
        {
          action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
          review_scope: "public_service_card",
          priority: "medium",
          target_card_id: "ekologus_service_bdo_reporting",
          target_card_title: "BDO i sprawozdawczość środowiskowa",
          decision_options: ["approve", "needs_changes", "stale", "reject"]
        },
        {
          action_id:
            "service_profile_review_private_proposal_ekologus_ai_brand_voice_2026_07_01",
          review_scope: "private_claim_policy_proposal",
          priority: "high",
          target_card_id: "ekologus_claim_policy_brand_voice",
          target_card_title: "Styl marki i claim policy Ekologus",
          decision_options: ["approve", "needs_changes", "stale", "reject"]
        }
      ],
      blockers: [
        "Brakuje zatwierdzonych production-depth kart usług Ekologus.",
        "WILQ nie powinien dopasowywać szerokiej karty środowiskowej do usługi bez źródła."
      ],
      safe_next_step:
        "Przejrzyj karty review-required i luki usługowe z Wilkiem przed użyciem ich jako production-depth."
    },
    approval_readiness: {
      status: "blocked",
      status_label: "wniosek o zatwierdzenie zablokowany",
      can_request_promotion: false,
      mutation_allowed: false,
      production_depth_unlocked: false,
      reviewed_output_required: true,
      approved_current_count: 0,
      review_required_count: 5,
      first_action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
      first_action_label: "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa",
      blockers: [
        "Publiczne karty usług sprawdzone przez człowieka",
        "Ślad źródłowy i zablokowane twierdzenia sprawdzone",
        "Prywatne propozycje ekologus-ai mają decyzję ownera",
        "Osobny wniosek o zatwierdzenie jest gotowy do przygotowania"
      ],
      checklist: [
        {
          code: "public_service_review",
          label: "Publiczne karty usług sprawdzone przez człowieka",
          status: "ready_for_review",
          blocking: true,
          detail:
            "6 publicznych kart czeka na decyzję review; żadna nie jest jeszcze zatwierdzona jako wiedza do finalnych treści.",
          next_step:
            "Zacznij od pierwszej publicznej karty usługi i zapisz decyzję.",
          related_action_id: "service_profile_review_card_ekologus_service_bdo_reporting"
        },
        {
          code: "source_trace_review",
          label: "Ślad źródłowy i zablokowane twierdzenia sprawdzone",
          status: "ready_for_review",
          blocking: true,
          detail:
            "Review musi potwierdzić czytelny ślad źródłowy, zablokowane twierdzenia, notatkę review i decyzję człowieka.",
          next_step: "Użyj pól review z Service Profile.",
          related_action_id: "service_profile_review_card_ekologus_service_bdo_reporting"
        },
        {
          code: "private_source_governance",
          label: "Prywatne propozycje ekologus-ai mają decyzję ownera",
          status: "blocked",
          blocking: true,
          detail:
            "5 prywatnych propozycji nadal wymaga decyzji review, retencji albo aktualności.",
          next_step:
            "Dla prywatnych propozycji potwierdź klasy danych, bloki źródła, aktualność i retencję."
        },
        {
          code: "promotion_request_packet",
          label: "Osobny wniosek o zatwierdzenie jest gotowy do przygotowania",
          status: "blocked",
          blocking: true,
          detail:
            "WILQ nie ma jeszcze zatwierdzonego wyniku review, więc nie wolno przygotować wniosku jako gotowego do promocji wiedzy.",
          next_step: "Najpierw zapisz wynik rozmowy review."
        }
      ],
      safe_next_step:
        "Przeprowadź review pierwszej karty Service Profile i zapisz wynik review; WILQ nadal nie zmieni kart ani source facts bez osobnej audytowanej ścieżki."
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
