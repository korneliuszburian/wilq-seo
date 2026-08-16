from __future__ import annotations

import pytest

from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.initial_draft_readability import readability_issues_for_output
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftFaqOutput,
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.quality.review import (
    ContentQualityReview,
    _weak_cta,
    build_content_quality_review,
)
from wilq.content.quality.semantic_review_guards import readability_quality_issues
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
)


def test_twelve_word_v2_section_is_not_thin() -> None:
    review = _review(
        _revision("Ta sekcja jasno wyjaśnia klientowi zakres działania i prowadzi go do decyzji.")
    )

    assert "thin_section" not in _finding_codes(review)


def test_v2_review_flags_only_sections_with_fewer_than_twelve_words() -> None:
    review = _review(
        _revision(
            "Krótka odpowiedź nie wyjaśnia klientowi kolejnego kroku.",
            second_body=(
                "Ta sekcja jasno wyjaśnia klientowi zakres działania i prowadzi go do decyzji."
            ),
        )
    )

    thin_findings = [finding for finding in review.findings if finding.code == "thin_section"]
    assert len(thin_findings) == 1
    assert thin_findings[0].severity == "needs_changes"
    assert thin_findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"


def test_semantic_guard_maps_colliding_heading_to_whole_document() -> None:
    base_revision = _revision(
        "Krótka odpowiedź nie wyjaśnia klientowi kolejnego kroku.",
        heading="Powtórzony nagłówek",
    )
    revision = base_revision.model_copy(
        update={
            "sections": [
                base_revision.sections[0],
                base_revision.sections[0].model_copy(update={"section_id": "section_two"}),
            ]
        }
    )

    assert (
        "answer_directness",
        "whole_document",
        "Sekcja zawiera 7 słów; bramka czytelności wymaga co najmniej 12.",
    ) in readability_quality_issues(revision)


def test_v2_review_flags_one_oversized_paragraph_and_ignores_short_paragraph() -> None:
    oversized = " ".join(["słowo"] * 221)
    short = " ".join(["krótki"] * 20)
    review = _review(_revision(f"{oversized}\n\n{short}", second_body=short))

    wall_findings = [finding for finding in review.findings if finding.code == "wall_of_text"]
    assert len(wall_findings) == 1
    assert wall_findings[0].severity == "needs_changes"
    assert wall_findings[0].affected_section == "Pierwsza sekcja"
    assert "Akapit zawiera 221 słów" in wall_findings[0].reason
    assert "Przykład:" in wall_findings[0].reason


def test_v2_review_flags_a_sentence_longer_than_twenty_words() -> None:
    long_sentence = " ".join(["Pierwsze", *[f"słowo{index}" for index in range(2, 26)]]) + "."
    review = _review(_revision(long_sentence))

    findings = [finding for finding in review.findings if finding.code == "long_sentence"]

    assert len(findings) == 1
    assert findings[0].label == "Sekcja zawiera zbyt długie zdanie"
    assert findings[0].reason == "Zdanie liczy 25 słów (limit: 20)."
    assert findings[0].next_step == "Podziel długie zdanie na krótsze."
    assert findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"
    assert (
        "logical_flow",
        "section_one",
        "Zdanie liczy 25 słów (limit: 20).",
    ) in readability_quality_issues(_revision(long_sentence))


@pytest.mark.parametrize("terminator", [".", "?", "!"])
def test_v2_review_ignores_sentences_with_at_most_twenty_words(terminator: str) -> None:
    first = " ".join(["Pierwsze", *[f"słowo{index}" for index in range(2, 21)]])
    first = f"{first}{terminator}"
    second = " ".join(["Drugie", *[f"hasło{index}" for index in range(2, 21)]]) + "."
    review = _review(_revision(f"{first} {second}"))

    assert "long_sentence" not in _finding_codes(review)


