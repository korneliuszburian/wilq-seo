import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ContentPlanningReviewPanel,
  initialServiceCardId,
  inventoryDispositionLabel,
  planningReviewCheckedItems,
  planningSectionMapReady,
  planningServiceSelectionMessage,
  planningScopeSummary,
  planningSourceSummary,
  requiresServiceOverrideReview,
  planningInventorySourceLabel,
  inventoryMaterialSourceLabel,
  serviceSelectionFieldLabel,
  serviceMatchReasonSummary
} from "./ContentPlanningReviewPanel";

describe("inventoryDispositionLabel", () => {
  it("keeps inventory actions concrete and Polish", () => {
    expect(inventoryDispositionLabel("preserve")).toBe("zachowaj");
    expect(inventoryDispositionLabel("merge")).toBe("scal po review");
    expect(inventoryDispositionLabel("rewrite")).toBe("przepisz");
    expect(inventoryDispositionLabel("create")).toBe("utwórz");
  });
});

describe("planningScopeSummary", () => {
  it("separates document sections from inventory rows needing review", () => {
    expect(
      planningScopeSummary([
        { inventory_disposition: "rewrite" },
        { inventory_disposition: "merge" },
        { inventory_disposition: "remove_review_required" }
      ])
    ).toBe("2 sekcje trafi do pełnego tekstu · 1 element pozostaje do osobnego review");
  });
});

describe("planningSourceSummary", () => {
  it("shows source, material, knowledge and connector counts without raw IDs", () => {
    expect(
      planningSourceSummary({
        evidence_ids: ["ev_1", "ev_2"],
        source_material_ids: ["material_1"],
        knowledge_card_ids: ["card_1", "card_2"],
        source_connectors: ["gsc", "wordpress"]
      })
    ).toBe("Plan opiera się na 2 źródłach · 1 materiale Ekologusa · 2 kartach · 2 połączeniach");
    expect(
      planningSourceSummary({
        evidence_ids: ["ev_1"],
        source_material_ids: [],
        knowledge_card_ids: [],
        source_connectors: ["gsc"],
        generation_status: "baseline"
      })
    ).toBe("Zakres opiera się na 1 źródle · 0 materiałach Ekologusa · 0 kartach · 1 połączeniu");
    expect(
      planningSourceSummary(
        {
          evidence_ids: [],
          source_material_ids: [],
          knowledge_card_ids: [],
          source_connectors: [],
          generation_status: "baseline"
        },
        {
          evidence_ids: ["ev_previous"],
          source_material_ids: ["material_previous"],
          knowledge_card_ids: ["card_previous"],
          source_connectors: ["gsc", "wordpress"]
        }
      )
    ).toBe("Zakres · lineage poprzedniej wersji opiera się na 1 źródle · 1 materiale Ekologusa · 1 karcie · 2 połączeniach");
  });
});

describe("planningReviewCheckedItems", () => {
  it("records explicit the_content provenance only after the marketer checks it", () => {
    expect(planningReviewCheckedItems("scope", true, true, false)).toEqual([
      "zakres i CTA"
    ]);
    expect(planningReviewCheckedItems("scope", true, true, true)).toEqual([
      "zakres i CTA",
      "existing_content_provenance"
    ]);
    expect(planningReviewCheckedItems("section_map", true, true, false)).toEqual([
      "kolejność, cel i źródła"
    ]);
    expect(planningReviewCheckedItems("section_map", true, true, true)).toEqual([
      "kolejność, cel i źródła",
      "existing_content_provenance"
    ]);
  });
});

describe("planningSectionMapReady", () => {
  it("treats only one generated proposal as a reviewable map", () => {
    const base = {
      generation_status: "baseline" as const,
      proposal_id: null
    };
    expect(planningSectionMapReady(base as never)).toBe(false);
    expect(
      planningSectionMapReady({
        ...base,
        generation_status: "codex_generated",
        proposal_id: "proposal_1"
      } as never)
    ).toBe(true);
  });
});

