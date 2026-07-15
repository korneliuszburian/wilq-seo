from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
    ContentDraftRevisionState,
    ContentDraftRevisionWriteResult,
)
from wilq.content.workflow.store import ContentWorkflowStore


def test_draft_revisions_remain_append_only_and_queryable_after_reopen(
    tmp_path: Path,
) -> None:
    path = tmp_path / "wilq.sqlite3"
    store = ContentWorkflowStore(path)

    first_result = store.append_draft_revision(_append_command())
    assert first_result.status == "created"
    assert first_result.revision is not None
    first = first_result.revision
    assert first.revision_number == 1
    assert first.base_revision_id is None
    assert len(first.content_digest) == 64

    second_result = store.append_draft_revision(
        _append_command(
            base_revision_id=first.revision_id,
            title="BDO — poprawiona wersja",
            body_markdown="Poprawiona treść związana z dowodami.",
        )
    )
    assert second_result.status == "created"
    assert second_result.revision is not None
    second = second_result.revision
    assert second.revision_number == 2
    assert second.base_revision_id == first.revision_id
    assert second.content_digest != first.content_digest

    reopened = ContentWorkflowStore(path)
    revisions = reopened.list_draft_revisions("content_work_item_bdo")
    state = reopened.load_draft_revision_state("content_work_item_bdo")

    assert [revision.revision_id for revision in revisions] == [
        first.revision_id,
        second.revision_id,
    ]
    assert [revision.revision_number for revision in revisions] == [1, 2]
    assert state.status == "unreviewed"
    assert state.latest_revision == second
    assert state.latest_review is None
    assert state.revision_count == 2


