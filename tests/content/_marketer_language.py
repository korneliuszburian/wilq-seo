from __future__ import annotations

from collections.abc import Iterable

FORBIDDEN_MARKETER_JARGON = (
    "Sales Brief",
    "Claim Ledger",
    "Draft Package",
    "human review",
    "handoff",
    "publish-ready",
    "work item",
    "evidence ID",
    "final canonical URL",
)


def assert_marketer_text_has_no_workflow_jargon(texts: Iterable[str]) -> None:
    joined = "\n".join(texts)
    for forbidden in FORBIDDEN_MARKETER_JARGON:
        assert forbidden not in joined
