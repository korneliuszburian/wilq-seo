from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.schemas import MetricFact

ContentInventoryStatus = Literal["missing", "resolved", "blocked"]
ContentCanonicalStatus = Literal["missing", "resolved", "blocked"]
ContentDuplicateStatus = Literal["missing", "checked", "risk_found", "blocked"]
ContentPreflightStatus = Literal[
    "missing",
    "blocked",
    "plan_allowed",
    "brief_allowed",
    "draft_allowed",
    "handoff_allowed",
]
ContentArtifactStatus = Literal["missing", "ready", "approved", "blocked"]
ContentHumanReviewStatus = Literal[
    "missing",
    "approved",
    "needs_changes",
    "rejected",
    "deferred",
]
ContentAuditStatus = Literal["missing", "recorded"]
ContentWordPressHandoffStatus = Literal[
    "missing",
    "blocked",
    "prepared",
    "draft_created",
]
ContentMeasurementWindowStatus = Literal[
    "missing",
    "planned",
    "open",
    "ready_for_review",
    "closed",
]
ContentWordPressSectionInventoryStatus = Literal["available", "missing"]
ContentWorkflowAction = Literal[
    "prepare_sales_brief",
    "prepare_draft",
    "create_wordpress_draft",
    "claim_measurement_outcome",
]
ContentWorkflowBlockerCode = Literal[
    "missing_evidence",
    "missing_source_connector",
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_inventory_resolution",
    "duplicate_gate_not_checked",
    "duplicate_or_canonical_risk",
    "missing_preflight",
    "blocked_preflight",
    "missing_preserve_first_plan",
    "missing_sales_brief",
    "missing_claim_ledger",
    "missing_draft_package",
    "missing_human_review",
    "missing_audit",
    "missing_measurement_window",
    "measurement_window_not_ready",
]


class ContentWorkItem(BaseModel):
    """One Ekologus content item moving through the content production workflow."""

    id: str
    topic: str
    source_public_url: str | None = None
    final_canonical_url: str | None = None
    intended_final_url: str | None = None
    preview_url: str | None = None
    wordpress_title_or_h1: str | None = None
    wordpress_section_headings: list[str] = Field(default_factory=list)
    wordpress_section_count: int | None = None
    wordpress_section_inventory_status: ContentWordPressSectionInventoryStatus = "missing"
    wordpress_content_summary: str | None = None
    wordpress_content_text: str | None = None
    wordpress_content_source_kind: str | None = None
    wordpress_content_extraction_region: str | None = None
    wordpress_content_material_confidence: str | None = None
    wordpress_content_source_field_lineage: list[str] = Field(default_factory=list)
    wordpress_content_word_count: int | None = None
    wordpress_content_inventory_status: Literal["available", "missing"] = "missing"
    wordpress_content_inventory_note: str | None = None
    wordpress_acf_section_inventory_status: Literal["available", "missing"] = "missing"
    wordpress_acf_section_inventory_note: str | None = None
    wordpress_acf_section_headings: list[str] = Field(default_factory=list)
    wordpress_acf_section_count: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    inventory_status: ContentInventoryStatus = "missing"
    canonical_status: ContentCanonicalStatus = "missing"
    duplicate_status: ContentDuplicateStatus = "missing"
    preflight_status: ContentPreflightStatus = "missing"
    preserve_first_plan_status: ContentArtifactStatus = "missing"
    sales_brief_status: ContentArtifactStatus = "missing"
    sales_brief_id: str | None = None
    claim_ledger_status: ContentArtifactStatus = "missing"
    claim_ledger_id: str | None = None
    draft_package_status: ContentArtifactStatus = "missing"
    draft_package_id: str | None = None
    human_review_status: ContentHumanReviewStatus = "missing"
    human_review_id: str | None = None
    audit_status: ContentAuditStatus = "missing"
    audit_id: str | None = None
    wordpress_handoff_status: ContentWordPressHandoffStatus = "missing"
    wordpress_post_id: str | None = None
    measurement_window_status: ContentMeasurementWindowStatus = "missing"
    measurement_window_id: str | None = None
    metric_facts: list[MetricFact] = Field(default_factory=list)


