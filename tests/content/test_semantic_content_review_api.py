from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_semantic_review as semantic_review_router
from apps.api.wilq_api.routers import content_snapshot as content_snapshot_router
from tests.content.dynamic_planning_test_support import PlanningClient
from tests.content.test_dynamic_planning_proposals_api import (
    BDO_WORK_ITEM_ID,
    OUTSOURCING_WORK_ITEM_ID,
    _approve_and_generate,
    _approve_generated_plan,
    _initial_draft_request,
    _snapshot,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.initial_full_draft_turn import (
    compact_initial_draft_planning_input,
)
from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.quality import semantic_review_store as semantic_review_store_module
from wilq.content.quality.semantic_review_turn import semantic_review_output_schema
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.storage.local_state import local_state_store

pytest_plugins = ("tests.content.test_dynamic_planning_proposals_api",)


def test_semantic_runtime_uses_a_separate_bounded_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_SEMANTIC_REVIEW_CODEX_TIMEOUT_SECONDS", "211")
    monkeypatch.setattr(
        semantic_review_router,
        "content_codex_app_server_client",
        lambda: StdioCodexAppServerClient(),
    )

    client = semantic_review_router._semantic_codex_client()

    assert isinstance(client, StdioCodexAppServerClient)
    assert client.timeout_seconds == 211.0


def test_semantic_output_schema_requires_defaulted_properties_for_codex() -> None:
    revision = ContentDraftRevision.model_construct(sections=[])
    schema = semantic_review_output_schema(revision)

    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema["$defs"].values():
        if not isinstance(definition, dict) or "properties" not in definition:
            continue
        assert set(definition["required"]) == set(definition["properties"])


def test_full_draft_model_envelope_is_compact_but_digest_bound(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    del client, runtime, proposal
    snapshot = content_snapshot_router.snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    service_card_id = snapshot.service_profile_context.service_card_id
    assert service_card_id is not None
    result = build_content_planning_input(snapshot, service_card_id=service_card_id)
    assert result.planning_input is not None
    full = result.planning_input.model_dump(mode="json")
    compact = compact_initial_draft_planning_input(result.planning_input)
    assert compact["planning_input_digest"] == full["planning_input_digest"]
    assert compact["inventory"] == full["inventory"]
    assert len(json.dumps(compact, ensure_ascii=False)) < len(
        json.dumps(full, ensure_ascii=False)
    )


def test_semantic_review_is_exact_persisted_advisory_for_both_services(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    expected_calls = 0
    for work_item_id in (BDO_WORK_ITEM_ID, OUTSOURCING_WORK_ITEM_ID):
        proposal = _approve_and_generate(
            client, runtime, work_item_id, expected_calls=expected_calls
        )
        expected_calls += 1
        _approve_generated_plan(client, work_item_id, proposal)
        initial = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=_initial_draft_request(proposal),
        ).json()
        assert initial["status"] == "created", initial["blockers"]
        expected_calls += 1
        revision = initial["revision"]
        path = _semantic_review_path(work_item_id, revision["revision_id"])

        assert client.get(path).json()["status"] == "not_generated"
        assert runtime.calls == expected_calls
        stale = client.post(
            path,
            json={"expected_revision_digest": "0" * 64, "requested_by": "wilku"},
        )
        assert stale.status_code == 409
        assert stale.json()["blockers"][0]["code"] == "stale_revision"
        assert runtime.calls == expected_calls
        created = client.post(
            path,
            json={
                "expected_revision_digest": revision["content_digest"],
                "requested_by": "wilku",
            },
        )
        assert created.status_code == 200, created.json()
        body = created.json()
        assert body["status"] == "created", body["blockers"]
        assert body["review"]["revision_digest"] == revision["content_digest"]
        assert body["review"]["criteria_version"] == "wilq_semantic_content_review_v1"
        assert body["review"]["status"] == "needs_changes"
        assert body["review"]["findings"][0]["affected_targets"] == [
            revision["sections"][0]["section_id"]
        ]
        assert body["review"]["human_review_required"] is True
        assert body["review"]["action_object_created"] is False
        assert body["publish_ready"] is False
        expected_calls += 1
        repeated = client.post(
            path,
            json={
                "expected_revision_digest": revision["content_digest"],
                "requested_by": "wilku",
            },
        )
        assert repeated.json()["status"] == "idempotent"
        assert repeated.json()["review"]["review_id"] == body["review"]["review_id"]
        ready = client.get(path)
        assert ready.json()["status"] == "ready"
        assert ready.json()["review"] == body["review"]
        assert runtime.calls == expected_calls
        assert _snapshot(client, work_item_id)["revision_workspace"][
            "latest_revision"
        ] == revision


def test_semantic_review_runtime_failure_leaves_no_partial_review(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    revision = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    ).json()["revision"]
    path = _semantic_review_path(BDO_WORK_ITEM_ID, revision["revision_id"])
    runtime.fail = True

    failed = client.post(
        path,
        json={
            "expected_revision_digest": revision["content_digest"],
            "requested_by": "wilku",
        },
    )

    assert failed.json()["status"] == "failed"
    calls_after_failure = runtime.calls
    terminal = client.get(path).json()
    assert terminal["status"] == "failed"
    assert terminal["blockers"][0]["code"] == "runtime_failed"
    assert runtime.calls == calls_after_failure


def test_semantic_review_rejects_external_attempt_without_partial_review(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    revision = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    ).json()["revision"]
    path = _semantic_review_path(BDO_WORK_ITEM_ID, revision["revision_id"])
    runtime.semantic_external_call_attempted = True

    blocked = client.post(
        path,
        json={
            "expected_revision_digest": revision["content_digest"],
            "requested_by": "wilku",
        },
    )

    assert blocked.json()["status"] == "blocked"
    assert blocked.json()["blockers"][0]["code"] == "runtime_blocked"
    assert blocked.json()["runtime"]["external_call_attempted"] is True
    calls_after_blocker = runtime.calls
    assert client.get(path).json()["status"] == "not_generated"
    assert runtime.calls == calls_after_blocker


def test_semantic_review_real_store_requires_maintenance_before_model(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    revision = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    ).json()["revision"]
    store_path = local_state_store().path
    monkeypatch.setattr(semantic_review_store_module, "DEFAULT_STATE_DB", store_path)
    calls_before = runtime.calls

    blocked = client.post(
        _semantic_review_path(BDO_WORK_ITEM_ID, revision["revision_id"]),
        json={
            "expected_revision_digest": revision["content_digest"],
            "requested_by": "wilku",
        },
    )

    assert blocked.json()["status"] == "blocked"
    assert blocked.json()["blockers"][0]["code"] == "storage_activation_required"
    assert runtime.calls == calls_before
    read_blocked = client.get(
        _semantic_review_path(BDO_WORK_ITEM_ID, revision["revision_id"])
    )
    assert read_blocked.json()["status"] == "blocked"
    assert read_blocked.json()["blockers"][0]["code"] == "storage_activation_required"
    with sqlite3.connect(store_path) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_semantic_reviews",),
        ).fetchone()
    assert table is None


def test_semantic_finding_section_id_drives_only_a_human_selected_child_revision(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    base_revision = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    ).json()["revision"]
    review = client.post(
        _semantic_review_path(BDO_WORK_ITEM_ID, base_revision["revision_id"]),
        json={
            "expected_revision_digest": base_revision["content_digest"],
            "requested_by": "wilku",
        },
    ).json()["review"]
    selected_section_id = review["findings"][0]["affected_targets"][0]
    selected_section = next(
        section
        for section in base_revision["sections"]
        if section["section_id"] == selected_section_id
    )
    human_review = client.post(
        _revision_review_path(BDO_WORK_ITEM_ID, base_revision["revision_id"]),
        json={
            "expected_revision_digest": base_revision["content_digest"],
            "reviewed_by": "wilku",
            "decision": "needs_changes",
            "notes": "Człowiek wybrał finding i sekcję do poprawy.",
            "checked_items": ["exact revision", "dowody", "advisory finding"],
            "evidence_ids": selected_section["evidence_ids"],
        },
    )
    assert human_review.status_code == 200, human_review.json()

    result = client.post(
        _section_proposal_path(BDO_WORK_ITEM_ID, base_revision["revision_id"]),
        json={
            "expected_base_digest": base_revision["content_digest"],
            "selected_section_ids": [selected_section_id],
            "requested_by": "wilku",
        },
    )

    assert result.status_code == 200, result.json()
    body = result.json()
    assert body["status"] == "created", body["blockers"]
    assert body["selected_section_headings"] == [selected_section["heading"]]
    child = body["revision"]
    assert child["base_revision_id"] == base_revision["revision_id"]
    assert child["sections"][0]["section_id"] == selected_section_id
    assert child["sections"][0]["body_markdown"] != selected_section["body_markdown"]
    for field in ("page_assets", "faq", "cta_blocks", "internal_links"):
        assert child[field] == base_revision[field]
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    assert snapshot["revision_workspace"]["status"] == "unreviewed"
    assert snapshot["revision_workspace"]["latest_review"] is None
    stale_child_review = client.get(
        _semantic_review_path(BDO_WORK_ITEM_ID, child["revision_id"])
    ).json()
    assert stale_child_review["status"] == "stale"
    assert stale_child_review["revision_id"] == base_revision["revision_id"]
    assert stale_child_review["revision_digest"] == base_revision["content_digest"]
    assert stale_child_review["review"]["review_id"] == review["review_id"]
    child_review = client.post(
        _semantic_review_path(BDO_WORK_ITEM_ID, child["revision_id"]),
        json={
            "expected_revision_digest": child["content_digest"],
            "requested_by": "wilku",
        },
    ).json()
    assert child_review["status"] == "created"
    assert child_review["review"]["revision_id"] == child["revision_id"]
    historical_review = client.get(
        _semantic_review_path(BDO_WORK_ITEM_ID, base_revision["revision_id"])
    ).json()
    assert historical_review["status"] == "stale"
    assert historical_review["review"]["review_id"] == review["review_id"]


def _semantic_review_path(work_item_id: str, revision_id: str) -> str:
    return (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/semantic-review"
    )


def _revision_review_path(work_item_id: str, revision_id: str) -> str:
    return f"/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review"


def _section_proposal_path(work_item_id: str, revision_id: str) -> str:
    return (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/codex-proposal"
    )
