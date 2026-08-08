from __future__ import annotations

import json
from hashlib import sha256
from html import escape
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.handoff.revision_document_renderer import revision_document_html
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.target.target_discovery import (
    ContentTargetContract,
    ContentTargetDiscovery,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target.target_mapping_blockers import (
    ContentTargetMappingBlocker,
    authoring_surface_blocker,
    discovery_blocker,
)
from wilq.content.workflow.target.target_mapping_preview_models import (
    ContentTargetDraftPreviewBlocker,
    ContentTargetDraftPreviewField,
    ContentTargetDraftPreviewPreservedSourceSummary,
)
from wilq.content.workflow.target.target_mapping_source_fields import (
    ContentTargetSourceKind,
    source_field_specs,
)
from wilq.content.workflow.workspace.delivery_projection import project_target_field_value


class ContentTargetMappingRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ContentTargetMappingTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_contract: ContentTargetContract
    target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_evidence: ContentTargetObservationEvidence


ContentTargetMappingComponentKind = ContentTargetSourceKind
ContentTargetMappingComponentStatus = Literal["mapped", "human_only", "blocked"]
ContentTargetMappingDeliveryScope = Literal["full_document", "selected_components"]


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
    source_fields: list[ContentTargetMappingSourceField] = Field(default_factory=list)


class ContentTargetMappingSourceField(BaseModel):
    """One named value from the canonical document that a human may map."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)


class ContentTargetMappingFieldBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_field: str = Field(min_length=1)
    target_field: str = Field(min_length=1)


class ContentTargetMappingSelection(BaseModel):
    """A human choice for one component; it never contains WordPress payload data."""

    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1)
    layout_name: str = Field(min_length=1)
    target_section_index: int | None = Field(default=None, ge=1)
    field_bindings: list[ContentTargetMappingFieldBinding] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_fields(self) -> ContentTargetMappingSelection:
        source_fields = [binding.source_field for binding in self.field_bindings]
        if len(source_fields) != len(set(source_fields)):
            raise ValueError("A component mapping cannot bind one source field twice.")
        return self


class ContentTargetMappingConfirmationCommand(BaseModel):
    """Local human confirmation of an exact, observed mapping preview."""

    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_by: str = Field(min_length=1)
    delivery_scope: ContentTargetMappingDeliveryScope = "full_document"
    selections: list[ContentTargetMappingSelection] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_components(self) -> ContentTargetMappingConfirmationCommand:
        component_ids = [selection.component_id for selection in self.selections]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("A mapping confirmation cannot select one component twice.")
        if not self.confirmed_by.strip():
            raise ValueError("Mapping confirmation requires a visible operator.")
        return self


class ContentTargetMappingConfirmation(BaseModel):
    """Immutable local decision that may later be referenced by a draft-only action."""

    model_config = ConfigDict(extra="forbid")

    confirmation_id: str = Field(min_length=1)
    confirmation_number: int = Field(ge=1)
    work_item_id: str = Field(min_length=1)
    revision: ContentTargetMappingRevision
    target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    delivery_scope: ContentTargetMappingDeliveryScope = "full_document"
    selections: list[ContentTargetMappingSelection] = Field(min_length=1)
    confirmed_by: str = Field(min_length=1)
    confirmation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(min_length=1)


class ContentTargetMappingConfirmationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["created", "idempotent"]
    confirmation: ContentTargetMappingConfirmation


class ContentTargetDraftPreviewComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    layout_name: str = Field(min_length=1)
    target_section_index: int | None = Field(default=None, ge=1)
    fields: list[ContentTargetDraftPreviewField] = Field(min_length=1)


class ContentTargetDraftPreview(BaseModel):
    """Exact payload preview; it is not an ActionObject and never writes WordPress."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_draft_preview"] = "content_target_draft_preview"
    contract_version: Literal["content_target_draft_preview_v1"] = "content_target_draft_preview_v1"
    work_item_id: str = Field(min_length=1)
    revision: ContentTargetMappingRevision
    status: Literal["ready", "blocked"]
    target: ContentTargetMappingTarget | None = None
    confirmation: ContentTargetMappingConfirmation | None = None
    root_field: str | None = None
    delivery_scope: ContentTargetMappingDeliveryScope = "full_document"
    draft_title: str | None = None
    components: list[ContentTargetDraftPreviewComponent] = Field(default_factory=list)
    preserved_source_summary: ContentTargetDraftPreviewPreservedSourceSummary | None = None
    payload_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    blockers: list[ContentTargetDraftPreviewBlocker] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_exact_ready_payload(self) -> ContentTargetDraftPreview:
        if self.status == "ready":
            has_document_title = any(
                component.component_id == "document-title"
                and any(field.source_field == "wordpress_title" for field in component.fields)
                for component in self.components
            )
            if (
                self.target is None
                or self.confirmation is None
                or self.root_field is None
                or (not self.draft_title and not has_document_title)
                or self.payload_digest is None
                or not self.components
            ):
                raise ValueError("Ready draft preview requires an exact confirmed payload.")
            if self.blockers:
                raise ValueError("Ready draft preview cannot expose blockers.")
        elif self.payload_digest is not None:
            raise ValueError("Blocked draft preview cannot expose a payload digest.")
        return self


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
    confirmation: ContentTargetMappingConfirmation | None = None
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
    target_blocker = discovery_blocker(discovery)
    if target_blocker is not None:
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            components=components,
            blocker=target_blocker,
        )
    if discovery.target is None:
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            components=components,
            blocker=ContentTargetMappingBlocker(
                code="target_unavailable",
                label="Brakuje potwierdzonego odczytu obiektu dev",
                reason="WILQ nie otrzymał kompletnego targetu do przygotowania mapowania.",
                next_step="Odczytaj ponownie dokładny obiekt dev przed mapowaniem.",
            ),
        )
    target = ContentTargetMappingTarget(
        target_contract=discovery.target.target_contract,
        target_contract_digest=discovery.target.target_contract_digest,
        observation_evidence=discovery.target.observation_evidence,
    )
    surface_blocker = authoring_surface_blocker(target.target_contract.authoring_surface)
    if surface_blocker is not None:
        return _blocked(
            work_item_id=work_item_id,
            revision=identity,
            target=target,
            components=components,
            blocker=surface_blocker,
        )
    surface = target.target_contract.authoring_surface
    if surface is None:
        raise RuntimeError("Validated target mapping lost its authoring surface.")
    if surface.kind == "wordpress_post_content":
        components = [
            _component("document-title", "document_title", "Tytuł strony"),
            _component("document-content", "document_content", "Treść dokumentu"),
        ]
    return _ready_mapping_preview(work_item_id, identity, target, components)


def _ready_mapping_preview(
    work_item_id: str,
    identity: ContentTargetMappingRevision,
    target: ContentTargetMappingTarget,
    components: list[ContentTargetMappingComponent],
) -> ContentTargetMappingPreview:
    surface = target.target_contract.authoring_surface
    if surface is None:
        raise RuntimeError("Ready mapping lost its observed authoring surface.")
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
                "source_fields": _source_fields(component.kind),
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


def _source_fields(
    kind: ContentTargetMappingComponentKind,
) -> list[ContentTargetMappingSourceField]:
    return [
        ContentTargetMappingSourceField(key=key, label=label)
        for key, label in source_field_specs(kind)
    ]


def validate_content_target_mapping_confirmation(
    *,
    command: ContentTargetMappingConfirmationCommand,
    preview: ContentTargetMappingPreview,
) -> None:
    """Fail closed unless every selected field belongs to this exact preview."""

    if preview.status != "ready_for_human_mapping" or preview.target is None:
        raise ValueError("Nie można potwierdzić mapowania bez gotowego odczytu targetu.")
    if preview.binding_digest is None:
        raise ValueError("Gotowe mapowanie nie ma identyfikatora powiązania.")
    if command.expected_revision_digest != preview.revision.content_digest:
        raise ValueError("Rewizja dokumentu zmieniła się przed potwierdzeniem mapowania.")
    if command.expected_target_contract_digest != preview.target.target_contract_digest:
        raise ValueError("Kontrakt targetu zmienił się przed potwierdzeniem mapowania.")
    if command.expected_binding_digest != preview.binding_digest:
        raise ValueError("Podgląd mapowania zmienił się przed potwierdzeniem.")

    components = {component.component_id: component for component in preview.components}
    surface = preview.target.target_contract.authoring_surface
    if surface is None:
        raise ValueError("Nie odczytano powierzchni authoringu dla targetu.")
    selections = {selection.component_id: selection for selection in command.selections}
    component_ids = set(components)
    if not set(selections).issubset(component_ids):
        raise ValueError("Potwierdzenie wskazuje element spoza dokładnego dokumentu.")
    if command.delivery_scope == "full_document":
        if set(selections) != component_ids:
            raise ValueError(
                "Potwierdzenie pełnego dokumentu musi wskazać każdy element dokładnie raz."
            )
    elif surface.kind != "acf_flexible_content":
        raise ValueError("Zakres wybranych elementów jest dostępny wyłącznie dla ACF.")
    elif any(components[component_id].kind != "rich_text" for component_id in selections):
        raise ValueError(
            "Zakres wybranych elementów ACF może obejmować wyłącznie sekcje treści."
        )
    observed_section_indexes = any(
        layout.section_index is not None for layout in surface.layouts
    )
    for component_id, selection in selections.items():
        component = components[component_id]
        if surface.kind == "acf_flexible_content":
            if observed_section_indexes:
                if selection.target_section_index is None:
                    raise ValueError("Mapowanie ACF musi wskazać dokładną pozycję sekcji.")
                layout = next(
                    (
                        candidate
                        for candidate in surface.layouts
                        if candidate.section_index == selection.target_section_index
                    ),
                    None,
                )
                if layout is not None and layout.name != selection.layout_name:
                    layout = None
            else:
                if selection.target_section_index is not None:
                    raise ValueError("Historyczny odczyt ACF nie zawiera pozycji wskazanej sekcji.")
                layout = next(
                    (
                        candidate
                        for candidate in surface.layouts
                        if candidate.name == selection.layout_name
                    ),
                    None,
                )
            target_fields = (
                set(layout.writable_fields or layout.fields) if layout is not None else None
            )
        else:
            if selection.target_section_index is not None:
                raise ValueError("Treść wpisu WordPress nie wskazuje pozycji sekcji ACF.")
            layout = next(
                (
                    candidate
                    for candidate in surface.layouts
                    if candidate.name == selection.layout_name
                ),
                None,
            )
            target_fields = set(layout.fields) if layout is not None else None
        if target_fields is None:
            raise ValueError("Wybrana sekcja nie należy do odczytanego układu targetu.")
        expected_source_fields = {field.key for field in component.source_fields}
        actual_source_fields = {binding.source_field for binding in selection.field_bindings}
        if actual_source_fields != expected_source_fields:
            raise ValueError("Mapowanie musi wskazać każde pole elementu dokumentu dokładnie raz.")
        if any(binding.target_field not in target_fields for binding in selection.field_bindings):
            raise ValueError("Wybrane pole nie należy do odczytanego layoutu targetu.")
        target_field_names = [binding.target_field for binding in selection.field_bindings]
        has_repeated_target = len(target_field_names) != len(set(target_field_names))
        if has_repeated_target and not _is_rich_text_html_mapping(component, selection):
            raise ValueError(
                "Jedno pole targetu może przyjąć dwa źródła wyłącznie jako "
                "połączoną sekcję rich text."
            )


