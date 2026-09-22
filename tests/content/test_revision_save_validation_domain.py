"""Domain-ownership guard for exact draft-revision save/review validation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from wilq.content.workflow.contracts.contracts import ContentDraftRevisionSaveRequest
from wilq.content.workflow.documents import revision_save_validation as domain
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection

ROUTER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "apps/api/wilq_api/routers/content_workflow.py"
)


def test_domain_owns_revision_save_validation() -> None:
    assert callable(domain.validate_revision_sections)
    assert callable(domain.validate_canonical_html_alignment)
    assert callable(domain.validate_review_evidence)
    assert set(domain.RevisionValidationViolation.__dataclass_fields__) == {
        "status_code",
        "detail",
    }


def test_router_delegates_instead_of_reimplementing() -> None:
    source = ROUTER_SOURCE.read_text(encoding="utf-8")
    assert "def _validate_revision_sections(" not in source
    assert "def _validate_canonical_html_alignment(" not in source
    assert "def _validate_review_evidence(" not in source
    assert "validate_revision_sections(" in source
    assert "validate_canonical_html_alignment(" in source
    assert "validate_review_evidence(" in source


def test_ordinary_save_requires_canonical_html_alignment() -> None:
    body_markdown = "A"
    section = ContentDraftRevisionSection(
        section_id="section-1",
        heading="Sekcja",
        body_markdown=body_markdown,
        content_html="<p>B</p>",
        evidence_ids=["ev-1"],
    )
    request = ContentDraftRevisionSaveRequest(
        title="Dokument",
        sections=[section],
        created_by="wilku",
    )
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(
                draft_package=SimpleNamespace(
                    sections=[
                        SimpleNamespace(heading=section.heading, evidence_ids=section.evidence_ids)
                    ]
                )
            )
        )
    )

    mismatch = domain.validate_revision_sections(
        request,
        snapshot,
        latest_revision=None,
        revision_context_current=False,
    )
    assert mismatch is not None
    assert mismatch.status_code == 422
    assert "canonical_html_alignment" in mismatch.detail

    aligned_request = request.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"content_html": content_html_from_markdown(body_markdown)}
                )
            ]
        }
    )
    assert (
        domain.validate_revision_sections(
            aligned_request,
            snapshot,
            latest_revision=None,
            revision_context_current=False,
        )
        is None
    )
