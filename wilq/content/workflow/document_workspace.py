from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.catalog import read_content_inventory_material
from wilq.content.workflow.decision_context import build_content_decision_context
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.content.workflow.store import content_workflow_store


class ContentDocumentWorkspaceSourceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    excerpt: str | None = None


class ContentDocumentWorkspaceSourceSnapshot(BaseModel):
    """Read-only public material; never an inferred WordPress authoring target."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "partial", "unavailable"]
    title: str | None = None
    url: str | None = None
    extraction_method: str | None = None
    lead: str | None = None
    content_excerpt: str | None = None
    ordered_sections: list[ContentDocumentWorkspaceSourceSection] = Field(default_factory=list)
    faq_status: Literal["observed", "not_observed", "unavailable"] = "not_observed"
    cta_status: Literal["observed", "not_observed", "unavailable"] = "not_observed"
    reason: str
    caveats: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentDocumentWorkspaceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "not_created", "unreviewed", "needs_changes", "approved", "rejected", "deferred"
    ]
    revision_id: str | None = None
    content_digest: str | None = None
    review_state: Literal["unreviewed", "needs_changes", "approved", "rejected", "deferred"] = (
        "unreviewed"
    )
    label: str
    reason: str
    preview: ContentDocumentWorkspaceDocumentPreview | None = None


class ContentDocumentWorkspaceDocumentSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str | None = None
    heading: str
    body_markdown: str
    content_html: str | None = None


class ContentDocumentWorkspaceDocumentPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    h1: str | None = None
    lead: str | None = None
    sections: list[ContentDocumentWorkspaceDocumentSection] = Field(default_factory=list)
    faq_count: int = 0
    cta_count: int = 0


class ContentDocumentWorkspaceNextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["open_review", "prepare_document", "none"]
    label: str
    reason: str


class ContentDocumentWorkspaceComparisonItem(BaseModel):
    """One honest source/document relation; never a semantic similarity guess."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["same_heading", "source_only", "document_only"]
    source_heading: str | None = None
    source_excerpt: str | None = None
    document_section_id: str | None = None
    document_heading: str | None = None
    document_excerpt: str | None = None
    reason: str


class ContentDocumentWorkspaceComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "unavailable"]
    reason: str
    items: list[ContentDocumentWorkspaceComparisonItem] = Field(default_factory=list)


