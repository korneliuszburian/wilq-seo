from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_semantic_review as semantic_review_router
from apps.api.wilq_api.routers import content_snapshot as content_snapshot_router
from tests.content.dynamic_planning_test_support import PlanningClient
from tests.content.test_dynamic_planning_proposals_api import (
    BDO_WORK_ITEM_ID,
    OUTSOURCING_WORK_ITEM_ID,
    _generate_plan,
    _initial_draft_request,
    _snapshot,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.initial_full_draft_turn import (
    compact_initial_draft_planning_input,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
)
from wilq.content.quality import semantic_review_store as semantic_review_store_module
from wilq.content.quality.semantic_review_contracts import (
    CONTENT_SEMANTIC_DIMENSIONS,
    ContentSemanticDimensionAssessment,
    ContentSemanticReviewModelOutput,
)
from wilq.content.quality.semantic_review_service import (
    _apply_deterministic_quality_guards,
    _SemanticInputs,
)
from wilq.content.quality.semantic_review_turn import (
    compact_semantic_review_planning_input,
    compact_semantic_review_proposal,
    semantic_review_output_schema,
    semantic_review_turn_request,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionSection
from wilq.schemas import CodexRun
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


def test_semantic_turn_exposes_exact_allowed_targets_to_the_reviewer() -> None:
    revision = ContentDraftRevision.model_construct(
        work_item_id="content_work_item_exact",
        revision_id="content_revision_exact",
        content_digest="a" * 64,
        planning_input_digest="b" * 64,
        sections=[
            ContentDraftRevisionSection(
                section_id="section_exact_01",
                heading="Zakres współpracy",
                body_markdown="Zakres jest opisany konkretnie.",
                evidence_ids=["ev_exact"],
            )
        ]
    )

    request = semantic_review_turn_request(
        revision=revision,
        planning_input=ContentPlanningInput.model_construct(),
        proposal=ContentPlanningProposal.model_construct(),
    )

    context = json.loads(request.application_context)
    assert context["allowed_targets"] == [
        "page_assets",
        "faq",
        "cta_blocks",
        "internal_links",
        "whole_document",
        "section_exact_01",
    ]
    assert context["allowed_evidence_ids"] == ["ev_exact"]
    assert "literalnych wartości z application_context.allowed_targets" in request.instruction
    assert "literalnych wartości z application_context.allowed_evidence_ids" in request.instruction
    assert "powtórzone akapity" in request.instruction
    assert "źródło wskazuje" in request.instruction
    assert "failure-mode mapping" in request.instruction
    assert "brak wymaganego CTA" in request.instruction


def test_semantic_quality_guards_cannot_waive_missing_cta_query_or_repetition() -> None:
    section = ContentDraftRevisionSection(
        section_id="section_exact_01",
        heading="BDO",
        body_markdown="Powtórzony tekst.",
        evidence_ids=["ev_exact"],
    )
    revision = ContentDraftRevision.model_construct(
        sections=[section, section.model_copy(update={"section_id": "section_exact_02"})],
        cta_blocks=[],
    )
    proposal = ContentPlanningProposal.model_construct(
        cta_blocks=[{"cta_id": "cta_required"}],
        sections=[
            SimpleNamespace(section_id="section_exact_01", query_terms=["bdo przedsiębiorca"])
        ],
    )
    output = ContentSemanticReviewModelOutput.model_construct(
        dimensions=[
            ContentSemanticDimensionAssessment(
                dimension=dimension,
                status="strong",
                reason="OK",
                affected_targets=["whole_document"],
            )
            for dimension in CONTENT_SEMANTIC_DIMENSIONS
        ],
        findings=[],
    )

    guarded = _apply_deterministic_quality_guards(
        _SemanticInputs(
            revision=revision,
            planning_input=ContentPlanningInput.model_construct(),
            proposal=proposal,
        ),
        output,
    )

    assert {finding.dimension for finding in guarded.findings} == {
        "conversion_clarity",
        "search_intent_fit",
        "repetition",
    }
    assert all(
        item.status == "needs_changes"
        for item in guarded.dimensions
        if item.dimension in {"conversion_clarity", "search_intent_fit", "repetition"}
    )


def test_queued_semantic_run_is_visible_before_worker_preflight() -> None:
    saved: list[object] = []

    def save(run: object) -> object:
        saved.append(run)
        return run

    store = SimpleNamespace(save_codex_run=save)
    revision = ContentDraftRevision.model_construct(
        work_item_id="content_work_item_exact",
        revision_id="content_revision_exact",
        planning_input_digest="b" * 64,
        sections=[
            ContentDraftRevisionSection(
                section_id="section_exact_01",
                heading="Zakres współpracy",
                body_markdown="Zakres jest opisany konkretnie.",
                evidence_ids=["ev_exact"],
            )
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )

    run = semantic_review_router._save_queued_semantic_run(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision=revision,
        run_id="codex_content_semantic_review_queued",
        store=store,
    )

    assert saved == [run]
    assert run.status == "started"
    assert run.planning_input_digest == revision.planning_input_digest
    assert run.evidence_ids == ["ev_exact"]


def test_stale_semantic_run_becomes_terminal_after_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = CodexRun(
        id="codex_content_semantic_review_old",
        hook="content_semantic_review",
        status="started",
        started_at=datetime.now(UTC) - timedelta(seconds=301),
        used_endpoints=[
            "/api/content/work-items/work/draft-revisions/revision/semantic-review"
        ],
    )
    saved: list[CodexRun] = []

    class Store:
        def list_codex_runs(self) -> list[CodexRun]:
            return [old]

        def save_codex_run(self, run: CodexRun) -> CodexRun:
            saved.append(run)
            return run

    monkeypatch.setattr(semantic_review_router, "local_state_store", lambda: Store())
    result = semantic_review_router._latest_semantic_run("work", "revision")

    assert result is not None
    assert result.status == "failed"
    assert result.error == "semantic_review_timeout"
    assert saved == [result]


def test_semantic_turn_exposes_regulatory_requirement_coverage() -> None:
    planning_input = ContentPlanningInput.model_construct(
        regulatory_coverage={
            "profile_id": "bdo_profile",
            "profile_version": "2026-08-03",
            "requirements": [
                {"id": "bdo_reporting", "label": "Sprawozdawczość"}
            ],
            "requirement_coverage": [
                {
                    "requirement_id": "bdo_reporting",
                    "source_fact_ids": ["fact_reporting"],
                    "evidence_ids": ["ev_reporting"],
                }
            ],
            "source_fact_ids": ["fact_reporting"],
            "evidence_ids": ["ev_reporting"],
            "source_facts": [],
        }
    )

    request = semantic_review_turn_request(
        revision=ContentDraftRevision.model_construct(
            work_item_id="content_work_item_exact",
            revision_id="content_revision_exact",
            content_digest="a" * 64,
            planning_input_digest="b" * 64,
            sections=[],
        ),
        planning_input=planning_input,
        proposal=ContentPlanningProposal.model_construct(),
    )

    context = json.loads(request.untrusted_context)
    assert context["planning_input"]["regulatory_coverage"]["profile_id"] == "bdo_profile"
    assert context["planning_input"]["regulatory_coverage"]["requirement_coverage"] == [
        {
            "requirement_id": "bdo_reporting",
            "source_fact_ids": ["fact_reporting"],
            "evidence_ids": ["ev_reporting"],
        }
    ]
    assert "regulatory_coverage.requirements" in request.instruction


def test_semantic_payload_keeps_regulatory_lineage_without_duplicate_page_telemetry() -> None:
    planning_input = ContentPlanningInput.model_construct(
        planning_input_digest="d" * 64,
        regulatory_coverage={
            "profile_id": "bdo_profile",
            "profile_version": "2026-08-03",
            "requirements": [{"id": "registration", "label": "Rejestracja"}],
            "requirement_coverage": [
                {
                    "requirement_id": "registration",
                    "source_fact_ids": ["fact_registration"],
                    "evidence_ids": ["ev_registration"],
                }
            ],
            "source_facts": [
                {
                    "source_id": "fact_registration",
                    "source_url_or_path": "https://bdo.mos.gov.pl/zasady-rejestracji/",
                    "extracted_fact": "Wymagany wpis zależy od działalności.",
                    "scope": "registration",
                    "freshness_date": "2026-08-03",
                    "review_status": "approved",
                    "evidence_ids": ["ev_registration"],
                    "regulatory_requirement_ids": ["registration"],
                    "official_source": True,
                }
            ],
        }
    )
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            {
                "section_id": "section_registration",
                "heading": "Kto podlega wpisowi?",
                "purpose": "Odpowiedź dla firmy",
                "reader_question": "Kogo dotyczy obowiązek?",
                "query_terms": ["kto musi mieć BDO"],
                "evidence_ids": ["ev_registration"],
                "regulatory_requirement_ids": ["registration"],
                "page_assets": {"should_not_be_forwarded": True},
            }
        ],
        page_assets=[{"should_not_be_forwarded": True}],
    )

    compact_input = compact_semantic_review_planning_input(planning_input)
    compact_proposal = compact_semantic_review_proposal(proposal)

    assert compact_input["regulatory_coverage"]["source_facts"][0]["evidence_ids"] == [
        "ev_registration"
    ]
    assert "page_assets" not in compact_proposal
    assert compact_proposal["sections"][0]["regulatory_requirement_ids"] == [
        "registration"
    ]
    assert "should_not_be_forwarded" not in json.dumps(
        compact_proposal, ensure_ascii=False
    )


def test_full_draft_model_envelope_is_compact_but_digest_bound(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _generate_plan(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
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
        proposal = _generate_plan(
            client, runtime, work_item_id, expected_calls=expected_calls
        )
        expected_calls += 1
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
        persisted_revision = _snapshot(client, work_item_id)["revision_workspace"][
            "latest_revision"
        ]
        assert persisted_revision["revision_id"] == revision["revision_id"]
        assert persisted_revision["content_digest"] == revision["content_digest"]


def test_semantic_review_runtime_failure_leaves_no_partial_review(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _generate_plan(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
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
    proposal = _generate_plan(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
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
    proposal = _generate_plan(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
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


def _semantic_review_path(work_item_id: str, revision_id: str) -> str:
    return (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/semantic-review"
    )


def _revision_review_path(work_item_id: str, revision_id: str) -> str:
    return f"/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review"