class ContentWorkflowBlocker(BaseModel):
    code: ContentWorkflowBlockerCode
    label: str
    reason: str
    next_step: str


def content_workflow_blockers(
    item: ContentWorkItem,
    action: ContentWorkflowAction,
) -> list[ContentWorkflowBlocker]:
    blockers: list[ContentWorkflowBlocker] = []
    blockers.extend(_source_blockers(item))

    if action in {"prepare_sales_brief", "prepare_draft", "create_wordpress_draft"}:
        blockers.extend(_inventory_and_url_blockers(item))
        blockers.extend(_preflight_blockers(item))

    if action in {"prepare_sales_brief", "prepare_draft"}:
        blockers.extend(_preserve_first_blockers(item))

    if action in {"prepare_draft", "create_wordpress_draft"}:
        blockers.extend(_draft_input_blockers(item))

    if action == "create_wordpress_draft":
        blockers.extend(_wordpress_handoff_blockers(item))

    if action == "claim_measurement_outcome":
        blockers.extend(_measurement_outcome_blockers(item))

    return blockers


def content_workflow_action_allowed(
    item: ContentWorkItem,
    action: ContentWorkflowAction,
) -> bool:
    return not content_workflow_blockers(item, action)


def _source_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    blockers: list[ContentWorkflowBlocker] = []
    if not item.evidence_ids:
        blockers.append(
            _blocker(
                "missing_evidence",
                "Brakuje dowodów",
                "WILQ nie może przygotować rekomendacji ani treści bez podpiętego dowodu.",
                "Najpierw podłącz lub odśwież źródła danych dla tego tematu.",
            )
        )
    if not item.source_connectors:
        blockers.append(
            _blocker(
                "missing_source_connector",
                "Brakuje źródła danych",
                "WILQ nie może używać samej notatki albo promptu jako źródła prawdy.",
                "Wskaż źródło danych, z którego pochodzi fakt: GSC, WordPress, "
                "GA4, Ahrefs lub inne.",
            )
        )
    return blockers


def _inventory_and_url_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    blockers: list[ContentWorkflowBlocker] = []
    if item.inventory_status != "resolved":
        blockers.append(
            _blocker(
                "missing_inventory_resolution",
                "Nie sprawdzono istniejącej treści",
                "Najpierw trzeba wiedzieć, czy temat ma już publiczną treść.",
                "Sprawdź istniejące treści i wybierz: zachować, odświeżyć, "
                "scalić, utworzyć albo zablokować.",
            )
        )
    if item.canonical_status != "resolved" or not item.final_canonical_url:
        blockers.append(
            _blocker(
                "missing_final_canonical",
                "Brakuje finalnego adresu",
                "Szkic nie może powstać bez publicznego docelowego adresu.",
                "Ustal finalny adres na ekologus.pl albo innym potwierdzonym publicznym hoście.",
            )
        )
    elif content_url_host(item.final_canonical_url) not in CONTENT_SOURCE_SITE_HOSTS:
        blockers.append(
            _blocker(
                "invalid_final_canonical",
                "Adres podglądu nie może być docelowy",
                "Adres dev albo podglądu może pomagać w projekcie, ale nie jest "
                "publicznym adresem SEO.",
                "Ustaw publiczny adres Ekologus jako docelowe miejsce treści.",
            )
        )
    if item.duplicate_status != "checked":
        code: ContentWorkflowBlockerCode = (
            "duplicate_or_canonical_risk"
            if item.duplicate_status in {"risk_found", "blocked"}
            else "duplicate_gate_not_checked"
        )
        blockers.append(
            _blocker(
                code,
                "Nie zamknięto ryzyka duplikacji",
                "Nowa treść bez sprawdzenia duplikacji może kanibalizować istniejące URL-e.",
                "Sprawdź podobne treści, adres docelowy i ryzyko kanibalizacji przed dalszą pracą.",
            )
        )
    return blockers