class ContentDocumentWorkspace(BaseModel):
    """One marketer-facing, read-only workspace for an existing public page."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_document_workspace"] = "content_document_workspace"
    contract_version: Literal["content_document_workspace_v1"] = "content_document_workspace_v1"
    work_item_id: str
    work_kind: Literal["refresh_existing"]
    service_label: str | None = None
    source_snapshot: ContentDocumentWorkspaceSourceSnapshot
    canonical_document: ContentDocumentWorkspaceDocument
    comparison: ContentDocumentWorkspaceComparison
    next_action: ContentDocumentWorkspaceNextAction
    secondary_disclosures: list[str] = Field(default_factory=list)


def build_content_document_workspace(work_item_id: str) -> ContentDocumentWorkspace | None:
    """Build a source-first workspace without planning, generation or delivery reads."""

    context = build_content_decision_context(work_item_id)
    if context is None or context.work_kind != "refresh_existing":
        return None
    source = (
        None
        if context.source_public.url is None
        else read_content_inventory_material(context.source_public.url)
    )
    source_snapshot = _source_snapshot(context, source)
    revision_state = content_workflow_store().load_draft_revision_state(work_item_id)
    document = _canonical_document(revision_state.status, revision_state.latest_revision)
    return ContentDocumentWorkspace(
        work_item_id=work_item_id,
        work_kind="refresh_existing",
        service_label=context.service.label,
        source_snapshot=source_snapshot,
        canonical_document=document,
        comparison=_comparison(source_snapshot, revision_state.latest_revision),
        next_action=_next_action(document),
        secondary_disclosures=[
            (
                "Target WordPress może pozostać nieznany: blokuje to dopiero delivery, "
                "nie odczyt źródła ani dokumentu."
            ),
            (
                "Snapshot źródła opisuje publiczny materiał. Nie jest mapą ACF, "
                "Gutenberga ani the_content."
            ),
        ],
    )


def _source_snapshot(context, material) -> ContentDocumentWorkspaceSourceSnapshot:
    if material is None or material.status != "ready":
        return ContentDocumentWorkspaceSourceSnapshot(
            status="unavailable",
            title=context.source_public.title,
            url=context.source_public.url,
            reason="Aktualny materiał publicznej strony nie jest dostępny do odczytu.",
            faq_status="unavailable",
            cta_status="unavailable",
            caveats=[context.source_public.reason],
            evidence_ids=list(context.source_public.material.evidence_ids),
        )
    headings = material.acf_section_headings or material.section_headings
    text = (material.content_text or "").strip()
    lead = _lead(text)
    status: Literal["available", "partial", "unavailable"] = "available" if text else "partial"
    return ContentDocumentWorkspaceSourceSnapshot(
        status=status,
        title=material.title or context.source_public.title,
        url=material.url,
        extraction_method=material.extraction_region or material.source_kind,
        lead=lead,
        content_excerpt=_excerpt(text),
        ordered_sections=[
            ContentDocumentWorkspaceSourceSection(heading=heading, excerpt=excerpt)
            for heading, excerpt in _source_sections(text, headings)
        ],
        faq_status="not_observed",
        cta_status="not_observed",
        reason=(
            "WILQ odczytał aktualny publiczny materiał tej strony."
            if text
            else "WILQ odczytał strukturę strony, ale nie pełny tekst jej głównej treści."
        ),
        caveats=[
            (
                "FAQ i CTA nie są tu rozpoznawane heurystycznie; ich brak w tym widoku "
                "nie znaczy, że nie istnieją na stronie."
            ),
            "Odczyt źródła nie potwierdza miejsca authoringu ani mapowania dev.",
        ],
        evidence_ids=list(
            dict.fromkeys(
                value
                for value in [
                    material.evidence_id,
                    *context.source_public.material.evidence_ids,
                ]
                if value
            )
        ),
    )


def _lead(text: str) -> str | None:
    if not text:
        return None
    for paragraph in text.split("\n\n"):
        candidate = paragraph.strip()
        if candidate and not candidate.startswith("#"):
            return _excerpt(candidate, limit=420)
    return _excerpt(text, limit=420)


def _excerpt(text: str, *, limit: int = 1000) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    boundary = max(text.rfind(marker, 0, limit) for marker in (". ", "! ", "? ", "\n"))
    if boundary < max(80, limit // 2):
        boundary = text.rfind(" ", 0, limit)
    if boundary <= 0:
        boundary = limit
    return f"{text[: boundary + 1].rstrip()}…"


def _source_sections(text: str, headings: list[str]) -> list[tuple[str, str | None]]:
    """Split only at exact observed headings; a missing match remains an honest outline item."""

    positions: list[tuple[str, int]] = []
    cursor = 0
    folded_text = text.casefold()
    for heading in headings:
        clean_heading = heading.strip()
        if not clean_heading:
            continue
        position = folded_text.find(clean_heading.casefold(), cursor)
        if position < 0:
            positions.append((clean_heading, -1))
            continue
        positions.append((clean_heading, position))
        cursor = position + len(clean_heading)
    sections: list[tuple[str, str | None]] = []
    for index, (heading, position) in enumerate(positions):
        if position < 0:
            sections.append((heading, None))
            continue
        next_positions = [
            item_position
            for _, item_position in positions[index + 1 :]
            if item_position >= 0
        ]
        end = next_positions[0] if next_positions else len(text)
        body = text[position + len(heading) : end].strip()
        sections.append((heading, _excerpt(body, limit=460)))
    return sections


def _canonical_document(status: str, revision) -> ContentDocumentWorkspaceDocument:
    if revision is None:
        return ContentDocumentWorkspaceDocument(
            status="not_created",
            label="Nowa wersja nie została jeszcze przygotowana",
            reason="WILQ ma materiał źródłowy, ale nie ma jeszcze zapisanej rewizji dokumentu.",
        )
    normalized = (
        status
        if status in {"unreviewed", "needs_changes", "approved", "rejected", "deferred"}
        else "unreviewed"
    )
    labels = {
        "unreviewed": "Nowa wersja czeka na review",
        "needs_changes": "Nowa wersja wymaga zmian",
        "approved": "Dokument zatwierdzony",
        "rejected": "Dokument odrzucony",
        "deferred": "Review dokumentu odłożone",
    }
    reasons = {
        "unreviewed": "Istnieje dokładna rewizja dokumentu, ale nie ma jeszcze decyzji człowieka.",
        "needs_changes": "Istnieje dokładna rewizja, dla której zapisano decyzję: wymaga zmian.",
        "approved": (
            "Dokument został zatwierdzony dla dokładnej rewizji. Nie został jeszcze "
            "przygotowany do konkretnego układu WordPressa."
        ),
        "rejected": "Istnieje dokładna rewizja, dla której zapisano decyzję: odrzucona.",
        "deferred": "Review dokładnej rewizji został odłożony.",
    }
    return ContentDocumentWorkspaceDocument(
        status=normalized,
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        review_state=normalized,
        label=labels[normalized],
        reason=reasons[normalized],
        preview=_document_preview(revision),
    )


def _document_preview(revision: ContentDraftRevision) -> ContentDocumentWorkspaceDocumentPreview:
    assets = revision.page_assets
    return ContentDocumentWorkspaceDocumentPreview(
        title=revision.title,
        h1=None if assets is None else assets.h1,
        lead=None if assets is None else assets.lead,
        sections=[
            ContentDocumentWorkspaceDocumentSection(
                section_id=section.section_id,
                heading=section.heading,
                body_markdown=section.body_markdown,
                content_html=section.content_html,
            )
            for section in revision.sections
        ],
        faq_count=len(revision.faq),
        cta_count=len(revision.cta_blocks),
    )


def _comparison(
    source: ContentDocumentWorkspaceSourceSnapshot,
    revision: ContentDraftRevision | None,
) -> ContentDocumentWorkspaceComparison:
    if revision is None:
        return ContentDocumentWorkspaceComparison(
            status="unavailable",
            reason="Porównanie pojawi się po zapisaniu nowej wersji dokumentu.",
        )
    source_by_heading: dict[str, list[tuple[int, ContentDocumentWorkspaceSourceSection]]] = {}
    for source_index, section in enumerate(source.ordered_sections):
        source_by_heading.setdefault(_heading_key(section.heading), []).append(
            (source_index, section)
        )
    items: list[ContentDocumentWorkspaceComparisonItem] = []
    matched_source_indices: set[int] = set()
    for section in revision.sections:
        key = _heading_key(section.heading)
        candidates = source_by_heading.get(key, [])
        source_match = candidates.pop(0) if candidates else None
        if source_match is None:
            items.append(
                ContentDocumentWorkspaceComparisonItem(
                    status="document_only",
                    document_section_id=section.section_id,
                    document_heading=section.heading,
                    document_excerpt=_excerpt(section.body_markdown, limit=460),
                    reason=(
                        "Ta sekcja nie ma bezpośrednio rozpoznanego odpowiednika "
                        "w układzie obecnej strony."
                    ),
                )
            )
            continue
        source_index, source_section = source_match
        matched_source_indices.add(source_index)
        items.append(
            ContentDocumentWorkspaceComparisonItem(
                status="same_heading",
                source_heading=source_section.heading,
                source_excerpt=source_section.excerpt,
                document_section_id=section.section_id,
                document_heading=section.heading,
                document_excerpt=_excerpt(section.body_markdown, limit=460),
                reason=(
                    "Obie wersje mają identycznie odczytany nagłówek. WILQ nie ocenia "
                    "automatycznie, czy znaczenie akapitów jest takie samo."
                ),
            )
        )
    for source_index, source_section in enumerate(source.ordered_sections):
        if source_index in matched_source_indices:
            continue
        items.append(
            ContentDocumentWorkspaceComparisonItem(
                status="source_only",
                source_heading=source_section.heading,
                source_excerpt=source_section.excerpt,
                reason=(
                    "Ten element układu obecnej strony nie ma bezpośrednio rozpoznanego "
                    "odpowiednika w nowym dokumencie."
                ),
            )
        )
    return ContentDocumentWorkspaceComparison(
        status="available",
        reason=(
            "Porównanie pokazuje tylko jednoznaczne relacje nagłówków oraz elementy "
            "występujące po jednej stronie."
        ),
        items=items,
    )


def _heading_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _next_action(document: ContentDocumentWorkspaceDocument) -> ContentDocumentWorkspaceNextAction:
    if document.status == "approved":
        return ContentDocumentWorkspaceNextAction(
            kind="open_review",
            label="Zobacz zatwierdzony dokument",
            reason="Przejdziesz do dokładnej, zatwierdzonej rewizji bez uruchamiania delivery.",
        )
    if document.status == "unreviewed":
        return ContentDocumentWorkspaceNextAction(
            kind="open_review",
            label="Przejdź do review",
            reason="Dokument istnieje i czeka na decyzję człowieka.",
        )
    if document.status == "not_created":
        return ContentDocumentWorkspaceNextAction(
            kind="prepare_document",
            label="Przygotuj nową wersję",
            reason=(
                "Przygotowanie dokumentu jest kolejnym krokiem; ten read-only workspace "
                "nie uruchamia generowania."
            ),
        )
    return ContentDocumentWorkspaceNextAction(
        kind="none",
        label="Brak kolejnej bezpiecznej akcji",
        reason=document.reason,
    )


__all__ = ["ContentDocumentWorkspace", "build_content_document_workspace"]
