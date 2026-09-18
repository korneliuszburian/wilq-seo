"""Domain-ownership guard for the exact public-deployment approval gate."""

from __future__ import annotations

from pathlib import Path

from wilq.content.measurement import deployment as domain

ROUTER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "apps/api/wilq_api/routers/content_public_deployment.py"
)


def test_domain_owns_exact_approval_gate() -> None:
    assert callable(domain.revision_review_is_exact_approved)


def test_router_delegates_exact_approval_gate() -> None:
    source = ROUTER_SOURCE.read_text(encoding="utf-8")
    assert "revision_review_is_exact_approved(" in source
    assert 'review.decision != "approved"' not in source
