from __future__ import annotations

import pytest

from wilq.actions import service as action_service
from wilq.actions.payloads import validate_action_payload
from wilq.actions.service import get_action
from wilq.content.workflow.new_page_apply_capability import new_page_apply_binding
from wilq.content.workflow.new_page_document import ContentNewPageDeliveryReadiness
from wilq.content.workflow.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
    ContentNewPageDraftActionCommand,
    create_new_page_draft_action,
    load_new_page_draft_action,
    persist_new_page_draft_action,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionPreviewRequest,
    ActionReviewRequest,
)


def _ready_readiness() -> ContentNewPageDeliveryReadiness:
    return ContentNewPageDeliveryReadiness(
        status="ready_for_action",
        work_item_id="content_work_item_new_page_test",
        brief_id="content_new_page_brief_test",
        brief_digest="c" * 64,
        foundation_id="content_new_page_foundation_test",
        service_card_id="service_environment",
        service_card_digest="d" * 64,
        revision_id="content_revision_new_page_test",
        revision_digest="a" * 64,
        allowed_content_types=["page"],
        authoring_profile_digest="b" * 64,
        evidence_ids=["ev_wordpress_authoring_profile"],
        safe_next_step="Wybierz obserwowany typ nowego szkicu.",
    )


def _command(**changes: object) -> ContentNewPageDraftActionCommand:
    values: dict[str, object] = {
        "expected_revision_digest": "a" * 64,
        "expected_authoring_profile_digest": "b" * 64,
        "content_type": "page",
        "requested_by": "Wilku",
    }
    values.update(changes)
    return ContentNewPageDraftActionCommand.model_validate(values)


def test_new_page_draft_action_binds_an_explicit_observed_type_without_vendor_write() -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())

    assert action.payload["action_type"] == CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE
    assert action.payload["mode"] == "dev_draft_only"
    assert action.payload["new_page_draft_binding"] == {
        "work_item_id": "content_work_item_new_page_test",
        "brief_id": "content_new_page_brief_test",
        "brief_digest": "c" * 64,
        "foundation_id": "content_new_page_foundation_test",
        "service_card_id": "service_environment",
        "service_card_digest": "d" * 64,
        "revision_id": "content_revision_new_page_test",
        "revision_digest": "a" * 64,
        "authoring_profile_digest": "b" * 64,
        "content_type": "page",
    }
    assert action.payload["destructive"] is False
    assert action.payload["apply_allowed"] is False
    assert action.payload["api_mutation_ready"] is False
    assert action.status.value == "needs_validation"


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (_command(expected_revision_digest="c" * 64), "inną rewizję"),
        (_command(expected_authoring_profile_digest="c" * 64), "inny profil"),
        (_command(content_type="post"), "nie należy do obserwowanych"),
    ],
)
def test_new_page_draft_action_fails_closed_when_the_ready_binding_changes(
    command: ContentNewPageDraftActionCommand,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        create_new_page_draft_action(_ready_readiness(), command)


def test_new_page_draft_action_persists_only_its_local_creation_event(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-action.sqlite3"))
    action = create_new_page_draft_action(_ready_readiness(), _command())

    persisted = persist_new_page_draft_action(action)

    assert persisted.id == action.id
    assert load_new_page_draft_action(action.id) == persisted
    assert get_action(action.id).id == action.id


def test_new_page_draft_action_payload_requires_exact_lineage() -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())

    assert validate_action_payload(action.connector, action.payload) == []
    action.payload["new_page_draft_binding"] = {
        "revision_id": action.payload["new_page_draft_binding"]["revision_id"]
    }

    assert validate_action_payload(action.connector, action.payload)


def test_new_page_action_records_local_review_gates_without_a_vendor_write() -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())

    assert action_service.validate_action(action).valid
    assert (
        action_service.preview_action(action, ActionPreviewRequest(requested_by="Wilku")).status
        == "blocked"
    )
    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="Wilku",
            notes="Zatwierdzono przygotowanie nowego szkicu.",
        ),
    )
    assert action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="Wilku",
            notes="Potwierdzam lokalny łańcuch akcji.",
            preview_acknowledged=True,
        ),
    ).confirmed
    assert (
        action_service.impact_check_action(
            action,
            ActionImpactCheckRequest(
                checked_by="Wilku",
                notes="Sprawdzono gotowość do przyszłego szkicu dev.",
            ),
        ).status
        == "blocked"
    )
    assert action.status.value != "applied"


def test_new_page_apply_binding_must_match_the_persisted_action() -> None:
    action = create_new_page_draft_action(_ready_readiness(), _command())
    binding = action.payload["new_page_draft_binding"]

    accepted, blockers = new_page_apply_binding(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=binding),
    )
    assert accepted is not None
    assert blockers == []
    changed = {**binding, "revision_digest": "f" * 64}
    _, blockers = new_page_apply_binding(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="Wilku", new_page_draft=changed),
    )
    assert [blocker.code for blocker in blockers] == ["new_page_revision_binding_mismatch"]
