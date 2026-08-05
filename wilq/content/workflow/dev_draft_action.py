from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.actions.metric_utils import unique_values
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.target_discovery import build_content_target_discovery
from wilq.content.workflow.target_mapping import (
    ContentTargetDraftPreview,
    ContentTargetDraftPreviewComponent,
    build_content_target_draft_preview,
    build_content_target_mapping_preview,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store

CONTENT_DEV_DRAFT_ACTION_TYPE = "content_dev_draft_create"
CONTENT_DEV_DRAFT_ACTION_CONTRACT = "content_dev_draft_action_v1"
CONTENT_DEV_DRAFT_ACTION_CREATED_EVENT = "content_dev_draft_action_created"
_LEADING_DOCUMENT_H1 = re.compile(
    r"\A\s*<h1(?:\s[^>]*)?>.*?</h1>\s*",
    re.IGNORECASE | re.DOTALL,
)


class ContentTargetDraftActionCommand(BaseModel):
    """Create a WILQ-local ActionObject from one exact data preview."""

    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_confirmation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1, max_length=200)


class ContentDevDraftWritePayload(BaseModel):
    """Strict WordPress create payload derived only from an exact confirmed mapping.

    This is an internal delivery projection.  Building it performs no vendor
    operation; a later ActionObject-owned adapter may consume it only after its
    own validation, preview, review, confirmation and apply gates.
    """

    model_config = ConfigDict(extra="forbid")

    connector: Literal["wordpress_ekologus"]
    endpoint: Literal["posts", "pages"]
    authoring_mode: Literal["acf_flexible_content", "wordpress_post_content"]
    post_status: Literal["draft"] = "draft"
    create_only: Literal[True] = True
    publish_allowed: Literal[False] = False
    update_allowed: Literal[False] = False
    delete_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    title: str = Field(min_length=1)
    acf: dict[str, list[dict[str, str]]] | None = None
    content_html: str | None = None
    binding: dict[str, str] = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_authoring_payload(self) -> ContentDevDraftWritePayload:
        if self.authoring_mode == "acf_flexible_content":
            if not self.acf or self.content_html is not None:
                raise ValueError("Payload ACF szkicu wymaga wyłącznie dokładnego układu ACF.")
        elif not self.content_html or self.acf is not None:
            raise ValueError("Payload treści WordPress wymaga wyłącznie HTML dokumentu.")
        return self


