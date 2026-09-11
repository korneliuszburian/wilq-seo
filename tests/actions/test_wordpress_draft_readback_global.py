from __future__ import annotations

from collections.abc import Callable

import pytest

from wilq.actions.wordpress_draft_readback import last_created_wordpress_draft_readback
from wilq.connectors.wordpress.client import WordPressDraftPostReadback
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
)
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE
from wilq.schemas import (
    ActionMode,
    ActionMutationAuditRecord,
    ActionObject,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def _binding() -> ContentDraftRevisionBinding:
    return ContentDraftRevisionBinding(
        work_item_id="work_item_content_dev_global_readback",
        handoff_id="wordpress_draft_handoff_content_dev_global_readback_revision",
        revision_id="revision_content_dev_global_readback",
        content_digest="c" * 64,
        draft_package_id="draft_package_content_dev_global_readback",
        draft_package_digest="d" * 64,
        planning_digest="e" * 64,
        approval_decision_id="decision_content_dev_global_readback",
        final_canonical_url="https://ekologus.pl/content-dev-global-readback/",
    )


def _action_and_audit(
    binding: ContentDraftRevisionBinding,
) -> tuple[ActionObject, ActionMutationAuditRecord]:
    action = ActionObject(
        id="act_content_dev_global_readback",
        title="Utwórz szkic dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.applied,
        evidence_ids=["ev_content_dev_global_readback"],
        human_diagnosis="Testowy create-only content draft.",
        recommended_reason="Sprawdź zapisany readback.",
        payload={"action_type": CONTENT_DEV_DRAFT_ACTION_TYPE},
        validation_status="valid",
        created_by="operator_test",
    )
    audit = ActionMutationAuditRecord(
        id="mutation_content_dev_global_readback",
        action_id=action.id,
        connector="wordpress_ekologus",
        action_type=CONTENT_DEV_DRAFT_ACTION_TYPE,
        status="applied",
        adapter_reached=True,
        external_write_attempted=True,
        mutation_attempted=True,
        mutation_adapter="content_dev_draft_execution_boundary",
        actor="operator_test",
        audit_event_id="audit_content_dev_global_readback",
        wordpress_draft_binding=binding,
        summary="Utworzono jeden szkic dev.",
    )
    return action, audit


def _execution(binding: ContentDraftRevisionBinding) -> ContentWordPressDraftExecutionResult:
    return ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        wordpress_post_id="1901",
        endpoint="posts",
        external_write_attempted=True,
        expected_content_digest="a" * 64,
        observed_content_digest="a" * 64,
    )


def _readback(content_digest: str, calls: list[str]) -> Callable[..., WordPressDraftPostReadback]:
    def read(
        post_id: str,
        *,
        endpoint: str = "posts",
    ) -> WordPressDraftPostReadback:
        calls.append(f"{endpoint}:{post_id}")
        return WordPressDraftPostReadback(
            post_id=post_id,
            endpoint=endpoint,
            status="draft",
            title="Utwórz szkic dev",
            link="https://ekologus.dev.proudsite.pl/?p=1901",
            edit_link="https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=1901&action=edit",
            modified_gmt="2026-09-11T10:00:00",
            content_summary="Nie ujawniaj treści w response.",
            content_word_count=2,
            acf_field_count=0,
            acf_field_names=[],
            content_digest=content_digest,
            acf_digest="f" * 64,
        )

    return read


def test_global_readback_supports_content_dev_action_without_second_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "global_readback.sqlite3"))
    binding = _binding()
    action, audit = _action_and_audit(binding)
    content_workflow_store().save_wordpress_draft_execution(
        binding.work_item_id,
        _execution(binding),
    )
    calls: list[str] = []
    monkeypatch.setattr(
        "wilq.content.workflow.pipeline_steps.stage_activation.read_wordpress_draft_post",
        _readback("a" * 64, calls),
    )

    result = last_created_wordpress_draft_readback(action, [audit])

    assert result is not None
    assert result.status == "available"
    assert result.wordpress_post_id == "1901"
    assert result.content_digest == "a" * 64
    assert calls == ["posts:1901"]


def test_global_readback_blocks_content_dev_digest_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "global_readback_mismatch.sqlite3"))
    binding = _binding()
    action, audit = _action_and_audit(binding)
    content_workflow_store().save_wordpress_draft_execution(
        binding.work_item_id,
        _execution(binding),
    )
    calls: list[str] = []
    monkeypatch.setattr(
        "wilq.content.workflow.pipeline_steps.stage_activation.read_wordpress_draft_post",
        _readback("b" * 64, calls),
    )

    result = last_created_wordpress_draft_readback(action, [audit])

    assert result is not None
    assert result.status == "blocked"
    assert [blocker.code for blocker in result.blockers] == [
        "wordpress_draft_content_mismatch"
    ]
    assert calls == ["posts:1901"]
