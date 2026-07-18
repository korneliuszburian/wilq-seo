from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_codex_proposal as section_proposal_router
from apps.api.wilq_api.routers import content_initial_draft as initial_draft_router
from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers import content_semantic_review as semantic_review_router
from apps.api.wilq_api.routers import content_snapshot as content_snapshot_router
from wilq.briefing import content_diagnostics
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.knowledge import cards as knowledge_cards
from wilq.content.planning import dynamic_input
from wilq.content.planning.internal_link_candidates import (
    ContentPlanningInternalLinkCandidate,
)
from wilq.content.workflow import catalog as inventory_catalog
from wilq.content.workflow import inventory_binding
from wilq.content.workflow.catalog import (
    ContentInventoryMaterialResponse,
    inventory_work_item_id,
)
from wilq.storage.metric_store import metric_store_path


class PlanningClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.planning_placement = "after_content"
        self.planning_link_target: str | None = None
        self.planning_link_evidence_ids: list[str] | None = None
        self.planning_link_claim_ids: list[str] | None = None
        self.initial_link_anchor_text: str | None = None
        self.initial_link_target_url: str | None = None
        self.initial_section_body_markdown: str | None = None
        self.semantic_external_call_attempted = False

    def run_structured_turn(self, request: Any) -> CodexAppServerTurnResult:
        self.calls += 1
        if self.fail:
            return CodexAppServerTurnResult(status="failed", blockers=())
        operation = json.loads(request.application_context)["operation"]
        if operation == "generate_initial_full_content_draft":
            output = _initial_draft_output(self, request)
        elif operation == "review_full_content_revision_semantics":
            output = _semantic_review_output(request)
        elif operation == "propose_section_revision":
            output = _section_revision_output(request)
        else:
            output = _planning_output(self, request)
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(output, ensure_ascii=False),
            thread_id=f"thread_{self.calls}",
            turn_id=f"turn_{self.calls}",
            event_methods=("turn/completed",),
            item_types=("agentMessage",),
            external_call_attempted=(
                self.semantic_external_call_attempted
                if operation == "review_full_content_revision_semantics"
                else False
            ),
        )


def _planning_output(client: PlanningClient, request: Any) -> dict[str, Any]:
    planning_input = json.loads(request.untrusted_context)["planning_input"]
    assert_planning_input_contract(planning_input)
    inventory_headings = [
        section["heading"]
        for section in planning_input["inventory"]["sections"]
        if _is_useful_synthetic_heading(section["heading"])
    ] or [planning_input["inventory"]["sections"][0]["heading"]]
    inventory_heading = inventory_headings[0]
    evidence_id = planning_input["evidence_ids"][0]
    query_rows = planning_input["query_portfolio"]["gsc_query_rows"]
    query_terms = [query_rows[0]["term"]] if query_rows else []
    allowed_claims = [
        entry["id"]
        for entry in planning_input["claim_ledger"]
        if entry["status"] in {"allowed_with_evidence", "allowed_general"}
    ]
    candidates = planning_input["internal_link_candidates"]
    assert request.output_schema["properties"]["internal_links"]["maxItems"] == len(
        candidates
    )
    link_schema = request.output_schema["$defs"]["ContentPlanningInternalLink"]
    assert link_schema["properties"]["target_url"]["enum"] == [
        item["target_url"] for item in candidates
    ]
    if len(candidates) == 1:
        assert link_schema["properties"]["evidence_ids"]["items"]["enum"] == (
            candidates[0]["evidence_ids"]
        )
    lineage = {"evidence_ids": [evidence_id], "claim_ids": allowed_claims[:1]}
    return {
        "language": "pl-PL",
        "service_card_id": planning_input["confirmed_service_card_id"],
        "target_reader": planning_input["target_reader"],
        "buyer_problem": planning_input["buyer_problem"],
        "buyer_trigger": planning_input["buyer_trigger"],
        "search_intent": planning_input["search_intent"],
        "angle": f"Plan dla {planning_input['service_label']}",
        "value_proposition": "Bezpieczna odpowiedź na pytanie czytelnika.",
        "page_assets": _planning_page_assets(planning_input, inventory_heading),
        # The real mapping gate covers every existing inventory heading. Keep
        # the fake Codex output aligned with that contract instead of creating
        # a partial one-section proposal that must correctly be marked stale.
        "sections": [
            _planning_section(heading, query_terms, lineage)
            for heading in inventory_headings
        ],
        "faq": [_planning_faq(query_terms, lineage)],
        "cta_blocks": [_planning_cta(client, lineage)],
        "internal_links": [_planning_link(client, item) for item in candidates],
        "conditional_hypotheses": [],
        "measurement_plan": {
            "metrics_to_watch": planning_input["measurement_metrics"],
            "baseline_evidence_ids": planning_input["measurement_baseline_evidence_ids"],
            "observation_rule": planning_input["measurement_observation_rule"],
            "success_claim_rule": planning_input["measurement_success_claim_rule"],
        },
        "publish_ready": False,
    }


