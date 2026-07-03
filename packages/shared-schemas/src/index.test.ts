import { describe, expect, it } from "vitest";

import {
  ActionObjectSchema,
  ContentWorkItemDraftPackageResponseSchema,
  ContentWorkItemHumanReviewResponseSchema,
  ContentWorkItemMeasurementOutcomeResponseSchema,
  ContentWorkItemMeasurementWindowResponseSchema,
  ContentWorkItemPreflightResponseSchema,
  ContentWorkItemSalesBriefResponseSchema,
  ContentWorkItemSnapshotAuditRequestSchema,
  ContentWorkItemSnapshotHumanReviewRequestSchema,
  ContentWorkItemSnapshotResponseSchema,
  ContentServiceProfileResponseSchema,
  ContentServiceProfileCoverageGapSchema,
  ContentWorkItemQualityReviewRequestSchema,
  ContentWorkItemStructuredDraftGenerationResponseSchema,
  ContentWorkItemStructuredDraftPreviewResponseSchema,
  ContentWorkItemStructuredDraftRuntimeResponseSchema,
  ContentQualityFindingSchema,
  ContentWorkItemSchema,
  ContentClaimLedgerSchema,
  ContentClaimReferenceSchema,
  ContentDraftPackageSchema,
  ContentKnowledgeConstraintTypeSchema,
  ContentRecommendedModeSchema,
  ContentGscSearchAnalyticsContractSchema,
  ContentServiceProfilePrivateSourceProposalSectionSchema,
  PrivateProposalSchema,
  StructuredDraftPreviewBlockerSchema,
  ContentWorkItemWordPressDraftExecutionRequestSchema,
  ContentWorkItemWordPressDraftExecutionResponseSchema,
  ContentWorkItemWordPressDraftHandoffResponseSchema,
  ContentWordPressAuthoringPayloadPreviewResultSchema,
  ContentWorkItemWorkflowSnapshotResponseSchema,
  ContentPreflightResponseSchema,
  MerchantDiagnosticsResponseSchema,
  SocialHistoryImportAuditSchema,
  SocialHistoryInventorySchema,
  SocialHistoryInventorySourceSchema,
  WordPressAuthoringProfileSchema
} from "./index";

describe("ActionObjectSchema", () => {
  const validAction = {
    id: "act_prepare_test",
    title: "Przygotuj review",
    domain: "content",
    connector: "wordpress_ekologus",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_content_service_profile_source_facts"],
    metrics: [],
    human_diagnosis: "Akcja wymaga review.",
    recommended_reason: "Przygotuj bezpieczny podgląd.",
    validation_status: "not_validated",
    payload: {},
    audit_events: []
  };

  it("accepts only backend-owned action enum values", () => {
    expect(ActionObjectSchema.safeParse(validAction).success).toBe(true);
    expect(
      ActionObjectSchema.safeParse({ ...validAction, domain: "ads" }).success
    ).toBe(false);
    expect(
      ActionObjectSchema.safeParse({ ...validAction, status: "waiting" }).success
    ).toBe(false);
    expect(
      ActionObjectSchema.safeParse({
        ...validAction,
        validation_status: "pending_validation"
      }).success
    ).toBe(false);
  });
});

describe("SocialHistoryInventorySourceSchema", () => {
  it("keeps social history metadata-only and rejects raw post body collection", () => {
    const validSource = {
      channel: "linkedin",
      connector_id: "linkedin",
      inventory_status: "missing",
      connector_access_status: "missing_credentials",
      required_evidence_id: "linkedin_historical_posts",
      required_metadata_fields: [
        "channel",
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id"
      ],
      safe_collection_mode: "metadata_only",
      raw_post_body_allowed: false
    };

    expect(SocialHistoryInventorySourceSchema.safeParse(validSource).success).toBe(true);
    expect(
      SocialHistoryInventorySourceSchema.safeParse({
        ...validSource,
        raw_post_body_allowed: true
      }).success
    ).toBe(false);
  });
});

describe("SocialHistoryImportAuditSchema", () => {
  it("keeps social history audit read-only and blocks publish claims", () => {
    const validAudit = {
      contract: "social_history_inventory_v1",
      read_only: true,
      status: "review_ready",
      item_count: 2,
      channel_counts: { facebook: 1, linkedin: 1 },
      missing_required_sources: [],
      required_metadata_fields: [
        "channel",
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id"
      ],
      forbidden_metadata_fields: ["raw_post_body", "comments", "access_token"],
      errors: [],
      duplicate_free_claim_allowed: false,
      publish_allowed: false,
      operator_next_step: "Przekaż metadata-only historię do review dedupe."
    };

    expect(SocialHistoryImportAuditSchema.safeParse(validAudit).success).toBe(true);
    expect(
      SocialHistoryImportAuditSchema.safeParse({
        ...validAudit,
        publish_allowed: true
      }).success
    ).toBe(false);
    expect(
      SocialHistoryImportAuditSchema.safeParse({
        ...validAudit,
        duplicate_free_claim_allowed: true
      }).success
    ).toBe(false);
  });
});

describe("ContentWordPressAuthoringPayloadPreviewResultSchema", () => {
  it("accepts review-only ACF row candidates without write permissions", () => {
    const preview = {
      status: "ready",
      mode: "dry_run",
      connector: "wordpress_ekologus",
      endpoint_kind: "posts",
      post_status: "draft",
      flexible_content_field_name: "podstrona",
      sections: [
        {
          layout_name: "podstrona",
          layout_label: "Podstrona",
          section_heading: "Kogo dotyczy BDO",
          field_values: { elementy: null },
          field_previews: [
            {
              field_name: "elementy",
              field_label: "Elementy",
              field_type: "flexible_content",
              value_preview: null,
              safe_to_autofill: true,
              note: "Pole zagnieżdżone wymaga ręcznego przeglądu.",
              nested_values: [],
              row_candidates: [
                {
                  row_type: "acf_flexible_content_row",
                  row_label: "Wiersz do ręcznego przeglądu: Kogo dotyczy BDO",
                  review_status: "review_required",
                  note: "Bez zapisu w WordPress.",
                  field_values: [
                    {
                      field_name: "opis",
                      field_label: "Opis",
                      field_type: "wysiwyg",
                      value_preview: "Opis sekcji do sprawdzenia.",
                      safe_to_autofill: true,
                      note: null
                    }
                  ],
                  evidence_ids: ["ev_gsc_bdo"]
                }
              ]
            }
          ],
          missing_required_fields: [],
          evidence_ids: ["ev_gsc_bdo"]
        }
      ],
      publish_allowed: false,
      destructive_update_allowed: false,
      external_write_attempted: false,
      required_action_contract: "actionobject_validate_preview_review_confirm_audit",
      blockers: []
    };

    expect(ContentWordPressAuthoringPayloadPreviewResultSchema.safeParse(preview).success)
      .toBe(true);
    expect(
      ContentWordPressAuthoringPayloadPreviewResultSchema.safeParse({
        ...preview,
        publish_allowed: true
      }).success
    ).toBe(false);
  });
});

describe("SocialHistoryInventorySchema", () => {
  it("keeps public discovery seeds metadata-only", () => {
    const validInventory = {
      contract: "social_history_inventory_v1",
      read_only: true,
      status: "missing",
      status_label: "brak spisu historycznych postów LinkedIn/Facebook",
      duplicate_risk_status: "blocked_until_social_history_review",
      required_sources: ["linkedin", "facebook"],
      missing_evidence_ids: ["linkedin_historical_posts", "facebook_historical_posts"],
      sources: [],
      discovery_seeds: [
        {
          id: "social_history_seed_ekologus_linkedin_posts",
          channel: "linkedin",
          source_type: "public_posts_url",
          source_url: "https://www.linkedin.com/company/ekologus/posts/?feedView=all",
          status: "seeded_not_collected",
          safe_collection_mode: "metadata_only",
          raw_post_body_allowed: false,
          required_review: true,
          operator_note: "Publiczny seed discovery nie jest gotową historią postów."
        }
      ],
      allowed_uses: ["sprawdzenie powtórek"],
      blocked_uses: ["twierdzenie że temat jest nowy bez historii postów"],
      dedupe_requirements: ["porównać temat, claim i CTA"],
      operator_next_step: "Zbierz metadata-only historię social."
    };

    expect(SocialHistoryInventorySchema.safeParse(validInventory).success).toBe(true);
    expect(
      SocialHistoryInventorySchema.safeParse({
        ...validInventory,
        discovery_seeds: [
          {
            ...validInventory.discovery_seeds[0],
            raw_post_body_allowed: true
          }
        ]
      }).success
    ).toBe(false);
  });
});