def test_identical_revision_and_review_retries_are_idempotent(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    command = _append_command()

    first_result = store.append_draft_revision(command)
    retry_result = store.append_draft_revision(command)

    assert first_result.status == "created"
    assert retry_result.status == "idempotent"
    assert retry_result.revision == first_result.revision
    assert store.load_draft_revision_state(command.work_item_id).revision_count == 1

    revision = _require_revision(first_result)
    review_command = _approved_review_command(revision.revision_id, revision.content_digest)
    first_review = store.review_draft_revision(review_command)
    retry_review = store.review_draft_revision(review_command)

    assert first_review.status == "created"
    assert retry_review.status == "idempotent"
    assert retry_review.review == first_review.review


def test_concurrent_review_decision_must_rebase_on_the_latest_decision(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    revision = _require_revision(store.append_draft_revision(_append_command()))
    deferred_command = ContentDraftRevisionReviewCommand(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="deferred",
        reviewed_by="wilku",
        notes="Najpierw trzeba sprawdzić dodatkowy dowód.",
    )
    concurrent_approval = _approved_review_command(
        revision.revision_id,
        revision.content_digest,
    )

    deferred = store.review_draft_revision(deferred_command)
    stale_approval = store.review_draft_revision(concurrent_approval)

    assert deferred.status == "created"
    assert deferred.review is not None
    assert stale_approval.status == "conflict"
    assert stale_approval.conflict is not None
    assert stale_approval.conflict.code == "stale_review"
    assert store.load_draft_revision_state(revision.work_item_id).status == "deferred"

    rebased_approval = store.review_draft_revision(
        concurrent_approval.model_copy(
            update={"base_decision_id": deferred.review.decision_id}
        )
    )
    assert rebased_approval.status == "created"
    assert store.load_draft_revision_state(revision.work_item_id).status == "approved"


def test_identical_content_from_another_actor_is_a_stale_base_conflict(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = _require_revision(store.append_draft_revision(_append_command()))

    other_actor_result = store.append_draft_revision(
        _append_command(created_by="inna_osoba")
    )

    assert other_actor_result.status == "conflict"
    assert other_actor_result.revision is None
    assert other_actor_result.conflict is not None
    assert other_actor_result.conflict.code == "stale_base"
    assert other_actor_result.conflict.current_revision_id == first.revision_id
    assert store.list_draft_revisions(first.work_item_id) == [first]


def test_stale_base_with_different_content_does_not_mutate_history(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = _require_revision(store.append_draft_revision(_append_command()))
    second = _require_revision(
        store.append_draft_revision(
            _append_command(
                base_revision_id=first.revision_id,
                body_markdown="Druga wersja.",
            )
        )
    )

    stale_result = store.append_draft_revision(
        _append_command(
            base_revision_id=first.revision_id,
            body_markdown="Konkurencyjna, inna druga wersja.",
        )
    )

    assert stale_result.status == "conflict"
    assert stale_result.revision is None
    assert stale_result.conflict is not None
    assert stale_result.conflict.code == "stale_base"
    assert stale_result.conflict.current_revision_id == second.revision_id
    assert stale_result.conflict.current_revision_digest == second.content_digest
    stored_revision_ids = [
        revision.revision_id
        for revision in store.list_draft_revisions(first.work_item_id)
    ]
    assert stored_revision_ids == [
        first.revision_id,
        second.revision_id,
    ]


def test_revision_state_is_isolated_by_work_item(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = _require_revision(store.append_draft_revision(_append_command()))
    other = _require_revision(
        store.append_draft_revision(
            _append_command(
                work_item_id="content_work_item_other",
                draft_package_id="draft_package_other",
                title="Inny temat",
            )
        )
    )

    first_state = store.load_draft_revision_state(first.work_item_id)
    other_state = store.load_draft_revision_state(other.work_item_id)

    assert first_state.latest_revision == first
    assert other_state.latest_revision == other
    assert first_state.revision_count == 1
    assert other_state.revision_count == 1
    assert store.load_draft_revision_state("content_work_item_missing").status == "empty"


def test_review_requires_the_current_exact_revision_and_digest(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = _require_revision(store.append_draft_revision(_append_command()))

    missing = store.review_draft_revision(
        _approved_review_command("content_revision_missing", first.content_digest)
    )
    wrong_digest = store.review_draft_revision(
        _approved_review_command(first.revision_id, "0" * 64)
    )

    assert missing.status == "conflict"
    assert missing.conflict is not None
    assert missing.conflict.code == "revision_not_found"
    assert wrong_digest.status == "conflict"
    assert wrong_digest.conflict is not None
    assert wrong_digest.conflict.code == "digest_mismatch"

    approved = store.review_draft_revision(
        _approved_review_command(first.revision_id, first.content_digest)
    )
    assert approved.status == "created"
    assert approved.review is not None
    assert approved.review.revision_id == first.revision_id
    assert approved.review.revision_digest == first.content_digest
    assert store.load_draft_revision_state(first.work_item_id).status == "approved"


def test_child_revision_invalidates_parent_approval(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    parent = _require_revision(store.append_draft_revision(_append_command()))
    approved = store.review_draft_revision(
        _approved_review_command(parent.revision_id, parent.content_digest)
    )
    assert approved.status == "created"

    child = _require_revision(
        store.append_draft_revision(
            _append_command(
                base_revision_id=parent.revision_id,
                body_markdown="Nowa wersja po zatwierdzeniu rodzica.",
            )
        )
    )
    state = store.load_draft_revision_state(parent.work_item_id)
    stale_review = store.review_draft_revision(
        _approved_review_command(parent.revision_id, parent.content_digest)
    )

    assert state.latest_revision == child
    assert state.latest_review is None
    assert state.status == "unreviewed"
    assert stale_review.status == "conflict"
    assert stale_review.conflict is not None
    assert stale_review.conflict.code == "stale_revision"
    assert stale_review.conflict.current_revision_id == child.revision_id
    assert approved.review is not None
    with pytest.raises(ValidationError):
        ContentDraftRevisionState(
            status="approved",
            latest_revision=child,
            latest_review=approved.review,
            revision_count=2,
        )


def test_deferred_review_is_persisted_as_current_state(tmp_path: Path) -> None:
    path = tmp_path / "wilq.sqlite3"
    store = ContentWorkflowStore(path)
    revision = _require_revision(store.append_draft_revision(_append_command()))

    result = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            decision="deferred",
            reviewed_by="wilku",
            notes="Decyzja wymaga dodatkowego źródła.",
        )
    )

    assert result.status == "created"
    state = ContentWorkflowStore(path).load_draft_revision_state(revision.work_item_id)
    assert state.status == "deferred"
    assert state.latest_review == result.review


def test_revision_content_rejects_blank_or_duplicate_sections() -> None:
    with pytest.raises(ValidationError):
        _append_command(title="   ")
    with pytest.raises(ValidationError):
        _append_command(created_by="   ")
    with pytest.raises(ValidationError):
        _append_command(body_markdown="   ")
    with pytest.raises(ValidationError):
        _append_command(
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres",
                    body_markdown="Pierwsza sekcja.",
                ),
                ContentDraftRevisionSection(
                    heading=" Zakres ",
                    body_markdown="Druga sekcja.",
                ),
            ]
        )
    with pytest.raises(ValidationError):
        ContentDraftRevisionAppendCommand(
            work_item_id="content_work_item_bdo",
            draft_package_id="draft_package_bdo",
            draft_package_digest="d" * 64,
            planning_digest="c" * 64,
            final_canonical_url="https://ekologus.pl/bdo/",
            title="BDO",
            sections=[],
            created_by="wilku",
        )


def test_revision_review_requires_proof_for_approval_and_notes_otherwise() -> None:
    with pytest.raises(ValidationError):
        ContentDraftRevisionReviewCommand(
            work_item_id="content_work_item_bdo",
            revision_id="content_revision_bdo",
            revision_digest="a" * 64,
            decision="approved",
            reviewed_by="wilku",
        )
    with pytest.raises(ValidationError):
        ContentDraftRevisionReviewCommand(
            work_item_id="content_work_item_bdo",
            revision_id="content_revision_bdo",
            revision_digest="a" * 64,
            decision="needs_changes",
            reviewed_by="wilku",
            notes="   ",
        )
    with pytest.raises(ValidationError):
        ContentDraftRevisionReviewCommand(
            work_item_id="content_work_item_bdo",
            revision_id="content_revision_bdo",
            revision_digest="a" * 64,
            decision="approved",
            reviewed_by="   ",
            checked_items=["Sprawdzono wersję."],
            evidence_ids=["ev_gsc_bdo"],
        )
    with pytest.raises(ValidationError):
        ContentDraftRevisionReviewCommand(
            work_item_id="content_work_item_bdo",
            revision_id="content_revision_bdo",
            revision_digest="a" * 64,
            decision="approved",
            reviewed_by="wilku",
            checked_items=["Sprawdzono wersję.", "   "],
            evidence_ids=["ev_gsc_bdo"],
        )


def test_revision_digest_is_computed_from_redacted_content(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    synthetic_token_like_text = "syntetyczny identyfikator " + ("X" * 40)

    revision = _require_revision(
        store.append_draft_revision(_append_command(body_markdown=synthetic_token_like_text))
    )

    assert revision.sections[0].body_markdown == "[REDACTED]"
    assert revision.content_digest != "[REDACTED]"
    assert len(revision.content_digest) == 64


def test_numeric_package_digest_is_preserved_by_redaction(tmp_path: Path) -> None:
    revision = _require_revision(
        ContentWorkflowStore(tmp_path / "wilq.sqlite3").append_draft_revision(
            _append_command(draft_package_digest="1" * 64)
        )
    )

    assert revision.draft_package_digest == "1" * 64


def test_revision_digest_binds_work_item_package_url_title_and_ordered_sections(
    tmp_path: Path,
) -> None:
    baseline = _require_revision(
        ContentWorkflowStore(tmp_path / "baseline.sqlite3").append_draft_revision(
            _append_command()
        )
    )
    variants = [
        _append_command(work_item_id="content_work_item_other"),
        _append_command(draft_package_id="draft_package_other"),
        _append_command(draft_package_digest="e" * 64),
        _append_command(final_canonical_url="https://ekologus.pl/inny-adres/"),
        _append_command(title="Inny tytuł"),
        _append_command(
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres obowiązków",
                    body_markdown="Treść związana z dowodami.",
                    evidence_ids=["ev_wp_bdo", "ev_gsc_bdo"],
                )
            ]
        ),
    ]

    variant_digests = {
        _require_revision(
            ContentWorkflowStore(tmp_path / f"variant-{index}.sqlite3").append_draft_revision(
                command
            )
        ).content_digest
        for index, command in enumerate(variants)
    }

    assert baseline.content_digest not in variant_digests


def _append_command(
    *,
    work_item_id: str = "content_work_item_bdo",
    base_revision_id: str | None = None,
    draft_package_id: str = "draft_package_content_work_item_bdo",
    draft_package_digest: str = "d" * 64,
    final_canonical_url: str = "https://ekologus.pl/bdo/",
    title: str = "BDO — obowiązki przedsiębiorcy",
    body_markdown: str = "Treść związana z dowodami.",
    sections: list[ContentDraftRevisionSection] | None = None,
    created_by: str = "wilku",
) -> ContentDraftRevisionAppendCommand:
    return ContentDraftRevisionAppendCommand(
        work_item_id=work_item_id,
        base_revision_id=base_revision_id,
        draft_package_id=draft_package_id,
        draft_package_digest=draft_package_digest,
        planning_digest="c" * 64,
        final_canonical_url=final_canonical_url,
        title=title,
        sections=(
            sections
            if sections is not None
            else [
                ContentDraftRevisionSection(
                    heading="Zakres obowiązków",
                    body_markdown=body_markdown,
                    evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                )
            ]
        ),
        created_by=created_by,
    )


def _approved_review_command(
    revision_id: str,
    revision_digest: str,
) -> ContentDraftRevisionReviewCommand:
    return ContentDraftRevisionReviewCommand(
        work_item_id="content_work_item_bdo",
        revision_id=revision_id,
        revision_digest=revision_digest,
        decision="approved",
        reviewed_by="wilku",
        notes="Sprawdzono dokładną wersję szkicu.",
        checked_items=["Treść i claimy sprawdzone."],
        evidence_ids=["ev_gsc_bdo"],
    )


def _require_revision(result: ContentDraftRevisionWriteResult) -> ContentDraftRevision:
    assert result.status == "created"
    assert result.revision is not None
    return result.revision
