import json
import time
from dataclasses import replace
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.inventory_binding as inventory_binding
from apps.api.wilq_api.routers import content_workflow as content_workflow_router
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content.dynamic_planning_test_support import PlanningClient, configure_planning_harness
from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.workflow.documents.revision_children import (
    build_child_draft_revision_command,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
    ContentDraftRevisionState,
)
from wilq.content.workflow.pipeline_steps.snapshot_assembly import (
    _revision_context_is_current,
)
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

ARTICLE_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
WORK_ITEM_ID = inventory_work_item_id(ARTICLE_URL)


class EditorialPlanningClient(PlanningClient):
    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        operation = json.loads(request.application_context)["operation"]
        context = json.loads(request.untrusted_context)
        planning_input = context.get("planning_input")
        if isinstance(planning_input, dict) and planning_input.get("content_kind") == "editorial":
            planning_input.setdefault("confirmed_service_card_id", None)
            planning_input.setdefault("service_label", None)
            proposal = context.get("approved_planning_proposal")
            if isinstance(proposal, dict):
                proposal.setdefault("service_label", "Artykuł bazy wiedzy")
            request = replace(
                request,
                untrusted_context=json.dumps(context, ensure_ascii=False),
            )
        result = super().run_structured_turn(request)
        if result.output_text is None or operation != "propose_content_plan":
            return result
        output = json.loads(result.output_text)
        output["content_kind"] = "editorial"
        output["service_card_id"] = None
        return replace(result, output_text=json.dumps(output, ensure_ascii=False))


def _editorial_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> tuple[TestClient, EditorialPlanningClient]:
    client, _service_runtime = configure_planning_harness(monkeypatch, tmp_path)
    runtime = EditorialPlanningClient()
    monkeypatch.setattr(
        "apps.api.wilq_api.routers.content_codex_runtime.content_codex_app_server_client",
        lambda: runtime,
    )
    monkeypatch.setattr(
        "apps.api.wilq_api.routers.content_initial_draft.content_codex_app_server_client",
        lambda: runtime,
    )
    catalog = inventory_binding.build_content_inventory_catalog()
    monkeypatch.setattr(
        inventory_binding,
        "build_content_inventory_catalog",
        lambda: catalog.model_copy(
            update={
                "items": [
                    item.model_copy(update={"content_type": "post"})
                    if item.work_item_id == WORK_ITEM_ID
                    else item
                    for item in catalog.items
                ]
            }
        ),
    )
    return client, runtime


def _assert_editorial_child_save(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    revision: dict[str, Any],
) -> None:
    edited_sections = revision["sections"]
    assert isinstance(edited_sections, list)
    assert isinstance(edited_sections[0], dict)
    edited_sections[0]["body_markdown"] += "\n\nZmiana redakcyjna."
    edited_sections[0]["content_html"] += "<p>Zmiana redakcyjna.</p>"
    child = build_child_draft_revision_command(
        ContentDraftRevision.model_validate(revision),
        sections=[
            ContentDraftRevisionSection.model_validate(section) for section in edited_sections
        ],
        proposal_metadata=None,
        created_by="wilku",
    )
    assert child.content_kind == "editorial"
    assert child.service_card_id is None
    evidence_ids = list(
        dict.fromkeys(
            evidence_id
            for section in revision["sections"]
            for evidence_id in section["evidence_ids"]
        )
    )
    reviewed = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/draft-revisions/"
        f"{revision['revision_id']}/review",
        json={
            "expected_revision_digest": revision["content_digest"],
            "reviewed_by": "wilku",
            "decision": "needs_changes",
            "notes": "Sprawdzono dokładną zapisaną wersję editorial.",
            "checked_items": ["tekst", "dowody", "CTA"],
            "evidence_ids": evidence_ids,
        },
    )
    assert reviewed.status_code == 200, reviewed.json()
    assert reviewed.json()["workspace"]["context_current"] is True
    assert reviewed.json()["workspace"]["can_save"] is True
    monkeypatch.setattr(
        content_workflow_router,
        "_validate_revision_sections",
        lambda *_args, **_kwargs: None,
    )
    saved = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/draft-revisions",
        json={
            "base_revision_id": revision["revision_id"],
            "title": revision["title"],
            "sections": edited_sections,
            "created_by": "wilku",
        },
    )
    assert saved.status_code == 200, saved.json()
    assert saved.json()["revision"]["content_kind"] == "editorial"
    assert saved.json()["revision"]["schema_version"] == "wilq_content_draft_revision_v2"
    assert saved.json()["revision"]["service_card_id"] is None
    assert saved.json()["revision"]["service_digest"] is None
    assert saved.json()["workspace"]["context_current"] is True
    assert saved.json()["workspace"]["can_review"] is True