describe("WordPressAuthoringProfileSchema", () => {
  it("keeps WordPress authoring draft-only", () => {
    const validProfile = {
      profile_version: "wordpress_authoring_profile_v1",
      connector: "wordpress_ekologus",
      site_kind: "primary",
      authoring_target: "staging",
      discovery_mode: "rest_first",
      discovery_order: ["rest", "acf_rest", "wp_cli", "helper"],
      rest_api: {
        method: "rest",
        status: "configured",
        base_url_configured: true,
        auth_configured: true,
        public_url_configured: true,
        post_types: ["page", "post"]
      },
      acf: {
        enabled_state: "unknown",
        rest_enabled_state: "unknown",
        flexible_content_field_name: null,
        post_types: ["page", "post"],
        layouts: [
          {
            name: "podstrona",
            label: "Podstrona",
            fields: [],
            source_method: "acf_export",
            required_field_names: [],
            optional_field_names: ["tytul", "glowny_opis"]
          }
        ],
        source_method: "acf_export",
        layouts_discovered: true
      },
      wp_cli: {
        method: "wp_cli",
        status: "configured",
        configured: true,
        missing_env: [],
        source_refs: ["WORDPRESS_EKOLOGUS_WP_CLI_PATH"]
      },
      helper_plugin: {
        method: "helper",
        status: "not_configured",
        configured: false,
        missing_env: ["WORDPRESS_EKOLOGUS_HELPER_URL"],
        source_refs: []
      },
      write_boundary: {
        allowed_operation: "create_wordpress_draft",
        direct_vendor_write_allowed: false,
        draft_writes_enabled_by_env: false,
        live_write_enabled: false,
        publish_allowed: false,
        destructive_update_allowed: false,
        external_write_attempted: false,
        required_action_contract: "actionobject_validate_preview_review_confirm_audit"
      },
      discovery_facts: [],
      blockers: [],
      evidence_ids: ["ev_connector_wordpress_ekologus_status"],
      source_connectors: ["wordpress_ekologus"]
    };

    expect(WordPressAuthoringProfileSchema.safeParse(validProfile).success).toBe(true);
    expect(
      WordPressAuthoringProfileSchema.safeParse({
        ...validProfile,
        write_boundary: {
          ...validProfile.write_boundary,
          publish_allowed: true
        }
      }).success
    ).toBe(false);
  });
});

describe("ContentQualityFindingSchema", () => {
  it("accepts backend-owned quality review signal and claim finding codes", () => {
    for (const code of [
      "required_claim_missing",
      "sales_brief_signal_review_required",
      "sales_brief_signal_thin"
    ]) {
      expect(
        ContentQualityFindingSchema.safeParse({
          code,
          severity: code === "sales_brief_signal_thin" ? "blocker" : "needs_changes",
          label: "Kontrola jakości",
          reason: "Powód z WILQ API.",
          next_step: "Wykonaj bezpieczny następny krok.",
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"]
        }).success
      ).toBe(true);
    }
  });
});

describe("ContentServiceProfileResponseSchema", () => {
  it("rejects unknown Service Profile gap source requirements", () => {
    expect(
      ContentServiceProfileCoverageGapSchema.safeParse({
        gap_id: "gap_no_approved_current_cards",
        area: "approved_current",
        severity: "blocker",
        label: "Brak zatwierdzonych kart",
        reason: "Production-depth content needs approved current cards.",
        needed_source_type: "random_source",
        safe_next_step: "Zbierz owner review.",
        example_work_item_ids: []
      }).success
    ).toBe(false);
  });

  it("accepts the read-only Service Profile contract", () => {
    const parsed = ContentServiceProfileResponseSchema.parse({
      workspace_id: "ekologus",
      workspace_label: "Ekologus",
      generated_at: "2026-07-01T00:00:00Z",
      read_only: true,
      review_policy: {
        can_edit_cards: false,
        can_promote_facts: false,
        can_request_review: true,
        review_required_label: "Review required.",
        blocked_write_reason: "No direct knowledge writes."
      },
      production_depth_readiness: {
        status: "source_backed_review_required",
        status_label: "źródła są, wymagają review",
        ready_for_daily_content: false,
        seeded_card_count: 3,
        source_backed_review_required_count: 5,
        production_depth_card_count: 0,
        blocker_labels: ["Brakuje zatwierdzonych kart."]
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
        missing_required_area_count: 1,
        ready_for_daily_content: false,
        status_label: "źródła są, wymagają review",
        safe_next_step: "Review cards."
      },
      service_sections: [
        {
          card_id: "ekologus_service_bdo_reporting",
          title: "BDO",
          status: "source_backed_review_required",
          status_label: "wymaga review",
          summary: "BDO service card.",
          source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
          evidence_ids: ["ev_owner_review_bdo_service_fact"],
          source_connector_labels: ["public_site"],
          source_lineage_labels: ["https://www.ekologus.pl/bdo/"],
          freshness_label: "public_site_review_required_2026-07-01",
          confidence_label: "średnia",
          service_fit_terms: ["bdo"],
          buyer_problem_terms: [],
          buyer_triggers: [],
          cta_patterns: [],
          allowed_claims: [],
          claims_needing_review: [],
          forbidden_claims: [],
          evidence_requirements: [],
          usage_notes: [],
          safe_next_step: "Review.",
          review_request_hint: "Ask owner."
        }
      ],
      claim_policy_sections: [],
      evidence_policy_sections: [],
      private_source_proposal_summary: {
        proposal_protocol_available: true,
        proposal_count: 2,
        service_proposal_count: 1,
        claim_policy_proposal_count: 1,
        evidence_requirement_proposal_count: 0,
        review_required_count: 2,
        approved_count: 0,
        promotion_ready: false,
        promotion_checklist: [
          "Wilku albo owner potwierdza, że propozycja opisuje realną ofertę Ekologus.",
          "Źródło zostaje streszczone jako redacted/source-safe fact bez raw private text."
        ],
        promotion_blocked_reason:
          "Brak zatwierdzenia człowieka i reviewed source fact.",
        proposal_source_labels: ["ekologus-ai reviewed handoff: Eko-Opieka"],
        review_required_proposal_ids: ["private_proposal_ekologus_ai_eko_opieka_2026_07_01"],
        redacted: true,
        safe_next_step: "Use private proposal protocol."
      },
      private_review_value: {
        proposal_count: 1,
        promotion_allowed_count: 0,
        blocked_claim_proposal_count: 1,
        cta_pattern_proposal_count: 0,
        buyer_trigger_proposal_count: 1,
        operator_value_score: 7,
        value_summary:
          "Prywatne propozycje ekologus-ai dają materiał do review, ale nie odblokowują production-depth.",
        review_value_points: [
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
          safe_next_step: "Pokazać Wilkowi zwykły handoff.",
          promotion_allowed: false,
          blocked_write_claim: "To jest redacted proposal do review."
        }
      ],
      coverage_gaps: [
        {
          gap_id: "gap_service_operat_wodnoprawny",
          area: "operat wodnoprawny",
          severity: "blocker",
          label: "Brak karty usługi",
          reason: "Missing direct source.",
          needed_source_type: "public_site_or_reviewed_internal_service_fact",
          safe_next_step: "Add source fact.",
          example_work_item_ids: ["content_work_item_operat_wodnoprawny"]
        }
      ],
      review_actions: [
        {
          action_id: "service_profile_request_knowledge_review",
          mode: "review_request",
          review_scope: "general_knowledge_review",
          priority: "medium",
          decision_options: ["approve", "needs_changes", "stale", "reject"],
          review_requirements: [
            {
              field: "action_id",
              label: "action ID z live Service Profile",
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
              field: "follow_up_beads",
              label: "follow-up Beads",
              requirement_type: "follow_up",
              required: false,
              blocking_rule: "Wymagane przy blokadzie."
            }
          ],
          label: "Poproś o review",
          reason: "Review required.",
          blocked_write_claim: "No write.",
          required_human_role: "Wilku"
        }
      ],
      review_action_summary: {
        total_count: 1,
        review_request_count: 1,
        prepare_count: 0,
        public_service_review_count: 0,
        private_review_count: 0,
        private_service_review_count: 0,
        private_policy_review_count: 0,
        first_review_action_id: "service_profile_request_knowledge_review",
        first_review_action_label: "Poproś o review",
        first_review_action_reason: "Review required.",
        first_review_action_scope: "general_knowledge_review",
        first_review_action_priority: "medium",
        first_review_action_target_card_id: null,
        first_review_action_gap_id: null,
        first_review_required_fields: ["action_id", "source_trace_clear"],
        first_review_safe_next_step: "Zbierz decyzję review człowieka.",
        safe_next_step: "Review public cards, then private proposals."
      },
      source_fact_coverage: {
        pass_state: true,
        knowledge_status: "source_backed_review_required",
        ready_for_daily_content: false,
        production_depth_percent: 0,
        approved_service_percent: 0,
        reviewed_fact_percent: 0,
        fact_count: 5,
        fact_review_counts: { review_required: 5 },
        fact_scope_counts: { service: 4, claim_policy: 1 },
        fact_connector_counts: { public_site: 4, ekologus_ai_private_source_catalog: 1 },
        service_card_count: 5,
        coverage_gap_count: 1,
        review_action_count: 1,
        first_review_action_id: "service_profile_request_knowledge_review",
        first_review_action_label: "Poproś o review",
        private_proposal_count: 1,
        private_review_required_count: 1,
        private_review_value: {
          proposal_count: 1,
          promotion_allowed_count: 0,
          blocked_claim_proposal_count: 1,
          cta_pattern_proposal_count: 0,
          buyer_trigger_proposal_count: 1,
          operator_value_score: 7,
          value_summary:
            "Prywatne propozycje ekologus-ai dają materiał do review, ale nie odblokowują production-depth.",
          review_value_points: [
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
              "private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
            source_id: "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
            scope: "service",
            target_card_id: "ekologus_service_eko_opieka_calendar",
            target_card_title: "Eko-Opieka / Eko Kalendarz",
            risk_tier: "medium",
            freshness_status: "current",
            audience: "company_wide",
            review_status: "review_required",
            promotion_allowed: false,
            blocked_claim_count: 1,
            safe_next_step: "Pokazać Wilkowi zwykły handoff."
          }
        ],
        review_action_queue: [
          {
            action_id: "service_profile_request_knowledge_review",
            review_scope: "general_knowledge_review",
            priority: "medium",
            target_card_id: null,
            target_card_title: "ogólny przegląd wiedzy",
            decision_options: ["approve", "needs_changes", "stale", "reject"]
          }
        ],
        blockers: ["Brakuje zatwierdzonych kart."],
        safe_next_step: "Review cards."
      },
      technical_trace: {
        knowledge_card_endpoint: "/api/content/knowledge-cards",
        source_fact_count: 5,
        source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
        private_source_proposal_ids: [
          "private_proposal_ekologus_ai_eko_opieka_2026_07_01"
        ],
        private_source_protocol_doc: "docs/architecture/private-source-proposal-protocol.md"
      }
    });

    expect(parsed.read_only).toBe(true);
    expect(parsed.review_policy.can_edit_cards).toBe(false);
    expect(parsed.coverage_gaps[0]?.gap_id).toBe("gap_service_operat_wodnoprawny");
    expect(parsed.private_source_proposals[0]?.promotion_allowed).toBe(false);
  });
});

