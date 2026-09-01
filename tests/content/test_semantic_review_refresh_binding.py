from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.api.wilq_api.routers import content_workflow as content_workflow_router


def test_refresh_bound_semantic_review_snapshot_uses_persisted_service_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_refresh"
    binding = SimpleNamespace(
        service_card_id="ekologus_service_operat_wodnoprawny",
        planning_input_digest="a" * 64,
        authorization_id="content_refresh_preparation_authorization_test",
        authorization_digest="b" * 64,
    )
    revision = SimpleNamespace(refresh_preparation_binding=binding)
    expected_snapshot = object()
    canonical_calls: list[tuple[str, object | None, str | None, bool | None]] = []

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda received_work_item_id: SimpleNamespace(
                latest_revision=revision if received_work_item_id == work_item_id else None
            )
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(resolve_planning=lambda *_args: object()),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda received_work_item_id, **kwargs: (
            canonical_calls.append(
                (
                    received_work_item_id,
                    kwargs.get("revision_state_override"),
                    kwargs.get("service_card_id_override"),
                    kwargs.get("prefer_revision_bound_proposal"),
                )
            )
            or expected_snapshot
        ),
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    assert result is expected_snapshot
    assert len(canonical_calls) == 1
    assert canonical_calls[0][0] == work_item_id
    assert canonical_calls[0][1] is not None
    assert canonical_calls[0][2] == binding.service_card_id
    assert canonical_calls[0][3] is True


def test_legacy_semantic_review_snapshot_keeps_default_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_legacy"
    expected_snapshot = object()

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=SimpleNamespace(refresh_preparation_binding=None)
            )
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda received_work_item_id, **_kwargs: (
            expected_snapshot if received_work_item_id == work_item_id else None
        ),
    )

    assert (
        content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)
        is expected_snapshot
    )


def test_refresh_bound_editorial_snapshot_prefers_revision_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_editorial"
    revision_state = SimpleNamespace(
        latest_revision=SimpleNamespace(
            refresh_preparation_binding=SimpleNamespace(service_card_id=None)
        )
    )
    expected_snapshot = object()
    observed_kwargs: dict[str, object] = {}
    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(load_draft_revision_state=lambda _work_item_id: revision_state),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id, **kwargs: observed_kwargs.update(kwargs) or expected_snapshot,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    assert result is expected_snapshot
    assert observed_kwargs == {
        "revision_state_override": revision_state,
        "service_card_id_override": None,
        "prefer_revision_bound_proposal": True,
    }
