from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content.dynamic_planning_test_support import (
    PlanningClient,
    configure_planning_harness,
)
from wilq.codex.app_server import CodexAppServerTurnBlocker, StdioCodexAppServerClient
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.handoff.revision_document_renderer import revision_document_markdown
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputSummary,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal import (
    _planning_output_quality_errors,
    _planning_runtime_blocker,
    generate_content_planning_proposal,
    read_content_planning_proposal,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningCtaBlock,
    ContentPlanningModelOutput,
    ContentPlanningModelSection,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment
from wilq.content.planning.runtime_contract import (
    planning_codex_timeout_seconds,
    planning_job_stale_after_seconds,
)
from wilq.content.workflow.catalog import inventory_work_item_id
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.schemas import CodexRun
from wilq.storage.local_state import local_state_store

BDO_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
OUTSOURCING_URL = (
    "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
)
BDO_WORK_ITEM_ID = inventory_work_item_id(BDO_URL)
OUTSOURCING_WORK_ITEM_ID = inventory_work_item_id(OUTSOURCING_URL)


class _FailingPlanningStore(ContentPlanningProposalStore):
    def save_generated(
        self,
        proposal: ContentPlanningProposal,
        completed_run: CodexRun,
    ) -> tuple[Literal["created", "idempotent"], ContentPlanningProposal]:
        raise RuntimeError("synthetic persistence failure")


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    return configure_planning_harness(monkeypatch, tmp_path)


def test_dynamic_planning_proposals_are_two_case_and_idempotent(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    generated = {
        work_item_id: _approve_and_generate(
            client,
            runtime,
            work_item_id,
            expected_calls=index,
        )
        for index, work_item_id in enumerate((BDO_WORK_ITEM_ID, OUTSOURCING_WORK_ITEM_ID))
    }
    assert runtime.calls == 2
    assert generated[BDO_WORK_ITEM_ID]["service_card_id"] == ("ekologus_service_bdo_reporting")
    assert generated[OUTSOURCING_WORK_ITEM_ID]["service_card_id"] == (
        "ekologus_service_environmental_consulting_outsourcing"
    )
    assert generated[BDO_WORK_ITEM_ID]["angle"] != generated[OUTSOURCING_WORK_ITEM_ID]["angle"]
    assert all(
        proposal["internal_links"][0]["target_url"]
        == "https://www.ekologus.pl/kontakt"
        for proposal in generated.values()
    )
    assert generated[BDO_WORK_ITEM_ID]["source_material_ids"]
    assert generated[BDO_WORK_ITEM_ID]["knowledge_card_ids"]
    assert all(
        "source_material_ids" in section and "knowledge_card_ids" in section
        for section in generated[BDO_WORK_ITEM_ID]["sections"]
    )


def test_dynamic_planning_rejects_a_plan_without_cta(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    runtime.planning_cta_blocks = False
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    before = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()

    result = _post_planning(
        client,
        BDO_WORK_ITEM_ID,
        _generation_request(service_card_id, before["planning_input_digest"]),
    )

    assert result.status_code == 200
    assert result.json()["status"] == "blocked"
    blocker = result.json()["blockers"][0]
    assert blocker["code"] == "quality_gate_failed"
    assert "missing_cta" in blocker["source_codes"]
    assert "bloku CTA" in blocker["reason"]
    assert runtime.calls == 1


def test_explicit_plan_request_confirms_only_service_selection(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    assert snapshot["planning_workspace"]["scope_current"] is False
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    before = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert before.json()["status"] == "not_generated", before.json()

    generated = _post_planning(
        client,
        BDO_WORK_ITEM_ID,
        _generation_request(service_card_id, before.json()["planning_input_digest"]),
    )

    assert generated.status_code == 200
    assert generated.json()["status"] in {"ready", "idempotent"}, generated.json()
    assert runtime.calls == 1
    current = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert current.json()["status"] == "ready", current.json()
    after = _snapshot(client, BDO_WORK_ITEM_ID)
    assert after["planning_workspace"]["proposal"]["proposal_id"] == generated.json()[
        "proposal"
    ]["proposal_id"]
    assert after["planning_workspace"]["scope_current"] is False
    assert after["planning_workspace"]["section_map_current"] is False


def test_executor_submission_failure_is_typed_and_retryable(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    input_state = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()
    digest = input_state["planning_input_digest"]

    class FailingExecutor:
        calls = 0

        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            self.calls += 1
            raise RuntimeError("executor unavailable")

    executor = FailingExecutor()
    monkeypatch.setattr(planning_router, "_PLANNING_GENERATION_EXECUTOR", executor)
    request = _generation_request(service_card_id, digest)

    first = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=request,
    )
    assert first.status_code == 200
    assert first.json()["status"] == "failed"
    assert first.json()["planning_input_digest"] == digest
    assert first.json()["service_card_id"] == service_card_id
    assert first.json()["blockers"][0]["code"] == "runtime_failed"
    monkeypatch.setattr(
        planning_router,
        "read_content_planning_proposal",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("pending GET must not rebuild the snapshot")
        ),
    )
    status = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert status.json()["status"] == "failed"
    second = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=request,
    )
    assert second.status_code == 200
    assert second.json()["status"] == "failed"
    assert executor.calls == 2


def test_planning_runtime_has_separate_bounded_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_PLANNING_CODEX_TIMEOUT_SECONDS", "17")
    monkeypatch.setattr(
        planning_router,
        "content_codex_app_server_client",
        lambda: StdioCodexAppServerClient(),
    )

    client = planning_router._planning_codex_client()

    assert isinstance(client, StdioCodexAppServerClient)
    assert client.timeout_seconds == 17


def test_planning_store_blocks_a_sibling_digest_while_generation_is_in_flight(
    tmp_path: Path,
) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite")
    source_names = (
        "wordpress", "service_profile", "gsc", "ga4", "google_ads",
        "ahrefs", "keyword_planner", "merchant", "localo", "social",
    )
    summary = ContentPlanningInputSummary(
        final_canonical_url="https://example.test/page",
        service_label="Test service",
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="missing",
        source_assessments=[
            ContentPlanningSourceAssessment(source=name, status="not_applicable", reason="test")
            for name in source_names
        ],
        source_fact_count=0,
        evidence_id_count=0,
        knowledge_card_count=0,
    )
    first = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="work-item",
        service_card_id="service-card",
        planning_input_digest="a" * 64,
        input_summary=summary,
        safe_next_step="Poczekaj na zakończenie generowania.",
        runtime=ContentCodexRuntimeTrace(
            status="not_started",
            run_id="planning_generation_first",
        ),
    )
    second = first.model_copy(
        update={
            "planning_input_digest": "b" * 64,
            "runtime": ContentCodexRuntimeTrace(
                status="not_started", run_id="planning_generation_second"
            ),
        }
    )

    assert store.enqueue_pending(
        work_item_id="work-item",
        service_card_id="service-card",
        planning_input_digest="a" * 64,
        response=first,
    ) == "queued"
    assert store.enqueue_pending(
        work_item_id="work-item",
        service_card_id="service-card",
        planning_input_digest="b" * 64,
        response=second,
    ) == "in_flight"
    active = store.active_generation_response(
        "work-item",
        "service-card",
        excluding_digest="b" * 64,
    )
    assert active is not None
    assert active.runtime.run_id == "planning_generation_first"


def test_planning_api_returns_typed_blocker_for_a_sibling_generation(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    current = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()

    class HoldingExecutor:
        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    monkeypatch.setattr(planning_router, "_PLANNING_GENERATION_EXECUTOR", HoldingExecutor())
    first = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=_generation_request(service_card_id, current["planning_input_digest"]),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "generating"

    second = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=_generation_request(service_card_id, "b" * 64),
    )
    assert second.status_code == 200
    assert second.json()["status"] == "blocked"
    assert second.json()["blockers"][0]["code"] == "runtime_blocked"
    assert second.json()["runtime"]["run_id"] == first.json()["runtime"]["run_id"]


def test_planning_runtime_default_allows_full_structured_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WILQ_PLANNING_CODEX_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(
        planning_router,
        "content_codex_app_server_client",
        lambda: StdioCodexAppServerClient(),
    )

    client = planning_router._planning_codex_client()

    assert isinstance(client, StdioCodexAppServerClient)
    assert client.timeout_seconds == 180.0


def test_planning_stale_window_shares_configured_codex_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_PLANNING_CODEX_TIMEOUT_SECONDS", "17")

    assert planning_codex_timeout_seconds() == 17.0
    assert planning_job_stale_after_seconds() == 17.0


def test_planning_runtime_stream_failure_has_operator_safe_next_step() -> None:
    blocker = _planning_runtime_blocker(
        [
            CodexAppServerTurnBlocker(
                "codex_response_stream_disconnected", "ignored"
            ).code
        ]
    )

    assert blocker == (
        "Połączenie z Codexem zostało przerwane",
        "Provider Codexa przerwał strumień odpowiedzi przed końcem tury; "
        "WILQ nie otrzymał bezpiecznego planu.",
        "Sprawdź status app-servera i połączenie, a potem uruchom nową próbę; "
        "WILQ nic nie zapisał.",
    )


def test_planning_output_quality_gate_rejects_navigation_and_dated_headings() -> None:
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Poniżej przedstawiamy często zadawane pytania dotyczące BDO"
            ),
            ContentPlanningModelSection.model_construct(
                heading='13 marca 2020 „Gospodarka opakowaniami”'
            ),
            ContentPlanningModelSection.model_construct(
                heading="Powiązane materiały o gospodarce odpadami"
            ),
        ],
        cta_blocks=[ContentPlanningCtaBlock.model_construct()],
    )

    assert _planning_output_quality_errors(output) == [
        "heading_presentation_noise",
        "heading_dated_event_noise",
        "heading_related_content_noise",
    ]