describe("ContentQualityFindingSchema", () => {
  it("accepts only known quality gate codes", () => {
    expect(
      ContentQualityFindingSchema.safeParse({
        code: "missing_forbidden_claim_acknowledgement",
        severity: "blocker",
        label: "Szkic nie potwierdza uniknięcia zakazanych claimów",
        reason: "Ocena jakości wymaga jawnego potwierdzenia.",
        next_step: "Uzupełnij listę unikniętych claimów.",
        evidence_ids: ["ev_wp_bdo"],
        source_connectors: ["wordpress_ekologus"]
      }).success
    ).toBe(true);

    expect(
      ContentQualityFindingSchema.safeParse({
        code: "new_unreviewed_quality_gate",
        severity: "blocker",
        label: "Nieznany kod",
        reason: "Nie powinien przejść shared schema.",
        next_step: "Dodaj kod do kontraktu przed użyciem.",
        evidence_ids: [],
        source_connectors: []
      }).success
    ).toBe(false);
  });
});

describe("PrivateProposalSchema", () => {
  const proposal = {
    proposal_id: "private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
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
    safe_next_step: "Pokazać Wilkowi zwykły handoff.",
    promotion_allowed: false,
    blocked_write_claim: "To jest redacted proposal do review."
  };

  it("keeps the legacy export as a compatibility alias", () => {
    expect(ContentServiceProfilePrivateSourceProposalSectionSchema).toBe(
      PrivateProposalSchema
    );
  });

  it("rejects unknown private proposal states", () => {
    expect(
      PrivateProposalSchema.safeParse(proposal).success
    ).toBe(true);

    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        review_status: "maybe_ready"
      }).success
    ).toBe(false);

    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        support_level: "looks_good"
      }).success
    ).toBe(false);

    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        risk_tier: "comfortable"
      }).success
    ).toBe(false);
    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        freshness_status: "fresh_enough"
      }).success
    ).toBe(false);
    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        audience: "everyone_on_internet"
      }).success
    ).toBe(false);
    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        retention_decision: "keep_forever"
      }).success
    ).toBe(false);

    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        privacy_class: "commit_safe"
      }).success
    ).toBe(false);
  });

  it("rejects weak private proposal governance fields", () => {
    for (const fieldName of [
      "data_classes",
      "source_block_refs",
      "deletion_path",
      "eval_case_ids",
      "blocked_claims"
    ] as const) {
      expect(
        PrivateProposalSchema.safeParse({
          ...proposal,
          [fieldName]: []
        }).success
      ).toBe(false);
      expect(
        PrivateProposalSchema.safeParse({
          ...proposal,
          [fieldName]: [" "]
        }).success
      ).toBe(false);
    }

    expect(
      PrivateProposalSchema.safeParse({
        ...proposal,
        safe_next_step: ""
      }).success
    ).toBe(false);
  });
});

