"""Focused contract for the bounded Terra semantic-review deadline."""

from wilq.content.quality.semantic_review_queue import semantic_timeout_seconds
from wilq.content.workflow.runtime.codex_run_lifecycle import (
    LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS,
)


def test_default_deadline_covers_a_full_terra_semantic_review(monkeypatch) -> None:
    monkeypatch.delenv("WILQ_SEMANTIC_REVIEW_CODEX_TIMEOUT_SECONDS", raising=False)

    assert LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS == 900.0
    assert semantic_timeout_seconds() == LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS
