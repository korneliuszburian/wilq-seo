from __future__ import annotations

import json
import re
from copy import deepcopy

from wilq.codex.app_server import CodexAppServerStructuredTurnRequest
from wilq.codex.prompts import resolve_prompt_template
from wilq.content.codex_turn import (
    definition,
    mapping,
    properties,
    require_all_object_properties,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
)
from wilq.content.regulatory import turn_context as regulatory_turn_context

# The persisted planning input is intentionally complete: its digest covers
# every connector row and every lineage edge.  The model envelope is a
# transport concern, however.  GSC/Ads rows repeat the same refresh-level
# evidence ids, and sending those repetitions makes structured planning both
# slow and needlessly expensive.  Keep every exact fact while removing only
# repeated/null presentation fields from the untrusted model context.
_MODEL_QUERY_EVIDENCE_IDS_PER_ROW = 3
_MODEL_QUERY_HEADINGS_PER_ROW = 4
_MODEL_INVENTORY_NOISE = (
    re.compile(
        r"\b\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|"
        r"sierpnia|września|października|listopada|grudnia)\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:zaufali nam|może cię również zainteresować)\b", re.IGNORECASE),
    re.compile(r"^(?:poniżej przedstawiamy|dowiedz się więcej)\b", re.IGNORECASE),
    re.compile(r"\[\s*(?:19|20)\d{2}\b[^\]]*\]", re.IGNORECASE),
)


def _model_inventory_sections(sections: object) -> list[object]:
    if not isinstance(sections, list):
        return []
    kept: list[object] = []
    for section in sections:
        if not isinstance(section, dict):
            kept.append(section)
            continue
        heading = str(section.get("heading") or "").strip()
        if heading and any(pattern.search(heading) for pattern in _MODEL_INVENTORY_NOISE):
            continue
        kept.append(section)
    return kept


def compact_planning_input_for_model(
    planning_input: ContentPlanningInput,
) -> tuple[dict[str, object], dict[str, int]]:
    """Build a bounded, lineage-preserving model view without changing the digest.

    Full input remains the source of truth for validation, persistence and
    stale detection.  Every query row is retained; only null fields and
    repeated row-level evidence/heading arrays are bounded.  The complete
    evidence id set stays at the planning-input top level and output schema,
    so the model can still cite any allowed evidence id.
    """

    payload = planning_input.model_dump(mode="json", exclude_none=True)
    inventory = payload.get("inventory")
    if isinstance(inventory, dict):
        inventory["sections"] = _model_inventory_sections(inventory.get("sections"))
    portfolio = payload.get("query_portfolio")
    if not isinstance(portfolio, dict):
        return payload, {"rows_available": 0, "rows_included": 0}
    row_keys = ("gsc_query_rows", "ads_term_rows", "keyword_planner_rows")
    rows_available = 0
    for key in row_keys:
        rows = portfolio.get(key)
        if not isinstance(rows, list):
            continue
        rows_available += len(rows)
        for row in rows:
            if not isinstance(row, dict):
                continue
            evidence_ids = row.get("evidence_ids")
            if isinstance(evidence_ids, list):
                row["evidence_ids"] = list(
                    dict.fromkeys(evidence_ids[:_MODEL_QUERY_EVIDENCE_IDS_PER_ROW])
                )
            headings = row.get("section_headings")
            if isinstance(headings, list):
                row["section_headings"] = headings[:_MODEL_QUERY_HEADINGS_PER_ROW]
    return payload, {
        "rows_available": rows_available,
        "rows_included": rows_available,
    }


