from __future__ import annotations

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def existing_draft_update_action() -> ActionObject:
    """Seed the prepare-only existing dev draft update action."""
    return ActionObject(
        id="act_prepare_wordpress_existing_draft_update",
        title="Przygotuj sprawdzenie aktualizacji istniejącego draftu WordPress",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.high,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id("wordpress_ekologus")],
        human_diagnosis=(
            "Aktualizacja istniejącego draftu dev wymaga osobnego podglądu "
            "różnic, review człowieka, potwierdzenia i audytu."
        ),
        recommended_reason=(
            "Najpierw pokaż bieżące sekcje ACF i proponowane zmiany; nie "
            "wykonuj zapisu, dopóki adapter update nie przejdzie pełnej ścieżki bezpieczeństwa."
        ),
        payload={
            "action_type": "wordpress_draft_update",
            "mode": "prepare_only",
            "preview_contract": "wordpress_existing_draft_update_preview_v1",
            "allowed_operation": "update_wordpress_dev_draft",
            "required_validation": [
                "existing_draft_readback",
                "acf_current_vs_proposed_review",
                "human_review_before_update",
                "action_confirm_before_update",
                "audit_event_before_update",
            ],
            "payload_preview": [
                {
                    "operation_type": "UpdateWordPressDevDraftOperation",
                    "current_state": "readback_required",
                    "proposed_state": "section_overrides_after_human_review",
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "destructive": False,
                }
            ],
            "blocked_claims": [
                "wordpress_publish",
                "production_wordpress_write",
                "wordpress_update_existing_post",
                "destructive_acf_update",
            ],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        preview_cards=[_existing_draft_update_preview_card()],
        created_by="system_core_seed",
    )


def _existing_draft_update_preview_card() -> ActionPreviewCardViewModel:
    return ActionPreviewCardViewModel(
        id="wordpress_existing_draft_update_preview",
        kind="wordpress_existing_draft_update_review",
        title_label="Aktualizacja istniejącego szkicu do sprawdzenia",
        subtitle_label="podgląd dev bez zapisu i bez publikacji",
        status_label="zapis zmian zablokowany",
        rows=[
            ActionPreviewRowViewModel(
                label="Stan bieżący",
                value="Najpierw odczytaj istniejący szkic i sekcje ACF na devie.",
            ),
            ActionPreviewRowViewModel(
                label="Proponowana zmiana",
                value="Nadpisania sekcji wymagają podglądu i review człowieka.",
            ),
            ActionPreviewRowViewModel(
                label="Dozwolony zakres",
                value="Wyłącznie istniejący szkic na devie; publikacja jest zablokowana.",
            ),
        ],
        apply_state_label="zapis zmian zablokowany",
        system_readiness_label="adapter aktualizacji nie jest gotowy",
    )