def test_v2_review_does_not_split_a_long_sentence_at_polish_abbreviation() -> None:
    sentence = (
        "np. To jest przykład bardzo długiego zdania, które nadal wyjaśnia "
        "czytelnikowi wszystkie istotne warunki procesu oraz kolejne bezpieczne "
        "działania firmy dzisiaj."
    )
    assert len(sentence.split()) == 21

    review = _review(_revision(sentence))

    findings = [finding for finding in review.findings if finding.code == "long_sentence"]
    assert len(findings) == 1
    assert findings[0].reason == "Zdanie liczy 21 słów (limit: 20)."


def test_pre_save_readability_gate_flags_a_long_sentence_in_faq_answer() -> None:
    long_answer = (
        "Przedsiębiorca najpierw zbiera dokumenty, sprawdza obowiązki, ustala terminy, "
        "wyznacza osoby odpowiedzialne, planuje kontrolę, porządkuje dane oraz "
        "bezpiecznie wdraża kolejne działania w swojej firmie każdego dnia."
    )
    assert len(long_answer.split()) == 25
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Czytelny przewodnik",
            meta_title="Czytelny przewodnik dla firmy",
            meta_description="Praktyczne kroki dla przedsiębiorcy.",
            h1="Jak uporządkować obowiązki",
            lead="Krótki przewodnik prowadzi przez najważniejsze działania.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_01",
                heading="Pierwszy krok",
                body_markdown=(
                    "Ta sekcja jasno wyjaśnia klientowi zakres działania i prowadzi go do "
                    "bezpiecznej decyzji."
                ),
            )
        ],
        faq=[
            ContentInitialDraftFaqOutput(
                question="Jak zacząć porządkowanie dokumentacji?",
                answer_markdown=long_answer,
            )
        ],
    )

    issues = readability_issues_for_output(output)

    assert (
        "long_sentence",
        "faq:1",
        "Zdanie liczy 25 słów (limit: 20).",
    ) in issues


def test_question_heading_with_only_vague_body_is_flagged() -> None:
    heading = "Jak pobiera się próbki gleby, ziemi i wód gruntowych do analizy?"
    vague_body = (
        "Próbki pobiera się w ramach prac terenowych. Zakres może obejmować glebę, "
        "ziemię i wody gruntowe. Po ustaleniu zakresu można przejść do dalszych prac."
    )

    review = _review(_revision(vague_body, heading=heading))

    findings = [finding for finding in review.findings if finding.code == "heading_answer_mismatch"]
    assert len(findings) == 1
    assert findings[0].label == "Nagłówek-pyranie nie doczekał się odpowiedzi"
    assert findings[0].reason == ("Nagłówek pyta o... ale treść omija odpowiedź ogólnikami.")
    assert findings[0].next_step == ("Rozwiń treść o konkretną odpowiedź na pytanie z nagłówka.")
    assert findings[0].affected_section == heading
    assert review.usefulness.status == "needs_changes"
    assert (
        "answer_directness",
        "section_one",
        "Nagłówek pyta o... ale treść omija odpowiedź ogólnikami.",
    ) in readability_quality_issues(_revision(vague_body, heading=heading))


def test_question_heading_with_concrete_answer_is_not_flagged() -> None:
    review = _review(
        _revision(
            (
                "W ramach prac próbki pobiera się przez wiercenie w wyznaczonych "
                "punktach. Następnie materiał trafia na analizę laboratoryjną."
            ),
            heading="Jak pobiera się próbki gleby do analizy?",
        )
    )

    assert "heading_answer_mismatch" not in _finding_codes(review)


def test_non_question_heading_with_vague_body_is_not_flagged() -> None:
    review = _review(
        _revision(
            (
                "Próbki pobiera się w ramach prac terenowych. Zakres może obejmować "
                "glebę, ziemię i wody gruntowe. Można przejść do dalszych prac."
            ),
            heading="Pobieranie próbek gleby, ziemi i wód gruntowych do analizy",
        )
    )

    assert "heading_answer_mismatch" not in _finding_codes(review)