def content_planning_turn_request(
    planning_input: ContentPlanningInput,
    *,
    operator_hint: str,
) -> CodexAppServerStructuredTurnRequest:
    application_context = json.dumps(
        {
            "operation": "propose_content_plan",
            "work_item_id": planning_input.work_item_id,
            "planning_input_digest": planning_input.planning_input_digest,
            "service_card_id": planning_input.confirmed_service_card_id,
            "input_schema": planning_input.schema_name,
            "criteria_version": planning_input.criteria_version,
            "scope_rules": {
                "preserve_lineage": True,
                "do_not_approve": True,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
            "regulatory_document_assertions": (
                regulatory_turn_context.regulatory_document_assertion_context(
                    planning_input
                )
            ),
            "placement_contract": _placement_contract(planning_input),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    model_input, coverage = compact_planning_input_for_model(planning_input)
    untrusted_context = json.dumps(
        {
            "planning_input": model_input,
            "planning_input_coverage": coverage,
            "operator_hint": operator_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return CodexAppServerStructuredTurnRequest(
        instruction=_planning_instruction(planning_input),
        application_context=application_context,
        untrusted_context=untrusted_context,
        output_schema=content_planning_output_schema(planning_input),
    )


def _planning_instruction(planning_input: ContentPlanningInput) -> str:
    prompt_template = resolve_prompt_template("planning_proposal")
    if planning_input.goal == "new_page":
        return prompt_template.render(
            plan_kind="nowej strony",
            page_scope_rules=(
                "Ta strona nie ma jeszcze publicznego URL-a ani inventory WordPress: nie "
                "przypisuj jej historycznych metryk, treści, nagłówków ani dowodów "
                "istniejącej strony. "
            ),
            query_inventory_rules=(
                "Każda sekcja musi mieć disposition create i nie może wskazywać "
                "inventory_section_id ani inventory_heading. "
            ),
            placement_rules=(
                "Placement CTA lub linku ma być after_lead, after_content albo dokładnym "
                "nagłówkiem zaplanowanej sekcji. "
            ),
        )
    return prompt_template.render(
        plan_kind="odświeżenia istniejącej strony",
        page_scope_rules=(
            "Zachowaj użyteczne elementy inventory i przypisz każdej sekcji konkretne "
            "pytanie czytelnika. Niski CTR jest tylko sygnałem do sprawdzenia, nie "
            "werdyktem. "
        ),
        query_inventory_rules=(
            "Jeśli wejście zawiera exact zapytania GSC/Ads/Keyword Planner, przypisz co "
            "najmniej jedno właściwe zapytanie do odpowiedniej sekcji przez query_terms; "
            "zapytania bez pewnego dopasowania mogą pozostać page_only, ale istotne "
            "zapytania muszą mieć jawne przypisanie albo review. Nie pomijaj istniejących "
            "sekcji inventory: każdą przypisz przez inventory_section_id do jednej sekcji "
            "planu z disposition albo pozostaw jako jawnie wymagającą review. Przy "
            "disposition rewrite zachowaj w nowym headingu główny termin i intencję "
            "odpowiadającej sekcji inventory. "
        ),
        placement_rules=(
            "Placement CTA lub linku ma być after_lead, after_content albo dokładnym "
            "nagłówkiem jednej z zaplanowanych sekcji, która nie ma disposition "
            "remove_review_required. Jeśli application_context zawiera placement_contract, "
            "traktuj forbidden_section_headings jako zakazane i użyj jednego z "
            "safe_fallback_placements. "
        ),
    )


def content_planning_output_schema(
    planning_input: ContentPlanningInput,
) -> dict[str, object]:
    schema = deepcopy(ContentPlanningModelOutput.model_json_schema())
    require_all_object_properties(schema)
    schema_properties = mapping(schema, "properties")
    definitions = mapping(schema, "$defs")
    section = definition(definitions, "ContentPlanningModelSection")
    faq = definition(definitions, "ContentPlanningFaqItem")
    cta = definition(definitions, "ContentPlanningCtaBlock")
    link = definition(definitions, "ContentPlanningInternalLink")
    hypothesis = definition(definitions, "ContentPlanningConditionalHypothesis")
    measurement = definition(definitions, "ContentPlanningMeasurementPlan")
    queries = [
        row.term
        for row in (
            *planning_input.query_portfolio.gsc_query_rows,
            *planning_input.query_portfolio.ads_term_rows,
            *planning_input.query_portfolio.keyword_planner_rows,
        )
    ]
    evidence_ids = planning_input.evidence_ids
    claim_ids = [
        entry.id
        for entry in planning_input.claim_ledger
        if entry.status in {"allowed_with_evidence", "allowed_general"}
    ]
    inventory_headings = [section.heading for section in planning_input.inventory.sections]
    inventory_section_ids = [section.section_id for section in planning_input.inventory.sections]
    internal_link_urls = [
        candidate.target_url for candidate in planning_input.internal_link_candidates
    ]

    mapping(schema_properties, "service_card_id")["const"] = (
        planning_input.confirmed_service_card_id
    )
    _restrict_array(properties(section), "query_terms", queries)
    _restrict_array(properties(section), "evidence_ids", evidence_ids)
    _restrict_array(properties(section), "claim_ids", claim_ids)
    _restrict_array(
        properties(section),
        "regulatory_requirement_ids",
        [requirement.id for requirement in planning_input.regulatory_coverage.requirements],
    )
    _restrict_nullable_string(
        properties(section),
        "inventory_heading",
        inventory_headings,
    )
    _restrict_nullable_string(
        properties(section),
        "inventory_section_id",
        inventory_section_ids,
    )
    if planning_input.goal == "new_page":
        mapping(properties(section), "inventory_disposition")["const"] = "create"
        mapping(properties(section), "inventory_heading")["const"] = None
        mapping(properties(section), "inventory_section_id")["const"] = None
    for schema_definition in (faq, cta):
        _restrict_array(properties(schema_definition), "evidence_ids", evidence_ids)
        _restrict_array(properties(schema_definition), "claim_ids", claim_ids)
    if planning_input.required_cta_patterns:
        _restrict_string(
            properties(cta),
            "copy_direction",
            planning_input.required_cta_patterns,
        )
    _restrict_array(properties(faq), "query_terms", queries)
    _restrict_array(properties(link), "evidence_ids", evidence_ids)
    _restrict_array(properties(link), "claim_ids", claim_ids)
    _restrict_string(properties(link), "target_url", internal_link_urls)
    _restrict_single_link_candidate_evidence(link, planning_input)
    _restrict_array(properties(hypothesis), "evidence_ids", evidence_ids)
    # Keep the first plan deliberately compact.  The model is producing a
    # reviewable strategy, not the full article; bounded arrays materially
    # reduce structured-output search while still leaving room for a normal
    # service page and its evidence lineage.
    _cap_array(schema_properties, "sections", 12)
    _cap_array(schema_properties, "faq", 8)
    _cap_array(schema_properties, "cta_blocks", 4)
    # The quality gate already owns this invariant after parsing, but the
    # structured-output boundary must communicate it to Codex as well.  An
    # empty array is schema-valid only when no CTA is required by the exact
    # planning input; otherwise it needlessly burns a run before being
    # rejected downstream.
    mapping(schema_properties, "cta_blocks")["minItems"] = planning_input.minimum_cta_blocks
    _cap_array(schema_properties, "conditional_hypotheses", 4)
    _restrict_array(
        properties(measurement),
        "metrics_to_watch",
        planning_input.measurement_metrics,
    )
    _restrict_array(
        properties(measurement),
        "baseline_evidence_ids",
        planning_input.measurement_baseline_evidence_ids,
    )
    mapping(properties(measurement), "observation_rule")["const"] = (
        planning_input.measurement_observation_rule
    )
    mapping(properties(measurement), "success_claim_rule")["const"] = (
        planning_input.measurement_success_claim_rule
    )
    if not any(
        source.status == "used" and source.source in {"google_ads", "social"}
        for source in planning_input.source_assessments
    ):
        mapping(schema_properties, "conditional_hypotheses")["maxItems"] = 0
    mapping(schema_properties, "internal_links")["maxItems"] = len(internal_link_urls)
    return schema


def _placement_contract(planning_input: ContentPlanningInput) -> dict[str, object]:
    """Expose server-derived placement guardrails to the model turn."""

    return {
        "inventory_section_headings": [
            section.heading for section in planning_input.inventory.sections
        ],
        "forbidden_placement_rule": (
            "Nie umieszczaj CTA ani linku przy żadnej sekcji, której output ma "
            "inventory_disposition=remove_review_required."
        ),
        "safe_fallback_placements": ["after_lead", "after_content"],
    }


def _restrict_array(
    properties: dict[str, object],
    key: str,
    values: list[str],
) -> None:
    field = mapping(properties, key)
    unique = list(dict.fromkeys(values))
    if unique:
        field["items"] = {"enum": unique, "type": "string"}
    else:
        field["maxItems"] = 0


def _restrict_nullable_string(
    properties: dict[str, object],
    key: str,
    values: list[str],
) -> None:
    field = mapping(properties, key)
    unique = list(dict.fromkeys(values))
    field.clear()
    field["anyOf"] = [
        {"enum": unique, "type": "string"} if unique else {"type": "null"},
        {"type": "null"},
    ]


def _restrict_string(
    properties: dict[str, object],
    key: str,
    values: list[str],
) -> None:
    field = mapping(properties, key)
    if values:
        field["enum"] = list(dict.fromkeys(values))


def _restrict_single_link_candidate_evidence(
    link_schema: dict[str, object],
    planning_input: ContentPlanningInput,
) -> None:
    """Enforce exact evidence when the input has one unambiguous link target."""

    if len(planning_input.internal_link_candidates) != 1:
        return
    _restrict_array(
        properties(link_schema),
        "evidence_ids",
        planning_input.internal_link_candidates[0].evidence_ids,
    )


def _cap_array(properties: dict[str, object], key: str, maximum: int) -> None:
    field = mapping(properties, key)
    current = field.get("maxItems")
    if not isinstance(current, int) or current > maximum:
        field["maxItems"] = maximum


__all__ = ["content_planning_output_schema", "content_planning_turn_request"]