describe("ContentGscSearchAnalyticsContractSchema", () => {
  const contract = {
    source_connector: "google_search_console",
    evidence_ids: ["ev_refresh_refresh_google_search_console_916af598b0fd"],
    data_availability_checked: true,
    date_availability_status: "available",
    expected_data_delay_days_min: 2,
    expected_data_delay_days_max: 3,
    availability_date_start: "2026-06-21",
    availability_date_end: "2026-06-30",
    detail_date_start: "2026-06-29",
    detail_date_end: "2026-06-29",
    latest_available_detail_date: "2026-06-29",
    search_type: "web",
    detail_dimensions: "query,page",
    detail_data_completeness: "partial_possible",
    read_granularity: "single_day_latest_available",
    api_recommended_page_size: 25000,
    api_daily_row_cap_per_search_type: 50000,
    query_page_row_limit: 250,
    query_page_max_rows: 1000,
    query_page_rows_truncated: false,
    aggregate_date_start: "2026-06-29",
    aggregate_date_end: "2026-06-29",
    aggregate_dimensions: "country,device",
    aggregate_aggregation_type: "byProperty",
    aggregate_data_completeness: "aggregate_without_query_page_dimensions",
    aggregate_row_count: 2,
    aggregate_clicks: 30,
    aggregate_impressions: 300,
    aggregate_ctr: 0.1,
    aggregate_average_position: 4.0,
    aggregate_summary_label:
      "Agregat GSC bez wymiarów query/page: 30 kliknięć i 300 wyświetleń.",
    summary_label: "GSC Search Analytics: najnowszy dostępny dzień szczegółów 2026-06-29.",
    partial_detail_warning_label:
      "Dane zapytań i adresów z Search Analytics są sygnałem, nie pełną sumą całego ruchu.",
    paging_label:
      "Paginacja zapytań i adresów: rowLimit=250, max rows=1000; wynik nie zgłasza ucięcia.",
    official_limits_label:
      "Oficjalny wzorzec GSC: dane zwykle pojawiają się po 2-3 dniach.",
    wilq_internal_cap_label: "Ten odczyt WILQ jest operacyjnie ograniczony."
  };

  it("accepts only the typed GSC Search Analytics read contract shape", () => {
    expect(ContentGscSearchAnalyticsContractSchema.safeParse(contract).success).toBe(true);

    expect(
      ContentGscSearchAnalyticsContractSchema.safeParse({
        ...contract,
        source_connector: "ahrefs"
      }).success
    ).toBe(false);

    expect(
      ContentGscSearchAnalyticsContractSchema.safeParse({
        ...contract,
        query_page_rows_truncated: "false"
      }).success
    ).toBe(false);

    expect(
      ContentGscSearchAnalyticsContractSchema.safeParse({
        ...contract,
        read_granularity: "monthly_rollup"
      }).success
    ).toBe(false);
  });
});

describe("ContentWorkItemSchema", () => {
  it("rejects unknown workflow status values", () => {
    const workItem = {
      id: "content_work_item_bdo",
      topic: "BDO",
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console"],
      inventory_status: "resolved",
      canonical_status: "resolved",
      duplicate_status: "checked",
      preflight_status: "draft_allowed",
      preserve_first_plan_status: "approved",
      sales_brief_status: "approved",
      claim_ledger_status: "approved",
      draft_package_status: "ready",
      human_review_status: "missing",
      wordpress_handoff_status: "missing",
      measurement_window_status: "planned",
      audit_status: "missing"
    };

    expect(ContentWorkItemSchema.safeParse(workItem).success).toBe(true);
    expect(
      ContentWorkItemSchema.safeParse({
        ...workItem,
        preflight_status: "secret_unreviewed_state"
      }).success
    ).toBe(false);
  });
});

describe("ContentClaimLedgerSchema", () => {
  const ledger = {
    id: "claim_ledger_bdo",
    work_item_id: "content_work_item_bdo",
    reviewed_by: "wilku",
    entries: [
      {
        id: "claim_general_bdo",
        claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
        claim_type: "service_claim",
        status: "allowed_with_evidence",
        strength: "strong",
        required: true,
        evidence_ids: ["ev_wp_bdo"],
        source_connectors: ["wordpress_ekologus"],
        reason: "Claim ma przypisany dowód źródłowy.",
        reviewer_id: "wilku"
      },
      {
        id: "claim_product_sorbent",
        claim_text: "Ekologus ma produkt sorpcyjny do sprawdzenia w sklepie.",
        claim_type: "product_claim",
        status: "allowed_with_evidence",
        strength: "strong",
        required: false,
        evidence_ids: ["ev_merchant_product"],
        source_connectors: ["google_merchant_center"],
        reason: "Claim produktowy ma dowód z Merchant."
      }
    ]
  };

  it("rejects unknown claim ledger enums", () => {
    expect(ContentClaimLedgerSchema.safeParse(ledger).success).toBe(true);
    expect(
      ContentClaimLedgerSchema.safeParse({
        ...ledger,
        entries: [
          {
            ...ledger.entries[0],
            status: "approved_by_prompt"
          }
        ]
      }).success
    ).toBe(false);
    expect(
      ContentClaimLedgerSchema.safeParse({
        ...ledger,
        entries: [
          {
            ...ledger.entries[0],
            claim_type: "marketing_vibe_claim"
          }
        ]
      }).success
    ).toBe(false);
  });
});

describe("ContentClaimReferenceSchema", () => {
  const claimReference = {
    claim_id: "claim_bdo_penalty",
    claim_text: "Ekologus gwarantuje uniknięcie kar BDO.",
    claim_type: "guarantee_claim",
    status: "blocked",
    evidence_ids: ["ev_content_claim_ledger_bdo"],
    source_connectors: ["wilq_claim_ledger"],
    reason: "Claim wymaga blokady w ledgerze."
  };

  it("rejects unknown claim reference enums", () => {
    expect(ContentClaimReferenceSchema.safeParse(claimReference).success).toBe(true);
    expect(
      ContentClaimReferenceSchema.safeParse({
        ...claimReference,
        claim_type: "marketing_vibe_claim"
      }).success
    ).toBe(false);
    expect(
      ContentClaimReferenceSchema.safeParse({
        ...claimReference,
        status: "approved_by_prompt"
      }).success
    ).toBe(false);
  });
});

describe("ContentDraftPackageSchema", () => {
  const draftPackage = {
    id: "draft_package_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_id: "claim_ledger_bdo",
    draft_kind: "outline",
    title: "BDO dla firm",
    sections: [
      {
        heading: "Co to jest BDO",
        purpose: "Sekcja wyjaśniająca obowiązki.",
        evidence_ids: ["ev_wp_bdo"],
        draft_notes: ["Zachowaj konsultacyjny CTA."]
      }
    ],
    section_to_evidence_map: [
      {
        section_heading: "Co to jest BDO",
        evidence_ids: ["ev_wp_bdo"]
      }
    ],
    claims_used: ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
    claims_removed_or_blocked: ["gwarancja uniknięcia kar"],
    human_review_questions: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false
  };

  it("rejects malformed draft sections and evidence maps", () => {
    expect(ContentDraftPackageSchema.safeParse(draftPackage).success).toBe(true);
    expect(
      ContentDraftPackageSchema.safeParse({
        ...draftPackage,
        sections: [{ heading: "Co to jest BDO" }]
      }).success
    ).toBe(false);
    expect(
      ContentDraftPackageSchema.safeParse({
        ...draftPackage,
        section_to_evidence_map: [{ evidence_ids: ["ev_wp_bdo"] }]
      }).success
    ).toBe(false);
    expect(
      ContentDraftPackageSchema.safeParse({
        ...draftPackage,
        draft_kind: "full_publishable_draft"
      }).success
    ).toBe(false);
  });
});

describe("ContentKnowledgeConstraintTypeSchema", () => {
  it("rejects unknown knowledge constraint categories", () => {
    expect(ContentKnowledgeConstraintTypeSchema.safeParse("evidence_requirement").success).toBe(
      true
    );
    expect(ContentKnowledgeConstraintTypeSchema.safeParse("needs_human_review").success).toBe(
      true
    );
    expect(ContentKnowledgeConstraintTypeSchema.safeParse("model_opinion").success).toBe(false);
  });
});

describe("ContentRecommendedModeSchema", () => {
  it("rejects unknown content recommended modes", () => {
    expect(ContentRecommendedModeSchema.safeParse("refresh").success).toBe(true);
    expect(ContentRecommendedModeSchema.safeParse("publish_now").success).toBe(false);
  });
});

describe("StructuredDraftPreviewBlockerSchema", () => {
  it("accepts only known structured preview blocker codes", () => {
    expect(
      StructuredDraftPreviewBlockerSchema.safeParse({
        code: "missing_forbidden_claim_acknowledgement",
        label: "Szkic nie potwierdza uniknięcia zakazanych claimów",
        reason: "Podgląd wymaga jawnego potwierdzenia.",
        next_step: "Uzupełnij listę unikniętych claimów."
      }).success
    ).toBe(true);

    expect(
      StructuredDraftPreviewBlockerSchema.safeParse({
        code: "new_unreviewed_preview_gate",
        label: "Nieznany kod",
        reason: "Nie powinien przejść shared schema.",
        next_step: "Dodaj kod do kontraktu przed użyciem."
      }).success
    ).toBe(false);
  });
});

