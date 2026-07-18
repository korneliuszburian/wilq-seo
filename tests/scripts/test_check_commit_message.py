from __future__ import annotations

from scripts.check_commit_message import validate_commit_message


def test_accepts_semantic_commit_with_scope() -> None:
    assert validate_commit_message("fix(content): preserve exact revision\n\nDetails") == []


def test_rejects_untyped_commit_header() -> None:
    errors = validate_commit_message("Record live proof")
    assert errors and "must match" in errors[0]


def test_rejects_capitalized_or_period_ended_subject() -> None:
    assert validate_commit_message("docs: Record live proof")
    assert validate_commit_message("docs: record live proof.")
