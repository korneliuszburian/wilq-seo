from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from wilq.actions.metric_utils import unique_values
from wilq.content.workflow.new_page_document import ContentNewPageDeliveryReadiness
from wilq.content.workflow.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store

CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE = "content_new_page_dev_draft_create"
CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT = "content_new_page_dev_draft_action_v1"
CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CREATED_EVENT = "content_new_page_dev_draft_action_created"


class ContentNewPageDraftActionCommand(BaseModel):
    """Explicit human choice of one observed type for a new dev draft."""

    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_authoring_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: str = Field(pattern=r"^(page|post)$")
    requested_by: str = Field(min_length=1, max_length=200)


def create_new_page_draft_action(
    readiness: ContentNewPageDeliveryReadiness,
    command: ContentNewPageDraftActionCommand,
) -> ActionObject:
    """Create a local ActionObject; this never calls a WordPress adapter."""

    if readiness.status != "ready_for_action":
        raise ValueError("Nowa strona nie jest gotowa do utworzenia ActionObjectu.")
    if readiness.revision_id is None or readiness.revision_digest is None:
        raise ValueError("Gotowość nowej strony nie ma exact rewizji.")
    if command.expected_revision_digest != readiness.revision_digest:
        raise ValueError("Akcja wskazuje inną rewizję nowej strony.")
    if command.expected_authoring_profile_digest != readiness.authoring_profile_digest:
        raise ValueError("Akcja wskazuje inny profil authoringu.")
    if command.content_type not in readiness.allowed_content_types:
        raise ValueError("Wybrany typ nie należy do obserwowanych capability WordPress.")
    binding = ContentNewPageDraftBinding(
        work_item_id=readiness.work_item_id,
        brief_id=readiness.brief_id,
        brief_digest=readiness.brief_digest,
        foundation_id=readiness.foundation_id,
        service_card_id=readiness.service_card_id,
        service_card_digest=readiness.service_card_digest,
        revision_id=readiness.revision_id,
        revision_digest=readiness.revision_digest,
        authoring_profile_digest=command.expected_authoring_profile_digest,
        content_type=command.content_type,
    )
    return ActionObject(
        id=f"act_content_new_page_dev_draft_{uuid4().hex}",
        title="Przygotuj nowy szkic na dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=unique_values(readiness.evidence_ids),
        human_diagnosis=(
            "Dokładna rewizja nowej strony została zatwierdzona. Operator wybrał "
            "obserwowany typ nowego obiektu; WILQ nadal nie publikuje ani nie aktualizuje treści."
        ),
        recommended_reason=(
            "Otwórz lokalną akcję w centrum działań i przejdź preview, review, "
            "confirm oraz kontrolę gotowości przed jednym szkicem na dev."
        ),
        payload={
            "action_type": CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "preview_contract": CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT,
            "mode": "dev_draft_only",
            "new_page_draft_binding": binding.model_dump(mode="json"),
            "payload_preview": [
                {
                    "preview_contract": CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT,
                    "operation_type_label": "Utworzenie nowego szkicu na dev",
                    "content_type": command.content_type,
                    "apply_allowed": True,
                    "api_mutation_ready": True,
                }
            ],
            "required_validation": [
                "validate_action_object",
                "exact_document_revision_check",
                "exact_authoring_profile_check",
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


def persist_new_page_draft_action(action: ActionObject) -> ActionObject:
    """Persist only creation of this local, non-writing ActionObject."""

    event = AuditEvent(
        id=f"audit_{action.id}_created",
        action_id=action.id,
        event_type=CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CREATED_EVENT,
        event_type_label="Przygotowano akcję nowego szkicu na dev",
        actor=action.created_by,
        summary=(
            "Przygotowano lokalną akcję dla zatwierdzonej nowej strony. "
            "Nie utworzono szkicu ani nie zapisano niczego w WordPressie."
        ),
        evidence_ids=action.evidence_ids,
        details={"content_new_page_draft_action": action.model_dump(mode="json")},
    )
    return _action_from_creation_event(local_state_store().save_audit_event(event))


def load_new_page_draft_action(action_id: str) -> ActionObject | None:
    """Load only the local creation event owned by this action type."""

    for event in local_state_store().list_audit_events(action_id):
        if event.event_type != CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CREATED_EVENT:
            continue
        try:
            return _action_from_creation_event(event)
        except ValueError:
            return None
    return None


def _action_from_creation_event(event: AuditEvent) -> ActionObject:
    payload = event.details.get("content_new_page_draft_action")
    if not isinstance(payload, dict):
        raise ValueError("Brakuje zapisanego payloadu akcji nowego szkicu na dev.")
    return ActionObject.model_validate(payload)


__all__ = [
    "CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT",
    "CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CREATED_EVENT",
    "CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE",
    "ContentNewPageDraftActionCommand",
    "create_new_page_draft_action",
    "load_new_page_draft_action",
    "persist_new_page_draft_action",
]
