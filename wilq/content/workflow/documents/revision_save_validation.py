"""Domain validation for exact draft-revision saves and review evidence.

These rules used to live in the FastAPI router. They are content-safety policy,
so they belong to the domain and are surfaced through a typed violation that the
public boundary maps to an HTTP status without re-deriving the rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from wilq.content.drafts.package import ContentDraftSection
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionReviewRequest,
    ContentDraftRevisionSaveRequest,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.editor_child import revision_evidence_ids
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
)


@dataclass(frozen=True, slots=True)
class RevisionValidationViolation:
    """One exact-save/review rule failure, mapped to HTTP by the boundary."""

    status_code: Literal[409, 422]
    detail: str


def validate_revision_sections(
    request: ContentDraftRevisionSaveRequest,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    latest_revision: ContentDraftRevision | None,
    revision_context_current: bool,
) -> RevisionValidationViolation | None:
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    if draft_package is None:
        return RevisionValidationViolation(422, "Brakuje pakietu sekcji do zapisu wersji.")
    for section in request.sections:
        if section.content_html != content_html_from_markdown(section.body_markdown):
            return RevisionValidationViolation(
                422,
                (
                    "HTML sekcji zapisu musi dokładnie wynikać z jej Markdownu; "
                    "użyj korekty canonical_html_alignment."
                ),
            )
    request_headings = [section.heading for section in request.sections]
    # A current v2 child edits the exact immutable document. Its body can have
    # been generated from a richer planning proposal than the legacy editor
    # package, so validate its section contract against that exact parent.
    # A stale parent remains bound to the current package and cannot bypass the
    # normal current-context gate below.
    expected_sections: Sequence[ContentDraftSection | ContentDraftRevisionSection] = (
        latest_revision.sections
        if (
            latest_revision is not None
            and latest_revision.schema_version == "wilq_content_draft_revision_v2"
            and request.base_revision_id == latest_revision.revision_id
            and revision_context_current
        )
        else draft_package.sections
    )
    current_revision = latest_revision
    if (
        current_revision is not None
        and current_revision.schema_version == "wilq_content_draft_revision_v2"
        and request.base_revision_id == current_revision.revision_id
        and revision_context_current
    ):
        parent_ids = [section.section_id for section in current_revision.sections]
        request_ids = [section.section_id for section in request.sections]
        headings = [section.heading.strip() for section in request.sections]
        if (
            any(section_id is None for section_id in request_ids)
            or len(request_ids) != len(set(request_ids))
            or request_ids != [section_id for section_id in parent_ids if section_id in request_ids]
        ):
            return RevisionValidationViolation(
                422,
                "Potomna wersja może zachować albo scalić sekcje bazowe w ich kolejności.",
            )
        if len(headings) != len(set(headings)):
            return RevisionValidationViolation(
                422,
                "Nagłówki sekcji potomnej wersji muszą być unikalne.",
            )
        if any(not section.evidence_ids for section in request.sections):
            return RevisionValidationViolation(
                422,
                "Każda sekcja potomnej wersji wymaga dowodów.",
            )
        allowed_evidence = revision_evidence_ids(current_revision)
        if any(
            set(section.evidence_ids).difference(allowed_evidence) for section in request.sections
        ):
            return RevisionValidationViolation(
                422,
                "Sekcje potomnej wersji mogą używać tylko dowodów wersji bazowej.",
            )
        return None
    expected_headings = [section.heading for section in expected_sections]
    if request_headings != expected_headings:
        return RevisionValidationViolation(
            422,
            (
                "Zapisywana wersja musi zawierać dokładnie wszystkie sekcje "
                "zatwierdzonego planu, w tej samej kolejności."
            ),
        )
    for section, expected_section in zip(
        request.sections,
        expected_sections,
        strict=True,
    ):
        if section.evidence_ids != expected_section.evidence_ids:
            return RevisionValidationViolation(
                422,
                "Dowody sekcji muszą dokładnie odpowiadać zatwierdzonemu planowi: "
                + section.heading,
            )
    return None


def validate_canonical_html_alignment(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
) -> RevisionValidationViolation | None:
    if (
        request.page_assets is not None
        or request.faq is not None
        or request.official_source_references is not None
    ):
        return RevisionValidationViolation(
            422,
            "Korekta HTML nie może zmieniać pozostałych pól dokumentu.",
        )
    if latest_revision is None or request.base_revision_id != latest_revision.revision_id:
        return RevisionValidationViolation(
            409,
            "Korekta HTML wymaga aktualnej wersji bazowej.",
        )
    if request.title != latest_revision.title or len(request.sections) != len(
        latest_revision.sections
    ):
        return RevisionValidationViolation(
            422,
            "Korekta HTML nie może zmieniać zakresu wersji.",
        )
    changed_html = False
    for submitted, current in zip(request.sections, latest_revision.sections, strict=True):
        if (
            submitted.section_id != current.section_id
            or submitted.heading != current.heading
            or submitted.body_markdown != current.body_markdown
            or submitted.query_terms != current.query_terms
            or submitted.evidence_ids != current.evidence_ids
            or submitted.claim_ids != current.claim_ids
            or submitted.source_material_ids != current.source_material_ids
            or submitted.knowledge_card_ids != current.knowledge_card_ids
        ):
            return RevisionValidationViolation(
                422,
                "Korekta HTML może zmienić wyłącznie kanoniczne HTML sekcji.",
            )
        expected_html = content_html_from_markdown(current.body_markdown)
        if submitted.content_html != expected_html:
            return RevisionValidationViolation(
                422,
                "Korekta HTML musi wynikać dokładnie z Markdownu wersji bazowej.",
            )
        changed_html = changed_html or current.content_html != expected_html
    if not changed_html:
        return RevisionValidationViolation(
            422,
            "Wersja bazowa nie wymaga korekty kanonicznego HTML.",
        )
    return None


def validate_review_evidence(
    request: ContentDraftRevisionReviewRequest,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> RevisionValidationViolation | None:
    latest_revision = snapshot.revision_workspace.latest_revision
    if latest_revision is None:
        return RevisionValidationViolation(
            422,
            "Brakuje zapisanej wersji, której dowody można sprawdzić.",
        )
    allowed_evidence = revision_evidence_ids(latest_revision)
    unknown_evidence = sorted(set(request.evidence_ids).difference(allowed_evidence))
    if unknown_evidence:
        return RevisionValidationViolation(
            422,
            "Decyzja zawiera dowody spoza snapshotu tego zadania: " + ", ".join(unknown_evidence),
        )
    return None


__all__ = [
    "RevisionValidationViolation",
    "validate_canonical_html_alignment",
    "validate_review_evidence",
    "validate_revision_sections",
]
