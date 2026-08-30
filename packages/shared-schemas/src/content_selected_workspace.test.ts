import { describe, expect, it } from "vitest";

import {
  ContentProductionDecisionSchema,
  ContentReusableDocumentSchema,
  ContentSelectedWorkspaceSchema
} from "./index";

function withoutKey(value: Record<string, unknown>, key: string): Record<string, unknown> {
  return Object.fromEntries(Object.entries(value).filter(([candidate]) => candidate !== key));
}

describe("ContentSelectedWorkspaceSchema", () => {
  const operatorJourney = {
    current_step_id: "draft",
    steps: [
      ["scope", "Zakres i cel", "complete", "ready", "zakres gotowy"],
      ["section_map", "Plan sekcji", "complete", "ready", "plan sekcji gotowy"],
      ["draft", "Szkic treści", "current", "ready", "czeka na wersję szkicu"],
      ["review", "Sprawdzenie treści", "pending", "blocked", "czeka na wersję szkicu"],
      ["dev_draft", "Szkic na devie", "pending", "blocked", "czeka na sprawdzenie wersji"]
    ].map(([id, title, phase, readiness, statusLabel]) => ({
      id,
      title,
      phase,
      readiness,
      status_label: statusLabel,
      summary: "Stan etapu pochodzi z API.",
      can_open: phase !== "pending",
      can_submit: id === "draft",
      blocker: id === "dev_draft" ? {
        code: "missing_revision_bound_draft",
        label: "Brakuje wersji gotowej do przekazania",
        reason: "Najpierw zapisz i zatwierdź dokładną wersję tekstu."
      } : null,
      safe_next_step: "Wykonaj następny bezpieczny krok wskazany przez API."
    }))
  };
  const workspace = {
    response_type: "content_document_workspace",
    contract_version: "content_document_workspace_v2",
    work_item_id: "content_work_item_bdo",
    work_kind: "refresh_existing",
    service_label: "BDO",
    source_snapshot: {
      status: "available",
      status_label: "materiał dostępny",
      title: "BDO",
      url: "https://ekologus.pl/bdo/",
      extraction_method: "wordpress_rest.content",
      lead: null,
      content_excerpt: null,
      ordered_sections: [],
      faq_status: "not_observed",
      cta_status: "not_observed",
      reason: "Źródło odczytane.",
      caveats: [],
      evidence_ids: ["ev_wp_bdo"]
    },
    canonical_document: {
      status: "not_created",
      revision_id: null,
      content_digest: null,
      review_state: "unreviewed",
      label: "Brak dokumentu",
      reason: "Brak rewizji.",
      preview: null
    },
    document_lineage: {
      status: "not_recorded",
      source_material_ids: [],
      knowledge_cards: [],
      unresolved_knowledge_card_ids: [],
      reason: "Brak rewizji."
    },
    comparison: { status: "unavailable", reason: "Brak rewizji.", items: [] },
    next_action: { kind: "prepare_document", label: "Przygotuj dokument", reason: "Brak rewizji." },
    regulatory_review_candidates: [{
      candidate_id: "bdo_sanctions_2026_08_02_r3",
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/sankcje/",
      source_title: "BDO: sankcje za naruszenia obowiązków",
      observed_on: "2026-08-02",
      requirement_ids: ["bdo_risks_and_sanctions"],
      requirement_labels: ["Ryzyka i sankcje"],
      review_status: "review_required",
      safe_next_step: "Sprawdź materiał urzędowy przed decyzją."
    }],
    secondary_disclosures: []
  };
  const retainedRevision = {
    schema_version: "wilq_content_draft_revision_v1",
    revision_id: "content_revision_retained",
    work_item_id: "content_work_item_retained",
    revision_number: 1,
    base_revision_id: null,
    content_digest: "9".repeat(64),
    draft_package_id: "content_draft_retained",
    draft_package_digest: "8".repeat(64),
    document_kind: "refresh_existing",
    final_canonical_url: "https://www.ekologus.pl/bdo/",
    title: "BDO",
    sections: [{ heading: "Zakres", body_markdown: "Sprawdź obowiązki BDO." }],
    publish_ready: false,
    created_by: "wilku",
    created_at: "2026-08-30T10:00:00Z"
  };
  const retainedReview = {
    decision_id: "review_retained",
    decision_number: 1,
    work_item_id: retainedRevision.work_item_id,
    revision_id: retainedRevision.revision_id,
    revision_digest: retainedRevision.content_digest,
    reviewed_by: "wilku",
    decision: "approved",
    notes: "",
    checked_items: ["Treść i źródła"],
    evidence_ids: ["ev_review_bdo"],
    created_at: "2026-08-30T10:01:00Z"
  };
  const availableDecision = {
    status: "available",
    run_id: "content_production_classification_test",
    run_digest: "a".repeat(64),
    decision_set_digest: "b".repeat(64),
    generation_allowed: false,
    lookup_basis: "current",
    canonical_path: "/bdo",
    public_url: "https://www.ekologus.pl/bdo/",
    current_work_item_id: "content_work_item_bdo",
    retained_work_item_id: "content_work_item_retained",
    reason_pl: "Zachowaj zatwierdzony dokument.",
    safe_next_step_pl: "Otwórz zachowany dokument bez ponownego generowania.",
    blockers: [],
    primary_evidence_ids: ["ev_bdo"],
    lineage_evidence_ids: ["lineage_bdo"],
    source_connectors: ["wordpress_ekologus"],
    freshness: {
      state: "fresh",
      checked_at: "2026-08-30T09:59:00Z",
      requires_refresh: false,
      connector_ids: ["wordpress_ekologus"]
    }
  };
  const reuseDecision = {
    ...availableDecision,
    decision: "reuse",
    revision_binding: {
      current_work_item_id: "content_work_item_bdo",
      retained_work_item_id: "content_work_item_retained",
      revision_work_item_id: "content_work_item_retained",
      identity_reconciliation_status: "fork",
      revision_id: retainedRevision.revision_id,
      revision_digest: retainedRevision.content_digest,
      verified_draft_action_ids: ["act_content_dev_draft_bdo"],
      verified_draft_post_ids: ["1991"],
      must_not_regenerate: true
    },
    reusable_document: {
      status: "ready",
      revision: retainedRevision,
      review: retainedReview
    }
  };
  const guardedWorkspace = {
    ...workspace,
    next_action: {
      kind: "none",
      label: "Generowanie nowej wersji jest wyłączone",
      reason: availableDecision.reason_pl
    }
  };

  it("keeps ready and missing selection states exact", () => {
    const parsed = ContentSelectedWorkspaceSchema.parse({
        status: "ready",
        work_item_id: "content_work_item_bdo",
        requested_work_item_id: "content_work_item_bdo",
        production_decision: { status: "missing" },
        operator_journey: operatorJourney,
        workspace,
        reason: "Odczytano workspace.",
        safe_next_step: "Przygotuj dokument"
      });
    expect(parsed.workspace?.regulatory_review_candidates).toEqual([
      expect.objectContaining({ candidate_id: "bdo_sanctions_2026_08_02_r3" })
    ]);
    expect(parsed.workspace?.source_snapshot.status_label).toBe("materiał dostępny");
    expect(
      ContentSelectedWorkspaceSchema.safeParse({
        status: "missing",
        work_item_id: "content_work_item_missing",
        requested_work_item_id: "content_work_item_missing",
        production_decision: { status: "missing" },
        operator_journey: operatorJourney,
        workspace: null,
        reason: "Nie znaleziono strony.",
        safe_next_step: "Wróć do wyboru."
      }).success
    ).toBe(true);
    expect(
      ContentSelectedWorkspaceSchema.safeParse({
        status: "ready",
        work_item_id: "content_work_item_other",
        requested_work_item_id: "content_work_item_other",
        production_decision: { status: "missing" },
        operator_journey: operatorJourney,
        workspace,
        reason: "Odczytano workspace.",
        safe_next_step: "Przygotuj dokument"
      }).success
    ).toBe(false);
  });

  it("accepts one exact reusable retained revision without changing current workspace identity", () => {
    const parsed = ContentSelectedWorkspaceSchema.parse({
      status: "ready",
      work_item_id: "content_work_item_bdo",
      requested_work_item_id: "content_work_item_bdo",
      production_decision: reuseDecision,
      operator_journey: operatorJourney,
      workspace: guardedWorkspace,
      reason: availableDecision.reason_pl,
      safe_next_step: availableDecision.safe_next_step_pl
    });

    expect(parsed.workspace?.work_item_id).toBe("content_work_item_bdo");
    expect(parsed.workspace?.canonical_document.status).toBe("not_created");
    expect(parsed.production_decision.status).toBe("available");
    if (
      parsed.production_decision.status !== "available" ||
      parsed.production_decision.decision !== "reuse" ||
      parsed.production_decision.reusable_document.status !== "ready"
    ) throw new Error("expected exact reusable document");
    expect(parsed.production_decision.generation_allowed).toBe(false);
    expect(parsed.production_decision.revision_binding.must_not_regenerate).toBe(true);
    expect(parsed.production_decision.reusable_document.revision.work_item_id).toBe(
      "content_work_item_retained"
    );
    expect(parsed.production_decision.reusable_document.review.revision_digest).toBe(
      retainedRevision.content_digest
    );
  });

  it("leads with the reusable-document blocker when retained state drifts", () => {
    const reusableBlocker = {
      status: "blocked",
      code: "latest_revision_drift",
      reason_pl: "Zachowana rewizja zmieniła się po klasyfikacji.",
      safe_next_step_pl: "Sprawdź zmianę rewizji przed dalszą pracą."
    };
    const productionDecision = {
      ...reuseDecision,
      reusable_document: reusableBlocker
    };
    const workspaceWithBlocker = {
      ...guardedWorkspace,
      next_action: {
        ...guardedWorkspace.next_action,
        reason: reusableBlocker.reason_pl
      }
    };
    const selected = {
      status: "ready",
      work_item_id: "content_work_item_bdo",
      requested_work_item_id: "content_work_item_bdo",
      production_decision: productionDecision,
      operator_journey: operatorJourney,
      workspace: workspaceWithBlocker,
      reason: reusableBlocker.reason_pl,
      safe_next_step: reusableBlocker.safe_next_step_pl
    };

    expect(ContentSelectedWorkspaceSchema.safeParse(selected).success).toBe(true);
    expect(
      ContentSelectedWorkspaceSchema.safeParse({
        ...selected,
        safe_next_step: availableDecision.safe_next_step_pl
      }).success
    ).toBe(false);
  });

  it("rejects reusable identity, digest, review, and strict-union drift", () => {
    const selected = {
      status: "ready",
      work_item_id: "content_work_item_bdo",
      requested_work_item_id: "content_work_item_bdo",
      production_decision: reuseDecision,
      operator_journey: operatorJourney,
      workspace: guardedWorkspace,
      reason: availableDecision.reason_pl,
      safe_next_step: availableDecision.safe_next_step_pl
    };
    const wrongDigest = {
      ...selected,
      production_decision: {
        ...reuseDecision,
        revision_binding: { ...reuseDecision.revision_binding, revision_digest: "7".repeat(64) }
      }
    };
    const wrongReview = {
      ...selected,
      production_decision: {
        ...reuseDecision,
        reusable_document: {
          ...reuseDecision.reusable_document,
          review: { ...retainedReview, work_item_id: "content_work_item_other" }
        }
      }
    };
    const wrongPublicUrl = {
      ...selected,
      production_decision: { ...reuseDecision, public_url: "/relative-only" }
    };
    const nonApprovedReview = {
      ...selected,
      production_decision: {
        ...reuseDecision,
        reusable_document: {
          ...reuseDecision.reusable_document,
          review: { ...retainedReview, decision: "needs_changes", notes: "Wymaga zmian." }
        }
      }
    };
    const pollutedMissing = {
      ...selected,
      production_decision: { status: "missing", generation_allowed: false }
    };
    const pollutedBlockedDocument = {
      ...selected,
      production_decision: {
        ...reuseDecision,
        reusable_document: {
          status: "blocked",
          code: "latest_revision_missing",
          reason_pl: "Brakuje rewizji.",
          safe_next_step_pl: "Sprawdź rewizję.",
          revision: retainedRevision
        }
      }
    };
    const retainedInsertedAsCurrent = {
      ...selected,
      workspace: {
        ...guardedWorkspace,
        canonical_document: {
          status: "unreviewed",
          revision_id: retainedRevision.revision_id,
          content_digest: retainedRevision.content_digest,
          review_state: "unreviewed",
          label: "Błędnie wstawiona rewizja",
          reason: "Zachowana rewizja nie jest bieżącym dokumentem.",
          revision: retainedRevision
        }
      }
    };

    for (const invalid of [
      wrongDigest,
      wrongPublicUrl,
      wrongReview,
      nonApprovedReview,
      pollutedMissing,
      pollutedBlockedDocument,
      retainedInsertedAsCurrent
    ]) {
      expect(ContentSelectedWorkspaceSchema.safeParse(invalid).success).toBe(false);
    }
  });

  it("accepts refresh and blocked decisions only without retained document data", () => {
    for (const decision of ["refresh", "blocked"] as const) {
      const projection = {
        ...availableDecision,
        decision,
        retained_work_item_id: null,
        blockers: [{
          code: "evidence_refresh_required",
          owner: "wilku",
          next_step_pl: "Odśwież źródła.",
          sources: ["gsc"],
          blocks_initial_generation: true
        }]
      };
      const selected = {
        status: "ready",
        work_item_id: "content_work_item_bdo",
        requested_work_item_id: "content_work_item_bdo",
        production_decision: projection,
        operator_journey: operatorJourney,
        workspace: guardedWorkspace,
        reason: projection.reason_pl,
        safe_next_step: projection.safe_next_step_pl
      };

      expect(ContentSelectedWorkspaceSchema.safeParse(selected).success).toBe(true);
      expect(
        ContentSelectedWorkspaceSchema.safeParse({
          ...selected,
          production_decision: { ...projection, reusable_document: reuseDecision.reusable_document }
        }).success
      ).toBe(false);
    }
  });

  it("requires production discriminants and arrays at the runtime boundary", () => {
    for (const key of [
      "status",
      "decision",
      "current_work_item_id",
      "retained_work_item_id",
      "blockers",
      "lineage_evidence_ids"
    ]) {
      expect(
        ContentProductionDecisionSchema.safeParse(withoutKey(reuseDecision, key)).success
      ).toBe(false);
    }

    for (const key of [
      "retained_work_item_id",
      "revision_work_item_id",
      "verified_draft_action_ids",
      "verified_draft_post_ids"
    ]) {
      expect(
        ContentProductionDecisionSchema.safeParse({
          ...reuseDecision,
          revision_binding: withoutKey(reuseDecision.revision_binding, key)
        }).success
      ).toBe(false);
    }

    expect(ContentProductionDecisionSchema.safeParse({}).success).toBe(false);
    expect(
      ContentReusableDocumentSchema.safeParse(withoutKey(reuseDecision.reusable_document, "status"))
        .success
    ).toBe(false);
    expect(
      ContentReusableDocumentSchema.safeParse({
        code: "latest_revision_missing",
        reason_pl: "Brakuje rewizji.",
        safe_next_step_pl: "Sprawdź rewizję."
      }).success
    ).toBe(false);
  });

  it("rejects blank optional IDs and string-array members", () => {
    const blocker = {
      code: "evidence_refresh_required",
      owner: "wilku",
      next_step_pl: "Odśwież źródła.",
      sources: ["gsc"],
      blocks_initial_generation: true
    };
    const invalidDecisions = [
      {
        ...reuseDecision,
        current_work_item_id: "",
        revision_binding: { ...reuseDecision.revision_binding, current_work_item_id: "" }
      },
      {
        ...reuseDecision,
        retained_work_item_id: "",
        revision_binding: {
          ...reuseDecision.revision_binding,
          retained_work_item_id: "",
          revision_work_item_id: ""
        }
      },
      {
        ...reuseDecision,
        revision_binding: {
          ...reuseDecision.revision_binding,
          verified_draft_action_ids: [""]
        }
      },
      {
        ...reuseDecision,
        revision_binding: {
          ...reuseDecision.revision_binding,
          verified_draft_post_ids: [""]
        }
      },
      { ...reuseDecision, blockers: [{ ...blocker, sources: [""] }] },
      { ...reuseDecision, primary_evidence_ids: [""] },
      { ...reuseDecision, lineage_evidence_ids: [""] },
      { ...reuseDecision, source_connectors: [""] }
    ];

    for (const invalid of invalidDecisions) {
      expect(ContentProductionDecisionSchema.safeParse(invalid).success).toBe(false);
    }
  });

  it("requires real blockers for refresh and blocked but does not invent one for write", () => {
    for (const decision of ["refresh", "blocked"] as const) {
      expect(
        ContentProductionDecisionSchema.safeParse({
          ...availableDecision,
          decision,
          retained_work_item_id: null,
          blockers: []
        }).success
      ).toBe(false);
    }

    expect(
      ContentProductionDecisionSchema.safeParse({
        ...availableDecision,
        decision: "write",
        retained_work_item_id: null,
        blockers: []
      }).success
    ).toBe(true);
  });
});