def test_changed_input_can_enqueue_replan_when_older_proposal_exists(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(
        client,
        runtime,
        BDO_WORK_ITEM_ID,
        expected_calls=0,
    )
    assert proposal["planning_input_digest"]

    class CaptureExecutor:
        submitted = 0

        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            self.submitted += 1

    executor = CaptureExecutor()
    monkeypatch.setattr(planning_router, "_PLANNING_GENERATION_EXECUTOR", executor)
    changed_digest = "f" * 64
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=_generation_request(
            proposal["service_card_id"],
            changed_digest,
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "generating"
    assert response.json()["planning_input_digest"] == changed_digest
    assert executor.submitted == 1

def test_dynamic_planning_rejects_an_unknown_document_placement(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    planning_digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    approved = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-review",
        json={
            "stage": "scope",
            "service_card_id": service_card_id,
            "expected_planning_digest": planning_digest,
            "decision": "approved",
            "reviewed_by": "wilku",
            "checked_items": ["strona", "usługa", "intencja", "CTA"],
            "notes": "Syntetyczny proof zatwierdzonej karty.",
        },
    )
    assert approved.status_code == 200
    planning_input = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()
    runtime.planning_placement = "gdzieś obok formularza"

    result = _post_planning(
        client,
        BDO_WORK_ITEM_ID,
        _generation_request(service_card_id, planning_input["planning_input_digest"]),
    )

    assert result.status_code == 200
    assert result.json()["status"] == "blocked"
    assert result.json()["blockers"][0]["code"] == "invalid_structured_output"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None


@pytest.mark.parametrize(
    ("mutation", "expected_source_code"),
    [
        ("target", "link_target:https://example.com/kontakt"),
        ("evidence", "link_inventory_evidence:https://www.ekologus.pl/kontakt"),
        ("claim", "link_claim:https://www.ekologus.pl/kontakt"),
    ],
)
def test_dynamic_planning_rejects_internal_link_outside_exact_lineage(
    planning_harness: tuple[TestClient, PlanningClient],
    mutation: str,
    expected_source_code: str,
) -> None:
    client, runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    planning_digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    approved = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-review",
        json={
            "stage": "scope",
            "service_card_id": service_card_id,
            "expected_planning_digest": planning_digest,
            "decision": "approved",
            "reviewed_by": "wilku",
            "checked_items": ["strona", "usługa", "intencja", "CTA"],
            "notes": "Syntetyczny proof linkowania.",
        },
    )
    assert approved.status_code == 200
    planning_input = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()
    if mutation == "target":
        runtime.planning_link_target = "https://example.com/kontakt"
    elif mutation == "evidence":
        runtime.planning_link_evidence_ids = ["ev_unknown"]
    else:
        runtime.planning_link_claim_ids = ["claim_unknown"]

    result = _post_planning(
        client,
        BDO_WORK_ITEM_ID,
        _generation_request(service_card_id, planning_input["planning_input_digest"]),
    )

    assert result.status_code == 200
    assert result.json()["status"] == "blocked"
    assert result.json()["blockers"][0]["code"] == "lineage_mismatch"
    assert expected_source_code in result.json()["blockers"][0]["source_codes"]
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None


def test_dynamic_planning_input_change_is_stale_and_runtime_fails_closed(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    generated = _approve_and_generate(
        client,
        runtime,
        BDO_WORK_ITEM_ID,
        expected_calls=0,
    )
    latest_snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    changed_item = latest_snapshot.preflight.item.model_copy(
        update={"wordpress_content_summary": "Zmienione exact inventory."}
    )
    changed_snapshot = latest_snapshot.model_copy(
        update={"preflight": latest_snapshot.preflight.model_copy(update={"item": changed_item})}
    )
    changed_input = build_content_planning_input(
        changed_snapshot,
        service_card_id="ekologus_service_bdo_reporting",
    ).planning_input
    assert changed_input is not None
    stale_read = read_content_planning_proposal(
        snapshot=changed_snapshot,
        store=content_planning_proposal_store(),
    )
    assert stale_read.status == "stale"

    runtime.fail = True
    failed = generate_content_planning_proposal(
        snapshot=changed_snapshot,
        request=ContentPlanningProposalRequest(
            service_card_id="ekologus_service_bdo_reporting",
            expected_planning_input_digest=changed_input.planning_input_digest,
            requested_by="wilku",
        ),
        client=runtime,
        store=content_planning_proposal_store(),
        run_store=local_state_store(),
    )
    assert failed.status == "failed"
    assert failed.runtime.run_id
    assert failed.runtime.run_id.startswith("codex_content_planning_")
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) == (
        generated_proposal_from(generated)
    )
    runtime.fail = False
    persistence_failed = generate_content_planning_proposal(
        snapshot=changed_snapshot,
        request=ContentPlanningProposalRequest(
            service_card_id="ekologus_service_bdo_reporting",
            expected_planning_input_digest=changed_input.planning_input_digest,
            requested_by="wilku",
        ),
        client=runtime,
        store=_FailingPlanningStore(content_planning_proposal_store().path),
        run_store=local_state_store(),
    )
    assert persistence_failed.status == "failed"
    assert persistence_failed.runtime.run_id
    assert persistence_failed.runtime.run_id.startswith("codex_content_planning_")
    assert persistence_failed.blockers[0].code == "persistence_failed"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) == (
        generated_proposal_from(generated)
    )


