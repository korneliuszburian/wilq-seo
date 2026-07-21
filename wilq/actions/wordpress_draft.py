from __future__ import annotations

from typing import Any

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)


def draft_handoff_action(
    *,
    source_connectors: list[str],
    source_metric_names: list[str],
    preview_items: list[dict[str, Any]],
    content_action_metrics: list[MetricFact],
    evidence_ids: list[str],
) -> ActionObject:
    return ActionObject(
        id="act_prepare_wordpress_draft_handoff",
        title="Przygotuj zablokowany podgląd szkicu WordPress",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        metrics=content_action_metrics,
        human_diagnosis=(
            "WILQ ma kolejkę treści z GSC, WordPress i Ahrefs i może przygotować "
            "wyłącznie zablokowany podgląd szkicu WordPress. To nie jest zapis "
            "ani publikacja."
        ),
        recommended_reason=(
            "Użyj tej akcji jako checklisty przed przyszłym szkicem WordPress: "
            "najpierw finalny URL, canonical, duplicate/cannibalization, legal/factual "
            "i przegląd człowieka. Bez tych bramek szkic pozostaje zablokowany."
        ),
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "wordpress_draft_handoff_preview_v1",
            "depends_on_action_id": "act_prepare_content_refresh_queue",
            "source_connectors": source_connectors,
            "source_metric_names": source_metric_names,
            "required_input_contracts": [
                "content_brief_preview_v1",
                "content_draft_generation_v1",
                "content_draft_readiness_review_v1",
                "wordpress_draft_handoff_v1",
                "post_publication_measurement_plan_v1",
            ],
            "payload_preview": preview_items,
            "required_validation": [
                "content_url_preflight_review",
                "final_canonical_review",
                "duplicate_or_cannibalization_check",
                "legal_factual_review",
                "content_draft_readiness_review",
                "wordpress_draft_preview_review",
                "human_confirm_before_wordpress_write",
            ],
            "blocked_claims": [
                "wordpress_draft_write",
                "wordpress_publish",
                "production_wordpress_write",
                "publish_ready_claim",
                "obietnica wzrostu pozycji albo leadów",
            ],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def draft_apply_action(
    *,
    handoff_action: ActionObject,
    apply_contract_payload: dict[str, Any],
) -> ActionObject:
    return ActionObject(
        id="act_apply_wordpress_draft_handoff",
        title="Aktywuj zapis szkicu WordPress draft-only",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=handoff_action.evidence_ids,
        metrics=handoff_action.metrics,
        human_diagnosis=(
            "To jest jawna propozycja apply-mode dla pierwszej bezpiecznej klasy "
            "zapisu: utworzenia szkicu WordPress. Nie publikuje i nie aktualizuje "
            "istniejących wpisów."
        ),
        recommended_reason=(
            "Użyj tej akcji do sprawdzania gotowości przyszłego zapisu szkicu. "
            "Dopóki podgląd zmian, review człowieka, potwierdzenie operatora, "
            "audyt wpływu, zgoda środowiska i warstwa wykonania nie są gotowe, "
            "WILQ nie może zapisać szkicu w WordPress."
        ),
        payload={
            "action_type": "wordpress_draft_handoff",
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "preview_contract": "wordpress_draft_apply_preview_v1",
            "depends_on_action_id": handoff_action.id,
            "allowed_operation": "create_wordpress_draft",
            "apply_contract": apply_contract_payload,
            "source_connectors": handoff_action.payload.get("source_connectors", []),
            "source_metric_names": handoff_action.payload.get("source_metric_names", []),
            "required_input_contracts": handoff_action.payload.get(
                "required_input_contracts", []
            ),
            "payload_preview": handoff_action.payload.get("payload_preview", []),
            "required_validation": [
                "content_url_preflight_review",
                "final_canonical_review",
                "duplicate_or_cannibalization_check",
                "legal_factual_review",
                "content_draft_readiness_review",
                "wordpress_draft_preview_review",
                "human_confirm_before_wordpress_write",
                "wordpress_draft_write_readiness",
            ],
            # These are forbidden outputs of the draft-only contract, not
            # blockers for creating the draft itself.  Keep them in the
            # contract's blocked_outputs so the generic ActionObject gate does
            # not confuse safety boundaries with an unavailable adapter.
            "blocked_outputs": [
                "wordpress_publish",
                "wordpress_update_existing_post",
                "wordpress_delete_post",
                "production_wordpress_write",
                "publish_ready_claim",
                "obietnica wzrostu pozycji albo leadów",
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_metric_seed",
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