describe("MerchantDiagnosticsResponseSchema", () => {
  it("accepts Merchant price-impact readiness decisions returned by the API", () => {
    const response = {
      generated_at: "2026-06-24T03:12:30Z",
      language: "pl-PL",
      strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
      connector: {
        id: "google_merchant_center",
        label: "Merchant Center",
        status: "configured",
        configured: true,
        missing_credentials: [],
        available_credential_sources: ["repo_env"],
        freshness: { state: "fresh" },
        supported_actions: ["merchant_feed_issue"]
      },
      latest_refresh: {
        id: "refresh_google_merchant_center_live",
        connector_id: "google_merchant_center",
        mode: "vendor_read",
        status: "completed",
        started_at: "2026-06-24T03:04:00Z",
        completed_at: "2026-06-24T03:04:08Z",
        evidence_ids: ["ev_refresh_merchant_feed"],
        missing_credentials: [],
        checked_credentials: ["GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"],
        external_call_attempted: true,
        vendor_data_collected: true,
        metric_summary: { total_products: 10776 },
        summary: "Merchant Center vendor read completed.",
        errors: [],
        redacted: true
      },
      live_data_available: true,
      product_count: 10776,
      issue_count: 19,
      freshness_assessment: {
        state: "fresh",
        checked_at: "2026-06-24T03:12:30Z",
        latest_refresh_id: "refresh_google_merchant_center_live",
        latest_refresh_completed_at: "2026-06-24T03:04:08Z",
        age_hours: 0.14,
        stale_after_hours: 48,
        requires_refresh: false,
        summary: "Merchant data is fresh.",
        next_step: "Use review queue."
      },
      unknowns: [],
      product_sample_readiness: {
        status: "ready",
        sample_products_available: true,
        sample_count: 1,
        sample_product_ids: ["pl~PL~gla_107394"],
        sample_product_titles: ["Produkt testowy"],
        current_read_contract: "merchant_aggregate_product_statuses",
        required_read_contracts: ["merchant_products_list_product_status"],
        source_endpoint: "aggregateProductStatuses",
        summary: "Samples are available.",
        next_step: "Review samples.",
        blocked_claims: ["feed write"]
      },
      product_performance_readiness: {
        id: "merchant_product_performance_readiness",
        status: "blocked",
        joined_product_count: 0,
        merchant_sample_count: 1,
        ads_product_fact_count: 0,
        ga4_product_fact_count: 0,
        current_read_contracts: ["merchant_aggregate_product_statuses"],
        required_read_contracts: ["google_ads_shopping_product_performance"],
        missing_read_contracts: ["google_ads_shopping_product_performance"],
        join_key_candidates: ["product_id"],
        sample_product_ids: ["pl~PL~gla_107394"],
        performance_rows: [],
        source_connectors: ["google_merchant_center"],
        evidence_ids: ["ev_refresh_merchant_feed"],
        summary: "Product performance is blocked.",
        next_step: "Collect product performance facts.",
        blocked_claims: ["product ROAS"]
      },
      price_impact_readiness: {
        id: "merchant_price_impact_readiness",
        status: "blocked",
        products_with_current_price: 1,
        products_with_previous_price: 1,
        products_with_price_change: 0,
        products_with_unchanged_price_history: 1,
        products_with_performance_metrics: 0,
        current_read_contracts: ["google_ads_shopping_product_current_price"],
        required_read_contracts: ["merchant_price_change_event_or_snapshot"],
        missing_read_contracts: ["merchant_price_change_event_or_snapshot"],
        payload_preview: [],
        source_connectors: ["google_merchant_center", "google_ads"],
        evidence_ids: ["ev_refresh_merchant_feed", "ev_refresh_google_ads_products"],
        summary: "Price impact is blocked.",
        next_step: "Collect price change event and performance window.",
        blocked_claims: ["price change impact"]
      },
      operator_summary: {
        id: "merchant_operator_summary",
        title: "Merchant operator summary",
        summary: "Review only.",
        next_step: "Review decision queue.",
        top_decision_ids: ["merchant_decision_review_price_impact_readiness"],
        top_issue_cluster_ids: [],
        top_tactical_item_ids: [],
        reported_issue_occurrences: 0,
        decision_source: "decision_queue",
        drilldown_source: "issue_clusters",
        count_semantics: "reported_issue_occurrences",
        issue_types: [],
        source_connectors: ["google_merchant_center"],
        evidence_ids: ["ev_refresh_merchant_feed"],
        action_ids: ["act_review_merchant_feed_issues"],
        blocked_claims: ["feed write"]
      },
      issue_clusters: [],
      decision_queue: [
        {
          id: "merchant_decision_review_price_impact_readiness",
          decision_type: "review_price_impact_readiness",
          status: "blocked",
          title: "Merchant: sprawdz gotowosc price impact",
          summary: "Price impact remains blocked until required read contracts exist.",
          priority: 30,
          metric_tiles: { produkty: 1 },
          source_connectors: ["google_merchant_center", "google_ads"],
          evidence_ids: ["ev_refresh_merchant_feed", "ev_refresh_google_ads_products"],
          metric_facts: [],
          action_ids: ["act_review_merchant_feed_issues"],
          blocked_claims: ["price change impact"],
          rationale: "This is a readiness decision, not a product mutation.",
          next_step: "Show missing read contracts before any recommendation.",
          risk: "medium"
        }
      ],
      sections: [],
      evidence_ids: ["ev_refresh_merchant_feed"],
      action_ids: ["act_review_merchant_feed_issues"],
      blocker_count: 0
    };

    const result = MerchantDiagnosticsResponseSchema.safeParse(response);

    expect(result.success).toBe(true);
  });
});

describe("ContentPreflightResponseSchema", () => {
  it("accepts first-class content preflight contracts", () => {
    const item = {
      id: "preflight_content_decision_bdo",
      technical_decision_id: "content_decision_bdo",
      recommended_mode: "refresh",
      status: "review_required",
      create_allowed: false,
      draft_allowed: false,
      wordpress_draft_allowed: false,
      sales_brief_allowed: true,
      source_public_url: "https://www.ekologus.pl/bdo/",
      preview_url: null,
      intended_final_url: "https://www.ekologus.pl/bdo/",
      final_canonical_url: "https://www.ekologus.pl/bdo/",
      inventory_gate_status: "confirmed_current_inventory",
      canonical_gate_status: "public_canonical_confirmed",
      duplicate_gate_status: "existing_public_content_requires_refresh_or_merge",
      claim_gate_status: "needs_claim_review",
      service_fit_status: "ready_for_service_review",
      similar_existing_urls: ["https://www.ekologus.pl/bdo/"],
      query_overlap_summary: "1 zapytań z GSC; główne zapytanie: bdo.",
      blocked_claims: ["ranking guarantee"],
      missing_inputs: [],
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      next_step: "Przygotuj sales brief odświeżenia dopiero po sprawdzeniu claimów."
    };
    const response = {
      generated_at: "2026-06-26T08:00:00Z",
      language: "pl-PL",
      strict_instruction: "ContentPreflight is required before writing.",
      primary_item: item,
      items: [item],
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      blocker_count: 0
    };

    const result = ContentPreflightResponseSchema.safeParse(response);

    expect(result.success).toBe(true);
  });
});

