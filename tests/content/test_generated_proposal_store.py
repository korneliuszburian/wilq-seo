from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.planning import (
    ContentPlanningPageAssets,
    ContentPlanningProposal,
    ContentPlanningSection,
)


def _proposal(*, service_card_id: str, version: int) -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id="content_work_item_multi_service",
        planning_digest=f"{version:064x}",
        proposal_id=f"proposal-{service_card_id}",
        proposal_version=version,
        planning_input_digest=f"{version + 10:064x}",
        final_canonical_url="https://ekologus.pl/test/",
        service_card_id=service_card_id,
        target_reader="firma",
        buyer_problem="brak porządku",
        buyer_trigger="zmiana wymagań",
        search_intent="informational",
        cta_direction="skonsultuj sytuację",
        sections=[
            ContentPlanningSection(
                heading="Najważniejsze pytanie",
                purpose="Odpowiedzieć na pytanie firmy.",
            )
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Nie ma dokładnych danych Ads.",
        ),
        page_assets=ContentPlanningPageAssets(title="Test"),
    )


def test_stale_queued_generation_can_be_reenqueued(
    tmp_path: Path,
) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite3")
    digest = "a" * 64
    response = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="content_work_item_demo",
        service_card_id="ekologus_service_demo",
        planning_input_digest=digest,
        safe_next_step="Plan jest przygotowywany.",
    )

    assert store.latest_generation_response(response.work_item_id) is None
    assert (
        store.enqueue_pending(
            work_item_id=response.work_item_id,
            service_card_id=response.service_card_id or "",
            planning_input_digest=digest,
            response=response,
        )
        == "queued"
    )
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            UPDATE content_planning_generation_jobs
            SET updated_at = ?
            WHERE work_item_id = ?
            """,
            (
                (datetime.now(UTC) - timedelta(minutes=3)).isoformat(),
                response.work_item_id,
            ),
        )

    assert (
        store.enqueue_pending(
            work_item_id=response.work_item_id,
            service_card_id=response.service_card_id or "",
            planning_input_digest=digest,
            response=response,
        )
        == "queued"
    )
    queued = store.queued_response(
        response.work_item_id,
        response.service_card_id or "",
        digest,
    )
    assert queued is not None
    assert queued.status == "generating"
    assert queued.planning_input_digest == digest
    latest = store.latest_generation_response(response.work_item_id)
    assert latest is not None
    assert latest.status == "generating"
    assert latest.planning_input_digest == digest


def test_identical_inflight_generation_is_claimed_once(tmp_path: Path) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite3")
    response = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="content_work_item_concurrent",
        service_card_id="ekologus_service_demo",
        safe_next_step="Plan jest przygotowywany.",
    )
    arguments = {
        "work_item_id": response.work_item_id,
        "service_card_id": response.service_card_id or "",
        "planning_input_digest": "b" * 64,
        "response": response,
    }

    def enqueue() -> str:
        return store.enqueue_pending(**arguments)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _item: enqueue(), range(2)))

    assert sorted(outcomes) == ["existing", "queued"]


def test_latest_can_be_scoped_to_service_card(tmp_path: Path) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite3")
    first = _proposal(service_card_id="service-a", version=1)
    second = _proposal(service_card_id="service-b", version=2)
    with store._connect() as connection:
        for proposal in (first, second):
            connection.execute(
                """
                INSERT INTO content_planning_proposals (
                  proposal_id, work_item_id, proposal_version, service_card_id,
                  planning_input_digest, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.work_item_id,
                    proposal.proposal_version,
                    proposal.service_card_id,
                    proposal.planning_input_digest,
                    "2026-07-17T00:00:00+00:00",
                    json.dumps(proposal.model_dump(mode="json"), sort_keys=True),
                ),
            )

    assert store.latest(first.work_item_id).service_card_id == "service-b"
    assert store.latest(first.work_item_id, service_card_id="service-a").service_card_id == (
        "service-a"
    )