def new_content_target_mapping_confirmation(
    *,
    work_item_id: str,
    preview: ContentTargetMappingPreview,
    command: ContentTargetMappingConfirmationCommand,
    confirmation_number: int,
    created_at: str,
) -> ContentTargetMappingConfirmation:
    validate_content_target_mapping_confirmation(command=command, preview=preview)
    if preview.target is None or preview.binding_digest is None:
        raise RuntimeError("Validated mapping preview lost its exact target binding.")
    digest_payload = {
        "work_item_id": work_item_id,
        "revision": preview.revision.model_dump(mode="json"),
        "target_contract_digest": preview.target.target_contract_digest,
        "binding_digest": preview.binding_digest,
        "selections": [selection.model_dump(mode="json") for selection in command.selections],
        "confirmed_by": command.confirmed_by,
    }
    if command.delivery_scope == "selected_components":
        digest_payload["delivery_scope"] = command.delivery_scope
    confirmation_digest = sha256(
        json.dumps(
            digest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return ContentTargetMappingConfirmation(
        confirmation_id=f"content_target_mapping_confirmation_{uuid4().hex}",
        confirmation_number=confirmation_number,
        work_item_id=work_item_id,
        revision=preview.revision,
        target_contract_digest=preview.target.target_contract_digest,
        binding_digest=preview.binding_digest,
        delivery_scope=command.delivery_scope,
        selections=command.selections,
        confirmed_by=command.confirmed_by,
        confirmation_digest=confirmation_digest,
        created_at=created_at,
    )


def build_content_target_draft_preview(
    *,
    work_item_id: str,
    revision_id: str,
    revisions: list[ContentDraftRevision],
    mapping_preview: ContentTargetMappingPreview,
    confirmation: ContentTargetMappingConfirmation | None,
) -> ContentTargetDraftPreview:
    """Project an exact confirmed mapping without creating an ActionObject or a draft.

    This is deliberately a separate, read-only seam.  It lets a marketer inspect
    what an eventual draft-only ActionObject would receive without granting the
    dashboard an adapter or a WordPress write path.
    """

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
    context = _confirmed_draft_preview_context(
        work_item_id, identity, mapping_preview, confirmation
    )
    if isinstance(context, ContentTargetDraftPreview):
        return context
    target, confirmation, root_field = context
    components = {component.component_id: component for component in mapping_preview.components}
    selections = {selection.component_id: selection for selection in confirmation.selections}
    projected = [
        ContentTargetDraftPreviewComponent(
            component_id=component_id,
            label=components[component_id].label,
            layout_name=selection.layout_name,
            target_section_index=selection.target_section_index,
            fields=_projected_fields(
                revision=revision,
                component=components[component_id],
                selection=selection,
                authoring_surface_kind=(
                    target.target_contract.authoring_surface.kind
                    if target.target_contract.authoring_surface is not None
                    else None
                ),
            ),
        )
        for component_id, selection in selections.items()
    ]
    payload = {
        "revision": identity.model_dump(mode="json"),
        "target_contract_digest": target.target_contract_digest,
        "confirmation_digest": confirmation.confirmation_digest,
        "root_field": root_field,
        "components": [component.model_dump(mode="json") for component in projected],
    }
    if confirmation.delivery_scope == "selected_components":
        payload["delivery_scope"] = confirmation.delivery_scope
        payload["draft_title"] = revision.title
    surface_kind = (
        target.target_contract.authoring_surface.kind
        if target.target_contract.authoring_surface is not None
        else None
    )
    return ContentTargetDraftPreview(
        work_item_id=work_item_id,
        revision=identity,
        status="ready",
        target=target,
        confirmation=confirmation,
        root_field=root_field,
        delivery_scope=confirmation.delivery_scope,
        draft_title=revision.title,
        components=projected,
        preserved_source_summary=_preserved_source_summary(target, projected),
        payload_digest=sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        caveats=_draft_preview_caveats(surface_kind, confirmation.delivery_scope),
    )


def _draft_preview_caveats(
    surface_kind: str | None,
    delivery_scope: ContentTargetMappingDeliveryScope,
) -> list[str]:
    caveats = [
        "To jest podgląd danych do szkicu na dev, nie zapis do WordPressa.",
        "Kolejny etap wymaga osobnej akcji, review, potwierdzenia i audytu.",
    ]
    if delivery_scope == "selected_components":
        caveats.append(
            "Zakres szkicu obejmuje wyłącznie potwierdzone elementy ACF; "
            "pozostałe pola zostaną zachowane z odczytanego targetu."
        )
    elif surface_kind == "acf_flexible_content":
        caveats.append(
            "Pełny szkic ACF zachowa z odczytanego targetu wszystkie niezmieniane "
            "layouty i pola; podgląd pokazuje tylko zmieniane elementy."
        )
    return caveats


def _preserved_source_summary(
    target: ContentTargetMappingTarget,
    projected: list[ContentTargetDraftPreviewComponent],
) -> ContentTargetDraftPreviewPreservedSourceSummary | None:
    surface = target.target_contract.authoring_surface
    if (
        surface is None
        or surface.kind != "acf_flexible_content"
        or surface.source_acf_root_field_count is None
        or surface.source_acf_row_count is None
        or any(component.target_section_index is None for component in projected)
    ):
        return None
    changed_rows = {component.target_section_index for component in projected}
    if (
        surface.source_acf_root_field_count < 1
        or surface.source_acf_row_count < 1
        or not changed_rows
        or len(changed_rows) > surface.source_acf_row_count
    ):
        return None
    return ContentTargetDraftPreviewPreservedSourceSummary(
        label="Pełny klon zachowa niezmieniane dane ACF ze źródła",
        source_root_field_count=surface.source_acf_root_field_count,
        source_row_count=surface.source_acf_row_count,
        changed_row_count=len(changed_rows),
        unchanged_row_count=surface.source_acf_row_count - len(changed_rows),
        preserved_sibling_root_field_count=surface.source_acf_root_field_count - 1,
    )


def _is_rich_text_html_mapping(
    component: ContentTargetMappingComponent,
    selection: ContentTargetMappingSelection,
) -> bool:
    return bool(
        component.kind == "rich_text"
        and len(selection.field_bindings) == 2
        and {binding.source_field for binding in selection.field_bindings}
        == {"heading", "content_html"}
        and len({binding.target_field for binding in selection.field_bindings}) == 1
    )


def _projected_fields(
    *,
    revision: ContentDraftRevision,
    component: ContentTargetMappingComponent,
    selection: ContentTargetMappingSelection,
    authoring_surface_kind: str | None,
) -> list[ContentTargetDraftPreviewField]:
    if _is_rich_text_html_mapping(component, selection):
        target_field = selection.field_bindings[0].target_field
        heading, _ = _source_value(revision, component.component_id, "heading")
        content_html, _ = _source_value(revision, component.component_id, "content_html")
        return [
            ContentTargetDraftPreviewField(
                target_field=target_field,
                source_field="rich_text_html",
                value=f"<h2>{escape(heading)}</h2>{content_html}",
                value_kind="html",
            )
        ]
    return [
        _projected_field(
            revision=revision,
            component_id=component.component_id,
            binding=binding,
            authoring_surface_kind=authoring_surface_kind,
        )
        for binding in selection.field_bindings
    ]


def _projected_field(
    *,
    revision: ContentDraftRevision,
    component_id: str,
    binding: ContentTargetMappingFieldBinding,
    authoring_surface_kind: str | None,
) -> ContentTargetDraftPreviewField:
    value, value_kind = _source_value(revision, component_id, binding.source_field)
    return ContentTargetDraftPreviewField(
        target_field=binding.target_field,
        source_field=binding.source_field,
        value=project_target_field_value(
            value,
            authoring_surface_kind=authoring_surface_kind,
            component_id=component_id,
            source_field=binding.source_field,
            target_field=binding.target_field,
            value_kind=value_kind,
        ),
        value_kind=value_kind,
    )


def _confirmed_draft_preview_context(
    work_item_id: str,
    identity: ContentTargetMappingRevision,
    mapping_preview: ContentTargetMappingPreview,
    confirmation: ContentTargetMappingConfirmation | None,
) -> (
    ContentTargetDraftPreview
    | tuple[ContentTargetMappingTarget, ContentTargetMappingConfirmation, str]
):
    target = mapping_preview.target
    if mapping_preview.status != "ready_for_human_mapping" or target is None:
        return _draft_preview_blocked(
            work_item_id=work_item_id,
            revision=identity,
            code="mapping_stale",
            label="Odczyt targetu wymaga ponownego sprawdzenia",
            reason="Nie ma aktualnego, gotowego podglądu przypisania do dokładnego targetu.",
            next_step="Otwórz przypisanie dokumentu do dev i odczytaj je ponownie.",
        )
    if not _confirmation_matches(confirmation, work_item_id, identity, mapping_preview):
        return _draft_preview_blocked(
            work_item_id=work_item_id,
            revision=identity,
            target=target,
            code="mapping_not_confirmed",
            label="Brakuje potwierdzonego przypisania",
            reason=(
                "WILQ nie przygotuje danych do szkicu, dopóki człowiek nie potwierdzi "
                "przypisania tej wersji do aktualnie odczytanego układu dev."
            ),
            next_step="Potwierdź przypisanie dokumentu do odczytanych layoutów i pól.",
        )
    surface = target.target_contract.authoring_surface
    if surface is None:
        return _draft_preview_blocked(
            work_item_id=work_item_id,
            revision=identity,
            target=target,
            code="mapping_stale",
            label="Układ targetu nie jest już dostępny",
            reason="Potwierdzone przypisanie nie ma aktualnie odczytanego pola układu.",
            next_step="Odczytaj ponownie układ dev i potwierdź przypisanie od nowa.",
        )
    if confirmation is None:
        return _draft_preview_blocked(
            work_item_id=work_item_id,
            revision=identity,
            target=target,
            code="mapping_not_confirmed",
            label="Brakuje potwierdzonego przypisania",
            reason="WILQ nie otrzymał kompletnego potwierdzenia dla tego targetu.",
            next_step="Potwierdź przypisanie dokumentu do odczytanych layoutów i pól.",
        )
    return target, confirmation, surface.root_field


def _confirmation_matches(
    confirmation: ContentTargetMappingConfirmation | None,
    work_item_id: str,
    identity: ContentTargetMappingRevision,
    mapping_preview: ContentTargetMappingPreview,
) -> bool:
    target = mapping_preview.target
    return bool(
        confirmation
        and target
        and confirmation.work_item_id == work_item_id
        and confirmation.revision == identity
        and confirmation.target_contract_digest == target.target_contract_digest
        and confirmation.binding_digest == mapping_preview.binding_digest
    )


def _draft_preview_blocked(
    *,
    work_item_id: str,
    revision: ContentTargetMappingRevision,
    code: Literal["mapping_not_confirmed", "mapping_stale"],
    label: str,
    reason: str,
    next_step: str,
    target: ContentTargetMappingTarget | None = None,
) -> ContentTargetDraftPreview:
    return ContentTargetDraftPreview(
        work_item_id=work_item_id,
        revision=revision,
        status="blocked",
        target=target,
        blockers=[
            ContentTargetDraftPreviewBlocker(
                code=code,
                label=label,
                reason=reason,
                next_step=next_step,
            )
        ],
        caveats=["Nie przygotowano ActionObjectu, draftu ani zapisu do WordPressa."],
    )


def _source_value(
    revision: ContentDraftRevision,
    component_id: str,
    source_field: str,
) -> tuple[str, Literal["plain_text", "html", "url"]]:
    if component_id == "document-title" and source_field == "wordpress_title":
        return (
            (
                revision.page_assets.wordpress_title
                if revision.page_assets is not None
                else revision.title
            ),
            "plain_text",
        )
    if component_id == "document-content" and source_field == "document_html":
        return revision_document_html(revision), "html"
    if component_id == "page-assets" and revision.page_assets is not None:
        return _page_asset_source_value(revision, source_field)
    if component_id.startswith("section:"):
        return _section_source_value(revision, component_id, source_field)
    if component_id.startswith("faq:"):
        return _faq_source_value(revision, component_id, source_field)
    if component_id.startswith("cta:"):
        return _cta_source_value(revision, component_id, source_field)
    if component_id.startswith("link:"):
        return _link_source_value(revision, component_id, source_field)
    raise ValueError("Potwierdzone przypisanie nie pasuje do pól dokładnej rewizji.")


def _page_asset_source_value(
    revision: ContentDraftRevision,
    source_field: str,
) -> tuple[str, Literal["plain_text"]]:
    if revision.page_assets is None:
        raise ValueError("Potwierdzone przypisanie wymaga dostępnych pól strony.")
    values = {
        "meta_title": revision.page_assets.meta_title,
        "meta_description": revision.page_assets.meta_description,
        "h1": revision.page_assets.h1,
        "lead": revision.page_assets.lead,
    }
    if source_field not in values:
        raise ValueError("Potwierdzone przypisanie nie pasuje do pól strony.")
    return values[source_field], "plain_text"


def _section_source_value(
    revision: ContentDraftRevision,
    component_id: str,
    source_field: str,
) -> tuple[str, Literal["plain_text", "html"]]:
    section_id = component_id.removeprefix("section:")
    section = next(
        (
            candidate
            for index, candidate in enumerate(revision.sections, start=1)
            if (candidate.section_id or str(index)) == section_id
        ),
        None,
    )
    if section is None:
        raise ValueError("Potwierdzone przypisanie nie pasuje do sekcji rewizji.")
    if source_field == "heading":
        return section.heading, "plain_text"
    if source_field == "content_html":
        return section.content_html or content_html_from_markdown(section.body_markdown), "html"
    raise ValueError("Potwierdzone przypisanie nie pasuje do pól sekcji.")


def _faq_source_value(
    revision: ContentDraftRevision,
    component_id: str,
    source_field: str,
) -> tuple[str, Literal["plain_text", "html"]]:
    item = next(
        (candidate for candidate in revision.faq if f"faq:{candidate.faq_id}" == component_id),
        None,
    )
    if item is None:
        raise ValueError("Potwierdzone przypisanie nie pasuje do pytania i odpowiedzi.")
    if source_field == "question":
        return item.question, "plain_text"
    if source_field == "answer_markdown":
        return content_html_from_markdown(item.answer_markdown), "html"
    raise ValueError("Potwierdzone przypisanie nie pasuje do pól pytań i odpowiedzi.")


def _cta_source_value(
    revision: ContentDraftRevision,
    component_id: str,
    source_field: str,
) -> tuple[str, Literal["html"]]:
    item = next(
        (
            candidate
            for candidate in revision.cta_blocks
            if f"cta:{candidate.cta_id}" == component_id
        ),
        None,
    )
    if item is None or source_field != "body_markdown":
        raise ValueError("Potwierdzone przypisanie nie pasuje do wezwania do działania.")
    return content_html_from_markdown(item.body_markdown), "html"


def _link_source_value(
    revision: ContentDraftRevision,
    component_id: str,
    source_field: str,
) -> tuple[str, Literal["plain_text", "url"]]:
    item = next(
        (
            candidate
            for candidate in revision.internal_links
            if f"link:{candidate.link_id}" == component_id
        ),
        None,
    )
    if item is None:
        raise ValueError("Potwierdzone przypisanie nie pasuje do linku wewnętrznego.")
    if source_field == "anchor_text":
        return item.anchor_text, "plain_text"
    if source_field == "target_url":
        return item.target_url, "url"
    raise ValueError("Potwierdzone przypisanie nie pasuje do pól linku wewnętrznego.")


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


__all__ = [
    "ContentTargetDraftPreview",
    "ContentTargetMappingConfirmation",
    "ContentTargetMappingConfirmationCommand",
    "ContentTargetMappingConfirmationResult",
    "ContentTargetMappingPreview",
    "build_content_target_mapping_preview",
    "build_content_target_draft_preview",
    "new_content_target_mapping_confirmation",
    "validate_content_target_mapping_confirmation",
]