def create_content_target_draft_action(
    preview: ContentTargetDraftPreview,
    command: ContentTargetDraftActionCommand,
) -> ActionObject:
    """Turn a confirmed data projection into an auditable, still non-writing action."""

    if preview.status != "ready" or preview.target is None or preview.confirmation is None:
        raise ValueError("Nie można przygotować akcji bez gotowego podglądu danych do szkicu.")
    if preview.payload_digest is None or preview.root_field is None:
        raise ValueError("Podgląd danych do szkicu nie ma kompletnej tożsamości.")
    if command.expected_revision_digest != preview.revision.content_digest:
        raise ValueError("Akcja wskazuje inną wersję dokumentu.")
    if command.expected_target_contract_digest != preview.target.target_contract_digest:
        raise ValueError("Akcja wskazuje inny odczyt obiektu dev.")
    if command.expected_confirmation_digest != preview.confirmation.confirmation_digest:
        raise ValueError("Akcja wskazuje inne potwierdzenie przypisania.")
    if command.expected_payload_digest != preview.payload_digest:
        raise ValueError("Akcja wskazuje inny podgląd danych do szkicu.")

    target = preview.target.target_contract
    surface = target.authoring_surface
    if surface is None:
        raise ValueError("Akcja szkicu dev wymaga odczytanego układu authoringu.")
    binding = {
        "work_item_id": preview.work_item_id,
        "revision_id": preview.revision.revision_id,
        "revision_digest": preview.revision.content_digest,
        "target_contract_digest": preview.target.target_contract_digest,
        "confirmation_id": preview.confirmation.confirmation_id,
        "confirmation_digest": preview.confirmation.confirmation_digest,
        "payload_digest": preview.payload_digest,
        "root_field": preview.root_field,
        "authoring_mode": surface.kind,
    }
    draft_payload = _draft_payload_identity(preview)
    payload_preview = {
        "preview_contract": CONTENT_DEV_DRAFT_ACTION_CONTRACT,
        "operation_type_label": "Utworzenie nowego szkicu na dev",
        "target_label": f"{_target_type_label(target.post_type)}: {target.url}",
        "revision_label": "Zatwierdzona, dokładna wersja dokumentu",
        "mapping_label": "Ręczne przypisanie do odczytanego układu dev",
        "status_label": "wymaga osobnego review i potwierdzenia akcji",
        "component_count_label": f"{len(preview.components)} elementów dokumentu",
        "apply_allowed": True,
        "api_mutation_ready": True,
    }
    return ActionObject(
        id=f"act_content_dev_draft_{uuid4().hex}",
        title="Przygotuj utworzenie szkicu na dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=unique_values([preview.target.observation_evidence.evidence_id]),
        human_diagnosis=(
            "Dokument został zatwierdzony, a człowiek potwierdził jego przypisanie do "
            "odczytanego układu dev. WILQ może przygotować wyłącznie ślad działania "
            "dla nowego szkicu; nie publikuje ani nie zmienia istniejącego obiektu."
        ),
        recommended_reason=(
            "Sprawdź dokładny zakres danych, zapisz osobne review i potwierdzenie akcji. "
            "Zapis do WordPressa może utworzyć wyłącznie jeden nowy szkic na dev po "
            "kompletnym łańcuchu ActionObject i jawnym potwierdzeniu operatora."
        ),
        payload={
            "action_type": CONTENT_DEV_DRAFT_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "preview_contract": CONTENT_DEV_DRAFT_ACTION_CONTRACT,
            "mode": "dev_draft_only",
            "content_target_draft_binding": binding,
            "draft_payload": draft_payload,
            "payload_preview": [payload_preview],
            "required_validation": [
                "validate_action_object",
                "exact_document_revision_check",
                "exact_target_contract_check",
                "confirmed_mapping_check",
                "human_review_before_apply",
                "human_confirm_before_wordpress_write",
            ],
            "operator_review_gates": [
                "exact_document_revision_check",
                "exact_target_contract_check",
                "confirmed_mapping_check",
                "human_review_before_apply",
                "human_confirm_before_wordpress_write",
            ],
            "destructive": False,
            "apply_allowed": True,
            "api_mutation_ready": True,
        },
        validation_status="not_validated",
        created_by=command.requested_by,
    )


def persist_content_target_draft_action(action: ActionObject) -> ActionObject:
    """Persist the WILQ ActionObject as an auditable local creation event."""

    event = AuditEvent(
        id=f"audit_{action.id}_created",
        action_id=action.id,
        event_type=CONTENT_DEV_DRAFT_ACTION_CREATED_EVENT,
        event_type_label="Przygotowano akcję szkicu na dev",
        actor=action.created_by,
        summary=(
            "Przygotowano lokalną akcję dla dokładnego szkicu na dev. "
            "Nie zapisano niczego w WordPressie."
        ),
        evidence_ids=action.evidence_ids,
        details={"content_target_draft_action": action.model_dump(mode="json")},
    )
    persisted = local_state_store().save_audit_event(event)
    return _action_from_creation_event(persisted)


def load_content_target_draft_action(action_id: str) -> ActionObject | None:
    """Load only the creation event that owns this exact content ActionObject."""

    for event in local_state_store().list_audit_events(action_id):
        if event.event_type != CONTENT_DEV_DRAFT_ACTION_CREATED_EVENT:
            continue
        try:
            return _action_from_creation_event(event)
        except ValueError:
            return None
    return None


def refresh_content_target_draft_action(action: ActionObject) -> ActionObject:
    """Fail closed when the exact document, mapping, or observed target changed."""

    if action.payload.get("action_type") != CONTENT_DEV_DRAFT_ACTION_TYPE:
        return action
    binding = action.payload.get("content_target_draft_binding")
    if not isinstance(binding, dict):
        return _blocked_action(action, "content_draft_action_binding_invalid")
    try:
        preview = current_content_target_draft_preview(
            work_item_id=_required_binding_value(binding, "work_item_id"),
            revision_id=_required_binding_value(binding, "revision_id"),
        )
    except ValueError:
        return _blocked_action(action, "content_draft_action_state_unavailable")
    if preview.status != "ready" or preview.target is None or preview.confirmation is None:
        return _blocked_action(action, "content_draft_action_state_unavailable")
    return action if _preview_matches_action_binding(preview, binding) else _blocked_action(
        action, "content_draft_action_stale"
    )


