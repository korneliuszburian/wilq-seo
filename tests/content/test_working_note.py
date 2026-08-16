from __future__ import annotations

import re

import pytest

from wilq.content.quality.reading_quality import WORKING_NOTE, revision_readability_issues
from wilq.content.quality.semantic_review_guards import repetition_quality_issues
from wilq.content.quality.working_note import (
    WORKING_NOTE_MARKERS,
    contains_working_note,
    working_note_pattern,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection


@pytest.mark.parametrize(
    ("marker_pattern", "example"),
    [
        (r"weryfikacj[ieą]? przez człowieka", "weryfikacji przez człowieka"),
        ("przed wykorzystaniem", "przed wykorzystaniem"),
        ("wymagają weryfikacj", "wymagają weryfikacji"),
        ("do weryfikacji", "do weryfikacji"),
        (r"notatk[ae] robocze?", "notatka robocza"),
        ("weryfikacja przez człowieka", "weryfikacja przez człowieka"),
        ("zweryfikować przez człowieka", "zweryfikować przez człowieka"),
        ("źródło wskazuje", "źródło wskazuje"),
        ("informacja wymaga weryfikacji", "informacja wymaga weryfikacji"),
        (r"\[do uzupełnienia\]", "[do uzupełnienia]"),
    ],
)
def test_shared_vocabulary_matches_every_former_marker(
    marker_pattern: str,
    example: str,
) -> None:
    assert marker_pattern in WORKING_NOTE_MARKERS
    assert working_note_pattern().search(example) is not None


@pytest.mark.parametrize(
    "marker",
    ["[do uzupełnienia]", "przed wykorzystaniem", "ŹRÓDŁO WSKAZUJE"],
)
def test_contains_working_note_finds_shared_markers_inside_body(marker: str) -> None:
    assert contains_working_note(f"Gotowy akapit zawiera {marker} przed zakończeniem tekstu.")
    assert working_note_pattern().flags & re.IGNORECASE


def test_reading_quality_reexports_the_shared_pattern() -> None:
    assert WORKING_NOTE is working_note_pattern()


def test_reading_quality_flags_former_semantic_guard_marker() -> None:
    issues = revision_readability_issues(
        [
            ContentDraftRevisionSection(
                section_id="section_01",
                heading="Zakres obowiązku",
                body_markdown=(
                    "Dokument opisuje obowiązek przedsiębiorcy i termin złożenia wniosku. "
                    "[do uzupełnienia] po sprawdzeniu danych dla tej działalności."
                ),
            )
        ]
    )

    assert any(issue.code == "working_note" for issue in issues)


def test_semantic_review_guard_flags_former_reading_quality_marker() -> None:
    issues = repetition_quality_issues(
        {
            "section_01": (
                "Dokument opisuje obowiązek przedsiębiorcy przed wykorzystaniem w gotowej "
                "treści."
            )
        }
    )

    assert (
        "repetition",
        "whole_document",
        "Dokument zawiera meta-komentarz źródłowy albo notatkę roboczą.",
    ) in issues


def test_source_attribution_is_not_a_working_note() -> None:
    assert not contains_working_note("wg denios")
