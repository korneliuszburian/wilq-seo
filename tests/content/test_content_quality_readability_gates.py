from __future__ import annotations

import pytest

from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.quality.review import (
    ContentQualityReview,
    _weak_cta,
    build_content_quality_review,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
)


def test_twelve_word_v2_section_is_not_thin() -> None:
    review = _review(
        _revision(
            
                "Ta sekcja jasno wyjaśnia klientowi zakres działania i prowadzi go do "
                "decyzji."
            
        )
    )

    assert "thin_section" not in _finding_codes(review)


def test_v2_review_flags_only_sections_with_fewer_than_twelve_words() -> None:
    review = _review(
        _revision(
            "Krótka odpowiedź nie wyjaśnia klientowi kolejnego kroku.",
            second_body=(
                "Ta sekcja jasno wyjaśnia klientowi zakres działania i prowadzi go do "
                "decyzji."
            ),
        )
    )

    thin_findings = [
        finding for finding in review.findings if finding.code == "thin_section"
    ]
    assert len(thin_findings) == 1
    assert thin_findings[0].severity == "needs_changes"
    assert thin_findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"


def test_v2_review_flags_one_oversized_paragraph_and_ignores_short_paragraph() -> None:
    oversized = " ".join(["słowo"] * 221)
    short = " ".join(["krótki"] * 20)
    review = _review(_revision(f"{oversized}\n\n{short}", second_body=short))

    wall_findings = [
        finding for finding in review.findings if finding.code == "wall_of_text"
    ]
    assert len(wall_findings) == 1
    assert wall_findings[0].severity == "needs_changes"
    assert wall_findings[0].affected_section == "Pierwsza sekcja"
    assert "Akapit zawiera 221 słów" in wall_findings[0].reason
    assert "Przykład:" in wall_findings[0].reason


def test_legacy_review_without_revision_emits_no_readability_findings() -> None:
    review = _review(None)

    assert {"thin_section", "wall_of_text"}.isdisjoint(_finding_codes(review))


@pytest.mark.parametrize(
    "cta",
    [
        "Pobierz bezpłatny przewodnik i zaplanuj audyt ekologiczny",
        (
            "Pobierz bezpłatny przewodnik i zaplanuj teraz spokojnie swój audyt "
            "ekologiczny z ekspertem"
        ),
    ],
)
def test_concrete_cta_is_not_weak(cta: str) -> None:
    assert _weak_cta(cta) is False


@pytest.mark.parametrize(
    "cta",
    [
        "Napisz",
        "Zadzwoń",
        "w razie wątpliwości prosimy o kontakt",
    ],
)
def test_short_or_vague_cta_is_weak(cta: str) -> None:
    assert _weak_cta(cta) is True


def _review(revision: ContentDraftRevision | None) -> ContentQualityReview:
    item = ContentWorkItem(
        id="content_work_item_readability",
        topic="Czytelność treści",
        evidence_ids=["ev_readability"],
        source_connectors=["wordpress_ekologus"],
        measurement_window_status="planned",
        measurement_window_id="measurement_readability",
    )
    return build_content_quality_review(
        item=item,
        draft_package=None,
        structured_output=None,
        revision=revision,
        claim_ledger=ContentClaimLedger(
            id="claim_ledger_readability",
            work_item_id=item.id,
        ),
    )


def _revision(
    body: str,
    *,
    second_body: str | None = None,
) -> ContentDraftRevision:
    sections = [
        ContentDraftRevisionSection(
            section_id="section_one",
            heading="Pierwsza sekcja",
            body_markdown=body,
            evidence_ids=["ev_readability"],
        )
    ]
    if second_body is not None:
        sections.append(
            ContentDraftRevisionSection(
                section_id="section_two",
                heading="Druga sekcja",
                body_markdown=second_body,
                evidence_ids=["ev_readability"],
            )
        )
    return ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="revision_readability",
        work_item_id="content_work_item_readability",
        content_digest="a" * 64,
        sections=sections,
    )


def _finding_codes(review: ContentQualityReview) -> set[str]:
    return {finding.code for finding in review.findings}
