from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.inventory.records import (
    ContentInventoryResolution,
    ContentInventoryResolutionStatus,
)
from wilq.content.workflow.models import ContentWorkItem

ContentPreflightVerdictStatus = Literal[
    "blocked",
    "plan_allowed",
    "brief_allowed",
    "draft_allowed",
    "handoff_allowed",
]


class ContentPreflightBlocker(BaseModel):
    code: str
    label: str
    reason: str
    next_step: str
    blocks_current_stage: bool = False


class ContentPreflightVerdict(BaseModel):
    status: ContentPreflightVerdictStatus
    recommended_mode: str
    create_allowed: bool = False
    sales_brief_allowed: bool = False
    draft_allowed: bool = False
    wordpress_draft_allowed: bool = False
    final_canonical_url: str | None = None
    preview_url: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    similar_existing_urls: list[str] = Field(default_factory=list)
    blockers: list[ContentPreflightBlocker] = Field(default_factory=list)
    next_step: str


def build_content_preflight_verdict(
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
) -> ContentPreflightVerdict:
    hard_blockers = [
        *_source_blockers(item),
        *_inventory_blockers(inventory_resolution),
    ]
    if hard_blockers:
        return _verdict(
            status="blocked",
            item=item,
            inventory_resolution=inventory_resolution,
            blockers=hard_blockers,
            next_step=(
                "Najpierw usuń twarde blokady: dowody, źródła, adres docelowy "
                "albo duplikację."
            ),
        )

    soft_blockers = _soft_blockers(item)
    status = _allowed_status(item)
    return _verdict(
        status=status,
        item=item,
        inventory_resolution=inventory_resolution,
        blockers=soft_blockers,
        next_step=_next_step_for_status(status, inventory_resolution.status),
    )


def _allowed_status(item: ContentWorkItem) -> ContentPreflightVerdictStatus:
    if item.preserve_first_plan_status not in {"ready", "approved"}:
        return "plan_allowed"
    if (
        item.sales_brief_status != "approved"
        or not item.sales_brief_id
        or item.claim_ledger_status != "approved"
        or not item.claim_ledger_id
        or item.measurement_window_status == "missing"
        or not item.measurement_window_id
    ):
        return "brief_allowed"
    if (
        item.draft_package_status != "ready"
        or not item.draft_package_id
        or item.human_review_status != "approved"
        or not item.human_review_id
        or item.audit_status != "recorded"
        or not item.audit_id
    ):
        return "draft_allowed"
    return "handoff_allowed"


def _source_blockers(item: ContentWorkItem) -> list[ContentPreflightBlocker]:
    blockers: list[ContentPreflightBlocker] = []
    if not item.evidence_ids:
        blockers.append(
            _blocker(
                "missing_evidence",
                "Brakuje dowodów",
                "WILQ nie może rekomendować pracy nad treścią bez podpiętego dowodu.",
                "Najpierw odśwież albo podłącz dane dla tego tematu.",
                blocks_current_stage=True,
            )
        )
    if not item.source_connectors:
        blockers.append(
            _blocker(
                "missing_source_connector",
                "Brakuje źródła danych",
                "WILQ nie może pisać z samego promptu albo notatki.",
                "Wskaż źródło danych, z którego pochodzi fakt.",
                blocks_current_stage=True,
            )
        )
    return blockers


def _inventory_blockers(
    inventory_resolution: ContentInventoryResolution,
) -> list[ContentPreflightBlocker]:
    if inventory_resolution.status != "blocked":
        return []
    return [
        _blocker(
            blocker.code,
            blocker.label,
            blocker.reason,
            blocker.next_step,
            blocks_current_stage=True,
        )
        for blocker in inventory_resolution.blockers
    ]


