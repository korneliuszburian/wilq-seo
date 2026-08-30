from __future__ import annotations

import time
from typing import Any, cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import tests.content.dynamic_planning_test_support as planning_support
import wilq.content.knowledge.work_item_service_profile as service_profile_module
import wilq.content.planning.dynamic_input as dynamic_input_module
import wilq.content.planning.generated_proposal as generated_proposal_module
import wilq.content.planning.input_sources as input_sources_module
import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.workspace.api as workspace_api
import wilq.content.workflow.workspace.snapshot_service_selection as snapshot_selection
from apps.api.wilq_api.routers.content_initial_draft import register_content_initial_draft_route
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.knowledge import cards as knowledge_cards
from wilq.content.knowledge import source_facts as source_facts_module
from wilq.content.knowledge.cards import ContentKnowledgeServiceCandidate
from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

_TARGET_URL = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
_TARGET_WORK_ITEM_ID = inventory_work_item_id(_TARGET_URL)
_SERVICE_CARD_ID = "ekologus_service_operat_wodnoprawny"


def test_explicit_service_override_rebuilds_brief_draft_and_planning_foundations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _unused, _runtime, decision = _configure_nonauto_harness(monkeypatch, tmp_path)
    baseline = snapshot_for_work_item_or_404(_TARGET_WORK_ITEM_ID)
    selected = workspace_api.build_content_work_item_snapshot_response_from_selected_decision(
        decision,
        freshness_assessment=baseline.freshness_assessment,
        service_card_id_override=_SERVICE_CARD_ID,
    )
    brief = selected.sales_brief.sales_brief_result.brief
    draft = selected.draft_package.draft_package_result.draft_package
    planning = build_content_planning_input(
        selected,
        service_card_id=_SERVICE_CARD_ID,
    ).planning_input

    assert baseline.service_profile_context.service_card_id is None
    assert selected.service_profile_context.service_card_id == _SERVICE_CARD_ID
    assert selected.service_profile_context.service_selection_confirmed is True
    assert brief is not None and _SERVICE_CARD_ID in brief.knowledge_card_ids
    assert draft is not None and draft.work_item_id == _TARGET_WORK_ITEM_ID
    assert planning is not None
    assert planning.work_item_id == _TARGET_WORK_ITEM_ID
    assert planning.confirmed_service_card_id == _SERVICE_CARD_ID
    assert planning.final_canonical_url == _TARGET_URL