def _is_useful_synthetic_heading(heading: str) -> bool:
    normalized = heading.strip().lower()
    if normalized.startswith(
        (
            "poniżej przedstawiamy",
            "zaufali nam",
            "copyright",
            "menu",
            "więcej",
            "powiązane materiały",
            "zobacz także",
            "materiały powiązane",
        )
    ):
        return False
    return not bool(
        re.search(
            r"\b\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}\b",
            normalized,
        )
    )


def _planning_page_assets(
    planning_input: dict[str, Any], inventory_heading: str
) -> dict[str, str]:
    service_label = planning_input["service_label"]
    return {
        "title": f"Plan: {service_label}",
        "h1": planning_input["inventory"].get("title_or_h1") or inventory_heading,
        "lead": "Najpierw odpowiedz na główny problem czytelnika.",
        "meta_title": f"{service_label} — Ekologus",
        "meta_description": "Sprawdź zakres, dokumenty i bezpieczny następny krok.",
    }


def _planning_section(
    inventory_heading: str,
    query_terms: list[str],
    lineage: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "heading": inventory_heading,
        "purpose": "Zachowaj użyteczną sekcję i doprecyzuj odpowiedź.",
        "reader_question": "Co trzeba sprawdzić przed działaniem?",
        "inventory_disposition": "rewrite",
        "inventory_heading": inventory_heading,
        "query_terms": query_terms,
        **lineage,
    }


def _planning_faq(
    query_terms: list[str], lineage: dict[str, list[str]]
) -> dict[str, Any]:
    return {
        "question": "Od czego zacząć?",
        "purpose": "Wyjaśnić bezpieczny pierwszy krok.",
        "query_terms": query_terms,
        **lineage,
    }


def _planning_cta(
    client: PlanningClient, lineage: dict[str, list[str]]
) -> dict[str, Any]:
    return {
        "placement": client.planning_placement,
        "purpose": "Przejście do konsultacji bez gwarancji wyniku.",
        "copy_direction": "Opisz sytuację firmy i poproś o weryfikację.",
        **lineage,
    }


def _planning_link(client: PlanningClient, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "placement": client.planning_placement,
        "target_url": client.planning_link_target or item["target_url"],
        "anchor_direction": item["anchor_hint"],
        "evidence_ids": (
            client.planning_link_evidence_ids
            if client.planning_link_evidence_ids is not None
            else item["evidence_ids"]
        ),
        "claim_ids": (
            client.planning_link_claim_ids
            if client.planning_link_claim_ids is not None
            else []
        ),
    }