def test_pre_save_gate_surfaces_heading_answer_mismatch() -> None:
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Pobieranie próbek gruntu",
            meta_title="Pobieranie próbek gruntu do analizy",
            meta_description="Praktyczne informacje o pobieraniu próbek.",
            h1="Pobieranie próbek gruntu",
            lead="Przewodnik opisuje prace terenowe i badania gruntu.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_02",
                heading=("Jak pobiera się próbki gleby, ziemi i wód gruntowych do analizy?"),
                body_markdown=(
                    "Próbki pobiera się w ramach prac terenowych. Zakres może obejmować "
                    "glebę, ziemię i wody gruntowe. Można przejść do dalszych prac."
                ),
            )
        ],
    )

    assert any(
        code == "heading_answer_mismatch" and section_id == "section_02"
        for code, section_id, _ in readability_issues_for_output(output)
    )


def test_v2_review_flags_a_vague_answer_phrase_without_concrete_signals() -> None:
    body = "Prosimy ustalić zakres i zebrać informacje o potrzebach."

    review = _review(_revision(body))

    findings = [finding for finding in review.findings if finding.code == "vague_answer_phrase"]
    assert len(findings) == 1
    assert findings[0].label == "Sekcja zawiera ogólnik zamiast odpowiedzi"
    assert findings[0].reason == (
        "Treść odsyła do ustalenia zakresu albo zebrania informacji zamiast podać konkret."
    )
    assert findings[0].next_step == (
        "Podaj konkretne obowiązki, dokumenty, terminy albo czynności z source facts."
    )
    assert findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"
    assert (
        "answer_directness",
        "section_one",
        "Treść odsyła do ustalenia zakresu albo zebrania informacji zamiast podać konkret.",
    ) in readability_quality_issues(_revision(body))


def test_v2_review_treats_adaptation_as_vague_only_in_a_hedging_construction() -> None:
    hedge_review = _review(
        _revision("Zakres można dopasować do potrzeb firmy po wspólnej rozmowie.")
    )
    action_review = _review(
        _revision(
            "Zespół wykorzystuje brief, aby dopasować do potrzeb firmy program spotkania."
        )
    )

    assert "vague_answer_phrase" in _finding_codes(hedge_review)
    assert "vague_answer_phrase" not in _finding_codes(action_review)


def test_v2_review_does_not_flag_an_exact_concrete_answer() -> None:
    review = _review(
        _revision(
            "Przygotowujemy wniosek o pozwolenie zintegrowane oraz raport początkowy IPPC."
        )
    )

    assert "vague_answer_phrase" not in _finding_codes(review)


def test_v2_review_does_not_flag_a_vague_phrase_beside_a_concrete_signal() -> None:
    review = _review(
        _revision(
            "Możemy zebrać informacje i omówić zakres. Przygotowujemy wniosek o "
            "pozwolenie zintegrowane oraz raport początkowy IPPC."
        )
    )

    assert "vague_answer_phrase" not in _finding_codes(review)


def test_v2_review_flags_a_benefit_heading_without_a_buyer_benefit() -> None:
    review = _review(
        _revision(
            "Wymaga porównania zakresu i zasobów.",
            heading="Jakie korzyści daje outsourcing?",
        )
    )

    assert "vague_answer_phrase" in _finding_codes(review)


def test_v2_review_accepts_a_benefit_heading_with_buyer_benefits() -> None:
    review = _review(
        _revision(
            (
                "Pozwala uniknąć kosztów zatrudniania pracowników i gwarantuje terminowy "
                "nadzór."
            ),
            heading="Jakie korzyści daje outsourcing?",
        )
    )

    assert "vague_answer_phrase" not in _finding_codes(review)


def test_v2_review_does_not_apply_the_benefit_gate_to_other_headings() -> None:
    review = _review(
        _revision(
            "Wymaga porównania zakresu i zasobów.",
            heading="Zakres outsourcingu",
        )
    )

    assert "vague_answer_phrase" not in _finding_codes(review)