def test_initial_full_draft_uses_the_same_atomic_contract_for_both_services(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    revisions: dict[str, dict[str, Any]] = {}
    expected_calls = 0
    for work_item_id in (BDO_WORK_ITEM_ID, OUTSOURCING_WORK_ITEM_ID):
        proposal = _approve_and_generate(
            client,
            runtime,
            work_item_id,
            expected_calls=expected_calls,
        )
        expected_calls += 1
        _approve_generated_plan(client, work_item_id, proposal)
        stale_request = _initial_draft_request(proposal)
        stale_request["expected_planning_digest"] = "0" * 64
        stale = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=stale_request,
        )
        assert stale.status_code == 409
        assert stale.json()["blockers"][0]["code"] == "proposal_mismatch"
        assert runtime.calls == expected_calls
        created = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=_initial_draft_request(proposal),
        )
        assert created.status_code == 200, created.json()
        payload = cast(dict[str, Any], created.json())
        assert payload["status"] == "created", payload["blockers"][0]["source_codes"]
        revision = cast(dict[str, Any], payload["revision"])
        assert revision["schema_version"] == "wilq_content_draft_revision_v2"
        assert revision["publish_ready"] is False
        assert revision["proposal_metadata"]["review_scope"] == (
            "persisted_full_document_and_declared_lineage"
        )
        assert revision["planning_input_digest"] == proposal["planning_input_digest"]
        assert revision["service_card_id"] == proposal["service_card_id"]
        assert all(section["evidence_ids"] for section in revision["sections"])
        assert revision["internal_links"][0]["target_url"] == (
            "https://www.ekologus.pl/kontakt"
        )
        rendered = revision_document_markdown(ContentDraftRevision.model_validate(revision))
        assert "[Kontakt z Ekologus](https://www.ekologus.pl/kontakt)" in rendered
        assert runtime.calls == expected_calls + 1
        expected_calls += 1
        repeated = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=_initial_draft_request(proposal),
        )
        assert repeated.status_code == 409
        assert repeated.json()["blockers"][0]["code"] == "revision_already_exists"
        assert runtime.calls == expected_calls
        revisions[work_item_id] = revision

    assert revisions[BDO_WORK_ITEM_ID]["page_assets"]["h1"] != (
        revisions[OUTSOURCING_WORK_ITEM_ID]["page_assets"]["h1"]
    )


