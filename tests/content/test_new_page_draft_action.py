from __future__ import annotations

import pytest

from wilq.content.workflow.new_page_document import ContentNewPageDeliveryReadiness
from wilq.content.workflow.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
    ContentNewPageDraftActionCommand,
    create_new_page_draft_action,
)


def _ready_readiness() -> ContentNewPageDeliveryReadiness:
    return ContentNewPageDeliveryReadiness(
        status="ready_for_action",
        work_item_id="content_work_item_new_page_test",
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