def _assert_v1_subject_compatibility(revision_payload: dict[str, Any]) -> None:
    snapshot = snapshot_for_work_item_or_404(WORK_ITEM_ID)
    package = snapshot.draft_package.draft_package_result.draft_package
    assert package is not None
    revision = ContentDraftRevision.model_validate(revision_payload)

    def is_current(
        candidate: ContentDraftRevision,
        *,
        item_kind: Literal["service", "editorial", "ambiguous"],
        service_id: str | None,
    ) -> bool:
        return _revision_context_is_current(
            item=snapshot.preflight.item.model_copy(update={"content_kind": item_kind}),
            draft_package=package,
            state=ContentDraftRevisionState(
                status="unreviewed",
                revision_count=1,
                latest_revision=candidate,
            ),
            planning_digest=revision.planning_digest,
            planning_input_digest=revision.planning_input_digest,
            service_card_id=service_id,
        )

    v1_without_service = revision.model_copy(
        update={
            "schema_version": "wilq_content_draft_revision_v1",
            "content_kind": "service",
            "service_card_id": None,
            "service_digest": None,
        }
    )
    assert is_current(v1_without_service, item_kind="editorial", service_id=None) is False
    assert is_current(v1_without_service, item_kind="service", service_id=None) is False
    assert is_current(v1_without_service, item_kind="ambiguous", service_id=None) is False

    service_id = "ekologus_service_legacy"
    v1_service = v1_without_service.model_copy(update={"service_card_id": service_id})
    assert is_current(v1_service, item_kind="service", service_id=service_id) is True
    assert is_current(v1_service, item_kind="ambiguous", service_id=service_id) is True


def test_editorial_request_generates_persists_and_reads_without_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, runtime = _editorial_harness(monkeypatch, tmp_path)

    before = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")
    assert before.status_code == 200
    assert before.json()["content_kind"] == "editorial"
    assert before.json()["service_card_id"] is None

    stale = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": "0" * 64,
            "requested_by": "wilku",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "stale"
    assert stale.json()["content_kind"] == "editorial"

    response = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    for _ in range(200):
        if response.json().get("status") != "generating":
            break
        time.sleep(0.05)
        response = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "idempotent"}, response.json().get("blockers")
    assert response.json()["content_kind"] == "editorial"
    assert response.json()["proposal"]["content_kind"] == "editorial"
    assert response.json()["proposal"]["service_card_id"] is None
    assert runtime.calls == 1

    repeated = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["content_kind"] == "editorial"
    assert runtime.calls == 1

    proposal = response.json()["proposal"]
    draft = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/initial-draft",
        json={
            "expected_proposal_id": proposal["proposal_id"],
            "expected_planning_digest": proposal["planning_digest"],
            "expected_planning_input_digest": proposal["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    for _ in range(200):
        if draft.json().get("status") != "generating":
            break
        time.sleep(0.05)
        draft = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/initial-draft")
    assert draft.json()["status"] in {"created", "idempotent"}, draft.json()["blockers"][0][
        "source_codes"
    ]
    assert draft.json()["revision"] is not None
    _assert_v1_subject_compatibility(draft.json()["revision"])
    _assert_editorial_child_save(client, monkeypatch, draft.json()["revision"])


def test_editorial_terminal_failure_preserves_content_kind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, runtime = _editorial_harness(monkeypatch, tmp_path)
    runtime.fail = True
    before = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    response = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    for _ in range(200):
        if response.json().get("status") != "generating":
            break
        time.sleep(0.05)
        response = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    assert response.json()["status"] == "failed"
    assert response.json()["content_kind"] == "editorial"
    assert response.json()["service_card_id"] is None
