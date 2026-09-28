from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from apps.api.wilq_api.routers.content_planning_proposals import (
    _legacy_unbound_refresh_reconciliation_status,
)
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.test_classified_refresh_generation_integration import (
    BDO_SERVICE_CARD_ID,
    BDO_URL,
    BDO_WORK_ITEM_ID,
    _app_client,
    _authority,
    _refresh_run,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationClassificationBinding,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas import CodexRun


def test_legacy_unbound_same_input_refresh_plan_requires_reconciliation_not_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    client = _app_client(_authority(store), monkeypatch)
    initial_status = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert initial_status.status_code == 200
    initial = cast(dict[str, Any], initial_status.json())
    planning_input_digest = cast(str, initial["planning_input_digest"])

    # Seed a synthetic historical record through the typed store. No model or
    # vendor generation occurred for this test fixture.
    created_at = datetime(2026, 9, 12, tzinfo=UTC)
    proposal_id = "proposal_historical_unbound_bdo_fixture"
    codex_run_id = "codex_run_historical_unbound_bdo_fixture"
    planning_digest = "a" * 64
    historical_proposal = ContentPlanningProposal(
        work_item_id=BDO_WORK_ITEM_ID,
        planning_digest=planning_digest,
        proposal_id=proposal_id,
        codex_run_id=codex_run_id,
        generation_status="codex_generated",
        planning_input_digest=planning_input_digest,
        content_kind="service",
        final_canonical_url=BDO_URL,
        service_card_id=BDO_SERVICE_CARD_ID,
        service_label="BDO",
        target_reader="Przedsiębiorca",
        buyer_problem="Syntetyczny historyczny plan fixture.",
        buyer_trigger="Test odczytu historycznego planu.",
        search_intent="informacyjny",
        cta_direction="Sprawdź kolejne kroki.",
        sections=[
            ContentPlanningSection(
                heading="Zakres",
                purpose="Syntetyczna sekcja wyłącznie do testu reconciliation.",
            )
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak danych popytowych w syntetycznym fixture.",
        ),
        created_at=created_at,
    )
    completed_run = CodexRun(
        id=codex_run_id,
        source="synthetic_test_fixture",
        status="completed",
        proposal_id=proposal_id,
        planning_digest=planning_digest,
        planning_input_digest=planning_input_digest,
        started_at=created_at,
        completed_at=created_at,
    )
    # Save before classification because the typed store rejects unbound saves
    # once a current refresh classification exists.
    seed_store = ContentPlanningProposalStore(store.path)
    save_outcome, seeded = seed_store.save_generated(historical_proposal, completed_run)
    assert save_outcome == "created"
    assert seeded.refresh_preparation_binding is None
    assert seeded.work_item_id == BDO_WORK_ITEM_ID
    assert seeded.service_card_id == BDO_SERVICE_CARD_ID
    assert seeded.planning_input_digest == planning_input_digest

    store.record_production_classification(_refresh_run())
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    )
    assert ready.status_code == 200, ready.text
    ready_body = cast(dict[str, Any], ready.json())
    assert ready_body["status"] == "ready_to_authorize"
    assert ready_body["work_item_id"] == seeded.work_item_id
    assert ready_body["service_candidate"]["service_card_id"] == seeded.service_card_id
    assert ready_body["planning_input_digest"] == seeded.planning_input_digest

    get_response = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")

    assert get_response.status_code == 200, get_response.text
    get_body = get_response.json()
    assert get_body["status"] == "blocked"
    assert get_body["proposal"] is None
    assert get_body["blockers"][0]["code"] == "refresh_preparation_proposal_binding_mismatch"
    assert "Nie ponawiaj" in get_body["blockers"][0]["reason"]
    assert runtime.calls == 0


def test_blocked_editorial_subject_still_does_not_reconcile_legacy_service() -> None:
    legacy = SimpleNamespace(
        refresh_preparation_binding=None,
        proposal=None,
        service_card_id=BDO_SERVICE_CARD_ID,
        planning_input_digest="a" * 64,
    )
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id="classification",
        classification_run_digest="a" * 64,
        decision_set_digest="b" * 64,
        source_packet_row_digest="c" * 64,
        current_work_item_id=BDO_WORK_ITEM_ID,
        canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
        public_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
    )
    service_mismatch = ContentRefreshPreparationBlocker(
        code="refresh_preparation_authorization_service_mismatch",
        label="Editorial nie przyjmuje usługi",
        reason="Bieżący subject jest editorial.",
        next_step="Użyj editorial subject.",
    )
    blocked = ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=BDO_WORK_ITEM_ID,
        classification=classification,
        blockers=[service_mismatch],
        safe_next_step=service_mismatch.next_step,
    )
    authority = SimpleNamespace(
        preview=lambda _work_item_id, *, service_card_id: (
            SimpleNamespace() if service_card_id is None else blocked
        )
    )

    assert (
        _legacy_unbound_refresh_reconciliation_status(
            store=SimpleNamespace(
                latest_generation_response=lambda _work_item_id: legacy
            ),
            work_item_id=BDO_WORK_ITEM_ID,
            authority=authority,
            inventory_binding_loader=lambda _work_item_id: SimpleNamespace(
                content_kind="editorial"
            ),
        )
        is None
    )


def test_legacy_service_plan_does_not_shadow_current_editorial_subject() -> None:
    legacy = SimpleNamespace(
        refresh_preparation_binding=None,
        proposal=None,
        service_card_id=BDO_SERVICE_CARD_ID,
        planning_input_digest="a" * 64,
    )
    store = SimpleNamespace(latest_generation_response=lambda _work_item_id: legacy)
    authority = SimpleNamespace(
        preview=lambda _work_item_id, *, service_card_id: SimpleNamespace(
            content_kind="editorial" if service_card_id is None else None
        )
    )

    assert (
        _legacy_unbound_refresh_reconciliation_status(
            store=store,
            work_item_id=BDO_WORK_ITEM_ID,
            authority=authority,
            inventory_binding_loader=lambda _work_item_id: SimpleNamespace(
                content_kind="editorial"
            ),
        )
        is None
    )