describe("Content work item workflow schemas", () => {
  const item = {
    id: "content_work_item_bdo",
    topic: "BDO dla firm",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    inventory_status: "resolved",
    canonical_status: "resolved",
    duplicate_status: "checked",
    preflight_status: "handoff_allowed",
    preserve_first_plan_status: "approved",
    sales_brief_status: "approved",
    sales_brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_status: "approved",
    claim_ledger_id: "claim_ledger_bdo",
    draft_package_status: "ready",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_status: "approved",
    human_review_id: "human_review_bdo",
    wordpress_handoff_status: "prepared",
    wordpress_post_id: null,
    measurement_window_status: "planned",
    measurement_window_id: "measurement_window_content_work_item_bdo",
    audit_status: "recorded",
    audit_id: "audit_bdo"
  };

  const blocker = {
    code: "measurement_window_not_ready",
    label: "Nie wolno jeszcze oceniać efektu",
    reason: "Okno obserwacji jeszcze trwa.",
    next_step: "Wróć po earliest_verdict_date."
  };

  it("rejects unknown quality review duplicate risk values", () => {
    expect(
      ContentWorkItemQualityReviewRequestSchema.safeParse({
        item,
        duplicate_risk: "clear"
      }).success
    ).toBe(true);
    expect(
      ContentWorkItemQualityReviewRequestSchema.safeParse({
        item,
        duplicate_risk: "probably_fine"
      }).success
    ).toBe(false);
  });

  it("accepts Goal 002 work item workflow API response shapes", () => {
    expect(
      ContentWorkItemPreflightResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "plan_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: false,
          draft_allowed: false,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Zatwierdź preserve-first plan."
        }
      }).success
    ).toBe(true);

    const brief = {
      id: "sales_brief_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      topic: "BDO dla firm",
      operations_context: {
        enrichment_id: "content_enrichment_content_work_item_bdo",
        intent_label: "informacyjno-usługowy",
        recommended_mode: "refresh",
        safe_next_step: "Przygotuj szkic wyłącznie po bramkach WILQ.",
        source_fact_ids: ["ev_gsc_bdo"]
      },
      target_reader: "właściciel firmy",
      buyer_problem: "nie wie, jak podejść do BDO",
      buyer_trigger: "zbliża się kontrola",
      search_intent: "informacyjno-usługowy",
      service_fit: "obsługa środowiskowa",
      source_public_url: "https://ekologus.pl/bdo/",
      final_canonical_url: "https://ekologus.pl/bdo/",
      intended_final_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      existing_content_plan: "Zacznij od istniejącej treści.",
      h1_direction: "BDO dla firm",
      h2_direction: ["Kogo dotyczy BDO"],
      faq_direction: ["Czy każda firma musi mieć BDO?"],
      cta_direction: "Skontaktuj się z Ekologus.",
      internal_link_direction: ["https://ekologus.pl/kontakt/"],
      source_facts: [
        {
          evidence_id: "ev_gsc_bdo",
          source_connector: "google_search_console",
          summary: "GSC pokazuje popyt na temat BDO."
        }
      ],
      knowledge_card_ids: ["content_knowledge_service_bdo", "content_knowledge_cta_consultation"],
      knowledge_constraints: [
        {
          card_id: "content_knowledge_service_bdo",
          constraint_type: "service_fit",
          label: "Dopasuj treść do usługi Ekologus",
          reason: "Szkic musi wspierać realną usługę, nie ogólny SEO tekst.",
          evidence_ids: ["ev_knowledge_bdo_service"]
        }
      ],
      signal_quality: {
        status: "review_required",
        status_label: "sygnał użyteczny, ale wymaga review",
        reason: "Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji człowieka.",
        evidence_id_count: 2,
        source_connector_count: 2,
        source_fact_count: 1,
        missing_evidence_count: 0,
        knowledge_constraint_count: 1,
        review_required_knowledge_card_count: 1,
        measurement_baseline_ready: true,
        safe_next_step: "Pokaż brief Wilkowi z ograniczeniami wiedzy."
      },
      forbidden_claims: [],
      missing_evidence: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      measurement_plan: {
        measurement_window_id: "measurement_window_content_work_item_bdo",
        metrics_to_watch: ["GSC clicks"],
        baseline_source_connectors: ["google_search_console"],
        baseline_evidence_ids: ["ev_gsc_bdo"],
        measurement_readiness_label: "pomiar zaplanowany",
        measurement_readiness_reason: "WILQ ma bazowy dowód i okno obserwacji.",
        earliest_verdict_note: "Nie oceniaj przed końcem okna.",
        success_claim_rule: "Nie claimuj sukcesu bez danych."
      },
      human_review_required: true,
      draft_allowed: false
    };

    expect(
      ContentWorkItemSalesBriefResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "brief_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: true,
          draft_allowed: false,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Przygotuj Sales Brief."
        },
        sales_brief_result: { brief, blockers: [] }
      }).success
    ).toBe(true);

    const draftPackage = {
      id: "draft_package_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      brief_id: "sales_brief_content_work_item_bdo",
      claim_ledger_id: "claim_ledger_bdo",
      draft_kind: "outline",
      title: "BDO dla firm",
      sections: [],
      section_to_evidence_map: [],
      claims_used: [],
      claims_removed_or_blocked: [],
      human_review_questions: ["Czy to brzmi jak Ekologus?"],
      publish_ready: false
    };

    expect(
      ContentWorkItemDraftPackageResponseSchema.safeParse({
        item,
        inventory_resolution: {
          status: "resolved",
          recommended_mode: "preserve",
          matched_url: "https://ekologus.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          duplicate_risk: "clear",
          blockers: [],
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          next_step: "Zacznij od preserve-first."
        },
        preflight_verdict: {
          status: "draft_allowed",
          recommended_mode: "preserve",
          create_allowed: false,
          sales_brief_allowed: true,
          draft_allowed: true,
          wordpress_draft_allowed: false,
          final_canonical_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          similar_existing_urls: ["https://ekologus.pl/bdo/"],
          blockers: [],
          blocked_claims: [],
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          next_step: "Przygotuj Draft Package."
        },
        sales_brief_result: { brief, blockers: [] },
        draft_package_result: { draft_package: draftPackage, blockers: [] }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftGenerationResponseSchema.safeParse({
        item,
        structured_generation_result: {
          contract: {
            schema_name: "wilq_content_structured_draft_v1",
            strict_schema: true,
            model_input: {
              work_item_id: "content_work_item_bdo",
              language: "pl-PL",
              draft_kind: "section_draft",
              title: "BDO dla firm",
              final_canonical_url: "https://ekologus.pl/bdo/",
              source_public_url: "https://ekologus.pl/bdo/",
              preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
              target_reader: "właściciel firmy",
              buyer_problem: "nie wie, jak podejść do BDO",
              buyer_trigger: "zbliża się kontrola",
              search_intent: "informacyjno-usługowy",
              service_fit: "obsługa środowiskowa",
              cta_direction: "Skontaktuj się z Ekologus.",
              sections: [
                {
                  heading: "Kogo dotyczy BDO",
                  purpose: "Sekcja konspektu do napisania po sprawdzeniu planu.",
                  evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
                  draft_notes: ["Zachowaj kierunek H1"]
                }
              ],
              source_facts: [
                {
                  evidence_id: "ev_gsc_bdo",
                  source_connector: "google_search_console",
                  summary: "GSC pokazuje popyt na temat BDO."
                }
              ],
              knowledge_constraints: [
                {
                  card_id: "content_knowledge_service_bdo",
                  constraint_type: "service_fit",
                  label: "Dopasuj treść do usługi Ekologus",
                  reason: "Szkic musi wspierać realną usługę, nie ogólny SEO tekst.",
                  evidence_ids: ["ev_knowledge_bdo_service"]
                }
              ],
              sales_brief_signal_quality: {
                status: "review_required",
                status_label: "sygnał użyteczny, ale wymaga review",
                reason: "Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji człowieka.",
                evidence_id_count: 2,
                source_connector_count: 2,
                source_fact_count: 1,
                missing_evidence_count: 0,
                knowledge_constraint_count: 1,
                review_required_knowledge_card_count: 1,
                measurement_baseline_ready: true,
                safe_next_step: "Pokaż brief Wilkowi z ograniczeniami wiedzy."
              },
              claim_markers: [
                {
                  claim_id: "claim_general_bdo",
                  claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
                  claim_type: "service_claim",
                  status: "allowed_with_evidence",
                  strength: "weak",
                  required: true,
                  evidence_ids: ["ev_wp_bdo"],
                  source_connectors: ["wordpress_ekologus"],
                  reviewer_id: "wilku"
                }
              ],
              removed_or_blocked_claim_markers: [
                {
                  claim_id: "claim_more_leads",
                  claim_text: "Ta treść zwiększy liczbę leadów.",
                  claim_type: "business_outcome_claim",
                  status: "blocked_until_measurement",
                  strength: "strong",
                  required: false,
                  evidence_ids: ["ev_gsc_bdo"],
                  source_connectors: ["google_search_console"]
                }
              ],
              claims_allowed: ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
              claims_removed_or_blocked: ["Ta treść zwiększy liczbę leadów."],
              human_review_questions: ["Czy to brzmi jak Ekologus?"]
            },
            output_schema: {
              type: "object",
              additionalProperties: false,
              properties: { sections: { type: "array" } }
            },
            system_instruction: "Pisz wyłącznie z przekazanych faktów.",
            user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
            publish_ready: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftRuntimeResponseSchema.safeParse({
        runtime_result: {
          status: "dry_run_ready",
          request_payload: {
            model: "gpt-5",
            input: [
              {
                role: "system",
                content: "Pisz wyłącznie z przekazanych faktów."
              },
              {
                role: "user",
                content: "Przygotuj ustrukturyzowany szkic treści dla WILQ."
              }
            ],
            text: {
              format: {
                type: "json_schema",
                name: "wilq_content_structured_draft_v1",
                strict: true,
                schema: {
                  type: "object",
                  additionalProperties: false,
                  properties: { sections: { type: "array" } }
                }
              }
            },
            temperature: 0.2,
            max_output_tokens: 4000
          },
          output: null,
          external_call_attempted: false,
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemHumanReviewResponseSchema.safeParse({
        item,
        reviewed_item: item,
        review: null,
        blockers: [
          {
            code: "missing_human_review",
            label: "Brakuje decyzji człowieka",
            reason: "Snapshot nie może udawać zatwierdzonego review.",
            next_step: "Zatwierdź brief, claimy i paczkę szkicu."
          }
        ],
        wordpress_handoff_allowed: false
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemHumanReviewResponseSchema.safeParse({
        item,
        reviewed_item: item,
        review: {
          id: "human_review_bdo",
          work_item_id: "content_work_item_bdo",
          stage: "draft_package",
          reviewed_by: "wilku",
          decision: "approved",
          notes: "Może iść dalej.",
          checked_items: ["claimy sprawdzone"],
          evidence_ids: ["ev_gsc_bdo"],
          blocked_claims_handled: [],
          draft_package_id: "draft_package_content_work_item_bdo"
        },
        blockers: [],
        wordpress_handoff_allowed: true
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemStructuredDraftPreviewResponseSchema.safeParse({
        preview_result: {
          preview: {
            title: "BDO dla firm",
            meta_title: "BDO dla firm",
            meta_description: "Sprawdź, kiedy warto skonsultować BDO.",
            h1: "BDO dla firm",
            sections: [
              {
                heading: "Kogo dotyczy BDO",
                body_markdown: "BDO warto sprawdzić na podstawie sytuacji firmy.",
                evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
                claims_used: ["Ekologus pomaga firmom uporządkować obowiązki BDO."]
              }
            ],
            faq: ["Czy każda firma musi mieć BDO?"],
            cta: "Skontaktuj się z Ekologus, żeby omówić sytuację firmy.",
            internal_links: ["https://ekologus.pl/kontakt/"],
            source_facts_used: ["ev_gsc_bdo", "ev_wp_bdo"],
            forbidden_claims_avoided: ["Ta treść zwiększy liczbę leadów."],
            human_review_checklist: ["Czy to brzmi jak Ekologus?"],
            publish_ready: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemSnapshotHumanReviewRequestSchema.safeParse({
        review: {
          id: "human_review_bdo",
          work_item_id: "content_work_item_bdo",
          stage: "draft_package",
          reviewed_by: "wilku",
          decision: "approved",
          notes: "Może iść dalej.",
          checked_items: ["claimy sprawdzone"],
          evidence_ids: ["ev_gsc_bdo"],
          blocked_claims_handled: [],
          draft_package_id: "draft_package_content_work_item_bdo"
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemSnapshotAuditRequestSchema.safeParse({
        audit: {
          audit_id: "audit_bdo",
          actor: "wilku",
          reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
          evidence_ids: ["ev_gsc_bdo"],
          human_review_id: "human_review_bdo"
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftHandoffResponseSchema.safeParse({
        item,
        handoff_result: {
          handoff: {
            id: "wordpress_draft_handoff_content_work_item_bdo",
            work_item_id: "content_work_item_bdo",
            draft_package_id: "draft_package_content_work_item_bdo",
            human_review_id: "human_review_bdo",
            audit_id: "audit_bdo",
            connector: "wordpress_ekologus",
            operation_type: "create_wordpress_draft",
            status: "prepared",
            post_status: "draft",
            title: "BDO dla firm",
            final_canonical_url: "https://ekologus.pl/bdo/",
            intended_final_url: "https://ekologus.pl/bdo/",
            preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            publish_allowed: false,
            destructive_update_allowed: false
          },
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftExecutionRequestSchema.safeParse({
        handoff: {
          id: "wordpress_draft_handoff_content_work_item_bdo",
          work_item_id: "content_work_item_bdo",
          draft_package_id: "draft_package_content_work_item_bdo",
          human_review_id: "human_review_bdo",
          audit_id: "audit_bdo",
          connector: "wordpress_ekologus",
          operation_type: "create_wordpress_draft",
          status: "prepared",
          post_status: "draft",
          title: "BDO dla firm",
          final_canonical_url: "https://ekologus.pl/bdo/",
          intended_final_url: "https://ekologus.pl/bdo/",
          preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          publish_allowed: false,
          destructive_update_allowed: false
        },
        draft_package: draftPackage,
        mode: "dry_run"
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemWordPressDraftExecutionResponseSchema.safeParse({
        execution_result: {
          status: "dry_run_ready",
          mode: "dry_run",
          boundary: {
            allowed_operation: "create_wordpress_draft",
            dry_run_default: true,
            live_write_enabled: false,
            live_adapter_configured: false,
            publish_allowed: false,
            destructive_update_allowed: false
          },
          payload: {
            connector: "wordpress_ekologus",
            endpoint_kind: "posts",
            post_status: "draft",
            title: "BDO dla firm",
            content_markdown: "# BDO dla firm",
            final_canonical_url: "https://ekologus.pl/bdo/",
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            publish_allowed: false,
            destructive_update_allowed: false
          },
          wordpress_post_id: null,
          external_write_attempted: false,
          blockers: []
        }
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemMeasurementWindowResponseSchema.safeParse({
        item,
        updated_item: item,
        measurement_window_result: {
          window: {
            id: "measurement_window_content_work_item_bdo",
            work_item_id: "content_work_item_bdo",
            content_url: "https://ekologus.pl/bdo/",
            baseline_period: { start: "2026-05-01", end: "2026-05-31" },
            observation_period: { start: "2026-07-01", end: "2026-07-31" },
            earliest_verdict_date: "2026-08-01",
            allowed_metrics: ["gsc_clicks"],
            source_connectors: ["google_search_console"],
            evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
            status: "planned",
            handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
            success_claim_allowed: false
          },
          blockers: []
        },
        outcome_blockers: [blocker]
      }).success
    ).toBe(true);

    expect(
      ContentWorkItemMeasurementOutcomeResponseSchema.safeParse({
        outcome: {
          id: "measurement_outcome_measurement_window_content_work_item_bdo",
          work_item_id: "content_work_item_bdo",
          measurement_window_id: "measurement_window_content_work_item_bdo",
          status: "measured_success",
          status_label: "Zmiana pozytywna w mierzonych danych",
          conclusion: "Metryki poprawiły się, ale bez udawania pełnej przyczynowości.",
          confidence: "medium",
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"],
          limitations: ["To nie jest pełny dowód przyczyny."],
          success_claim_allowed: true,
          queue_feedback_allowed: true,
          safe_next_step: "Zapisz wynik jako pozytywny sygnał."
        }
      }).success
    ).toBe(true);

    const inventoryResolution = {
      status: "resolved",
      recommended_mode: "preserve",
      records: [],
      similar_existing_urls: ["https://ekologus.pl/bdo/"],
      blockers: [],
      evidence_ids: ["ev_wp_bdo"],
      source_connectors: ["wordpress_ekologus"],
      next_step: "Zacznij od preserve-first."
    };
    const preflightVerdict = {
      status: "plan_allowed",
      recommended_mode: "preserve",
      create_allowed: false,
      sales_brief_allowed: false,
      draft_allowed: false,
      wordpress_draft_allowed: false,
      similar_existing_urls: ["https://ekologus.pl/bdo/"],
      blockers: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      next_step: "Zatwierdź preserve-first plan."
    };
    const humanReview = {
      id: "human_review_bdo",
      work_item_id: "content_work_item_bdo",
      stage: "draft_package",
      reviewed_by: "wilku",
      decision: "approved",
      notes: "Może iść dalej.",
      checked_items: ["claimy sprawdzone"],
      evidence_ids: ["ev_gsc_bdo"],
      blocked_claims_handled: [],
      draft_package_id: "draft_package_content_work_item_bdo"
    };
    const wordpressHandoff = {
      id: "wordpress_draft_handoff_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      draft_package_id: "draft_package_content_work_item_bdo",
      human_review_id: "human_review_bdo",
      audit_id: "audit_bdo",
      connector: "wordpress_ekologus",
      operation_type: "create_wordpress_draft",
      status: "prepared",
      post_status: "draft",
      title: "BDO dla firm",
      final_canonical_url: "https://ekologus.pl/bdo/",
      intended_final_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      publish_allowed: false,
      destructive_update_allowed: false
    };
    const measurementWindow = {
      id: "measurement_window_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      content_url: "https://ekologus.pl/bdo/",
      baseline_period: { start: "2026-05-01", end: "2026-05-31" },
      observation_period: { start: "2026-07-01", end: "2026-07-31" },
      earliest_verdict_date: "2026-08-01",
      allowed_metrics: ["gsc_clicks"],
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      status: "planned",
      handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
      success_claim_allowed: false
    };
    const structuredContract = {
      schema_name: "wilq_content_structured_draft_v1",
      strict_schema: true,
      model_input: {
        work_item_id: "content_work_item_bdo",
        language: "pl-PL",
        draft_kind: "section_draft",
        title: "BDO dla firm",
        final_canonical_url: "https://ekologus.pl/bdo/",
        source_public_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        target_reader: "właściciel firmy",
        buyer_problem: "nie wie, jak podejść do BDO",
        buyer_trigger: "zbliża się kontrola",
        search_intent: "informacyjno-usługowy",
        service_fit: "obsługa środowiskowa",
        cta_direction: "Skontaktuj się z Ekologus.",
        sections: [],
        source_facts: [],
        knowledge_constraints: [],
        sales_brief_signal_quality: {
          status: "thin",
          status_label: "sygnał cienki - tylko analiza/review",
          reason: "Brief nie ma pełnego śladu dowodowego.",
          evidence_id_count: 0,
          source_connector_count: 0,
          source_fact_count: 0,
          missing_evidence_count: 0,
          knowledge_constraint_count: 0,
          review_required_knowledge_card_count: 0,
          measurement_baseline_ready: false,
          safe_next_step: "Uzupełnij dowody przed szkicem."
        },
        claims_allowed: [],
        claims_removed_or_blocked: [],
        human_review_questions: ["Czy to brzmi jak Ekologus?"]
      },
      output_schema: { type: "object", additionalProperties: false },
      system_instruction: "Pisz wyłącznie z przekazanych faktów.",
      user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
      publish_ready: false
    };
    const claimLedger = {
      id: "claim_ledger_bdo",
      work_item_id: "content_work_item_bdo",
      reviewed_by: "wilku",
      entries: [
        {
          id: "claim_general_bdo",
          claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
          claim_type: "service_claim",
          status: "allowed_with_evidence",
          strength: "strong",
          required: true,
          evidence_ids: ["ev_wp_bdo"],
          source_connectors: ["wordpress_ekologus"],
          reason: "Claim ma przypisany dowód źródłowy.",
          reviewer_id: "wilku"
        }
      ]
    };

    expect(
      ContentWorkItemWorkflowSnapshotResponseSchema.safeParse({
        claim_ledger: claimLedger,
        preflight: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict
        },
        sales_brief: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict,
          sales_brief_result: { brief, blockers: [] }
        },
        draft_package: {
          item,
          inventory_resolution: inventoryResolution,
          preflight_verdict: preflightVerdict,
          sales_brief_result: { brief, blockers: [] },
          draft_package_result: { draft_package: draftPackage, blockers: [] }
        },
        structured_generation: {
          item,
          structured_generation_result: { contract: structuredContract, blockers: [] }
        },
        human_review: {
          item,
          reviewed_item: item,
          review: humanReview,
          blockers: [],
          wordpress_handoff_allowed: true
        },
        wordpress_handoff: {
          item,
          handoff_result: { handoff: wordpressHandoff, blockers: [] }
        },
        measurement_window: {
          item,
          updated_item: item,
          measurement_window_result: { window: measurementWindow, blockers: [] },
          outcome_blockers: [blocker]
        },
        operator_steps: [
          {
            id: "content_preflight",
            title: "Sprawdzenie pisania",
            status_label: "można planować",
            summary: "Zatwierdź preserve-first plan."
          },
          {
            id: "sales_brief",
            title: "Plan sprzedażowy",
            status_label: "gotowy do sprawdzenia",
            summary: "nie wie, jak podejść do BDO"
          }
        ]
      }).success
    ).toBe(true);
  });

  it("accepts a typed blocked content workflow snapshot", () => {
    const blocker = {
      code: "missing_final_canonical",
      label: "Brakuje finalnego adresu",
      reason: "Szkic nie może powstać bez publicznego docelowego adresu.",
      next_step: "Ustal finalny adres na ekologus.pl.",
      decision_id: "content_decision_ahrefs_gap_records_review",
      evidence_ids: ["ev_ahrefs_gap"],
      source_connectors: ["ahrefs"]
    };
    const candidate = {
      work_item_id: "content_work_item_content_decision_ahrefs_gap_records_review",
      decision_id: "content_decision_ahrefs_gap_records_review",
      title: "Ahrefs: zweryfikuj luki SEO przed planem treści",
      topic: "beczki",
      priority: 18,
      recommended_mode: "block",
      recommended_mode_label: "zablokuj pisanie",
      status_label: "wymaga sprawdzenia przed pisaniem",
      reason: "Brak istniejącego rekordu nie oznacza jeszcze, że wolno tworzyć nowy URL.",
      evidence_ids: ["ev_ahrefs_gap"],
      source_connectors: ["ahrefs"],
      source_connector_labels: ["Ahrefs"],
      source_public_url: null,
      final_canonical_url: null,
      intended_final_url: null,
      preview_url: null,
      preflight_status: "blocked",
      preflight_status_label: "zablokowane",
      duplicate_canonical_risk_summary: "Brak istniejącego rekordu.",
      measurement_readiness: {
        status: "blocked",
        label: "pomiar zablokowany",
        reason: "Brak finalnego adresu.",
        source_connectors: []
      },
      safe_next_step: "Sprawdź podobne treści i finalny adres.",
      blockers: [blocker]
    };

    expect(
      ContentWorkItemSnapshotResponseSchema.safeParse({
        response_type: "blocked_snapshot",
        work_item_id: candidate.work_item_id,
        decision_id: candidate.decision_id,
        title: candidate.title,
        topic: candidate.topic,
        status_label: candidate.status_label,
        reason: candidate.reason,
        safe_next_step: candidate.safe_next_step,
        recommended_mode: candidate.recommended_mode,
        preflight_status: candidate.preflight_status,
        blockers: [blocker],
        evidence_ids: ["ev_ahrefs_gap"],
        source_connectors: ["ahrefs"],
        candidate
      }).success
    ).toBe(true);
  });
});
