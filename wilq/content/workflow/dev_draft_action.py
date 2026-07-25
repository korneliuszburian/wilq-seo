from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from wilq.actions.metric_utils import unique_values
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.target_discovery import build_content_target_discovery
from wilq.content.workflow.target_mapping import (
    ContentTargetDraftPreview,
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


class ContentTargetDraftActionCommand(BaseModel):
    """Create a WILQ-local ActionObject from one exact data preview."""

    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_confirmation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1, max_length=200)


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
    binding = {
        "work_item_id": preview.work_item_id,
        "revision_id": preview.revision.revision_id,
        "revision_digest": preview.revision.content_digest,
        "target_contract_digest": preview.target.target_contract_digest,
        "confirmation_id": preview.confirmation.confirmation_id,
        "confirmation_digest": preview.confirmation.confirmation_digest,
        "payload_digest": preview.payload_digest,
        "root_field": preview.root_field,
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
        "apply_allowed": False,
        "api_mutation_ready": False,
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
            "Zapis do WordPressa pozostaje zablokowany, dopóki nie istnieje osobna, "
            "bezpieczna granica wykonania dev draft-only."
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
            "blocked_claims": [
                "wordpress_publish",
                "wordpress_update_existing_post",
                "wordpress_delete_post",
                "production_write",
                "bulk_delivery",
            ],
            "destructive": False,
            "apply_allowed": False,
            "api_mutation_ready": False,
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
    exact = (
        preview.revision.content_digest == binding.get("revision_digest")
        and preview.target.target_contract_digest == binding.get("target_contract_digest")
        and preview.confirmation.confirmation_digest == binding.get("confirmation_digest")
        and preview.payload_digest == binding.get("payload_digest")
        and preview.root_field == binding.get("root_field")
    )
    return action if exact else _blocked_action(action, "content_draft_action_stale")


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


def _required_binding_value(binding: dict[str, Any], key: str) -> str:
    value = binding.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Brakuje pola {key} w powiązaniu akcji.")
    return value


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
    "ContentTargetDraftActionCommand",
    "create_content_target_draft_action",
    "current_content_target_draft_preview",
    "load_content_target_draft_action",
    "persist_content_target_draft_action",
    "refresh_content_target_draft_action",
]