def _initial_draft_output(client: PlanningClient, request: Any) -> dict[str, Any]:
    context = json.loads(request.untrusted_context)
    proposal = context["approved_planning_proposal"]
    planning_input = context["planning_input"]
    assert len(planning_input["source_assessments"]) == 10
    assert planning_input["inventory"]["sections"]
    assert "query_portfolio" in planning_input
    assert "measurement_metrics" in planning_input
    assert "generation_constraints" in context
    schema = request.output_schema
    _assert_all_object_properties_required(schema)
    section_schema = schema["$defs"]["ContentInitialDraftSectionOutput"]
    assert schema["properties"]["sections"]["minItems"] == len(proposal["sections"])
    assert section_schema["properties"]["section_id"]["enum"] == [
        item["section_id"] for item in proposal["sections"]
    ]
    service_label = proposal["service_label"]
    return {
        "language": "pl-PL",
        "page_assets": {
            "wordpress_title": f"Pełny tekst: {service_label}",
            "meta_title": f"{service_label} — Ekologus",
            "meta_description": "Sprawdź sytuację firmy i możliwy następny krok.",
            "h1": f"{service_label} dla firm",
            "lead": f"Wyjaśniamy, kiedy {service_label} może pomóc w uporządkowaniu działań.",
        },
        "sections": [
            {
                "section_id": section["section_id"],
                "heading": section["heading"],
                "body_markdown": (
                    client.initial_section_body_markdown
                    or (
                        f"{section['reader_question']} Odpowiedź wynika z dokładnego planu "
                        f"dla usługi {service_label}."
                    )
                ),
            }
            for section in proposal["sections"]
        ],
        "faq": [
            {
                "question": item["question"],
                "answer_markdown": (
                    f"Najpierw opisz sytuację firmy w kontekście usługi {service_label}."
                ),
            }
            for item in proposal["faq"]
        ],
        "cta_blocks": [
            {"body_markdown": f"Opisz potrzeby firmy dotyczące: {service_label}."}
            for _ in proposal["cta_blocks"]
        ],
        "internal_links": [
            {
                "target_url": client.initial_link_target_url or item["target_url"],
                "anchor_text": client.initial_link_anchor_text
                or item["anchor_direction"],
            }
            for item in proposal["internal_links"]
        ],
        "publish_ready": False,
    }


