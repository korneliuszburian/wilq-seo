from __future__ import annotations

from pathlib import Path

import pytest

from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Proposal,
    build_current_page_disposition_v2_proposal,
    build_current_page_disposition_v2_receipt,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def _evidence(
    *, material_digest: str, current_ids: list[str], catalog_ids: list[str]
) -> CurrentPageEvidenceResponse:
    return CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Reviewed current material.",
        work_item_id="work-item-1",
        page_url="https://www.ekologus.pl/exact-page/",
        material_meaning_digest=material_digest,
        current_evidence_ids=current_ids,
        catalog_evidence_ids=catalog_ids,
        safe_next_step="Prepare exact ActionObject review.",
    )


def _action(proposal: CurrentPageDispositionV2Proposal) -> ActionObject:
    return ActionObject(
        id=proposal.proposal_id,
        title="Review page disposition",
        domain=OpportunityDomain.content,
        connector="local",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.new,
        evidence_ids=list(proposal.snapshot.current_evidence_ids),
        human_diagnosis="Current material reviewed.",
        recommended_reason="Keep the current page.",
        payload={"current_page_disposition_v2": proposal.proposal_id},
        validation_status="valid",
        created_by="wilku",
    )


def test_v2_proposal_identity_tracks_semantics_and_keeps_first_snapshot(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    first = build_current_page_disposition_v2_proposal(
        _evidence(material_digest="a" * 64, current_ids=["wp-1"], catalog_ids=["catalog-1"])
    )
    rotated = build_current_page_disposition_v2_proposal(
        _evidence(material_digest="a" * 64, current_ids=["wp-2"], catalog_ids=["catalog-2"])
    )
    changed = build_current_page_disposition_v2_proposal(
        _evidence(material_digest="b" * 64, current_ids=["wp-3"], catalog_ids=["catalog-3"])
    )

    stored_first = store.record_current_page_disposition_v2_proposal(first)
    stored_rotated = store.record_current_page_disposition_v2_proposal(rotated)
    stored_changed = store.record_current_page_disposition_v2_proposal(changed)

    assert stored_first.proposal_id == stored_rotated.proposal_id
    assert stored_rotated.snapshot == first.snapshot
    assert stored_first.snapshot.canonical_path == "/exact-page"
    assert stored_first.snapshot.generation_allowed is False
    assert stored_changed.proposal_id != stored_first.proposal_id
    assert store.load_current_page_disposition_v2_proposal(stored_first.proposal_id) == stored_first
    assert store.load_content_current_disposition_proposal(stored_first.proposal_id) is None


def test_v2_receipt_is_append_only_idempotent_and_v1_reads_stay_safe(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    proposal = store.record_current_page_disposition_v2_proposal(
        build_current_page_disposition_v2_proposal(
            _evidence(material_digest="a" * 64, current_ids=["wp-1"], catalog_ids=["catalog-1"])
        )
    )
    receipt = build_current_page_disposition_v2_receipt(
        action=_action(proposal),
        proposal=proposal,
        preview_audit_id="audit-preview",
        review_audit_id="audit-review",
        confirmation_audit_id="audit-confirm",
        impact_audit_id="audit-impact",
        reviewed_by="reviewer",
        confirmed_by="confirmer",
    )
    rotated_proposal = build_current_page_disposition_v2_proposal(
        _evidence(material_digest="a" * 64, current_ids=["wp-2"], catalog_ids=["catalog-2"])
    )
    mismatched_receipt = build_current_page_disposition_v2_receipt(
        action=_action(rotated_proposal),
        proposal=rotated_proposal,
        preview_audit_id="audit-preview",
        review_audit_id="audit-review",
        confirmation_audit_id="audit-confirm",
        impact_audit_id="audit-impact",
        reviewed_by="reviewer",
        confirmed_by="confirmer",
    )

    with pytest.raises(ValueError, match="snapshot does not match proposal"):
        store.record_current_page_disposition_v2_receipt(mismatched_receipt)
    with pytest.raises(ValueError, match="requires a stored proposal"):
        ContentWorkflowStore(tmp_path / "empty.sqlite3").record_current_page_disposition_v2_receipt(
            receipt
        )

    status, stored = store.record_current_page_disposition_v2_receipt(receipt)
    retry_status, retried = store.record_current_page_disposition_v2_receipt(receipt)

    assert status == "created"
    assert retry_status == "idempotent"
    assert retried == stored
    assert stored.action_id == proposal.proposal_id
    assert stored.action_payload_digest
    assert stored.review_audit_id == "audit-review"
    assert store.load_current_page_disposition_v2_receipt(stored.action_id) == stored
    assert store.load_content_current_disposition_receipt(stored.action_id) is None
