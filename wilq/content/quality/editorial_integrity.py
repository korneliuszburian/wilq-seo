from __future__ import annotations

import re
from collections.abc import Iterable
from hashlib import sha256
from html.parser import HTMLParser

from wilq.content.workflow.contracts import (
    ContentEditorialIntegrityHumanReview,
    ContentEditorialIntegrityReport,
    ContentEditorialIntegrityRevision,
    ContentEditorialIntegrityScope,
    ContentEditorialLintSignal,
    ContentEditorialStructuralInvariants,
    ContentProtectedContentUnit,
    ContentRepresentationAlignment,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[\wąćęłńóśźż]+", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
_STOPWORDS = frozenset(
    {
        "aby",
        "albo",
        "będzie",
        "być",
        "co",
        "czy",
        "dla",
        "do",
        "i",
        "ich",
        "jak",
        "jest",
        "je",
        "już",
        "lub",
        "ma",
        "może",
        "na",
        "nad",
        "nie",
        "o",
        "od",
        "oraz",
        "po",
        "przed",
        "przez",
        "się",
        "są",
        "ta",
        "tak",
        "te",
        "ten",
        "to",
        "w",
        "we",
        "z",
        "za",
        "ze",
    }
)
_LINT_ROOTS = ("warto", "należ", "weryfik", "uporządk")


def build_content_editorial_integrity_report(
    *,
    work_item_id: str,
    revision_id: str,
    revisions: Iterable[ContentDraftRevision],
    human_review: ContentDraftRevisionReview | None = None,
) -> ContentEditorialIntegrityReport:
    """Compare one immutable child with a stable same-structure ancestor.

    The report is intentionally lexical and structural. It surfaces where a
    human must judge meaning; it never calls a style score an editorial verdict.
    """

    by_id = {revision.revision_id: revision for revision in revisions}
    child = by_id.get(revision_id)
    if child is None or child.work_item_id != work_item_id:
        raise ValueError("Nie znaleziono wskazanej rewizji tego zadania.")
    direct_parent = None if child.base_revision_id is None else by_id.get(child.base_revision_id)
    if direct_parent is None:
        raise ValueError("Raport integralności wymaga rewizji z zapisaną wersją bazową.")
    baseline = _stable_baseline(child, by_id)
    invariants = _structural_invariants(baseline, child)
    alignment = [
        _representation_alignment(section) for section in child.sections if section.section_id
    ]
    protected_units = _protected_units(baseline, child)
    lint_signals = _lint_signals(child)
    result = _result(invariants, alignment)
    return ContentEditorialIntegrityReport(
        work_item_id=work_item_id,
        baseline_revision=_identity(baseline),
        direct_parent_revision=_identity(direct_parent),
        child_revision=_identity(child),
        human_review=_exact_human_review(child, human_review),
        observed_scope=_observed_scope(baseline, child),
        structural_invariants=invariants,
        protected_content_units=protected_units,
        representation_alignment=alignment,
        lint_signals=lint_signals,
        human_readable_diff=_diff_summary(invariants, protected_units, alignment, lint_signals),
        result=result,
    )


def _stable_baseline(
    child: ContentDraftRevision, by_id: dict[str, ContentDraftRevision]
) -> ContentDraftRevision:
    """Use the oldest ancestor with unchanged document structure.

    A canonical-HTML repair must not hide a preceding content loss merely
    because its direct parent already contains the reduced body.
    """

    baseline = by_id[child.base_revision_id or ""]
    cursor = baseline
    while cursor.base_revision_id:
        ancestor = by_id.get(cursor.base_revision_id)
        if ancestor is None or not _same_document_structure(ancestor, child):
            break
        baseline = ancestor
        cursor = ancestor
    return baseline


def _identity(revision: ContentDraftRevision) -> ContentEditorialIntegrityRevision:
    return ContentEditorialIntegrityRevision(
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        revision_number=revision.revision_number,
    )


def _exact_human_review(
    child: ContentDraftRevision,
    human_review: ContentDraftRevisionReview | None,
) -> ContentEditorialIntegrityHumanReview | None:
    if (
        human_review is None
        or human_review.revision_id != child.revision_id
        or human_review.revision_digest != child.content_digest
    ):
        return None
    return ContentEditorialIntegrityHumanReview(
        decision=human_review.decision,
        reviewed_by=human_review.reviewed_by,
    )


def _same_document_structure(left: ContentDraftRevision, right: ContentDraftRevision) -> bool:
    return (
        _section_ids(left) == _section_ids(right)
        and [section.heading for section in left.sections]
        == [section.heading for section in right.sections]
        and left.title == right.title
    )


def _section_ids(revision: ContentDraftRevision) -> list[str | None]:
    return [section.section_id for section in revision.sections]


def _structural_invariants(
    parent: ContentDraftRevision, child: ContentDraftRevision
) -> ContentEditorialStructuralInvariants:
    return ContentEditorialStructuralInvariants(
        section_ids_unchanged=set(_section_ids(parent)) == set(_section_ids(child)),
        section_order_unchanged=_section_ids(parent) == _section_ids(child),
        headings_unchanged=[section.heading for section in parent.sections]
        == [section.heading for section in child.sections],
        title_unchanged=parent.title == child.title,
        faq_unchanged=parent.faq == child.faq,
        cta_semantics_unchanged=parent.cta_blocks == child.cta_blocks,
        links_unchanged=parent.internal_links == child.internal_links,
        evidence_lineage_unchanged=_lineage(parent) == _lineage(child),
    )


def _lineage(revision: ContentDraftRevision) -> list[tuple[object, ...]]:
    return [
        (
            section.section_id,
            section.evidence_ids,
            section.claim_ids,
            section.source_material_ids,
            section.knowledge_card_ids,
        )
        for section in revision.sections
    ]


def _observed_scope(
    parent: ContentDraftRevision, child: ContentDraftRevision
) -> ContentEditorialIntegrityScope:
    fields: list[str] = []
    changed_sections = [
        section.section_id
        for parent_section, section in zip(parent.sections, child.sections, strict=False)
        if parent_section.body_markdown != section.body_markdown and section.section_id
    ]
    if changed_sections:
        fields.append("body")
    if parent.title != child.title:
        fields.append("title")
    if parent.faq != child.faq:
        fields.append("faq")
    if parent.cta_blocks != child.cta_blocks:
        fields.append("cta")
    if parent.internal_links != child.internal_links:
        fields.append("links")
    return ContentEditorialIntegrityScope(section_ids=changed_sections, fields=fields)


def _representation_alignment(
    section: ContentDraftRevisionSection,
) -> ContentRepresentationAlignment:
    source_text = _normalized_text(section.body_markdown)
    html = section.content_html
    rendered_text = None if html is None else _normalized_text(_html_text(html))
    return ContentRepresentationAlignment(
        section_id=section.section_id or section.heading,
        section_heading=section.heading,
        source_body_sha256=_hash(section.body_markdown),
        rendered_html_sha256=None if html is None else _hash(html),
        normalized_source_text_sha256=_hash(source_text),
        normalized_rendered_text_sha256=(None if rendered_text is None else _hash(rendered_text)),
        status="aligned" if rendered_text == source_text else "mismatch",
    )


def _protected_units(
    parent: ContentDraftRevision, child: ContentDraftRevision
) -> list[ContentProtectedContentUnit]:
    child_by_id = {section.section_id: section for section in child.sections}
    units: list[ContentProtectedContentUnit] = []
    for section in parent.sections:
        if not section.section_id:
            continue
        candidate = child_by_id.get(section.section_id)
        for sentence in _sentences(section.body_markdown):
            anchors = _anchors(sentence)
            if len(anchors) < 3:
                continue
            matched = _best_sentence_match(
                anchors, _sentences(candidate.body_markdown) if candidate else []
            )
            coverage = _coverage(anchors, matched)
            status = "preserved" if coverage >= 0.7 else "changed"
            if coverage < 0.35:
                status = "removed"
            units.append(
                ContentProtectedContentUnit(
                    unit_id=f"unit_{_hash(f'{section.section_id}:{sentence}')[:16]}",
                    section_id=section.section_id,
                    section_heading=section.heading,
                    claim_ids=section.claim_ids,
                    evidence_ids=section.evidence_ids,
                    before_excerpt=sentence,
                    after_excerpt=matched or None,
                    status=status,
                )
            )
    return units


def _lint_signals(revision: ContentDraftRevision) -> list[ContentEditorialLintSignal]:
    signals: list[ContentEditorialLintSignal] = []
    all_body = "\n".join(section.body_markdown for section in revision.sections)
    em_dash_count = all_body.count("—")
    if em_dash_count:
        signals.append(
            ContentEditorialLintSignal(
                code="em_dash",
                occurrences=em_dash_count,
                excerpts=[
                    section.heading for section in revision.sections if "—" in section.body_markdown
                ],
                reason="Wykryto długie myślniki w body; ich zasadność wymaga oceny redakcyjnej.",
            )
        )
    roots = _stemmed_words(all_body)
    for root in _LINT_ROOTS:
        count = sum(1 for word in roots if word.startswith(root))
        if count >= 3:
            signals.append(
                ContentEditorialLintSignal(
                    code=f"repeated_root_{root.rstrip('ż')}",
                    occurrences=count,
                    excerpts=[],
                    reason=(
                        f"Rdzeń „{root}” powtarza się {count} razy; raport nie ocenia, "
                        "czy to błąd stylu."
                    ),
                )
            )
    openings = [
        " ".join(_words(sentence)[:4])
        for section in revision.sections
        for sentence in _sentences(section.body_markdown)
    ]
    for opening in sorted(set(openings)):
        count = openings.count(opening)
        if opening and count >= 2:
            signals.append(
                ContentEditorialLintSignal(
                    code="repeated_sentence_opening",
                    occurrences=count,
                    excerpts=[opening],
                    reason=(
                        "Powtarza się początek zdań; potrzebna jest ocena redakcyjna, "
                        "nie automatyczna korekta."
                    ),
                )
            )
    return signals


def _result(
    invariants: ContentEditorialStructuralInvariants,
    alignment: list[ContentRepresentationAlignment],
) -> str:
    if any(item.status == "mismatch" for item in alignment):
        return "invalid_representation"
    if not all(invariants.model_dump().values()):
        return "structural_change_observed"
    return "integrity_ok"


def _diff_summary(
    invariants: ContentEditorialStructuralInvariants,
    units: list[ContentProtectedContentUnit],
    alignment: list[ContentRepresentationAlignment],
    lint: list[ContentEditorialLintSignal],
) -> str:
    removed = sum(unit.status == "removed" for unit in units)
    changed = sum(unit.status == "changed" for unit in units)
    mismatches = sum(item.status == "mismatch" for item in alignment)
    changed_invariants = sum(not value for value in invariants.model_dump().values())
    return (
        f"Niezmienniki struktury naruszone: {changed_invariants}; "
        f"niespójne reprezentacje body/HTML: {mismatches}; "
        f"sygnały leksykalne: zmienione {changed}; niedopasowane {removed}; "
        f"sygnały redakcyjne: {len(lint)}."
    )


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip() for sentence in _SENTENCE_SPLIT.split(text.strip()) if sentence.strip()
    ]


def _best_sentence_match(anchors: set[str], candidates: list[str]) -> str:
    if not candidates:
        return ""
    return max(candidates, key=lambda candidate: _coverage(anchors, candidate))


def _coverage(anchors: set[str], candidate: str) -> float:
    if not anchors:
        return 0.0
    return len(anchors.intersection(_anchors(candidate))) / len(anchors)


def _anchors(text: str) -> set[str]:
    return {word for word in _stemmed_words(text) if len(word) >= 4 and word not in _STOPWORDS}


def _words(text: str) -> list[str]:
    return [word.casefold() for word in _WORD.findall(text)]


def _stemmed_words(text: str) -> list[str]:
    # This is intentionally only a lexical anchor, not Polish lemmatisation.
    # Five characters keep forms such as „rodzaje”/„rodzajów” comparable while
    # leaving the final meaning judgement to the reviewer.
    return [word[:5] for word in _words(text)]


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalized_text(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self.chunks.append(data)


def _html_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return " ".join(parser.chunks)


__all__ = ["build_content_editorial_integrity_report"]