def test_nonauto_refresh_selection_authorization_plan_poll_and_draft(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _unused, runtime, decision = _configure_nonauto_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run_for_target())
    baseline = snapshot_for_work_item_or_404(_TARGET_WORK_ITEM_ID)
    authority = _authority(decision, baseline.freshness_assessment)
    client = _client(authority)

    selection = client.get(f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/refresh-preparation")
    ready = client.get(
        f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": _SERVICE_CARD_ID},
    )

    assert selection.status_code == ready.status_code == 200
    assert selection.json()["status"] == "selection_required", selection.json()["blockers"]
    assert ready.json()["status"] == "ready_to_authorize", ready.json()["blockers"][0][
        "source_codes"
    ]
    authorization = _authorize(client, ready.json())
    plan = _generate_and_poll_plan(client, ready.json(), authorization)
    polled = client.get(f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/planning-proposals")
    draft = client.post(
        f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/initial-draft",
        json={
            "expected_proposal_id": plan["proposal_id"],
            "expected_planning_digest": plan["planning_digest"],
            "expected_planning_input_digest": plan["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )

    assert plan["service_card_id"] == _SERVICE_CARD_ID
    assert plan["refresh_preparation_binding"]["service_card_id"] == _SERVICE_CARD_ID
    assert polled.status_code == 200, polled.text
    assert polled.json()["status"] == "ready", polled.json()
    assert polled.json()["service_card_id"] == _SERVICE_CARD_ID
    assert polled.json()["refresh_preparation_binding"]["service_card_id"] == _SERVICE_CARD_ID
    assert draft.status_code == 200, draft.text
    assert draft.json()["status"] == "created"
    assert runtime.calls == 2


def _configure_nonauto_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> tuple[TestClient, object, object]:
    client, runtime = configure_planning_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(
        planning_support,
        "_PLANNING_URLS",
        (*planning_support._PLANNING_URLS, _TARGET_URL),  # noqa: SLF001
    )
    original_decision = planning_support._synthetic_planning_decision  # noqa: SLF001
    target_decision = _target_decision_from(original_decision)

    def target_aware_decision(url: str):
        if url == _TARGET_URL:
            return target_decision
        return original_decision(url)

    monkeypatch.setattr(planning_support, "_synthetic_planning_decision", target_aware_decision)
    cards = tuple(
        card.model_copy(update={"lifecycle_status": "approved_current"})
        if card.id == _SERVICE_CARD_ID
        else card
        for card in knowledge_cards.ekologus_content_knowledge_cards()
    )
    monkeypatch.setattr(knowledge_cards, "ekologus_content_knowledge_cards", lambda: cards)
    _patch_operat_service_profile(monkeypatch, cards)
    _patch_nonauto_operat_matcher(monkeypatch, cards)
    return client, runtime, target_decision


def _target_decision_from(build):
    return build(_TARGET_URL).model_copy(
        update={
            "title": "Operat wodnoprawny — analiza pozwoleń zintegrowanych",
            "wordpress_title_or_h1": "Operat wodnoprawny",
            "wordpress_content_text": (
                "Operat wodnoprawny pomaga przygotować analizę obowiązków przy "
                "pozwoleniu zintegrowanym."
            ),
            "wordpress_content_summary": "Operat wodnoprawny i analiza obowiązków.",
        }
    )


def _patch_nonauto_operat_matcher(
    monkeypatch: pytest.MonkeyPatch,
    cards: tuple[object, ...],
) -> None:
    service_card = next(card for card in cards if getattr(card, "id", None) == _SERVICE_CARD_ID)
    original = knowledge_cards.match_content_knowledge_cards

    def nonauto_match(item: object):
        match = original(item)
        candidate = ContentKnowledgeServiceCandidate(
            card=service_card,
            matched_terms=["operat wodnoprawny", "pozwolenie zintegrowane"],
        )
        candidates = [
            candidate,
            *[
                existing
                for existing in match.service_candidates
                if existing.card.id != _SERVICE_CARD_ID
            ],
        ]
        return match.model_copy(
            update={
                "service_card": None,
                "recommended_service_card_id": _SERVICE_CARD_ID,
                "service_candidates": candidates,
                "buyer_problem_cards": [],
            }
        )

    monkeypatch.setattr(snapshot_selection, "match_content_knowledge_cards", nonauto_match)
    monkeypatch.setattr(generated_proposal_module, "match_content_knowledge_cards", nonauto_match)


def _patch_operat_service_profile(
    monkeypatch: pytest.MonkeyPatch,
    cards: tuple[object, ...],
) -> None:
    card = next(item for item in cards if getattr(item, "id", None) == _SERVICE_CARD_ID)
    approved_fact = source_facts_module.ekologus_seed_source_facts()[0].model_copy(
        update={
            "source_id": "source_fact_operat_current",
            "review_status": "approved",
            "reviewer": "Wilku",
            "target_card_id": _SERVICE_CARD_ID,
            "target_card_title": card.title,
            "evidence_ids": ["ev_content_service_profile_source_facts"],
            "source_connectors": ["public_site"],
        }
    )
    approved_facts = (approved_fact,)
    monkeypatch.setattr(dynamic_input_module, "ekologus_source_facts", lambda: approved_facts)
    monkeypatch.setattr(input_sources_module, "ekologus_source_facts", lambda: approved_facts)
    profile = service_profile_module.content_service_profile_response()
    sections = [
        section.model_copy(
            update={
                "status": "approved_current",
                "status_label": "zatwierdzona i aktualna",
                "source_fact_ids": [approved_fact.source_id],
                "evidence_ids": ["ev_content_service_profile_source_facts"],
                "source_connector_labels": ["public_site"],
                "freshness_label": "źródło aktualne",
            }
        )
        if section.card_id == _SERVICE_CARD_ID
        else section
        for section in profile.service_sections
    ]
    monkeypatch.setattr(
        service_profile_module,
        "content_service_profile_response",
        lambda: profile.model_copy(update={"service_sections": sections}),
    )


def _authority(
    decision: object,
    freshness_assessment: object,
) -> ContentRefreshPreparationAuthority:
    def snapshot_loader(
        work_item_id: str,
        service_card_id: str | None,
    ) -> object:
        assert work_item_id == _TARGET_WORK_ITEM_ID
        return workspace_api.build_content_work_item_snapshot_response_from_selected_decision(
            decision,
            freshness_assessment=freshness_assessment,
            service_card_id_override=service_card_id,
        )

    return ContentRefreshPreparationAuthority(
        store=content_workflow_store(),
        snapshot_loader=snapshot_loader,  # type: ignore[arg-type]
        proposal_store=content_planning_proposal_store(),
    )


def _client(authority: ContentRefreshPreparationAuthority) -> TestClient:
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    register_content_planning_proposal_routes(
        router,
        snapshot_loader=snapshot_for_work_item_or_404,
        refresh_authority_factory=lambda: authority,
    )
    register_content_initial_draft_route(
        router,
        snapshot_loader=snapshot_for_work_item_or_404,
        refresh_authority_factory=lambda: authority,
    )
    app.include_router(router)
    return TestClient(app)


def _authorize(client: TestClient, ready: dict[str, Any]) -> dict[str, str]:
    classification = cast(dict[str, Any], ready["classification"])
    response = client.post(
        f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/refresh-preparation/authorizations",
        json={
            "expected_production_classification_run_digest": classification[
                "classification_run_digest"
            ],
            "expected_production_classification_decision_set_digest": classification[
                "decision_set_digest"
            ],
            "expected_production_classification_source_packet_row_digest": classification[
                "source_packet_row_digest"
            ],
            "expected_planning_input_digest": ready["planning_input_digest"],
            "service_card_id": _SERVICE_CARD_ID,
            "authorized_by": "wilku",
            "acknowledged_classification_blocker_codes": classification[
                "classification_blocker_codes"
            ],
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, str], response.json()["authorization"])


def _generate_and_poll_plan(
    client: TestClient,
    ready: dict[str, Any],
    authorization: dict[str, str],
) -> dict[str, Any]:
    response = client.post(
        f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": _SERVICE_CARD_ID,
            "expected_planning_input_digest": ready["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    for _ in range(100):
        body = cast(dict[str, Any], response.json())
        if response.status_code != 200 or body.get("status") != "generating":
            assert response.status_code == 200, response.text
            assert body["status"] in {"created", "idempotent", "ready"}, body
            return cast(dict[str, Any], body["proposal"])
        time.sleep(0.02)
        response = client.get(f"/api/content/work-items/{_TARGET_WORK_ITEM_ID}/planning-proposals")
    raise AssertionError("Authorized non-auto plan did not finish within the focused poll window.")


def _refresh_run_for_target():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "canonical_path": "/analiza-pozwolen-zintegrowanych",
            "public_url": _TARGET_URL,
            "current_work_item_id": _TARGET_WORK_ITEM_ID,
            "decision": "refresh",
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    rows = tuple(sorted((row, run.rows[1]), key=lambda item: item.canonical_path))
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts(rows),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=rows,
        audit=run.audit,
    )
