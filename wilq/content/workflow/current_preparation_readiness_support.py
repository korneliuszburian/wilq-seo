"""Pure/read-only helpers for current-preparation readiness."""

from __future__ import annotations

from typing import cast

from wilq.content.workflow.current_preparation_readiness_contracts import (
    CurrentPreparationReadinessStore,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    ContentProductionRegisteredInventoryReceipt,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityBinding,
    content_delivery_identity_logical_id,
)
from wilq.content.workflow.research_packet_preparation import (
    ResearchPacketPreparationStore,
    latest_source_pack_for_work_item,
)
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding

BLOCKER_COPY: dict[str, tuple[str, str]] = {
    "classification_current_missing": (
        "Brakuje bieżącej klasyfikacji.",
        "Najpierw odczytaj bieżącą klasyfikację produkcyjną.",
    ),
    "classification_item_missing": (
        "Bieżąca klasyfikacja nie ma exact wiersza dla tej strony.",
        "Odczytaj exact wiersz klasyfikacji dla bieżącego work itemu.",
    ),
    "current_work_item_mismatch": (
        "Receipt refresh nie może przejąć aliasu ani historycznego work itemu.",
        "Otwórz exact current work item wskazany przez bieżącą klasyfikację.",
    ),
    "current_content_binding_missing": (
        "Ten wyjątek dotyczy wyłącznie blocked row z jednym blockerem "
        "current_content_binding_missing.",
        "Zachowaj bieżącą klasyfikację i przejdź jej wskazaną ścieżkę.",
    ),
    "registered_current_inventory_required": (
        "Bieżący receipt inventory nie jest dokładnym, nieukończonym receipt-em current.",
        "Odczytaj exact registered_current_inventory bez retained revision, action "
        "ani draft lineage.",
    ),
    "classification_stale": (
        "Bieżąca klasyfikacja nie ma świeżych źródeł wymaganych przez refresh.",
        "Odśwież klasyfikację z aktualnych źródeł przed autoryzacją refresh.",
    ),
    "identity_binding_missing": (
        "Brakuje exact current delivery identity dla tego wiersza.",
        "Zarejestruj exact delivery identity dla bieżącej klasyfikacji i inventory.",
    ),
    "identity_binding_not_exact_current": (
        "Delivery identity nie odpowiada dokładnie bieżącej klasyfikacji.",
        "Odśwież exact identity po bieżącej klasyfikacji; nie rejestruj jej z samego URL-a.",
    ),
    "disposition_not_keep": (
        "Refresh authorization wymaga exact current identity z decyzją keep.",
        "Nie generuj treści dla tego URL-a; przejdź bieżącą ścieżkę disposition.",
    ),
    "source_pack_binding_missing": (
        "Brakuje source-pack bindingu dla exact current work itemu.",
        "Zapisz exact source-pack na podstawie bieżącej identity i source-fact authority.",
    ),
    "source_pack_identity_mismatch": (
        "Najnowszy source-pack nie jest związany z bieżącą identity.",
        "Odśwież source-pack dla exact current identity; nie używaj starszej paczki.",
    ),
}


def latest_run(
    store: CurrentPreparationReadinessStore,
) -> ContentProductionClassificationRun | None:
    loader = getattr(store, "load_latest_production_classification", None)
    if not callable(loader):
        return None
    try:
        value = loader()
    except (AttributeError, TypeError, ValueError):
        return None
    return value if isinstance(value, ContentProductionClassificationRun) else None


def load_identity(
    store: CurrentPreparationReadinessStore, binding_id: str
) -> ContentDeliveryIdentityBinding | None:
    loader = getattr(store, "load_content_delivery_identity", None)
    if callable(loader):
        try:
            value = loader(binding_id)
        except (AttributeError, TypeError, ValueError):
            value = None
        if isinstance(value, ContentDeliveryIdentityBinding):
            return value
    loader = getattr(store, "load_content_delivery_identity_record", None)
    if callable(loader):
        try:
            record = loader(binding_id)
        except (AttributeError, TypeError, ValueError):
            return None
        value = None if record is None else getattr(record, "binding", None)
        return value if isinstance(value, ContentDeliveryIdentityBinding) else None
    return None


def latest_source_pack(
    store: CurrentPreparationReadinessStore, work_item_id: str
) -> ContentSourcePackBinding | None:
    return latest_source_pack_for_work_item(
        cast(ResearchPacketPreparationStore, store),
        work_item_id,
    )


def is_safe_blocked_row(row: ContentProductionClassificationRow) -> bool:
    return (
        row.decision == "blocked"
        and len(row.blockers) == 1
        and row.blockers[0].code == "current_content_binding_missing"
    )


def registered_inventory_is_pending(row: ContentProductionClassificationRow) -> bool:
    receipt = row.source_receipt
    return (
        isinstance(receipt, ContentProductionRegisteredInventoryReceipt)
        and row.current_work_item_id == receipt.current_work_item_id
        and row.canonical_path == receipt.canonical_path
        and row.public_url == receipt.public_url
        and row.retained_work_item_id is None
        and row.revision_id is None
        and row.revision_digest is None
        and row.revision_approved is False
        and row.revision_complete is False
        and row.retained_binding is None
        and not row.verified_actions
        and not row.verified_drafts
    )


def identity_id(
    run: ContentProductionClassificationRun, row: ContentProductionClassificationRow
) -> str:
    logical_id = content_delivery_identity_logical_id(
        {
            "canonical_path": row.canonical_path,
            "public_url": row.public_url,
            "current_work_item_id": row.current_work_item_id,
            "classification_run_id": run.run_id,
        }
    )
    return f"content_delivery_identity_{logical_id[:24]}"


def context(
    run: ContentProductionClassificationRun,
    row: ContentProductionClassificationRow | None,
) -> dict[str, str | None]:
    return {
        "classification_run_id": run.run_id,
        "classification_run_digest": run.run_digest,
        "decision_set_digest": run.input.decision_set_digest,
        "source_packet_row_digest": None if row is None else row.source_packet_row_digest,
    }


def blocker_copy(code: str) -> tuple[str, str]:
    return BLOCKER_COPY.get(
        code,
        (
            "Bieżące receipt-y nie tworzą exact current kontekstu.",
            "Odśwież exact receipt-y i ponów przygotowanie refresh.",
        ),
    )


__all__ = [
    "blocker_copy",
    "context",
    "identity_id",
    "is_safe_blocked_row",
    "latest_run",
    "latest_source_pack",
    "load_identity",
    "registered_inventory_is_pending",
]
