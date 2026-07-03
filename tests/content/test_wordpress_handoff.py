from __future__ import annotations

from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    ContentWordPressDraftHandoffBlocker,
    apply_content_wordpress_draft_handoff_to_work_item,
    build_content_wordpress_draft_handoff,
    content_wordpress_draft_handoff_blockers,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBlocker,
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.models import ContentWorkItem


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
        "preflight_status": "handoff_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "sales_brief_bdo",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_package_status": "ready",
        "draft_package_id": "draft_package_bdo",
        "human_review_status": "approved",
        "human_review_id": "human_review_bdo",
        "audit_status": "recorded",
        "audit_id": "audit_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _draft_package(**overrides: object) -> ContentDraftPackage:
    payload: dict[str, object] = {
        "id": "draft_package_bdo",
        "work_item_id": "content_work_item_bdo",
        "brief_id": "sales_brief_bdo",
        "claim_ledger_id": "claim_ledger_bdo",
        "title": "BDO dla firm: co sprawdzić",
        "sections": [
            {
                "heading": "Kogo dotyczy BDO",
                "purpose": "Wyjaśnij, kiedy firma powinna sprawdzić obowiązki BDO.",
                "evidence_ids": ["ev_gsc_bdo"],
                "draft_notes": ["Nie obiecuj pełnej zgodności bez sprawdzenia sytuacji."],
            }
        ],
        "section_to_evidence_map": [
            {"section_heading": "Kogo dotyczy BDO", "evidence_ids": ["ev_gsc_bdo"]}
        ],
        "claims_used": ["Ekologus pomaga firmom w obowiązkach związanych z BDO."],
        "publish_ready": False,
    }
    payload.update(overrides)
    return ContentDraftPackage(**payload)


def _review(**overrides: object) -> ContentHumanReview:
    payload: dict[str, object] = {
        "id": "human_review_bdo",
        "work_item_id": "content_work_item_bdo",
        "stage": "wordpress_handoff",
        "reviewed_by": "wilku",
        "decision": "approved",
        "checked_items": ["draft package", "claimy", "final canonical"],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "draft_package_id": "draft_package_bdo",
    }
    payload.update(overrides)
    return ContentHumanReview(**payload)


def _audit(**overrides: object) -> ContentWordPressDraftAuditEnvelope:
    payload: dict[str, object] = {
        "audit_id": "audit_bdo",
        "actor": "wilku",
        "reason": "Przekazanie zatwierdzonego szkicu do WordPress jako draft.",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "human_review_id": "human_review_bdo",
    }
    payload.update(overrides)
    return ContentWordPressDraftAuditEnvelope(**payload)


def test_wordpress_handoff_blocks_without_approved_review_audit_and_final_url() -> None:
    item = _item(
        final_canonical_url=None,
        canonical_status="missing",
        human_review_status="needs_changes",
    )

    blockers = content_wordpress_draft_handoff_blockers(
        item=item,
        draft_package=_draft_package(),
        human_review=_review(decision="needs_changes"),
        audit=None,
    )

    assert "missing_final_canonical" in [blocker.code for blocker in blockers]
    assert "human_review_not_approved" in [blocker.code for blocker in blockers]
    _assert_operator_blockers_have_no_jargon(blockers)
    assert "missing_audit" in [blocker.code for blocker in blockers]


def test_wordpress_handoff_blocks_dev_preview_as_final_canonical() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.handoff is None
    assert "invalid_final_canonical" in [blocker.code for blocker in result.blockers]
    _assert_operator_blockers_have_no_jargon(result.blockers)


def test_wordpress_handoff_plan_is_draft_only_and_never_publish() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.blockers == []
    assert result.handoff is not None
    assert result.handoff.connector == "wordpress_ekologus"
    assert result.handoff.post_status == "draft"
    assert result.handoff.publish_allowed is False
    assert result.handoff.destructive_update_allowed is False
    assert result.handoff.final_canonical_url == "https://ekologus.pl/bdo/"
    assert result.handoff.preview_url == "https://ekologus.dev.proudsite.pl/bdo/"


def test_wordpress_handoff_requires_matching_draft_package() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(id="draft_package_other"),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.handoff is None
    assert "draft_package_mismatch" in [blocker.code for blocker in result.blockers]
    _assert_operator_blockers_have_no_jargon(result.blockers)


def test_wordpress_handoff_requires_audit_evidence_lineage() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(evidence_ids=["ev_gsc_bdo"]),
        audit=_audit(evidence_ids=["ev_other"]),
    )

    assert result.handoff is None
    assert "audit_evidence_mismatch" in [blocker.code for blocker in result.blockers]
    _assert_operator_blockers_have_no_jargon(result.blockers)


def test_wordpress_handoff_updates_workflow_as_prepared_or_created() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(wordpress_handoff_status="missing", wordpress_post_id=None),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert result.handoff is not None

    prepared = apply_content_wordpress_draft_handoff_to_work_item(_item(), result.handoff)
    created = apply_content_wordpress_draft_handoff_to_work_item(
        _item(),
        result.handoff,
        wordpress_post_id="123",
    )

    assert prepared.wordpress_handoff_status == "prepared"
    assert prepared.wordpress_post_id is None
    assert created.wordpress_handoff_status == "draft_created"
    assert created.wordpress_post_id == "123"