def _assert_all_object_properties_required(value: object) -> None:
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            assert set(value.get("required", [])) == set(properties)
        for nested in value.values():
            _assert_all_object_properties_required(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_all_object_properties_required(nested)


def _semantic_review_output(request: Any) -> dict[str, Any]:
    context = json.loads(request.untrusted_context)
    revision = context["revision"]
    proposal = context["approved_planning_proposal"]
    planning_input = context["planning_input"]
    revision_digest = json.loads(request.application_context)["revision_digest"]
    assert revision["content_digest"] == revision_digest
    assert proposal["planning_input_digest"] == planning_input["planning_input_digest"]
    target = revision["sections"][0]["section_id"]
    evidence_id = revision["sections"][0]["evidence_ids"][0]
    dimensions = [
        "answer_directness",
        "completeness",
        "logical_flow",
        "specificity",
        "repetition",
        "search_intent_fit",
        "buyer_fit",
        "credibility",
        "conversion_clarity",
    ]
    output = {
        "language": "pl-PL",
        "dimensions": [
            {
                "dimension": dimension,
                "status": "needs_changes" if dimension == "answer_directness" else "strong",
                "reason": (
                    "Pierwsza odpowiedź powinna szybciej przejść do decyzji czytelnika."
                    if dimension == "answer_directness"
                    else "Wymiar nie ma konkretnego problemu w tej syntetycznej wersji."
                ),
                "affected_targets": [target],
            }
            for dimension in dimensions
        ],
        "findings": [
            {
                "dimension": "answer_directness",
                "severity": "medium",
                "label": "Odpowiedź zaczyna się zbyt ogólnie",
                "reason": "Czytelnik zbyt późno widzi bezpośredni następny krok.",
                "instruction": "Przenieś konkretną odpowiedź na początek wybranej sekcji.",
                "affected_targets": [target],
                "evidence_ids": [evidence_id],
            }
        ],
        "publish_ready": False,
        "human_review_required": True,
    }
    finding_schema = request.output_schema["$defs"]["ContentSemanticFindingOutput"]
    assert target in finding_schema["properties"]["affected_targets"]["items"]["enum"]
    return output


def _section_revision_output(request: Any) -> dict[str, Any]:
    context = json.loads(request.untrusted_context)
    generation_input = context["generation_input"]
    base_revision = context["base_revision"]
    selected_headings = context["editable_section_headings"]
    base_by_heading = {
        section["heading"]: section for section in base_revision["sections"]
    }
    selected_sections = [base_by_heading[heading] for heading in selected_headings]
    evidence_ids = list(
        dict.fromkeys(
            evidence_id
            for section in selected_sections
            for evidence_id in section["evidence_ids"]
        )
    )
    return {
        "draft_kind": "section_draft",
        "language": "pl-PL",
        "title": base_revision["title"],
        "meta_title": generation_input["title"],
        "meta_description": "Sprawdź zakres przed kontaktem z Ekologus.",
        "h1": generation_input["title"],
        "sections": [
            {
                "heading": section["heading"],
                "body_markdown": (
                    "Konkretna odpowiedź poprawiona po decyzji człowieka i advisory review."
                ),
                "evidence_ids": section["evidence_ids"],
                "claims_used": generation_input["claims_allowed"],
            }
            for section in selected_sections
        ],
        "faq": ["Co warto sprawdzić przed kontaktem z Ekologus?"],
        "cta": "Skontaktuj się z Ekologus, żeby sprawdzić sytuację firmy.",
        "internal_links": ["https://ekologus.pl/kontakt/"],
        "source_facts_used": evidence_ids,
        "claims_needing_review": [],
        "forbidden_claims_avoided": generation_input["claims_removed_or_blocked"],
        "human_review_checklist": generation_input["human_review_questions"],
        "publish_ready": False,
    }


def assert_planning_input_contract(planning_input: dict[str, Any]) -> None:
    assert planning_input["schema_name"] == "wilq_content_planning_input_v6"
    excluded_connectors = {
        "google_search_console",
        "google_ads",
        "google_analytics_4",
        "ahrefs",
        "google_merchant_center",
        "localo",
    }
    assert not {
        fact["source_connector"] for fact in planning_input["source_facts"]
    }.intersection(excluded_connectors)
    assert "baseline_proposal" not in planning_input


def configure_planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    source_metric_db = metric_store_path()
    isolated_metric_db = tmp_path / "metrics.duckdb"
    if source_metric_db.exists():
        shutil.copy2(source_metric_db, isolated_metric_db)
    monkeypatch.setenv("WILQ_METRIC_DB", str(isolated_metric_db))
    _patch_approved_service_cards(monkeypatch)
    _patch_fresh_diagnostics(monkeypatch)
    _patch_synthetic_inventory_material(monkeypatch)
    _patch_internal_link_candidates(monkeypatch)
    runtime = PlanningClient()
    _patch_codex_clients(monkeypatch, runtime)
    return TestClient(app), runtime


def _patch_approved_service_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    approved_service_ids = {
        "ekologus_service_bdo_reporting",
        "ekologus_service_environmental_consulting_outsourcing",
    }
    approved_cards = tuple(
        card.model_copy(update={"lifecycle_status": "approved_current"})
        if card.id in approved_service_ids
        else card
        for card in knowledge_cards.ekologus_content_knowledge_cards()
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: approved_cards,
    )


def _patch_fresh_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    original_diagnostics = content_snapshot_router.diagnostics_with_exact_gsc_demand
    diagnostics_cache: dict[str, Any] = {}
    # Planning/child-revision tests do not exercise action registry output.
    # Avoid rebuilding every metric-backed action candidate while constructing
    # the snapshot; those candidates have their own focused proof suite.
    monkeypatch.setattr(content_diagnostics, "_list_actions", lambda: [])

    def fresh_diagnostics(work_item_id: str) -> Any:
        cached = diagnostics_cache.get(work_item_id)
        if cached is not None:
            return cached
        diagnostics = original_diagnostics(work_item_id)
        decisions = [
            decision.model_copy(
                update={
                    "wordpress_section_headings": (
                        decision.wordpress_section_headings
                        or [f"Istniejąca sekcja: {decision.primary_query or decision.title}"]
                    ),
                    "wordpress_section_count": decision.wordpress_section_count or 1,
                    "wordpress_section_inventory_status": "available",
                    "wordpress_content_summary": (
                        decision.wordpress_content_summary
                        or "Syntetyczne podsumowanie publicznej treści."
                    ),
                    "wordpress_content_word_count": decision.wordpress_content_word_count or 500,
                    "wordpress_content_inventory_status": "available",
                    # The harness supplies a reviewed synthetic material snapshot;
                    # production keeps the review-required gate for real imports.
                    "wordpress_content_material_confidence": "source_bound",
                    "wordpress_content_source_kind": "synthetic_reviewed_fixture",
                }
            )
            if inventory_work_item_id(
                decision.page or decision.source_public_url or ""
            ) == work_item_id
            else decision
            for decision in diagnostics.decision_queue
        ]
        freshness = diagnostics.freshness_assessment.model_copy(
            update={
                "state": "fresh",
                "requires_refresh": False,
                "missing_connector_ids": [],
                "blocked_connector_ids": [],
                "stale_connector_ids": [],
                "connector_labels_requiring_refresh": [],
                "summary": "Syntetyczny świeży proof planowania.",
                "next_step": "Można zbudować wejście planu do testu.",
            }
        )
        result = diagnostics.model_copy(
            update={"decision_queue": decisions, "freshness_assessment": freshness}
        )
        diagnostics_cache[work_item_id] = result
        return result

    monkeypatch.setattr(
        content_snapshot_router,
        "diagnostics_with_exact_gsc_demand",
        fresh_diagnostics,
    )


def _patch_internal_link_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    def candidates(
        directions: Any, *, allowed_evidence_ids: Any
    ) -> list[ContentPlanningInternalLinkCandidate]:
        if not list(directions) or not list(allowed_evidence_ids):
            return []
        return [
            ContentPlanningInternalLinkCandidate(
                target_url="https://www.ekologus.pl/kontakt",
                anchor_hint="Kontakt z Ekologus",
                source_connector="wordpress_ekologus",
                evidence_ids=[next(iter(allowed_evidence_ids))],
            )
        ]

    monkeypatch.setattr(
        dynamic_input,
        "load_content_internal_link_candidates",
        candidates,
    )


def _patch_synthetic_inventory_material(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep planning tests off the live WordPress material endpoint."""

    def material(
        url: str,
        *,
        catalog: Any = None,
    ) -> ContentInventoryMaterialResponse:
        current_catalog = catalog or inventory_catalog.build_content_inventory_catalog_cached()
        item = next(
            (
                candidate
                for candidate in current_catalog.items
                if candidate.url.rstrip("/") == url.rstrip("/")
            ),
            None,
        )
        headings = [] if item is None else (item.acf_section_headings or [])
        return ContentInventoryMaterialResponse(
            status="ready",
            url=url,
            source_kind="synthetic_reviewed_fixture",
            title=None if item is None else item.title,
            content_text="Syntetyczny materiał strony do testu planowania.",
            content_summary="Syntetyczne podsumowanie publicznej treści.",
            content_word_count=500,
            section_headings=headings,
            acf_section_headings=headings,
            evidence_id=None if item is None else item.evidence_id,
            extraction_region="synthetic_test_fixture",
            material_confidence="source_bound",
            source_field_lineage=["synthetic_test_fixture"],
        )

    monkeypatch.setattr(inventory_binding, "read_content_inventory_material", material)


def _patch_codex_clients(
    monkeypatch: pytest.MonkeyPatch, runtime: PlanningClient
) -> None:
    for router in (
        planning_router,
        initial_draft_router,
        semantic_review_router,
        section_proposal_router,
    ):
        monkeypatch.setattr(
            router,
            "content_codex_app_server_client",
            lambda: runtime,
        )
