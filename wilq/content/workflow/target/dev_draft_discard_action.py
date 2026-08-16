"""Recoverable cleanup of one exact WILQ-created WordPress dev draft."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from wilq.actions.metric_utils import unique_values
from wilq.connectors.wordpress.client import (
    WordPressDraftDiscardReadback,
    WordPressDraftReadError,
    WordPressDraftWriteError,
    read_wordpress_draft_discard_readback,
    trash_wordpress_draft,
)
from wilq.content.workflow.policies import wordpress_draft_writes_enabled
from wilq.content.workflow.target.dev_draft_action import load_content_target_draft_action
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store

CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE = "content_dev_draft_discard"
CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT = "content_dev_draft_discard_action_v1"
CONTENT_DEV_DRAFT_DISCARD_ACTION_CREATED_EVENT = "content_dev_draft_discard_action_created"

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StateLabel = Callable[[Any], str]


class ContentDevDraftDiscardActionCommand(BaseModel):
    """Request a reviewable trash operation for one known WILQ dev draft."""

    model_config = ConfigDict(extra="forbid")

    post_id: str = Field(pattern=r"^[1-9][0-9]*$")
    endpoint: Literal["posts", "pages", "uslugi"]
    origin_action_id: str = Field(min_length=1, max_length=200)
    defect_codes: list[
        Literal["duplicate_h1", "official_sources_footer", "incomplete_acf_clone"]
    ] = Field(min_length=1, max_length=3)
    requested_by: str = Field(min_length=1, max_length=200)


def create_content_dev_draft_discard_action(
    command: ContentDevDraftDiscardActionCommand,
) -> ActionObject:
    """Prepare one exact, recoverable cleanup action; performs no WordPress write."""

    origin = load_content_target_draft_action(command.origin_action_id)
    if origin is None:
        raise ValueError("Nie znaleziono pierwotnej akcji WILQ dla wskazanego szkicu.")
    if not _origin_action_applied(command.origin_action_id):
        raise ValueError("Pierwotna akcja WILQ nie ma potwierdzonego zapisu szkicu.")
    try:
        observed = read_wordpress_draft_discard_readback(
            command.post_id,
            endpoint=command.endpoint,
        )
    except WordPressDraftReadError as error:
        raise ValueError(str(error)) from error
    if observed.status != "draft":
        raise ValueError("Można wycofać wyłącznie aktualny obiekt WordPress ze statusem draft.")
    if not observed.title or not observed.modified_gmt:
        raise ValueError("Odczyt szkicu WordPress nie ma kompletnej tożsamości do wycofania.")

    target = _target_payload(command, observed)
    evidence_ids = unique_values(
        [connector_evidence_id("wordpress_ekologus"), *origin.evidence_ids]
    )
    return ActionObject(
        id=f"act_content_dev_draft_discard_{uuid4().hex}",
        title="Przenieś wadliwy szkic WILQ do kosza na dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "WILQ wykrył wadliwy, wcześniej utworzony szkic dev. Ta akcja nie "
            "dotyka opublikowanego źródła ani nie wykonuje trwałego usunięcia."
        ),
        recommended_reason=(
            "Sprawdź dokładny fingerprint szkicu, zapisz review i potwierdzenie. "
            "Po apply WordPress ma przenieść wyłącznie ten jeden niezmieniony draft do kosza."
        ),
        payload={
            "action_type": CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "preview_contract": CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT,
            "mode": "dev_draft_trash_only",
            "allowed_operation": "trash_wordpress_dev_draft",
            "draft_discard_target": target,
            "payload_preview": [_preview_item(target)],
            "required_validation": [
                "validate_action_object",
                "origin_action_applied_check",
                "exact_draft_fingerprint_check",
                "human_review_before_apply",
                "human_confirm_before_wordpress_write",
            ],
            "operator_review_gates": [
                "origin_action_applied_check",
                "exact_draft_fingerprint_check",
                "human_review_before_apply",
                "human_confirm_before_wordpress_write",
            ],
            "recoverable_operation": True,
            "destructive": False,
            "apply_allowed": True,
            "api_mutation_ready": True,
        },
        validation_status="not_validated",
        created_by=command.requested_by,
    )


def persist_content_dev_draft_discard_action(action: ActionObject) -> ActionObject:
    event = AuditEvent(
        id=f"audit_{action.id}_created",
        action_id=action.id,
        event_type=CONTENT_DEV_DRAFT_DISCARD_ACTION_CREATED_EVENT,
        event_type_label="Przygotowano akcję przeniesienia szkicu do kosza",
        actor=action.created_by,
        summary=(
            "Przygotowano lokalną akcję przeniesienia jednego wadliwego szkicu dev "
            "do kosza. Nie zapisano niczego w WordPressie."
        ),
        evidence_ids=action.evidence_ids,
        details={"content_dev_draft_discard_action": action.model_dump(mode="json")},
    )
    return _action_from_creation_event(local_state_store().save_audit_event(event))


def load_content_dev_draft_discard_action(action_id: str) -> ActionObject | None:
    for event in local_state_store().list_audit_events(action_id):
        if event.event_type != CONTENT_DEV_DRAFT_DISCARD_ACTION_CREATED_EVENT:
            continue
        try:
            return _action_from_creation_event(event)
        except ValueError:
            return None
    return None


def execute_content_dev_draft_discard_action(
    action: ActionObject,
) -> tuple[dict[str, object] | None, list[str]]:
    """Execute one already-reviewed trash operation through the ActionObject seam."""

    if action.payload.get("action_type") != CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE:
        return None, ["Ta akcja nie jest obsługiwaną akcją wycofania szkicu dev."]
    if not _dev_draft_writes_enabled():
        return None, [
            "Środowisko dev nie zezwala obecnie na przeniesienie szkicu WordPress do kosza."
        ]
    target = action.payload.get("draft_discard_target")
    if not isinstance(target, dict):
        return None, ["Akcja wycofania szkicu nie ma dokładnego targetu."]
    required = ("post_id", "endpoint", "modified_gmt", "content_digest", "acf_digest")
    if any(not isinstance(target.get(key), str) or not target[key] for key in required):
        return None, ["Akcja wycofania szkicu ma niekompletny fingerprint targetu."]
    try:
        current = read_wordpress_draft_discard_readback(
            target["post_id"],
            endpoint=target["endpoint"],
        )
        if current.status == "trash":
            return {
                "adapter": "content_dev_draft_discard_execution_boundary",
                "connector": action.connector,
                "allowed_operation": "trash_wordpress_dev_draft",
                "trashed_draft_id": current.post_id,
                "external_write_attempted": False,
                "reconciled_existing_trash": True,
                "publish_allowed": False,
                "update_allowed": False,
                "force_delete_allowed": False,
                "recoverable_operation": True,
                "redacted": True,
            }, []
        post_id = trash_wordpress_draft(
            post_id=target["post_id"],
            endpoint=target["endpoint"],
            expected_modified_gmt=target["modified_gmt"],
            expected_content_digest=target["content_digest"],
            expected_acf_digest=target["acf_digest"],
        )
    except (ValueError, WordPressDraftReadError, WordPressDraftWriteError) as error:
        return None, [str(error)]
    return {
        "adapter": "content_dev_draft_discard_execution_boundary",
        "connector": action.connector,
        "allowed_operation": "trash_wordpress_dev_draft",
        "trashed_draft_id": post_id,
        "external_write_attempted": True,
        "reconciled_existing_trash": False,
        "publish_allowed": False,
        "update_allowed": False,
        "force_delete_allowed": False,
        "recoverable_operation": True,
        "redacted": True,
    }, []


def _origin_action_applied(action_id: str) -> bool:
    return any(
        event.event_type == "apply_succeeded"
        for event in local_state_store().list_audit_events(action_id)
    )


def _dev_draft_writes_enabled() -> bool:
    return wordpress_draft_writes_enabled()


def _target_payload(
    command: ContentDevDraftDiscardActionCommand,
    observed: WordPressDraftDiscardReadback,
) -> dict[str, object]:
    return {
        "post_id": observed.post_id,
        "endpoint": observed.endpoint,
        "title": observed.title,
        "modified_gmt": observed.modified_gmt,
        "content_digest": observed.content_digest,
        "acf_digest": observed.acf_digest,
        "origin_action_id": command.origin_action_id,
        "defect_codes": sorted(set(command.defect_codes)),
    }


def _preview_item(target: dict[str, object]) -> dict[str, object]:
    defect_codes = target.get("defect_codes")
    count = len(defect_codes) if isinstance(defect_codes, list) else 0
    return {
        "operation_type_label": "Przeniesienie jednego szkicu dev do kosza",
        "target_label": f"{target['endpoint']} #{target['post_id']}: {target['title']}",
        "status_label": "odzyskiwalne; bez publikacji i bez trwałego usunięcia",
        "defect_count_label": f"{count} potwierdzone problemy",
        "apply_allowed": True,
        "api_mutation_ready": True,
    }


def content_dev_draft_discard_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render the exact recoverable target instead of a generic raw payload."""

    target = payload.get("draft_discard_target")
    if not isinstance(target, dict):
        return []
    post_id = target.get("post_id")
    endpoint = target.get("endpoint")
    title = target.get("title")
    target_label = (
        f"{endpoint} #{post_id}: {title}"
        if all(isinstance(value, str) and value for value in (endpoint, post_id, title))
        else "dokładny szkic wymaga ponownego odczytu"
    )
    defect_codes = target.get("defect_codes")
    known_defect_codes = defect_codes if isinstance(defect_codes, list) else []
    defects = [
        _defect_label(code)
        for code in known_defect_codes
        if isinstance(code, str)
    ]
    origin_action_id = target.get("origin_action_id")
    rows = [
        preview_row("Szkic dev", target_label),
        preview_row(
            "Operacja",
            "Przeniesienie do kosza WordPress (możliwe odzyskanie; bez trwałego usunięcia)",
        ),
        preview_row(
            "Wykryte problemy",
            ", ".join(defects) if defects else "wymagają potwierdzenia",
        ),
    ]
    if isinstance(origin_action_id, str) and origin_action_id:
        rows.append(preview_row("Pochodzenie", "wcześniejsza akcja WILQ jest zapisana w audycie"))
    return [
        ActionPreviewCardViewModel(
            id="content_dev_draft_discard_preview",
            kind="content_dev_draft_discard_review",
            title_label="Wadliwy szkic dev do wycofania",
            subtitle_label="dokładny target; bez publikacji i bez trwałego usunięcia",
            status_label="wymaga potwierdzenia człowieka przed zapisem WordPress",
            rows=rows,
            apply_state_label=apply_state_label(payload.get("apply_allowed")),
            system_readiness_label=system_readiness_label(payload.get("api_mutation_ready")),
        )
    ]


def _defect_label(code: str) -> str:
    return {
        "duplicate_h1": "powielony nagłówek H1 w treści",
        "official_sources_footer": "automatyczna stopka źródeł w treści",
        "incomplete_acf_clone": "niekompletna struktura ACF",
    }.get(code, "problem wymagający sprawdzenia")


def _action_from_creation_event(event: AuditEvent) -> ActionObject:
    payload = event.details.get("content_dev_draft_discard_action")
    if not isinstance(payload, dict):
        raise ValueError("Brakuje danych akcji wycofania szkicu.")
    return ActionObject.model_validate(payload)


__all__ = [
    "CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT",
    "CONTENT_DEV_DRAFT_DISCARD_ACTION_CREATED_EVENT",
    "CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE",
    "ContentDevDraftDiscardActionCommand",
    "content_dev_draft_discard_preview_cards",
    "create_content_dev_draft_discard_action",
    "execute_content_dev_draft_discard_action",
    "load_content_dev_draft_discard_action",
    "persist_content_dev_draft_discard_action",
]