def build_content_dev_draft_write_payload(
    action: ActionObject,
    *,
    preview: ContentTargetDraftPreview | None = None,
) -> ContentDevDraftWritePayload:
    """Build one create-only dev payload or fail closed before any adapter runs."""

    binding = action.payload.get("content_target_draft_binding")
    if not isinstance(binding, dict):
        raise ValueError("Akcja szkicu dev nie ma kompletnego powiązania.")
    current = preview or current_content_target_draft_preview(
        work_item_id=_required_binding_value(binding, "work_item_id"),
        revision_id=_required_binding_value(binding, "revision_id"),
    )
    if current.status != "ready" or current.target is None or current.confirmation is None:
        raise ValueError("Nie można zbudować payloadu bez aktualnego mapowania do dev.")
    if current.root_field is None:
        raise ValueError("Nie można zbudować payloadu bez odczytanego pola ACF.")
    if not _preview_matches_action_binding(current, binding):
        raise ValueError(
            "Dokładna rewizja, mapowanie albo odczyt dev zmieniły się przed "
            "przygotowaniem payloadu."
        )

    endpoint = _wordpress_endpoint(current.target.target_contract.post_type)
    title = _document_title(current.components)
    exact_binding = {
        key: _required_binding_value(binding, key)
        for key in (
            "work_item_id",
            "revision_id",
            "revision_digest",
            "target_contract_digest",
            "confirmation_id",
            "confirmation_digest",
            "payload_digest",
            "root_field",
        )
    }
    surface = current.target.target_contract.authoring_surface
    if surface is None:
        raise ValueError("Nie można zbudować payloadu bez odczytanego układu authoringu.")
    if surface.kind == "wordpress_post_content":
        return ContentDevDraftWritePayload(
            connector="wordpress_ekologus",
            endpoint=endpoint,
            title=title,
            binding=exact_binding,
            authoring_mode=surface.kind,
            content_html=_wordpress_post_content_html(current.components),
        )
    layouts = [_acf_layout(component) for component in current.components]
    return ContentDevDraftWritePayload(
        connector="wordpress_ekologus",
        endpoint=endpoint,
        title=title,
        binding=exact_binding,
        authoring_mode=surface.kind,
        acf={current.root_field: layouts},
    )


def current_content_target_draft_preview(
    *, work_item_id: str, revision_id: str
) -> ContentTargetDraftPreview:
    """Rebuild the same API-owned projection used by the public draft-preview seam."""

    store = content_workflow_store()
    discovery = build_content_target_discovery(work_item_id)
    if discovery is None:
        raise ValueError("Nie znaleziono strony do sprawdzenia na dev.")
    revisions = store.list_draft_revisions(work_item_id)
    mapping = build_content_target_mapping_preview(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revisions=revisions,
        human_review=store.load_draft_revision_review(
            work_item_id=work_item_id,
            revision_id=revision_id,
        ),
        discovery=discovery,
    )
    confirmation = None
    if mapping.target is not None and mapping.binding_digest is not None:
        confirmation = store.load_target_mapping_confirmation(
            work_item_id=work_item_id,
            revision_id=revision_id,
            target_contract_digest=mapping.target.target_contract_digest,
            binding_digest=mapping.binding_digest,
        )
    return build_content_target_draft_preview(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revisions=revisions,
        mapping_preview=mapping,
        confirmation=confirmation,
    )


def _blocked_action(action: ActionObject, code: str) -> ActionObject:
    payload = deepcopy(action.payload)
    payload["runtime_blockers"] = [code]
    payload["runtime_blocker_reasons"] = [_runtime_blocker_reason(code)]
    return action.model_copy(update={"payload": payload, "status": ActionStatus.blocked})


def _action_from_creation_event(event: AuditEvent) -> ActionObject:
    payload = event.details.get("content_target_draft_action")
    if not isinstance(payload, dict):
        raise ValueError("Brakuje zapisanego payloadu akcji szkicu na dev.")
    return ActionObject.model_validate(payload)


def _draft_payload_identity(preview: ContentTargetDraftPreview) -> dict[str, Any]:
    return {
        "root_field": preview.root_field,
        "component_ids": [component.component_id for component in preview.components],
    }