def test_wordpress_draft_execution_dry_run_returns_draft_only_payload() -> None:
    handoff_result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert handoff_result.handoff is not None

    result = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(),
    )

    assert result.status == "dry_run_ready"
    assert result.mode == "dry_run"
    assert result.boundary.allowed_operation == "create_wordpress_draft"
    assert result.boundary.dry_run_default is True
    assert result.boundary.live_write_enabled is False
    assert result.boundary.live_adapter_configured is False
    assert result.boundary.publish_allowed is False
    assert result.boundary.destructive_update_allowed is False
    assert result.external_write_attempted is False
    assert result.wordpress_post_id is None
    assert result.blockers == []
    assert result.payload is not None
    assert result.payload.post_status == "draft"
    assert result.payload.publish_allowed is False
    assert result.payload.destructive_update_allowed is False
    assert result.payload.title == "BDO dla firm: co sprawdzić"
    assert "# BDO dla firm: co sprawdzić" in result.payload.content_markdown
    assert "Kogo dotyczy BDO" in result.payload.content_markdown


def test_wordpress_draft_execution_blocks_missing_or_mismatched_inputs() -> None:
    handoff_result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert handoff_result.handoff is not None

    missing = execute_content_wordpress_draft_handoff(
        handoff=None,
        draft_package=None,
    )
    mismatched = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(id="draft_package_other"),
    )
    publish_ready = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(publish_ready=True),
    )

    assert {blocker.code for blocker in missing.blockers} == {
        "missing_handoff",
        "missing_draft_package",
    }
    assert [blocker.code for blocker in mismatched.blockers] == [
        "draft_package_mismatch"
    ]
    assert [blocker.code for blocker in publish_ready.blockers] == [
        "draft_package_marked_publish_ready"
    ]
    _assert_execution_blockers_have_no_jargon(
        [*missing.blockers, *mismatched.blockers, *publish_ready.blockers]
    )


def test_wordpress_draft_execution_blocks_live_write_without_enabled_adapter() -> None:
    handoff_result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert handoff_result.handoff is not None

    disabled = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(),
        mode="live",
    )
    missing_adapter = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(),
        mode="live",
        live_write_enabled=True,
    )
    missing_authorization = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(),
        mode="live",
        live_write_enabled=True,
        create_draft=lambda _payload: "123",
    )

    assert disabled.status == "blocked"
    assert [blocker.code for blocker in disabled.blockers] == ["live_write_not_enabled"]
    assert disabled.external_write_attempted is False
    assert [blocker.code for blocker in missing_adapter.blockers] == ["missing_live_adapter"]
    assert [blocker.code for blocker in missing_authorization.blockers] == [
        "missing_write_authorization"
    ]
    assert missing_authorization.external_write_attempted is False
    _assert_execution_blockers_have_no_jargon(
        [*disabled.blockers, *missing_adapter.blockers, *missing_authorization.blockers]
    )


def test_wordpress_draft_execution_live_mode_uses_explicit_adapter_only() -> None:
    handoff_result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert handoff_result.handoff is not None
    created_payload_titles: list[str] = []

    def create_draft(payload) -> str:  # type: ignore[no-untyped-def]
        assert payload.post_status == "draft"
        assert payload.publish_allowed is False
        assert payload.destructive_update_allowed is False
        created_payload_titles.append(payload.title)
        return "123"

    result = execute_content_wordpress_draft_handoff(
        handoff=handoff_result.handoff,
        draft_package=_draft_package(),
        mode="live",
        live_write_enabled=True,
        create_draft=create_draft,
        write_authorization=ContentWordPressDraftWriteAuthorization(
            action_id="act_prepare_wordpress_draft_handoff",
            preview_audit_id="audit_preview_123",
            review_audit_id="audit_review_123",
            confirmation_audit_id="audit_confirm_123",
            confirmed_by="wilku",
        ),
        write_authorization_verified=True,
    )

    assert result.status == "created"
    assert result.boundary.allowed_operation == "create_wordpress_draft"
    assert result.boundary.live_write_enabled is True
    assert result.boundary.live_adapter_configured is True
    assert result.boundary.publish_allowed is False
    assert result.boundary.destructive_update_allowed is False
    assert result.external_write_attempted is True
    assert result.wordpress_post_id == "123"
    assert created_payload_titles == ["BDO dla firm: co sprawdzić"]


def _assert_operator_blockers_have_no_jargon(
    blockers: list[ContentWordPressDraftHandoffBlocker],
) -> None:
    forbidden_terms = [
        "human review",
        "review ",
        "handoff",
        "claimy",
        "publish-ready",
        "audit envelope",
        "Draft Package",
        "work item",
        "final canonical URL",
    ]
    for blocker in blockers:
        text = " ".join([blocker.label, blocker.reason, blocker.next_step])
        for term in forbidden_terms:
            assert term.lower() not in text.lower()


def _assert_execution_blockers_have_no_jargon(
    blockers: list[ContentWordPressDraftExecutionBlocker],
) -> None:
    forbidden_terms = [
        "human review",
        "review ",
        "handoff",
        "claimy",
        "publish-ready",
        "audit envelope",
        "Draft Package",
        "work item",
        "final canonical URL",
    ]
    for blocker in blockers:
        text = " ".join([blocker.label, blocker.reason, blocker.next_step])
        for term in forbidden_terms:
            assert term.lower() not in text.lower()