def _preflight_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    if item.preflight_status == "missing":
        return [
            _blocker(
                "missing_preflight",
                "Brakuje sprawdzenia wstępnego",
                "WILQ nie może pisać ani briefować bez decyzji, czy temat jest bezpieczny.",
                "Uruchom sprawdzenie wstępne dla tego tematu.",
            )
        ]
    if item.preflight_status == "blocked":
        return [
            _blocker(
                "blocked_preflight",
                "Sprawdzenie wstępne blokuje pisanie",
                "Aktualne dane mówią, że nie wolno przejść dalej.",
                "Rozwiąż blokadę albo zmień tryb pracy na zachowanie, scalenie "
                "lub sprawdzenie przez człowieka.",
            )
        ]
    return []


def _preserve_first_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    if item.preserve_first_plan_status in {"ready", "approved"}:
        return []
    return [
        _blocker(
            "missing_preserve_first_plan",
            "Brakuje decyzji o istniejącej treści",
            "Najpierw trzeba ustalić, czy zachowujemy, odświeżamy, scalamy czy tworzymy.",
            "Przygotuj plan pracy na podstawie istniejących treści i ryzyka duplikacji.",
        )
    ]


def _draft_input_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    blockers: list[ContentWorkflowBlocker] = []
    if item.sales_brief_status != "approved" or not item.sales_brief_id:
        blockers.append(
            _blocker(
                "missing_sales_brief",
                "Brakuje zaakceptowanego briefu",
                "Szkic bez planu sprzedażowego będzie promptową improwizacją.",
                "Przygotuj i zatwierdź plan sprzedażowy przed szkicem.",
            )
        )
    if item.claim_ledger_status != "approved" or not item.claim_ledger_id:
        blockers.append(
            _blocker(
                "missing_claim_ledger",
                "Brakuje sprawdzenia twierdzeń",
                "Treść nie może używać ryzykownych obietnic bez ich sprawdzenia.",
                "Sprawdź i zatwierdź ryzykowne twierdzenia przed szkicem.",
            )
        )
    if item.measurement_window_status == "missing" or not item.measurement_window_id:
        blockers.append(
            _blocker(
                "missing_measurement_window",
                "Brakuje planu pomiaru",
                "Nie trzeba czekać na wyniki, ale trzeba od razu wiedzieć, co będzie mierzone.",
                "Utwórz plan pomiaru przed szkicem albo przekazaniem do WordPress.",
            )
        )
    return blockers


def _wordpress_handoff_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    blockers: list[ContentWorkflowBlocker] = []
    if item.draft_package_status != "ready" or not item.draft_package_id:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Szkic WordPress wymaga gotowej paczki szkicu z mapą dowodów i twierdzeń.",
                "Przygotuj paczkę szkicu przed przekazaniem do WordPress.",
            )
        )
    if item.human_review_status != "approved" or not item.human_review_id:
        blockers.append(
            _blocker(
                "missing_human_review",
                "Brakuje decyzji człowieka",
                "Szkic WordPress nie może powstać bez decyzji człowieka.",
                "Zatwierdź szkic w sprawdzeniu człowieka.",
            )
        )
    if item.audit_status != "recorded" or not item.audit_id:
        blockers.append(
            _blocker(
                "missing_audit",
                "Brakuje audytu",
                "Każde przekazanie do WordPress musi zostawić ślad audytowy.",
                "Zapisz audyt przed przekazaniem do WordPress.",
            )
        )
    return blockers


def _measurement_outcome_blockers(item: ContentWorkItem) -> list[ContentWorkflowBlocker]:
    if (
        item.measurement_window_status in {"ready_for_review", "closed"}
        and item.measurement_window_id
    ):
        return []
    code: ContentWorkflowBlockerCode = (
        "missing_measurement_window"
        if item.measurement_window_status == "missing" or not item.measurement_window_id
        else "measurement_window_not_ready"
    )
    return [
        _blocker(
            code,
            "Nie wolno jeszcze oceniać efektu",
            "WILQ może zbierać dane, ale nie może mówić, że treść zadziałała albo nie zadziałała.",
            "Poczekaj na koniec okna pomiaru i dopiero wtedy oceń "
            "GSC/GA4/Ahrefs/Ads/Merchant/Localo.",
        )
    ]


def _blocker(
    code: ContentWorkflowBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentWorkflowBlocker:
    return ContentWorkflowBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
