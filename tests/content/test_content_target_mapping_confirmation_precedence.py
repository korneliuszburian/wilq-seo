from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.content.test_content_target_mapping_persistence import (
    _confirmation_row_count,
    _corrupt_latest_record,
    _insert_legacy_confirmation,
    _preview_and_command,
    _RouteStore,
)
from wilq.content.workflow.store import store_target_mapping
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.target import dev_draft_action
from wilq.content.workflow.target.target_mapping_persistence import (
    ContentTargetMappingPersistenceError,
)


def test_confirmation_never_skips_newer_legacy_or_corrupt_revision_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, _, _, preview, command = _preview_and_command()
    store = ContentWorkflowStore(tmp_path / "newer-legacy.sqlite3")
    first = store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    newer_preview = preview.model_copy(update={"binding_digest": "e" * 64}, deep=True)
    newer_command = command.model_copy(
        update={"expected_binding_digest": "e" * 64, "confirmed_by": "Jan Kowalski"}
    )
    newer_legacy_id = _insert_legacy_confirmation(
        store,
        preview=newer_preview,
        command=newer_command,
        confirmation_number=2,
        created_at="3000-01-01T00:00:00+00:00",
        require_empty=False,
    )

    state = store.load_target_mapping_draft_state(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )
    assert state is not None
    assert state.status == "legacy_confirmation"
    assert state.confirmation.confirmation_id == newer_legacy_id

    _corrupt_latest_record(store.path, "unknown_version")
    with pytest.raises(ContentTargetMappingPersistenceError):
        store.record_target_mapping_confirmation(
            work_item_id=revision.work_item_id,
            preview=preview,
            command=command,
        )
    _insert_legacy_confirmation(
        store,
        preview=newer_preview,
        command=newer_command,
        confirmation_number=3,
        created_at="3000-01-02T00:00:00+00:00",
        require_empty=False,
    )
    monkeypatch.setattr(
        store_target_mapping,
        "utc_now",
        lambda: datetime(3001, 1, 1, tzinfo=UTC),
    )
    created = store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    assert created.status == "created"
    assert created.confirmation.confirmation_id != first.confirmation.confirmation_id
    assert _confirmation_row_count(store.path) == 4

    _corrupt_latest_record(store.path, "unknown_version")
    with pytest.raises(ContentTargetMappingPersistenceError):
        store.load_target_mapping_draft_state(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
        )


def test_live_action_preview_rejects_newer_legacy_or_corrupt_revision_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, review, discovery, preview, command = _preview_and_command()
    store = _RouteStore(
        tmp_path / "action-newer-legacy.sqlite3",
        revision=revision,
        review=review,
    )
    store.record_target_mapping_confirmation(
        work_item_id=revision.work_item_id,
        preview=preview,
        command=command,
    )
    newer_preview = preview.model_copy(update={"binding_digest": "e" * 64}, deep=True)
    _insert_legacy_confirmation(
        store,
        preview=newer_preview,
        command=command.model_copy(update={"expected_binding_digest": "e" * 64}),
        confirmation_number=2,
        created_at="3000-01-01T00:00:00+00:00",
        require_empty=False,
    )
    monkeypatch.setattr(dev_draft_action, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        dev_draft_action,
        "build_content_target_discovery",
        lambda work_item_id: discovery,
    )

    current = dev_draft_action.current_content_target_draft_preview(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    )
    assert current.status == "blocked"
    assert current.confirmation is None
    assert current.blockers[0].code == "mapping_not_confirmed"

    _corrupt_latest_record(store.path, "unknown_version")
    with pytest.raises(ContentTargetMappingPersistenceError):
        dev_draft_action.current_content_target_draft_preview(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
        )
