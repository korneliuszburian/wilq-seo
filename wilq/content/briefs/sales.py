from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.claims.ledger import ContentClaimLedger, claim_ledger_blockers
from wilq.content.inventory.records import ContentInventoryResolution
from wilq.content.preflight.workflow import ContentPreflightVerdict
from wilq.content.workflow.models import ContentWorkItem

ContentSalesBriefBlockerCode = Literal[
    "preflight_not_ready",
    "missing_evidence",
    "missing_source_connector",
    "missing_source_fact",
    "unknown_source_fact_evidence",
    "unknown_source_fact_connector",
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_measurement_plan",
]


class ContentSalesBriefSourceFact(BaseModel):
    evidence_id: str
    source_connector: str
    summary: str


class ContentSalesBriefSeed(BaseModel):
    target_reader: str
    buyer_problem: str
    buyer_trigger: str
    search_intent: str
    service_fit: str
    h1_direction: str
    h2_direction: list[str] = Field(default_factory=list)
    faq_direction: list[str] = Field(default_factory=list)
    cta_direction: str
    internal_link_direction: list[str] = Field(default_factory=list)
    source_facts: list[ContentSalesBriefSourceFact] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class ContentSalesBriefMeasurementPlan(BaseModel):
    measurement_window_id: str
    metrics_to_watch: list[str]
    earliest_verdict_note: str
    success_claim_rule: str


class ContentSalesBriefForbiddenClaim(BaseModel):
    claim_id: str
    claim_text: str
    status: str
    reason: str


class ContentSalesBrief(BaseModel):
    id: str
    work_item_id: str
    topic: str
    target_reader: str
    buyer_problem: str
    buyer_trigger: str
    search_intent: str
    service_fit: str
    source_public_url: str | None = None
    final_canonical_url: str
    intended_final_url: str | None = None
    preview_url: str | None = None
    existing_content_plan: str
    h1_direction: str
    h2_direction: list[str] = Field(default_factory=list)
    faq_direction: list[str] = Field(default_factory=list)
    cta_direction: str
    internal_link_direction: list[str] = Field(default_factory=list)
    source_facts: list[ContentSalesBriefSourceFact] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    forbidden_claims: list[ContentSalesBriefForbiddenClaim] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    measurement_plan: ContentSalesBriefMeasurementPlan
    human_review_required: bool = True
    draft_allowed: bool = False


class ContentSalesBriefBlocker(BaseModel):
    code: ContentSalesBriefBlockerCode
    label: str
    reason: str
    next_step: str


class ContentSalesBriefBuildResult(BaseModel):
    brief: ContentSalesBrief | None = None
    blockers: list[ContentSalesBriefBlocker] = Field(default_factory=list)


def build_content_sales_brief(
    *,
    item: ContentWorkItem,
    preflight: ContentPreflightVerdict,
    inventory: ContentInventoryResolution,
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
) -> ContentSalesBriefBuildResult:
    blockers = content_sales_brief_blockers(
        item=item,
        preflight=preflight,
        seed=seed,
    )
    if blockers:
        return ContentSalesBriefBuildResult(blockers=blockers)

    final_canonical_url = item.final_canonical_url or ""
    return ContentSalesBriefBuildResult(
        brief=ContentSalesBrief(
            id=f"sales_brief_{item.id}",
            work_item_id=item.id,
            topic=item.topic,
            target_reader=seed.target_reader,
            buyer_problem=seed.buyer_problem,
            buyer_trigger=seed.buyer_trigger,
            search_intent=seed.search_intent,
            service_fit=seed.service_fit,
            source_public_url=item.source_public_url,
            final_canonical_url=final_canonical_url,
            intended_final_url=item.intended_final_url,
            preview_url=item.preview_url,
            existing_content_plan=_existing_content_plan(inventory),
            h1_direction=seed.h1_direction,
            h2_direction=seed.h2_direction,
            faq_direction=seed.faq_direction,
            cta_direction=seed.cta_direction,
            internal_link_direction=seed.internal_link_direction,
            source_facts=seed.source_facts,
            evidence_ids=_unique([*item.evidence_ids, *preflight.evidence_ids]),
            source_connectors=_unique(
                [*item.source_connectors, *preflight.source_connectors]
            ),
            forbidden_claims=_forbidden_claims(claim_ledger),
            missing_evidence=seed.missing_evidence,
            measurement_plan=ContentSalesBriefMeasurementPlan(
                measurement_window_id=str(item.measurement_window_id),
                metrics_to_watch=[
                    "GSC: zapytania, adres, kliknięcia, wyświetlenia, CTR i pozycja",
                    "GA4: jakość ruchu, zaangażowanie i braki pomiaru",
                    "Ahrefs/Ads/Merchant/Localo: sygnały pomocnicze tylko gdy mają dowody",
                ],
                earliest_verdict_note=(
                    "Nie oceniaj sukcesu ani porażki przed końcem okna pomiaru."
                ),
                success_claim_rule=(
                    "Po publikacji wolno mówić o efekcie tylko na podstawie zamkniętego "
                    "measurement window i aktualnych dowodów."
                ),
            ),
            draft_allowed=False,
        )
    )