def _wordpress_endpoint(post_type: str) -> Literal["posts", "pages"]:
    endpoints: dict[str, Literal["posts", "pages"]] = {"post": "posts", "page": "pages"}
    endpoint = endpoints.get(post_type)
    if endpoint is None:
        raise ValueError("Odczytany typ obiektu dev nie obsługuje tworzenia szkicu.")
    return endpoint


def _document_title(components: list[ContentTargetDraftPreviewComponent]) -> str:
    titles = [
        field.value.strip()
        for component in components
        if component.component_id == "document-title"
        for field in component.fields
        if field.source_field == "wordpress_title"
    ]
    if len(titles) != 1 or not titles[0]:
        raise ValueError("Mapowanie szkicu musi wskazywać dokładnie jeden tytuł dokumentu.")
    return str(titles[0])


def _acf_layout(component: ContentTargetDraftPreviewComponent) -> dict[str, str]:
    fields: dict[str, str] = {"acf_fc_layout": component.layout_name}
    for field in component.fields:
        if field.target_field in fields:
            raise ValueError("Mapowanie szkicu zawiera powtórzone pole targetu.")
        fields[field.target_field] = field.value
    return fields


def _wordpress_post_content_html(components: list[ContentTargetDraftPreviewComponent]) -> str:
    """Map a full document into a WordPress post body without a second page H1.

    Native WordPress themes render the post title as the page H1. The immutable
    document deliberately retains its H1, but its delivery projection must not
    put that same heading into ``post_content``.
    """

    document_html = _document_content_html(components)
    return _LEADING_DOCUMENT_H1.sub("", document_html, count=1).strip()


def _document_content_html(components: list[ContentTargetDraftPreviewComponent]) -> str:
    values = [
        field.value.strip()
        for component in components
        if component.component_id == "document-content"
        for field in component.fields
        if field.source_field == "document_html"
        and field.target_field == "content_html"
        and field.value_kind == "html"
    ]
    if len(values) != 1 or not values[0]:
        raise ValueError(
            "Mapowanie szkicu treści musi wskazywać dokładnie jeden pełny dokument HTML."
        )
    return values[0]


def _required_binding_value(binding: dict[str, Any], key: str) -> str:
    value = binding.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Brakuje pola {key} w powiązaniu akcji.")
    return value


def _preview_matches_action_binding(
    preview: ContentTargetDraftPreview,
    binding: dict[str, Any],
) -> bool:
    """Keep an ActionObject tied to the exact preview used for its payload."""

    if (
        preview.status != "ready"
        or preview.target is None
        or preview.confirmation is None
        or preview.payload_digest is None
        or preview.root_field is None
    ):
        return False
    return (
        preview.work_item_id == binding.get("work_item_id")
        and preview.revision.revision_id == binding.get("revision_id")
        and preview.revision.content_digest == binding.get("revision_digest")
        and preview.target.target_contract_digest == binding.get("target_contract_digest")
        and preview.confirmation.confirmation_id == binding.get("confirmation_id")
        and preview.confirmation.confirmation_digest == binding.get("confirmation_digest")
        and preview.payload_digest == binding.get("payload_digest")
        and preview.root_field == binding.get("root_field")
    )


def _runtime_blocker_reason(code: str) -> str:
    reasons = {
        "content_draft_action_binding_invalid": (
            "Akcja nie ma kompletnego powiązania z dokumentem i targetem."
        ),
        "content_draft_action_state_unavailable": (
            "WILQ nie może teraz potwierdzić aktualnej rewizji, mapowania lub odczytu dev."
        ),
        "content_draft_action_stale": (
            "Rewizja dokumentu, potwierdzenie mapowania albo odczyt targetu zmieniły się "
            "od przygotowania tej akcji."
        ),
    }
    return reasons[code]


def _target_type_label(post_type: str) -> str:
    return "Artykuł dev" if post_type == "post" else "Strona dev"


__all__ = [
    "CONTENT_DEV_DRAFT_ACTION_CONTRACT",
    "CONTENT_DEV_DRAFT_ACTION_CREATED_EVENT",
    "CONTENT_DEV_DRAFT_ACTION_TYPE",
    "ContentDevDraftWritePayload",
    "ContentTargetDraftActionCommand",
    "build_content_dev_draft_write_payload",
    "create_content_target_draft_action",
    "current_content_target_draft_preview",
    "load_content_target_draft_action",
    "persist_content_target_draft_action",
    "refresh_content_target_draft_action",
]
