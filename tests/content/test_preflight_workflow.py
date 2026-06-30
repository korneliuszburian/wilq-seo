from __future__ import annotations

from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
from wilq.content.preflight.workflow import build_content_preflight_verdict
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
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _record(**overrides: object) -> ContentInventoryRecord:
    payload: dict[str, object] = {
        "id": "inventory_bdo",
        "url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "content_status": "published",
        "source_connectors": ["wordpress_ekologus"],
        "evidence_ids": ["ev_wp_bdo"],
    }
    payload.update(overrides)
    return ContentInventoryRecord(**payload)


def test_preflight_blocks_without_evidence() -> None:
    verdict = build_content_preflight_verdict(
        _item(evidence_ids=[]),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "blocked"
    assert verdict.draft_allowed is False
    assert [blocker.code for blocker in verdict.blockers] == ["missing_evidence"]
    assert verdict.blockers[0].blocks_current_stage is True


def test_preflight_blocks_without_source_connector() -> None:
    verdict = build_content_preflight_verdict(
        _item(source_connectors=[]),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "blocked"
    assert [blocker.code for blocker in verdict.blockers] == ["missing_source_connector"]


def test_preflight_blocks_missing_final_canonical() -> None:
    verdict = build_content_preflight_verdict(
        _item(),
        resolve_content_inventory(
            [_record(final_canonical_url=None, intended_final_url=None)],
            duplicate_risk="clear",
        ),
    )

    assert verdict.status == "blocked"
    assert [blocker.code for blocker in verdict.blockers] == ["missing_final_canonical"]


def test_preflight_blocks_dev_preview_as_canonical() -> None:
    verdict = build_content_preflight_verdict(
        _item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
        resolve_content_inventory(
            [_record(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/")],
            duplicate_risk="clear",
        ),
    )

    assert verdict.status == "blocked"
    assert [blocker.code for blocker in verdict.blockers] == ["invalid_final_canonical"]


def test_preflight_existing_content_allows_preserve_first_plan() -> None:
    verdict = build_content_preflight_verdict(
        _item(),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "plan_allowed"
    assert verdict.recommended_mode == "preserve"
    assert verdict.sales_brief_allowed is False
    assert "missing_preserve_first_plan" in [blocker.code for blocker in verdict.blockers]


def test_preflight_duplicate_risk_blocks_create() -> None:
    verdict = build_content_preflight_verdict(
        _item(),
        resolve_content_inventory([], duplicate_risk="high"),
    )

    assert verdict.status == "blocked"
    assert [blocker.code for blocker in verdict.blockers] == ["duplicate_risk_high"]
    assert verdict.create_allowed is False


def test_preflight_missing_brief_blocks_draft_but_allows_brief() -> None:
    verdict = build_content_preflight_verdict(
        _item(
            preserve_first_plan_status="approved",
            measurement_window_status="planned",
            measurement_window_id="measure_bdo",
        ),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "brief_allowed"
    assert verdict.sales_brief_allowed is True
    assert verdict.draft_allowed is False
    assert "missing_sales_brief" in [blocker.code for blocker in verdict.blockers]


def test_preflight_missing_human_review_blocks_handoff_but_allows_draft() -> None:
    verdict = build_content_preflight_verdict(
        _item(
            preserve_first_plan_status="approved",
            sales_brief_status="approved",
            sales_brief_id="brief_bdo",
            claim_ledger_status="approved",
            claim_ledger_id="claims_bdo",
            measurement_window_status="planned",
            measurement_window_id="measure_bdo",
            draft_package_status="ready",
            draft_package_id="draft_bdo",
            audit_status="recorded",
            audit_id="audit_bdo",
        ),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "draft_allowed"
    assert verdict.draft_allowed is True
    assert verdict.wordpress_draft_allowed is False
    assert "missing_human_review" in [blocker.code for blocker in verdict.blockers]


def test_preflight_allows_handoff_after_review_and_audit() -> None:
    verdict = build_content_preflight_verdict(
        _item(
            preserve_first_plan_status="approved",
            sales_brief_status="approved",
            sales_brief_id="brief_bdo",
            claim_ledger_status="approved",
            claim_ledger_id="claims_bdo",
            measurement_window_status="planned",
            measurement_window_id="measure_bdo",
            draft_package_status="ready",
            draft_package_id="draft_bdo",
            human_review_status="approved",
            human_review_id="review_bdo",
            audit_status="recorded",
            audit_id="audit_bdo",
        ),
        resolve_content_inventory([_record()], duplicate_risk="clear"),
    )

    assert verdict.status == "handoff_allowed"
    assert verdict.wordpress_draft_allowed is True
    assert verdict.next_step == (
        "Można przygotować WordPress draft. Publikacja nadal nie jest automatyczna."
    )
