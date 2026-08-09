from __future__ import annotations

import re
from itertools import pairwise

from wilq.content.quality.semantic_review_turn import _INSTRUCTION

_REQUIRED_RULE_PHRASES = (
    "literalnych wartości z application_context.allowed_targets",
    "literalnych wartości z application_context.allowed_evidence_ids",
    "powtórzone akapity",
    "źródło wskazuje",
    "failure-mode mapping",
    "brak wymaganego CTA",
    "regulatory_coverage.requirements",
)

_TRAILING_SPLICE_TOKENS = frozenset(
    {
        "a",
        "aby",
        "do",
        "i",
        "jeżeli",
        "jeśli",
        "lub",
        "na",
        "nie",
        "oraz",
        "to",
        "tylko",
        "w",
        "że",
    }
)


def test_semantic_review_instruction_preserves_required_rule_phrases() -> None:
    for phrase in _REQUIRED_RULE_PHRASES:
        assert phrase in _INSTRUCTION


def test_semantic_review_instruction_has_no_clear_line_splices() -> None:
    lines = [line for line in _INSTRUCTION.splitlines() if line.strip()]
    assert len(lines) > 1

    for current_line, next_line in pairwise(lines):
        trailing_word = re.search(r"(?P<token>[^\W\d_]+)\s*$", current_line)
        has_dangling_token = (
            trailing_word is not None
            and trailing_word.group("token").casefold() in _TRAILING_SPLICE_TOKENS
        )
        next_line_starts_sentence = next_line.lstrip()[:1].isupper()

        assert not (has_dangling_token and next_line_starts_sentence), (
            f"Instrukcja zawiera urwany splice między liniami: {current_line!r} / "
            f"{next_line!r}"
        )