def test_initial_full_draft_rejects_unstructured_or_unsafe_links(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    malicious_outputs = (
        ("initial_link_anchor_text", "Kontakt](https://example.com/phish)[dalej"),
        (
            "initial_link_target_url",
            "https://www.ekologus.pl/kontakt) [phish](https://example.com",
        ),
        ("initial_section_body_markdown", "Treść [phish](https://example.com)."),
        (
            "initial_section_body_markdown",
            '<a\thref\t=\t"//example.com/phish">kliknij</a>',
        ),
        (
            "initial_section_body_markdown",
            "[phish]: //example.com/phish\nKliknij [phish]",
        ),
    )

    for runtime_field, malicious_value in malicious_outputs:
        setattr(runtime, runtime_field, malicious_value)
        result = client.post(
            f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
            json=_initial_draft_request(proposal),
        )
        setattr(runtime, runtime_field, None)

        assert result.status_code == 200
        assert result.json()["status"] == "blocked"
        assert result.json()["blockers"][0]["code"] == "invalid_structured_output"
        assert _snapshot(client, BDO_WORK_ITEM_ID)["revision_workspace"][
            "latest_revision"
        ] is None


def test_initial_full_draft_runtime_failure_writes_no_partial_revision_and_get_is_model_free(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    runtime.fail = True
    failed = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed", failed.json()
    calls_after_failure = runtime.calls
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    assert snapshot["revision_workspace"]["latest_revision"] is None
    assert runtime.calls == calls_after_failure


def _approve_and_generate(
    client: TestClient,
    runtime: PlanningClient,
    work_item_id: str,
    *,
    expected_calls: int,
) -> dict[str, Any]:
    snapshot = _snapshot(client, work_item_id)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    planning_digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    approved = client.post(
        f"/api/content/work-items/{work_item_id}/planning-review",
        json={
            "stage": "scope",
            "service_card_id": service_card_id,
            "expected_planning_digest": planning_digest,
            "decision": "approved",
            "reviewed_by": "wilku",
            "checked_items": ["strona", "usługa", "intencja", "CTA"],
            "notes": "Syntetyczny proof zatwierdzonej karty.",
        },
    )
    assert approved.status_code == 200
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert before.status_code == 200
    assert before.json()["status"] == "not_generated", before.json()["blockers"]
    input_summary = before.json()["input_summary"]
    assert len(input_summary["source_assessments"]) == 10
    gsc_assessment = next(
        item for item in input_summary["source_assessments"] if item["source"] == "gsc"
    )
    assert gsc_assessment["status"] == "used"
    assert gsc_assessment["landing_match_tiers"]
    assert input_summary["evidence_id_count"] > 0
    assert runtime.calls == expected_calls
    if expected_calls == 0:
        assert not _planning_table_exists()
    input_digest = before.json()["planning_input_digest"]
    unknown = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request("ekologus_service_unknown", input_digest),
    )
    assert unknown.status_code == 422
    assert unknown.json()["blockers"][0]["code"] == "unknown_service_card"
    stale = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, "0" * 64),
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "stale"
    assert stale.json().get("planning_input_digest") in {None, input_digest}
    created = _post_planning(
        client,
        work_item_id,
        _generation_request(service_card_id, input_digest),
    )
    assert created.status_code == 200
    assert created.json()["status"] in {"ready", "idempotent"}, [
        (blocker.get("code"), blocker.get("source_codes"), blocker.get("reason"))
        for blocker in created.json().get("blockers", [])
    ]
    assert created.json()["proposal"]["input_schema_version"] == (
        "wilq_content_planning_input_v6"
    )
    repeated = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, input_digest),
    )
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["proposal"]["proposal_id"] == created.json()["proposal"]["proposal_id"]
    ready = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert ready.json()["status"] == "ready"
    assert ready.json()["proposal"] == created.json()["proposal"]
    assert ready.json()["input_summary"] == input_summary
    return cast(dict[str, Any], created.json()["proposal"])


