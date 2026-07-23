from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionReview
from wilq.content.workflow.target_discovery import (
    ContentTargetContract,
    ContentTargetDiscovery,
    ContentTargetObservationEvidence,
)


class ContentTargetMappingRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ContentTargetMappingTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_contract: ContentTargetContract
    target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_evidence: ContentTargetObservationEvidence


ContentTargetMappingComponentKind = Literal[
    "document_title",
    "page_assets",
    "rich_text",
    "faq",
    "cta",
    "internal_link",
]
ContentTargetMappingComponentStatus = Literal["mapped", "human_only", "blocked"]


class ContentTargetMappingComponent(BaseModel):
    """One canonical document component, never a generated WordPress payload."""

    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1)
    kind: ContentTargetMappingComponentKind
    label: str = Field(min_length=1)
    status: ContentTargetMappingComponentStatus
    reason: str = Field(min_length=1)
    target_root_field: str | None = None
    available_layouts: list[str] = Field(default_factory=list)


class ContentTargetMappingBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "revision_not_approved",
        "target_unavailable",
        "target_ambiguous",
        "authoring_surface_unknown",
    ]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class ContentTargetMappingPreview(BaseModel):
    """Read-only relation between an exact revision and an observed target contract."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_mapping_preview"] = "content_target_mapping_preview"
    contract_version: Literal["content_target_mapping_preview_v1"] = (
        "content_target_mapping_preview_v1"
    )
    work_item_id: str = Field(min_length=1)
    revision: ContentTargetMappingRevision
    status: Literal["ready_for_human_mapping", "blocked"]
    target: ContentTargetMappingTarget | None = None
    binding_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    components: list[ContentTargetMappingComponent] = Field(default_factory=list)
    blockers: list[ContentTargetMappingBlocker] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_exact_ready_binding(self) -> ContentTargetMappingPreview:
        if self.status == "ready_for_human_mapping":
            if self.target is None or self.binding_digest is None:
                raise ValueError("Ready mapping preview requires an exact target binding.")
            if self.blockers:
                raise ValueError("Ready mapping preview cannot expose blockers.")
        elif self.binding_digest is not None:
            raise ValueError("Blocked mapping preview cannot expose a binding digest.")
        return self


def build_content_target_mapping_preview(
    *,
    work_item_id: str,
    revision_id: str,
    revisions: list[ContentDraftRevision],
    human_review: ContentDraftRevisionReview | None,
    discovery: ContentTargetDiscovery,
) -> ContentTargetMappingPreview:
    revision = next(
        (
            candidate
            for candidate in revisions
            if candidate.work_item_id == work_item_id and candidate.revision_id == revision_id
        ),
        None,
    )
    if revision is None:
        raise ValueError("Nie znaleziono wskazanej rewizji tego zadania.")
    identity = ContentTargetMappingRevision(
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
    )
    components = _components(revision)
    if not _is_exact_approved_review(revision, human_review):
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            components=components,
            blocker=ContentTargetMappingBlocker(
                code="revision_not_approved",
                label="Dokument wymaga zatwierdzenia",
                reason=(
                    "Mapowanie można przygotować wyłącznie dla dokładnej rewizji "
                    "zatwierdzonej przez człowieka."
                ),
                next_step="Otwórz review tej rewizji i zapisz decyzję człowieka.",
            ),
        )
    target, target_blocker = _target_or_blocker(discovery)
    if target_blocker is not None:
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            components=components,
            blocker=target_blocker,
        )
    assert target is not None
    surface = target.target_contract.authoring_surface
    if surface is None or not surface.layouts:
        surface_reason = (
            "WILQ zna dokładny obiekt dev, ale nie odczytał pola ani układu, "
            "do którego można przypisać dokument."
            if surface is None
            else (
                "WILQ odczytał pole układu treści, ale nie odczytał żadnego "
                "layoutu, do którego można przypisać dokument."
            )
        )
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            target=target,
            components=components,
            blocker=ContentTargetMappingBlocker(
                code="authoring_surface_unknown",
                label="Nie rozpoznano układu treści na dev",
                reason=surface_reason,
                next_step=(
                    "Odczytaj potwierdzoną powierzchnię authoringu tego obiektu bez "
                    "zgadywania pola lub layoutu."
                ),
            ),
        )
    human_components = [
        component.model_copy(
            update={
                "status": "human_only",
                "reason": (
                    "Odczyt targetu pokazuje dostępny układ, ale nie zawiera "
                    "zatwierdzonego przypisania tego elementu dokumentu do konkretnego pola."
                ),
                "target_root_field": surface.root_field,
                "available_layouts": [layout.name for layout in surface.layouts],
            }
        )
        for component in components
    ]
    binding_digest = _binding_digest(identity, target, human_components)
    return ContentTargetMappingPreview(
        work_item_id=work_item_id,
        revision=identity,
        status="ready_for_human_mapping",
        target=target,
        binding_digest=binding_digest,
        components=human_components,
        caveats=[
            "To jest podgląd do decyzji człowieka, nie zapis do WordPressa.",
            "Zmiana rewizji albo kontraktu targetu wymaga nowego odczytu mapowania.",
        ],
    )


def _target_or_blocker(
    discovery: ContentTargetDiscovery,
) -> tuple[ContentTargetMappingTarget | None, ContentTargetMappingBlocker | None]:
    if discovery.relation_status == "ambiguous":
        return None, ContentTargetMappingBlocker(
            code="target_ambiguous",
            label="Wymagany jest wybór obiektu dev",
            reason=(
                "WILQ odczytał kilka obiektów dev o tym samym adresie i nie "
                "wybiera jednego samodzielnie."
            ),
            next_step="Potwierdź właściwy obiekt dev, zanim powstanie mapowanie.",
        )
    if discovery.relation_status != "partial" or discovery.target is None:
        return None, ContentTargetMappingBlocker(
            code="target_unavailable",
            label="Brakuje potwierdzonego odczytu obiektu dev",
            reason=discovery.reason,
            next_step=(
                "Otwórz odczyt dev ponownie, gdy inventory będzie dostępne i "
                "wskaże jeden obiekt."
            ),
        )
    return ContentTargetMappingTarget(
        target_contract=discovery.target.target_contract,
        target_contract_digest=discovery.target.target_contract_digest,
        observation_evidence=discovery.target.observation_evidence,
    ), None


def _components(revision: ContentDraftRevision) -> list[ContentTargetMappingComponent]:
    components = [
        _component("document-title", "document_title", "Tytuł dokumentu"),
    ]
    if revision.page_assets is not None:
        components.append(_component("page-assets", "page_assets", "Lead i meta strony"))
    components.extend(
        _component(
            f"section:{section.section_id or index}",
            "rich_text",
            section.heading,
        )
        for index, section in enumerate(revision.sections, start=1)
    )
    components.extend(
        _component(f"faq:{item.faq_id}", "faq", item.question) for item in revision.faq
    )
    components.extend(
        _component(f"cta:{item.cta_id}", "cta", "Wezwanie do działania")
        for item in revision.cta_blocks
    )
    components.extend(
        _component(f"link:{item.link_id}", "internal_link", item.anchor_text)
        for item in revision.internal_links
    )
    return components


def _component(
    component_id: str,
    kind: ContentTargetMappingComponentKind,
    label: str,
) -> ContentTargetMappingComponent:
    return ContentTargetMappingComponent(
        component_id=component_id,
        kind=kind,
        label=label,
        status="blocked",
        reason="Nie ma jeszcze potwierdzonego układu targetu dla tego elementu.",
    )


def _blocked(
    *,
    work_item_id: str,
    revision: ContentTargetMappingRevision,
    components: list[ContentTargetMappingComponent],
    blocker: ContentTargetMappingBlocker,
    target: ContentTargetMappingTarget | None = None,
) -> ContentTargetMappingPreview:
    return ContentTargetMappingPreview(
        work_item_id=work_item_id,
        revision=revision,
        status="blocked",
        target=target,
        components=[
            component.model_copy(update={"reason": blocker.reason}) for component in components
        ],
        blockers=[blocker],
        caveats=["Nie przygotowano payloadu, draftu ani zapisu do WordPressa."],
    )


def _is_exact_approved_review(
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview | None,
) -> bool:
    return bool(
        review
        and review.decision == "approved"
        and review.revision_id == revision.revision_id
        and review.revision_digest == revision.content_digest
    )


def _binding_digest(
    revision: ContentTargetMappingRevision,
    target: ContentTargetMappingTarget,
    components: list[ContentTargetMappingComponent],
) -> str:
    payload = {
        "revision": revision.model_dump(mode="json"),
        "target_contract_digest": target.target_contract_digest,
        "components": [component.model_dump(mode="json") for component in components],
    }
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


__all__ = ["ContentTargetMappingPreview", "build_content_target_mapping_preview"]