def content_sales_brief_blockers(
    *,
    item: ContentWorkItem,
    preflight: ContentPreflightVerdict,
    seed: ContentSalesBriefSeed,
) -> list[ContentSalesBriefBlocker]:
    blockers: list[ContentSalesBriefBlocker] = []
    if not preflight.sales_brief_allowed:
        blockers.append(
            _blocker(
                "preflight_not_ready",
                "Preflight nie pozwala na brief",
                "Sales Brief może powstać dopiero po preflight verdict.",
                "Rozwiąż blokady preflightu i plan preserve-first.",
            )
        )
    if not item.evidence_ids and not preflight.evidence_ids:
        blockers.append(
            _blocker(
                "missing_evidence",
                "Brakuje dowodów",
                "Brief bez evidence ID byłby promptem, nie kontraktem WILQ.",
                "Najpierw dodaj evidence IDs z GSC, WordPress, GA4, Ahrefs albo innego źródła.",
            )
        )
    if not item.source_connectors and not preflight.source_connectors:
        blockers.append(
            _blocker(
                "missing_source_connector",
                "Brakuje źródła danych",
                "Brief musi wskazywać, z jakich connectorów pochodzi wiedza.",
                "Podłącz lub wskaż source connector dla tego work itemu.",
            )
        )
    if not seed.source_facts:
        blockers.append(
            _blocker(
                "missing_source_fact",
                "Brakuje faktów źródłowych",
                "Brief musi zawierać konkretne fakty z dowodami, nie tylko kierunek pisania.",
                "Dodaj source_facts z evidence ID i connector ID.",
            )
        )
    blockers.extend(_source_fact_reference_blockers(item, preflight, seed.source_facts))
    if not item.final_canonical_url:
        blockers.append(
            _blocker(
                "missing_final_canonical",
                "Brakuje finalnego adresu",
                "Brief nie może powstać bez final_canonical_url.",
                "Ustal publiczny final canonical URL przed briefem.",
            )
        )
    elif content_url_host(item.final_canonical_url) not in CONTENT_SOURCE_SITE_HOSTS:
        blockers.append(
            _blocker(
                "invalid_final_canonical",
                "Nieprawidłowy canonical",
                "Dev albo preview URL nie może być finalnym adresem SEO.",
                "Ustaw final_canonical_url na publiczny adres Ekologus.",
            )
        )
    if item.measurement_window_status == "missing" or not item.measurement_window_id:
        blockers.append(
            _blocker(
                "missing_measurement_plan",
                "Brakuje planu pomiaru",
                "Nie czekamy na wyniki, ale brief musi od razu wiedzieć, co będzie mierzone.",
                "Utwórz measurement window przed Sales Brief.",
            )
        )
    return blockers


def _source_fact_reference_blockers(
    item: ContentWorkItem,
    preflight: ContentPreflightVerdict,
    source_facts: list[ContentSalesBriefSourceFact],
) -> list[ContentSalesBriefBlocker]:
    blockers: list[ContentSalesBriefBlocker] = []
    known_evidence = set(_unique([*item.evidence_ids, *preflight.evidence_ids]))
    known_connectors = set(_unique([*item.source_connectors, *preflight.source_connectors]))
    unknown_evidence = [
        fact.evidence_id for fact in source_facts if fact.evidence_id not in known_evidence
    ]
    unknown_connectors = [
        fact.source_connector
        for fact in source_facts
        if fact.source_connector not in known_connectors
    ]
    if unknown_evidence:
        blockers.append(
            _blocker(
                "unknown_source_fact_evidence",
                "Fakt używa nieznanego dowodu",
                "Każdy source fact musi wskazywać evidence ID obecne w work itemie albo preflight.",
                f"Usuń albo podłącz dowody: {', '.join(_unique(unknown_evidence))}.",
            )
        )
    if unknown_connectors:
        blockers.append(
            _blocker(
                "unknown_source_fact_connector",
                "Fakt używa nieznanego connectora",
                "Każdy source fact musi wskazywać connector obecny w work itemie albo preflight.",
                f"Usuń albo podłącz connectory: {', '.join(_unique(unknown_connectors))}.",
            )
        )
    return blockers


def _existing_content_plan(inventory: ContentInventoryResolution) -> str:
    if inventory.recommended_mode == "preserve":
        return "Zacznij od istniejącej treści: preserve-first, potem refresh albo merge."
    if inventory.recommended_mode == "create_after_review":
        return "Create candidate tylko po review, preflight i kontroli duplikacji."
    if inventory.recommended_mode == "block":
        return "Nie przygotowuj briefu, dopóki inventory blokuje pracę."
    return inventory.next_step


def _forbidden_claims(
    claim_ledger: ContentClaimLedger,
) -> list[ContentSalesBriefForbiddenClaim]:
    entries_by_id = {entry.id: entry for entry in claim_ledger.entries}
    forbidden: list[ContentSalesBriefForbiddenClaim] = []
    for blocker in claim_ledger_blockers(claim_ledger):
        entry = entries_by_id.get(blocker.claim_id)
        if entry is None:
            continue
        forbidden.append(
            ContentSalesBriefForbiddenClaim(
                claim_id=entry.id,
                claim_text=entry.claim_text,
                status=entry.status,
                reason=blocker.reason,
            )
        )
    return forbidden


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _blocker(
    code: ContentSalesBriefBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentSalesBriefBlocker:
    return ContentSalesBriefBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
