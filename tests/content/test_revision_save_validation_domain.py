"""Domain-ownership guard for exact draft-revision save/review validation."""

from __future__ import annotations

from pathlib import Path

from wilq.content.workflow.documents import revision_save_validation as domain

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
