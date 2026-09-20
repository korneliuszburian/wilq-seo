"""A malformed assurance fingerprint must never block an approved draft.

Live BDO: the draft failed persistence with
``worker_exception:ValidationError:proposal_metadata.regulatory_assurance_fingerprint``.
Normalize provenance so only well-formed hashes reach immutable metadata.
"""

from __future__ import annotations

from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.initial_full_draft_document import _revision_metadata
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection
from wilq.schemas import CodexRun


def _metadata_with_fingerprint(value: str) -> object:
    receipt = ContentDraftAssuranceReceipt.model_construct(
        status="passed",
        criteria_version="wilq_regulatory_draft_assurance_v1",
        profile_id="bdo",
        profile_version="2026-08",
        codex_run_id="run_x",
        failed_constraint_ids=[],
        assurance_fingerprint=value,
        critic_input_digest="a" * 64,
    )
    return _revision_metadata(
        proposal=ContentPlanningProposal.model_construct(
            proposal_id="p1", refresh_preparation_binding=None
        ),
        planning_input=ContentPlanningInput.model_construct(
            work_item_id="work_x", planning_input_digest="a" * 64
        ),
        sections=[
            ContentDraftRevisionSection.model_construct(
                section_id="s1",
                heading="Nagłówek",
                body_markdown="Treść.",
                evidence_ids=["ev_1"],
                claim_ids=[],
                source_material_ids=[],
                knowledge_card_ids=[],
            )
        ],
        run=CodexRun.model_construct(id="run_x"),
        regulatory_assurance=receipt,
        prepared_plan=None,
    )


def test_malformed_fingerprint_is_dropped_not_fatal() -> None:
    failure = ""
    metadata: object | None
    try:
        metadata = _metadata_with_fingerprint("not-a-hash")
    except Exception as error:  # noqa: BLE001 - the parent raises before the assert
        metadata = None
        failure = repr(error)
    assert metadata is not None, f"metadata build must not fail: {failure}"
    assert metadata.regulatory_assurance_fingerprint is None  # type: ignore[attr-defined]


def test_wellformed_fingerprint_is_preserved() -> None:
    value = "b" * 64
    metadata = _metadata_with_fingerprint(value)
    assert metadata.regulatory_assurance_fingerprint == value  # type: ignore[attr-defined]