def _soft_blockers(item: ContentWorkItem) -> list[ContentPreflightBlocker]:
    blockers: list[ContentPreflightBlocker] = []
    if item.preserve_first_plan_status not in {"ready", "approved"}:
        blockers.append(
            _blocker(
                "missing_preserve_first_plan",
                "Brakuje planu dla istniejącej treści",
                "WILQ musi rozstrzygnąć, czy zachować, odświeżyć, scalić czy tworzyć.",
                "Przygotuj plan dla istniejącej treści przed planem sprzedażowym.",
            )
        )
    if item.sales_brief_status != "approved" or not item.sales_brief_id:
        blockers.append(
            _blocker(
                "missing_sales_brief",
                "Brakuje zaakceptowanego briefu",
                "Bez briefu sprzedażowego szkic będzie zbyt łatwo generyczny.",
                "Przygotuj i zatwierdź plan sprzedażowy.",
            )
        )
    if item.claim_ledger_status != "approved" or not item.claim_ledger_id:
        blockers.append(
            _blocker(
                "missing_claim_ledger",
                "Brakuje sprawdzenia twierdzeń",
                "Ryzykowne twierdzenia muszą być sprawdzone przed szkicem.",
                "Sprawdź i zatwierdź ryzykowne twierdzenia.",
            )
        )
    if item.measurement_window_status == "missing" or not item.measurement_window_id:
        blockers.append(
            _blocker(
                "missing_measurement_window",
                "Brakuje planu pomiaru",
                "Nie czekamy na wyniki, ale musimy wiedzieć, co będziemy mierzyć.",
                "Utwórz plan pomiaru przed szkicem albo przekazaniem do WordPress.",
            )
        )
    if item.draft_package_status != "ready" or not item.draft_package_id:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Przekazanie do WordPress wymaga paczki szkicu z dowodami i twierdzeniami.",
                "Przygotuj paczkę szkicu przed przekazaniem.",
            )
        )
    if item.human_review_status != "approved" or not item.human_review_id:
        blockers.append(
            _blocker(
                "missing_human_review",
                "Brakuje decyzji człowieka",
                "Szkic nie może trafić do WordPress bez decyzji człowieka.",
                "Zatwierdź szkic w sprawdzeniu człowieka.",
            )
        )
    if item.audit_status != "recorded" or not item.audit_id:
        blockers.append(
            _blocker(
                "missing_audit",
                "Brakuje audytu",
                "Każde przekazanie musi zostawić ślad audytowy.",
                "Zapisz audyt przed utworzeniem szkicu w WordPress.",
            )
        )
    return blockers


def _verdict(
    *,
    status: ContentPreflightVerdictStatus,
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
    blockers: list[ContentPreflightBlocker],
    next_step: str,
) -> ContentPreflightVerdict:
    return ContentPreflightVerdict(
        status=status,
        recommended_mode=inventory_resolution.recommended_mode,
        create_allowed=(
            status != "blocked" and inventory_resolution.recommended_mode == "create_after_review"
        ),
        sales_brief_allowed=status in {"brief_allowed", "draft_allowed", "handoff_allowed"},
        draft_allowed=status in {"draft_allowed", "handoff_allowed"},
        wordpress_draft_allowed=status == "handoff_allowed",
        final_canonical_url=item.final_canonical_url,
        preview_url=item.preview_url,
        evidence_ids=item.evidence_ids or inventory_resolution.evidence_ids,
        source_connectors=item.source_connectors or inventory_resolution.source_connectors,
        similar_existing_urls=inventory_resolution.similar_existing_urls,
        blockers=blockers,
        next_step=next_step,
    )


def _next_step_for_status(
    status: ContentPreflightVerdictStatus,
    inventory_status: ContentInventoryResolutionStatus,
) -> str:
    if status == "plan_allowed":
        return (
            "Przygotuj plan dla istniejącej treści na podstawie spisu treści "
            "i ryzyka duplikacji."
        )
    if status == "brief_allowed":
        return "Przygotuj plan sprzedażowy, sprawdzenie twierdzeń i plan pomiaru przed szkicem."
    if status == "draft_allowed":
        return "Można przygotować paczkę szkicu, ale WordPress wymaga decyzji człowieka i audytu."
    if status == "handoff_allowed":
        return "Można przygotować szkic w WordPress. Publikacja nadal nie jest automatyczna."
    if inventory_status == "blocked":
        return "Najpierw rozwiąż blokady w spisie treści."
    return "Najpierw rozwiąż blokady sprawdzenia wstępnego."


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    *,
    blocks_current_stage: bool = False,
) -> ContentPreflightBlocker:
    return ContentPreflightBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        blocks_current_stage=blocks_current_stage,
    )
