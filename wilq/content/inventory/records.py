from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.canonical.urls import (
    CONTENT_SOURCE_SITE_HOSTS,
    content_normalized_url,
    content_url_host,
)

ContentInventoryContentStatus = Literal["published", "draft", "private", "unknown"]
ContentInventoryDuplicateRisk = Literal["unknown", "clear", "review_required", "high"]
ContentInventoryMode = Literal["preserve", "refresh", "merge", "create_after_review", "block"]
ContentInventoryResolutionStatus = Literal["resolved", "review_required", "blocked"]
ContentInventoryBlockerCode = Literal[
    "missing_final_canonical",
    "invalid_final_canonical",
    "duplicate_risk_unresolved",
    "duplicate_risk_high",
]


class ContentInventoryRecord(BaseModel):
    id: str
    url: str
    final_canonical_url: str | None = None
    intended_final_url: str | None = None
    preview_url: str | None = None
    content_status: ContentInventoryContentStatus = "unknown"
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    title: str | None = None
    h1: str | None = None
    topic_tags: list[str] = Field(default_factory=list)


class ContentInventoryBlocker(BaseModel):
    code: ContentInventoryBlockerCode
    label: str
    reason: str
    next_step: str


class ContentInventoryResolution(BaseModel):
    status: ContentInventoryResolutionStatus
    recommended_mode: ContentInventoryMode
    records: list[ContentInventoryRecord] = Field(default_factory=list)
    similar_existing_urls: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[ContentInventoryBlocker] = Field(default_factory=list)
    next_step: str


def resolve_content_inventory(
    records: list[ContentInventoryRecord],
    *,
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown",
) -> ContentInventoryResolution:
    normalized_records = _deduplicated_records(records)
    blockers = _record_blockers(normalized_records)
    if duplicate_risk == "high":
        blockers.append(
            _blocker(
                "duplicate_risk_high",
                "Wysokie ryzyko duplikacji",
                "Nie wolno tworzyć nowej treści, gdy podobny temat może już istnieć.",
                    "Najpierw sprawdź podobne adresy i zdecyduj: zachować, odświeżyć albo scalić.",
            )
        )
    elif duplicate_risk in {"unknown", "review_required"} and not normalized_records:
        blockers.append(
            _blocker(
                "duplicate_risk_unresolved",
                "Nie sprawdzono duplikacji",
                "Brak istniejącego rekordu nie oznacza jeszcze, że wolno tworzyć nowy URL.",
                    "Sprawdź podobne treści, adres docelowy i ryzyko kanibalizacji "
                    "przed tworzeniem nowej treści.",
            )
        )

    if blockers:
        return ContentInventoryResolution(
            status="blocked",
            recommended_mode="block",
            records=normalized_records,
            similar_existing_urls=_public_canonical_urls(normalized_records),
            source_connectors=_unique(
                connector for record in normalized_records for connector in record.source_connectors
            ),
            evidence_ids=_unique(
                evidence_id for record in normalized_records for evidence_id in record.evidence_ids
            ),
            blockers=blockers,
            next_step="Najpierw rozwiąż blokady spisu treści, adresu docelowego i duplikacji.",
        )

    if normalized_records:
        return ContentInventoryResolution(
            status="resolved",
            recommended_mode="preserve",
            records=normalized_records,
            similar_existing_urls=_public_canonical_urls(normalized_records),
            source_connectors=_unique(
                connector for record in normalized_records for connector in record.source_connectors
            ),
            evidence_ids=_unique(
                evidence_id for record in normalized_records for evidence_id in record.evidence_ids
            ),
            next_step=(
                "Zacznij od istniejącej treści: zachowaj istniejący adres albo przygotuj "
                "odświeżenie/scalenie z dowodami."
            ),
        )

    return ContentInventoryResolution(
        status="review_required",
        recommended_mode="create_after_review",
        next_step=(
            "Nie znaleziono istniejącego rekordu. Można przygotować kandydat do nowej treści "
            "dopiero po sprawdzeniu człowieka i sprawdzeniu wstępnym."
        ),
    )


def _record_blockers(records: Iterable[ContentInventoryRecord]) -> list[ContentInventoryBlocker]:
    blockers: list[ContentInventoryBlocker] = []
    for record in records:
        final_url = record.final_canonical_url or record.intended_final_url
        if not final_url:
            blockers.append(
                _blocker(
                    "missing_final_canonical",
                    "Brakuje finalnego adresu",
                    "Rekord spisu treści nie może zasilać planu bez publicznego adresu docelowego.",
                    "Ustal publiczny adres docelowy dla istniejącej treści.",
                )
            )
            continue
        if content_url_host(final_url) not in CONTENT_SOURCE_SITE_HOSTS:
            blockers.append(
                _blocker(
                    "invalid_final_canonical",
                    "Nieprawidłowy adres docelowy",
                    "Adres podglądu albo dev nie może być finalnym adresem SEO.",
                    "Ustaw publiczny adres Ekologus jako adres docelowy.",
                )
            )
    return blockers


def _deduplicated_records(
    records: Iterable[ContentInventoryRecord],
) -> list[ContentInventoryRecord]:
    deduplicated: dict[str, ContentInventoryRecord] = {}
    for record in records:
        key = content_normalized_url(record.final_canonical_url or record.intended_final_url)
        if not key:
            key = content_normalized_url(record.url) or record.id
        deduplicated.setdefault(key, record)
    return list(deduplicated.values())


def _public_canonical_urls(records: Iterable[ContentInventoryRecord]) -> list[str]:
    urls: list[str] = []
    for record in records:
        final_url = record.final_canonical_url or record.intended_final_url
        if content_url_host(final_url) in CONTENT_SOURCE_SITE_HOSTS:
            urls.append(str(final_url))
    return _unique(urls)


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _blocker(
    code: ContentInventoryBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentInventoryBlocker:
    return ContentInventoryBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
