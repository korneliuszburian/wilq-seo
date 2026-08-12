from __future__ import annotations

import json
from copy import deepcopy
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.codex.app_server import CodexAppServerStructuredTurnRequest
from wilq.codex.prompts import resolve_prompt_template
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.regulatory_repair_policy import regulatory_section_repair_modes
from wilq.content.drafts.structured_generation import StructuredDraftGenerationContract
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


class _RegulatorySectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    mode: Literal["append", "replace"]
    body_markdown: str = Field(min_length=1)


class _RegulatoryAssertionRepairOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[_RegulatorySectionPatch] = Field(min_length=1)
    publish_ready: bool = False


def initial_full_draft_turn_request(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    generation_contract: StructuredDraftGenerationContract,
) -> CodexAppServerStructuredTurnRequest:
    application_context = json.dumps(
        {
            "operation": "generate_initial_full_content_draft",
            "work_item_id": planning_input.work_item_id,
            "proposal_id": proposal.proposal_id,
            "planning_digest": proposal.planning_digest,
            "planning_input_digest": planning_input.planning_input_digest,
            "service_card_id": planning_input.confirmed_service_card_id,
            "regulatory_document_assertions": _regulatory_document_assertion_context(
                planning_input
            ),
            "scope_rules": {
                "preserve_exact_document_structure": True,
                "excluded_inventory_sections_are_not_document_targets": True,
                "use_only_api_owned_lineage": True,
                "do_not_approve": True,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    untrusted_context = json.dumps(
        {
            "planning_input": compact_initial_draft_planning_input(planning_input),
            "approved_planning_proposal": compact_initial_draft_proposal(proposal),
            "generation_constraints": generation_contract.model_input.model_dump(mode="json"),
            "document_scope": {
                "included_section_ids": [
                    section.section_id for section in draftable_planning_sections(proposal.sections)
                ],
                "excluded_section_ids": [
                    section.section_id
                    for section in proposal.sections
                    if section.inventory_disposition == "remove_review_required"
                ],
            },
            "approved_regulatory_facts_by_section": _regulatory_facts_by_section(
                planning_input,
                proposal,
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    prompt_template = resolve_prompt_template("content_initial_draft")
    return CodexAppServerStructuredTurnRequest(
        instruction=prompt_template.render(
            regulatory_draft_directive=_regulatory_draft_directive(
                planning_input,
                proposal,
            )
        ),
        application_context=application_context,
        untrusted_context=untrusted_context,
        output_schema=initial_full_draft_output_schema(proposal),
    )


def regulatory_assertion_repair_turn_request(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    candidate: ContentInitialDraftModelOutput,
    missing_assertion_codes: list[str],
    repair_reasons: dict[str, str] | None = None,
) -> CodexAppServerStructuredTurnRequest:
    """Make one bounded correction turn for deterministic regulatory omissions."""

    assertions, section_ids = _missing_assertions_for_repair(
        planning_input, proposal, missing_assertion_codes
    )
    section_repair_modes = regulatory_section_repair_modes(
        proposal,
        missing_assertion_codes,
        repair_reasons or {},
    )
    requirement_ids = {item["requirement_id"] for item in assertions}
    source_facts = [
        {
            "summary": fact.extracted_fact,
            "requirement_ids": fact.regulatory_requirement_ids,
        }
        for fact in planning_input.regulatory_coverage.source_facts
        if fact.official_source
        and fact.review_status == "approved"
        and requirement_ids.intersection(fact.regulatory_requirement_ids)
    ]
    return CodexAppServerStructuredTurnRequest(
        instruction=(
            "Zwróć wyłącznie patch body_markdown wskazanych section_id wraz z server-owned "
            "mode. append oznacza dopisanie kwalifikowanego zdania bez usuwania istniejącej "
            "treści. replace oznacza pełne, poprawione body_markdown tej jednej sekcji: usuń "
            "nadmierne albo niewspierane twierdzenie, zachowaj użyteczną odpowiedź dla "
            "czytelnika i oprzyj ją wyłącznie na approved_official_source_facts. Nie dotykaj "
            "innych sekcji, nagłówków, FAQ, CTA ani linków. Dla każdego requirementu zachowaj "
            "podmiot, warunek, zakres, wyjątek oraz termin lub wartość z właściwego faktu. "
            "Nie rozszerzaj obowiązku, wyjątków, terminów ani sankcji. Zwróć wyłącznie JSON "
            "zgodny ze schema."
        ),
        application_context=json.dumps(
            {
                "operation": "repair_initial_draft_regulatory_assertions",
                "work_item_id": planning_input.work_item_id,
                "proposal_id": proposal.proposal_id,
                "missing_regulatory_document_assertions": assertions,
                "critic_reasons": repair_reasons or {},
                "section_repair_modes": section_repair_modes,
                "do_not_approve": True,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        untrusted_context=json.dumps(
            {
                "candidate_document": candidate.model_dump(mode="json"),
                "approved_official_source_facts": source_facts,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        output_schema=_regulatory_assertion_repair_output_schema(section_ids),
    )


def readability_repair_turn_request(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    candidate: ContentInitialDraftModelOutput,
    issues: list[tuple[str, str, str]],
) -> CodexAppServerStructuredTurnRequest:
    candidate_section_ids = {section.section_id for section in candidate.sections}
    auxiliary_section_ids = {
        *(f"faq:{index}" for index, _ in enumerate(candidate.faq, start=1)),
        *(f"cta:{index}" for index, _ in enumerate(candidate.cta_blocks, start=1)),
        "page_assets:wordpress_title",
        "page_assets:meta_title",
        "page_assets:meta_description",
        "page_assets:h1",
        "page_assets:lead",
        *(f"link:{index}" for index, _ in enumerate(candidate.internal_links, start=1)),
    }
    if candidate_section_ids & auxiliary_section_ids:
        raise ValueError("Candidate section IDs collide with reserved repair targets.")
    candidate_section_ids.update(auxiliary_section_ids)
    affected_section_ids = list(
        dict.fromkeys(
            section_id for _, section_id, _ in issues if section_id in candidate_section_ids
        )
    )
    if not affected_section_ids:
        raise ValueError("Readability repair requires an affected candidate section.")
    auxiliary_targets = any(
        section_id in auxiliary_section_ids for section_id in affected_section_ids
    )
    instruction = (
        (
            "Napraw wyłącznie pola wskazane w issues. Identyfikator zwykłej sekcji oznacza jej "
            "body_markdown, faq:<index> odpowiedź FAQ, cta:<index> treść CTA, "
            "page_assets:<field> wskazane pole page assets, a link:<index> anchor_text linku. "
            "Usuń notatki robocze, meta-komentarze i powtórzone akapity, podziel ściany tekstu "
            "i zbyt długie zdania "
            "oraz rozwiń zbyt krótkie odpowiedzi. Każdy patch musi usuwać dokładny problem "
            "opisany w jego reason. Zachowaj znaczenie, fakty, zakres i ton tekstu dla "
            "czytelnika. Nie dotykaj żadnych innych pól. Dla FAQ, CTA, page assets i linków "
            "zawsze użyj replace. Zwróć dokładnie po jednym patchu dla każdego dozwolonego "
            "section_id. Dla zwykłej sekcji użyj replace dla pełnej poprawionej treści albo "
            "append wyłącznie do uzupełnienia zbyt krótkiej sekcji. Nie dodawaj nowych notatek "
            "roboczych ani informacji wymagających weryfikacji. Zwróć wyłącznie JSON zgodny ze "
            "schema."
        )
        if auxiliary_targets
        else (
            "Napraw wyłącznie body_markdown sekcji wskazanych w polu issues. Usuń notatki "
            "robocze, meta-komentarze i powtórzone akapity, podziel ściany tekstu "
            "i zbyt długie zdania oraz rozwiń "
            "zbyt krótkie odpowiedzi. Każdy patch musi usuwać dokładny problem opisany w jego "
            "reason. Zachowaj znaczenie, fakty, zakres i ton tekstu dla czytelnika. Nie dotykaj "
            "innych sekcji, nagłówków, page assets, FAQ, CTA ani linków. Zwróć dokładnie po "
            "jednym patchu dla każdego dozwolonego section_id. Użyj replace dla pełnej "
            "poprawionej treści sekcji albo append wyłącznie do uzupełnienia zbyt krótkiej "
            "sekcji. Nie dodawaj nowych notatek roboczych ani informacji wymagających "
            "weryfikacji. Zwróć wyłącznie JSON zgodny ze schema."
        )
    )
    return CodexAppServerStructuredTurnRequest(
        instruction=instruction,
        application_context=json.dumps(
            {
                "operation": "repair_initial_draft_readability",
                "work_item_id": planning_input.work_item_id,
                "proposal_id": proposal.proposal_id,
                "affected_section_ids": affected_section_ids,
                "do_not_approve": True,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        untrusted_context=json.dumps(
            {
                "candidate_document": candidate.model_dump(mode="json"),
                "issues": [
                    {
                        "code": code,
                        "affected_section_id": section_id,
                        "reason": reason,
                    }
                    for code, section_id, reason in issues
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        output_schema=_regulatory_assertion_repair_output_schema(affected_section_ids),
    )


def _missing_assertions_for_repair(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    missing_codes: list[str],
) -> tuple[list[dict[str, object]], list[str]]:
    missing = set(missing_codes)
    requirements = {item.id: item for item in planning_input.regulatory_coverage.requirements}
    assertions: list[dict[str, object]] = []
    section_ids: list[str] = []
    for section in draftable_planning_sections(proposal.sections):
        for requirement_id in section.regulatory_requirement_ids:
            requirement = requirements.get(requirement_id)
            if requirement is None:
                continue
            for assertion in requirement.document_assertions:
                code = f"regulatory_document_assertion:{requirement_id}:{assertion.id}"
                if code in missing or f"requirement:{requirement_id}" in missing:
                    assertions.append(
                        {
                            "section_id": section.section_id,
                            "requirement_id": requirement_id,
                            "assertion_id": assertion.id,
                            "required_any_of": assertion.required_any_of,
                        }
                    )
                    if section.section_id not in section_ids:
                        section_ids.append(section.section_id)
    return assertions, section_ids


def _regulatory_assertion_repair_output_schema(section_ids: list[str]) -> dict[str, object]:
    schema = deepcopy(_RegulatoryAssertionRepairOutput.model_json_schema())
    _require_all_object_properties(schema)
    definition = _mapping(_mapping(schema, "$defs"), "_RegulatorySectionPatch")
    section_properties = _mapping(definition, "properties")
    section_id = _mapping(section_properties, "section_id")
    section_id["enum"] = section_ids
    sections = _mapping(_mapping(schema, "properties"), "sections")
    sections["minItems"] = len(section_ids)
    sections["maxItems"] = len(section_ids)
    return schema


def compact_initial_draft_planning_input(
    planning_input: ContentPlanningInput,
) -> dict[str, object]:
    """Keep draft transport useful without replaying connector bookkeeping.

    This is a model-envelope projection only. The caller still validates and
    persists against the complete typed planning input and its digest.
    """

    payload = planning_input.model_dump(mode="json", exclude_none=True)
    assessments = payload.get("source_assessments")
    if isinstance(assessments, list):
        compact_assessments: list[object] = []
        assessment_keys = {
            "source",
            "status",
            "reason",
            "landing_match_tiers",
            "evidence_ids",
            "knowledge_card_ids",
            "refresh_run_id",
            "settlement_state",
            "quality_state",
            "interpretation_caveats",
        }
        for assessment in assessments:
            if isinstance(assessment, dict):
                compact_assessments.append(
                    {key: value for key, value in assessment.items() if key in assessment_keys}
                )
            else:
                compact_assessments.append(assessment)
        payload["source_assessments"] = compact_assessments

    comparisons = payload.get("metric_comparisons")
    if isinstance(comparisons, list):
        compact_comparisons: list[object] = []
        comparison_keys = {
            "source_connector",
            "status",
            "baseline_period",
            "comparison_period",
            "metric_names",
            "evidence_ids",
            "reason",
        }
        for comparison in comparisons:
            if isinstance(comparison, dict):
                compact_comparisons.append(
                    {key: value for key, value in comparison.items() if key in comparison_keys}
                )
            else:
                compact_comparisons.append(comparison)
        payload["metric_comparisons"] = compact_comparisons

    return payload


def compact_initial_draft_proposal(
    proposal: ContentPlanningProposal,
) -> dict[str, object]:
    """Keep the writer's editorial contract without replaying page telemetry."""

    payload = proposal.model_dump(mode="json", exclude_none=True)
    allowed = {
        "work_item_id",
        "planning_digest",
        "proposal_id",
        "planning_input_digest",
        "final_canonical_url",
        "service_card_id",
        "service_label",
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "angle",
        "value_proposition",
        "cta_direction",
        "sections",
        "faq",
        "cta_blocks",
        "internal_links",
        "evidence_ids",
        "source_connectors",
        "source_material_ids",
        "knowledge_card_ids",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def initial_full_draft_output_schema(
    proposal: ContentPlanningProposal,
) -> dict[str, object]:
    schema = deepcopy(ContentInitialDraftModelOutput.model_json_schema())
    _require_all_object_properties(schema)
    properties = _mapping(schema, "properties")
    definitions = _mapping(schema, "$defs")
    page_assets = _properties(_mapping(definitions, "ContentDraftRevisionPageAssets"))
    page_assets.pop("byline", None)
    page_assets_required = _mapping(definitions, "ContentDraftRevisionPageAssets").get("required")
    if isinstance(page_assets_required, list) and "byline" in page_assets_required:
        page_assets_required.remove("byline")
    section_definition = _mapping(definitions, "ContentInitialDraftSectionOutput")
    section = _properties(section_definition)
    faq = _properties(_mapping(definitions, "ContentInitialDraftFaqOutput"))
    link = _properties(_mapping(definitions, "ContentInitialDraftInternalLinkOutput"))

    draftable_sections = draftable_planning_sections(proposal.sections)
    _set_array_size(properties, "sections", len(draftable_sections))
    section_id = _mapping(section, "section_id")
    section_id["enum"] = [item.section_id for item in draftable_sections]
    heading = _mapping(section, "heading")
    heading["enum"] = [item.heading for item in draftable_sections]
    _set_array_size(properties, "faq", len(proposal.faq))
    question = _mapping(faq, "question")
    question["enum"] = [item.question for item in proposal.faq] or ["__WILQ_EMPTY_ARRAY_ONLY__"]
    _set_array_size(properties, "cta_blocks", len(proposal.cta_blocks))
    _set_array_size(properties, "internal_links", len(proposal.internal_links))
    target_url = _mapping(link, "target_url")
    target_url["enum"] = [item.target_url for item in proposal.internal_links] or [
        "__WILQ_EMPTY_ARRAY_ONLY__"
    ]
    return schema


def _regulatory_draft_directive(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> str:
    """Render the trusted, section-bound regulatory concepts for the writer."""

    requirements = {
        requirement.id: requirement
        for requirement in planning_input.regulatory_coverage.requirements
    }
    obligations: list[str] = []
    for section in draftable_planning_sections(proposal.sections):
        terms: list[str] = []
        for requirement_id in section.regulatory_requirement_ids:
            requirement = requirements.get(requirement_id)
            if requirement is not None:
                terms.extend(
                    " lub ".join(assertion.required_any_of)
                    for assertion in requirement.document_assertions
                )
        if terms:
            obligations.append(f"{section.section_id}: {'; '.join(terms)}")
    if not obligations:
        return ""
    return (
        " Dla poniższych section_id body_markdown musi zawierać każdy wskazany "
        "koncept (jedną z podanych dopuszczalnych form), oparty na źródłach z planu: "
        + " | ".join(obligations)
        + "."
    )


def _regulatory_document_assertion_context(
    planning_input: ContentPlanningInput,
) -> list[dict[str, object]]:
    """Expose only server-owned assertion policy to the document writer."""

    return [
        {
            "requirement_id": requirement.id,
            "assertion_id": assertion.id,
            "label": assertion.label,
            "required_any_of": assertion.required_any_of,
        }
        for requirement in planning_input.regulatory_coverage.requirements
        for assertion in requirement.document_assertions
    ]


def _regulatory_facts_by_section(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[dict[str, object]]:
    """Project reviewed official facts next to each regulated document target."""

    facts_by_requirement = {
        requirement_id: [
            {
                "source_fact_id": fact.source_id,
                "summary": fact.extracted_fact,
                "evidence_ids": fact.evidence_ids,
                "requirement_ids": fact.regulatory_requirement_ids,
            }
            for fact in planning_input.regulatory_coverage.source_facts
            if fact.official_source
            and fact.review_status == "approved"
            and requirement_id in fact.regulatory_requirement_ids
        ]
        for requirement_id in {
            requirement_id
            for section in draftable_planning_sections(proposal.sections)
            for requirement_id in section.regulatory_requirement_ids
        }
    }
    return [
        {
            "section_id": section.section_id,
            "requirement_ids": section.regulatory_requirement_ids,
            "source_facts": [
                fact
                for requirement_id in section.regulatory_requirement_ids
                for fact in facts_by_requirement[requirement_id]
            ],
        }
        for section in draftable_planning_sections(proposal.sections)
        if section.regulatory_requirement_ids
    ]


def _properties(definition: dict[str, object]) -> dict[str, object]:
    return _mapping(definition, "properties")


def _mapping(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise RuntimeError(f"Initial draft output schema is missing {key}.")
    return cast(dict[str, object], nested)


def _set_array_size(properties: dict[str, object], key: str, size: int) -> None:
    field = _mapping(properties, key)
    field["minItems"] = size
    field["maxItems"] = size


def _require_all_object_properties(value: object) -> None:
    """Make Pydantic's optional defaults valid for Codex structured output."""

    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            value["required"] = list(properties)
        value.pop("default", None)
        for nested in value.values():
            _require_all_object_properties(nested)
    elif isinstance(value, list):
        for nested in value:
            _require_all_object_properties(nested)


__all__ = [
    "initial_full_draft_output_schema",
    "initial_full_draft_turn_request",
    "regulatory_assertion_repair_turn_request",
]