def test_pre_save_gate_surfaces_a_vague_answer_phrase() -> None:
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Czytelny zakres wsparcia",
            meta_title="Czytelny zakres wsparcia dla firmy",
            meta_description="Praktyczne informacje o zakresie wsparcia.",
            h1="Zakres wsparcia dla firmy",
            lead="Krótki przewodnik prowadzi przez najważniejsze działania.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_vague",
                heading="Zakres wsparcia",
                body_markdown=(
                    "Możemy omówić zakres podczas rozmowy. Szczegóły pozostają otwarte "
                    "dla zespołu i klienta."
                ),
            )
        ],
    )

    assert (
        "vague_answer_phrase",
        "section_vague",
        "Treść odsyła do ustalenia zakresu albo zebrania informacji zamiast podać konkret.",
    ) in readability_issues_for_output(output)


def test_legacy_review_without_revision_emits_no_readability_findings() -> None:
    review = _review(None)

    assert {
        "thin_section",
        "wall_of_text",
        "long_sentence",
        "heading_answer_mismatch",
        "vague_answer_phrase",
        "working_note",
        "duplicate_paragraph",
    }.isdisjoint(_finding_codes(review))


def test_v2_review_flags_a_source_working_note_in_a_section() -> None:
    review = _review(
        _revision(
            "Zgodnie z treścią źródła obowiązek aktualizacji wpisu w terminie 30 dni "
            "od dnia zmiany. Treść wymaga weryfikacji przez człowieka przed "
            "wykorzystaniem."
        )
    )

    working_note_findings = [
        finding for finding in review.findings if finding.code == "working_note"
    ]
    assert len(working_note_findings) == 1
    assert working_note_findings[0].severity == "needs_changes"
    assert working_note_findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"


def test_v2_review_ignores_a_section_without_a_working_note() -> None:
    review = _review(
        _revision(
            "Obowiązek wpisu może dotyczyć podmiotów wytwarzających odpady. "
            "Zakres obowiązku zależy od rodzaju prowadzonej działalności."
        )
    )

    assert "working_note" not in _finding_codes(review)


def test_v2_review_flags_a_duplicate_paragraph_inside_a_section() -> None:
    first = (
        "Wpis do Rejestru-BDO może dotyczyć podmiotów wytwarzających odpady "
        "oraz podmiotów wprowadzających produkty w opakowaniach."
    )
    second = (
        "Wpis do Rejestru-BDO może dotyczyć podmiotów wytwarzających odpady "
        "oraz podmiotów wprowadzających produkty w opakowaniach oraz opony."
    )
    review = _review(_revision(f"{first}\n\n{second}"))

    duplicate_findings = [
        finding for finding in review.findings if finding.code == "duplicate_paragraph"
    ]
    assert len(duplicate_findings) == 1
    assert duplicate_findings[0].severity == "needs_changes"
    assert duplicate_findings[0].affected_section == "Pierwsza sekcja"
    assert review.usefulness.status == "needs_changes"


def test_v2_review_ignores_distinct_paragraphs_in_a_section() -> None:
    first = (
        "Obowiązek wpisu może dotyczyć podmiotów wytwarzających odpady lub "
        "prowadzących ich ewidencję."
    )
    second = (
        "Zakres obowiązku zależy od rodzaju prowadzonej działalności, dlatego "
        "należy sprawdzić go w odpowiednich przepisach."
    )
    review = _review(_revision(f"{first}\n\n{second}"))

    assert "duplicate_paragraph" not in _finding_codes(review)


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
    heading: str = "Pierwsza sekcja",
) -> ContentDraftRevision:
    sections = [
        ContentDraftRevisionSection(
            section_id="section_one",
            heading=heading,
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


def test_turn_advisory_findings_include_reading_gates_even_without_review() -> None:
    from wilq.content.drafts.codex_section_proposal_turn import (
        _advisory_findings,
    )

    revision = _revision(
        "Treść wymaga weryfikacji przez człowieka przed wykorzystaniem.",
    )
    findings = _advisory_findings(
        None,
        base_revision=revision,
        selected_headings=["Pierwsza sekcja"],
        selected_cta_ids=[],
    )

    assert any(
        finding["finding_id"].startswith("readability_working_note_") for finding in findings
    )
    assert findings


def _finding_codes(review: ContentQualityReview) -> set[str]:
    return {finding.code for finding in review.findings}
