"""Domain-ownership guard for append-only social reuse review numbering."""

from __future__ import annotations

from pathlib import Path

from wilq.social import reuse as domain

ROUTER_SOURCE = Path(__file__).resolve().parents[2] / "apps/api/wilq_api/routers/social.py"


def test_domain_owns_social_review_numbering() -> None:
    assert callable(domain.build_social_reuse_review)


def test_router_delegates_social_review_numbering() -> None:
    source = ROUTER_SOURCE.read_text(encoding="utf-8")
    assert "build_social_reuse_review(" in source
    assert "latest.review_number + 1" not in source
