from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.content_html import content_html_from_markdown
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
    field_bindings: list[ContentTargetMappingFieldBinding] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_fields(self) -> ContentTargetMappingSelection:
        source_fields = [binding.source_field for binding in self.field_bindings]
        target_fields = [binding.target_field for binding in self.field_bindings]
        if len(source_fields) != len(set(source_fields)):
            raise ValueError("A component mapping cannot bind one source field twice.")
        if len(target_fields) != len(set(target_fields)):
            raise ValueError("A component mapping cannot bind one target field twice.")
        return self


class ContentTargetMappingConfirmationCommand(BaseModel):
    """Local human confirmation of an exact, observed mapping preview."""

    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_by: str = Field(min_length=1)
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
    selections: list[ContentTargetMappingSelection] = Field(min_length=1)
    confirmed_by: str = Field(min_length=1)
    confirmation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(min_length=1)


class ContentTargetMappingConfirmationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["created", "idempotent"]
    confirmation: ContentTargetMappingConfirmation


class ContentTargetDraftPreviewField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_field: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    value_kind: Literal["plain_text", "html", "url"]


class ContentTargetDraftPreviewComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    layout_name: str = Field(min_length=1)
    fields: list[ContentTargetDraftPreviewField] = Field(min_length=1)


class ContentTargetDraftPreviewBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["mapping_not_confirmed", "mapping_stale"]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class ContentTargetDraftPreview(BaseModel):
    """Exact payload preview; it is not an ActionObject and never writes WordPress."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_target_draft_preview"] = "content_target_draft_preview"
    contract_version: Literal["content_target_draft_preview_v1"] = (
        "content_target_draft_preview_v1"
    )
    work_item_id: str = Field(min_length=1)
    revision: ContentTargetMappingRevision
    status: Literal["ready", "blocked"]
    target: ContentTargetMappingTarget | None = None
    confirmation: ContentTargetMappingConfirmation | None = None
    root_field: str | None = None
    components: list[ContentTargetDraftPreviewComponent] = Field(default_factory=list)
    payload_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    blockers: list[ContentTargetDraftPreviewBlocker] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_exact_ready_payload(self) -> ContentTargetDraftPreview:
        if self.status == "ready":
            if (
                self.target is None
                or self.confirmation is None
                or self.root_field is None
                or self.payload_digest is None
                or not self.components
            ):
                raise ValueError("Ready draft preview requires an exact confirmed payload.")
            if self.blockers:
                raise ValueError("Ready draft preview cannot expose blockers.")
        elif self.payload_digest is not None:
            raise ValueError("Blocked draft preview cannot expose a payload digest.")
        return self


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


def _source_fields(
    kind: ContentTargetMappingComponentKind,
) -> list[ContentTargetMappingSourceField]:
    fields_by_kind: dict[
        ContentTargetMappingComponentKind, list[ContentTargetMappingSourceField]
    ] = {
        "document_title": [
            ContentTargetMappingSourceField(key="wordpress_title", label="Tytuł strony"),
        ],
        "page_assets": [
            ContentTargetMappingSourceField(key="meta_title", label="Tytuł meta"),
            ContentTargetMappingSourceField(
                key="meta_description", label="Opis meta"
            ),
            ContentTargetMappingSourceField(key="h1", label="Nagłówek H1"),
            ContentTargetMappingSourceField(key="lead", label="Lead strony"),
        ],
        "rich_text": [
            ContentTargetMappingSourceField(key="heading", label="Nagłówek sekcji"),
            ContentTargetMappingSourceField(key="content_html", label="Treść sekcji"),
        ],
        "faq": [
            ContentTargetMappingSourceField(key="question", label="Pytanie"),
            ContentTargetMappingSourceField(key="answer_markdown", label="Odpowiedź"),
        ],
        "cta": [
            ContentTargetMappingSourceField(key="body_markdown", label="Treść CTA"),
        ],
        "internal_link": [
            ContentTargetMappingSourceField(key="anchor_text", label="Tekst linku"),
            ContentTargetMappingSourceField(key="target_url", label="Adres linku"),
        ],
    }
    return fields_by_kind[kind]


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
    selections = {selection.component_id: selection for selection in command.selections}
    if set(selections) != set(components):
        raise ValueError("Potwierdzenie musi wskazać każdy element dokumentu dokładnie raz.")

    surface = preview.target.target_contract.authoring_surface
    if surface is None:
        raise ValueError("Nie odczytano powierzchni authoringu dla targetu.")
    layouts = {layout.name: set(layout.fields) for layout in surface.layouts}
    for component_id, component in components.items():
        selection = selections[component_id]
        target_fields = layouts.get(selection.layout_name)
        if target_fields is None:
            raise ValueError("Wybrany layout nie należy do odczytanego układu targetu.")
        expected_source_fields = {field.key for field in component.source_fields}
        actual_source_fields = {
            binding.source_field for binding in selection.field_bindings
        }
        if actual_source_fields != expected_source_fields:
            raise ValueError("Mapowanie musi wskazać każde pole elementu dokumentu dokładnie raz.")
        if any(binding.target_field not in target_fields for binding in selection.field_bindings):
            raise ValueError("Wybrane pole nie należy do odczytanego layoutu targetu.")


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
            fields=[
                ContentTargetDraftPreviewField(
                    target_field=binding.target_field,
                    source_field=binding.source_field,
                    value=_source_value(revision, component_id, binding.source_field)[0],
                    value_kind=_source_value(revision, component_id, binding.source_field)[1],
                )
                for binding in selection.field_bindings
            ],
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
    return ContentTargetDraftPreview(
        work_item_id=work_item_id,
        revision=identity,
        status="ready",
        target=target,
        confirmation=confirmation,
        root_field=root_field,
        components=projected,
        payload_digest=sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        caveats=[
            "To jest podgląd danych do szkicu na dev, nie zapis do WordPressa.",
            "Kolejny etap wymaga osobnej akcji, review, potwierdzenia i audytu.",
        ],
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
    assert confirmation is not None
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
    assert revision.page_assets is not None
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
