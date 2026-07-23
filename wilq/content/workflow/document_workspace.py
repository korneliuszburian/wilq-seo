from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.catalog import read_content_inventory_material
from wilq.content.workflow.decision_context import build_content_decision_context
from wilq.content.workflow.store import content_workflow_store


class ContentDocumentWorkspaceSourceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str


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


class ContentDocumentWorkspaceNextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["open_review", "prepare_document", "none"]
    label: str
    reason: str


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
            ContentDocumentWorkspaceSourceSection(heading=heading) for heading in headings
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
            return candidate[:420]
    return text[:420]


def _excerpt(text: str) -> str | None:
    if not text:
        return None
    return text[:1000]


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
    )


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