def _post_planning(
    client: TestClient,
    work_item_id: str,
    request: dict[str, str],
) -> Any:
    response = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=request,
    )
    if response.status_code == 200 and response.json().get("status") == "generating":
        for _ in range(200):
            time.sleep(0.05)
            response = client.get(
                f"/api/content/work-items/{work_item_id}/planning-proposals"
            )
            if response.json().get("status") != "generating":
                break
    return response


def _snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _approve_generated_plan(
    client: TestClient,
    work_item_id: str,
    proposal: dict[str, Any],
) -> None:
    for stage in ("scope", "section_map"):
        response = client.post(
            f"/api/content/work-items/{work_item_id}/planning-review",
            json={
                "stage": stage,
                "service_card_id": proposal["service_card_id"] if stage == "scope" else None,
                "expected_planning_digest": proposal["planning_digest"],
                "decision": "approved",
                "reviewed_by": "wilku",
                "checked_items": ["strona", "usługa", "intencja", "sekcje", "CTA"],
                "notes": "Syntetyczne zatwierdzenie aktualnego planu.",
            },
        )
        assert response.status_code == 200, response.json()


def _initial_draft_request(proposal: dict[str, Any]) -> dict[str, str]:
    return {
        "expected_proposal_id": proposal["proposal_id"],
        "expected_planning_digest": proposal["planning_digest"],
        "expected_planning_input_digest": proposal["planning_input_digest"],
        "requested_by": "wilku",
    }


def _generation_request(service_card_id: str, digest: str) -> dict[str, str]:
    return {
        "service_card_id": service_card_id,
        "expected_planning_input_digest": digest,
        "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
        "requested_by": "wilku",
    }


def generated_proposal_from(payload: dict[str, Any]) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_validate(payload)


def _planning_table_exists() -> bool:
    path = content_planning_proposal_store().path
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_planning_proposals",),
        ).fetchone()
    return row is not None