describe("generated section-map presentation", () => {
  it("keeps the automatic map compact until details are requested", () => {
    render(
      <ContentPlanningReviewPanel
        actions={{
          conflict: null,
          error: null,
          pending: false,
          refresh: () => undefined,
          save: () => undefined
        }}
        planning={{
          scope_decision: null,
          scope_current: true,
          section_map_decision: null,
          section_map_current: true,
          proposal: {
            generation_status: "codex_generated",
            proposal_id: "proposal_1",
            service_selection_confirmed: true,
            service_card_id: "service_bdo",
            sections: [
              {
                heading: "Wprowadzenie",
                purpose: "Wyjaśnia temat.",
                inventory_disposition: "create",
                inventory_heading: null,
                evidence_ids: ["evidence_1"],
                query_terms: []
              }
            ],
            inventory_mapping: [
              {
                inventory_section_id: "inventory_1",
                inventory_heading: "Stara sekcja",
                status: "mapped",
                mapped_section_heading: "Wprowadzenie",
                disposition: "rewrite",
                reason: null
              }
            ],
            search_demand: {
              gsc_query_rows: [],
              ads_term_rows: [],
              optional_ads_status: "not_available",
              safe_next_step: "Brak danych.",
              keyword_planner_rows: []
            },
            evidence_ids: ["evidence_1"],
            source_material_ids: [],
            knowledge_card_ids: [],
            source_connectors: ["gsc"]
          }
        } as never}
        serviceCandidates={[
          {
            service_card_id: "service_bdo",
            service_label: "BDO",
            lifecycle_label: "zatwierdzona i aktualna",
            lifecycle_status: "approved_current",
            recommended: true,
            matched_terms: ["bdo"],
            match_reasons: ["bdo"]
          }
        ]}
        stage="section_map"
      />
    );

    expect(screen.getByTestId("planning-section-map-summary")).toHaveTextContent("Sekcje dokumentu");
    expect(screen.getByTestId("planning-section-map-auto-status")).toHaveTextContent(
      "Nie wymaga osobnego zatwierdzania"
    );
    expect(screen.getByTestId("planning-section-map-details")).not.toHaveAttribute("open");
  });

  it("does not repeat a confirmed service selector until the marketer asks to change it", () => {
    render(
      <ContentPlanningReviewPanel
        actions={{ conflict: null, error: null, pending: false, refresh: () => undefined, save: () => undefined }}
        planning={{
          scope_decision: null,
          scope_current: true,
          section_map_decision: null,
          section_map_current: false,
          proposal: {
            generation_status: "baseline",
            proposal_id: null,
            service_selection_confirmed: true,
            service_card_id: "service_bdo",
            final_canonical_url: "/bdo/",
            buyer_problem: "problem",
            buyer_trigger: "trigger",
            internal_link_directions: [],
            search_intent: "informational",
            target_reader: "reader",
            cta_direction: "contact",
            sections: [],
            inventory_mapping: [],
            search_demand: {
              gsc_query_rows: [],
              ads_term_rows: [],
              optional_ads_status: "not_available",
              safe_next_step: "Brak danych.",
              keyword_planner_rows: []
            },
            evidence_ids: [],
            source_material_ids: [],
            knowledge_card_ids: [],
            source_connectors: []
          }
        } as never}
        serviceCandidates={[{
          service_card_id: "service_bdo",
          service_label: "BDO",
          lifecycle_label: "zatwierdzona i aktualna",
          lifecycle_status: "approved_current",
          recommended: true,
          matched_terms: ["bdo"],
          match_reasons: ["bdo"]
        }]}
        stage="scope"
      />
    );

    expect(screen.getByTestId("planning-confirmed-service")).toHaveTextContent("BDO");
    expect(screen.queryByLabelText("Potwierdzona usługa")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zmień usługę" }));
    expect(screen.getByLabelText("Potwierdzona usługa")).toBeInTheDocument();
  });
});

describe("requiresServiceOverrideReview", () => {
  it("keeps non-current service cards visibly review-bound", () => {
    expect(requiresServiceOverrideReview(undefined)).toBe(false);
    expect(
      requiresServiceOverrideReview({ lifecycle_status: "approved_current" } as never)
    ).toBe(false);
    expect(
      requiresServiceOverrideReview({ lifecycle_status: "source_backed_review_required" } as never)
    ).toBe(true);
  });
});

describe("planningServiceSelectionMessage", () => {
  it("keeps an unbound page blocked instead of implying a service choice", () => {
    expect(planningServiceSelectionMessage(0)).toContain("nie znalazł karty usługi");
    expect(planningServiceSelectionMessage(1)).toBeNull();
  });
});

describe("planningInventorySourceLabel", () => {
  it("names the actual WordPress content seam instead of inventing ACF sections", () => {
    expect(planningInventorySourceLabel("missing", "available")).toBe(
      "the_content (główna treść WordPress)"
    );
    expect(planningInventorySourceLabel("available", "missing", ["Hero"])).toBe("ACF/flexible content");
    expect(planningInventorySourceLabel("available", "missing")).toBe(
      "pola ACF bez wykrytych sekcji strukturalnych"
    );
    expect(planningInventorySourceLabel("available", "available")).toContain(
      "pola ACF bez sekcji"
    );
    expect(planningInventorySourceLabel("missing", "missing")).toBe("niepotwierdzone");
  });
});

describe("inventoryMaterialSourceLabel", () => {
  it("keeps the dynamic REST-versus-rendered fallback visible", () => {
    expect(inventoryMaterialSourceLabel("wordpress_rest")).toContain("WordPress REST");
    expect(inventoryMaterialSourceLabel("rendered_html")).toContain("wyrenderowany HTML");
  });
});

describe("initialServiceCardId", () => {
  it("does not turn an API recommendation into implicit human confirmation", () => {
    expect(initialServiceCardId(false, "ekologus_service_bdo_reporting")).toBe("");
  });

  it("restores only an explicitly confirmed service selection", () => {
    expect(initialServiceCardId(true, "ekologus_service_bdo_reporting")).toBe(
      "ekologus_service_bdo_reporting"
    );
  });
});

describe("serviceSelectionFieldLabel", () => {
  it("names an unresolved recommendation as a choice, not a confirmation", () => {
    expect(serviceSelectionFieldLabel(false)).toBe("Wybierz usługę dla tej strony");
    expect(serviceSelectionFieldLabel(true)).toBe("Potwierdzona usługa");
  });
});

describe("serviceMatchReasonSummary", () => {
  it("shows the strongest exact terms and condenses weaker body mentions", () => {
    expect(
      serviceMatchReasonSummary({
        matched_terms: [
          "doradztwo środowiskowe",
          "outsourcing ekologiczny",
          "bdo",
          "kobize"
        ]
      })
    ).toBe("Najmocniejsze dopasowania: „outsourcing ekologiczny” · „doradztwo środowiskowe” · +2 słabsze.");
  });

  it("does not invent a reason when the API has no exact term", () => {
    expect(serviceMatchReasonSummary({ matched_terms: [] })).toBe(
      "Brak exact frazy dopasowania do tej karty usługi."
    );
  });
});
