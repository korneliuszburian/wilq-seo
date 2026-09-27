"""Ask-only content intake: idempotent request without a prewritten brief."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)

FieldProvenance = Literal["user_input", "evidence", "inference", "unknown"]

DEMAND_CONNECTOR_IDS = ("google_search_console", "google_analytics_4", "ahrefs")
WORDPRESS_CONNECTOR_ID = "wordpress_ekologus"
DEMAND_OWNER = "WILQ demand evidence"
WORDPRESS_OWNER = "WILQ WordPress connector"
WORKFLOW_OWNER = "WILQ content workflow"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_GENERIC_TOKENS = frozenset(
    {
        "artykul",
        "content",
        "cos",
        "dla",
        "fajnego",
        "jest",
        "mamy",
        "oferta",
        "oraz",
        "post",
        "potrzebuje",
        "prosba",
        "strona",
        "tresc",
        "wpis",
        "zrob",
    }
)
_POLISH_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
    }
)
_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentIntakeAskRequest(_FrozenModel):
    request_id: UUID
    ask: str = Field(min_length=3, max_length=2000)


class ContentIntakeBlocker(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=600)


class ContentIntakeFieldProvenance(_FrozenModel):
    field: str = Field(min_length=1, max_length=120)
    provenance: FieldProvenance
    detail: str = Field(min_length=1, max_length=600)
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_sorted_evidence(self) -> Self:
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Intake provenance evidence IDs must be sorted and unique.")
        return self


class ContentIntakeQueueItem(_FrozenModel):
    schema_version: Literal["wilq_content_intake_v1"] = "wilq_content_intake_v1"
    queue_id: str = Field(min_length=1, max_length=240)
    request_id: UUID
    input_digest: str = Field(pattern=_HEX64)
    actor_id: str = LOCAL_PILOT_AUDIT_IDENTITY.principal_id
    actor_trust_level: Literal["local_unverified"] = "local_unverified"
    status: Literal["queued", "blocked"]
    ask: str = Field(min_length=3, max_length=2000)
    provenance: tuple[ContentIntakeFieldProvenance, ...] = Field(min_length=1)
    candidate_work_item_ids: tuple[str, ...] = ()
    candidate_paths: tuple[str, ...] = ()
    candidate_public_urls: tuple[str, ...] = ()
    blockers: tuple[ContentIntakeBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1, max_length=600)
    generation_allowed: Literal[False] = False
    created_at: datetime

    @model_validator(mode="after")
    def require_exact_intake_shape(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("Intake queue time must be timezone-aware.")
        if len(self.candidate_work_item_ids) != len(self.candidate_paths) or len(
            self.candidate_paths
        ) != len(self.candidate_public_urls):
            raise ValueError("Intake candidates must align work item, path and URL.")
        if self.candidate_paths != tuple(sorted(self.candidate_paths)):
            raise ValueError("Intake candidate paths must be sorted.")
        if len(self.candidate_paths) != len(set(self.candidate_paths)):
            raise ValueError("Intake candidate paths must be unique.")
        codes = tuple(blocker.code for blocker in self.blockers)
        if len(codes) != len(set(codes)):
            raise ValueError("Intake blockers must be unique.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked intake requests need at least one typed blocker.")
        if self.status == "queued" and self.blockers:
            raise ValueError("Queued intake requests cannot carry blockers.")
        return self


def build_content_intake_queue_item(
    *,
    request_id: UUID,
    ask: str,
    catalog: ContentInventoryCatalogResponse,
    source_facts: Sequence[ContentSourceFact],
    connector_freshness: Mapping[str, str],
    created_at: datetime,
) -> ContentIntakeQueueItem:
    """Resolve one ask-only request into an evidence-linked intake queue item.

    This function never runs research, planning, generation, ActionObject or a
    vendor write; it only binds the ask to current local evidence and blockers.
    """

    normalized_ask = ask.strip()
    digest = canonical_json_digest(
        {"request_id": str(request_id), "ask": normalized_ask}
    )
    tokens = _ask_tokens(normalized_ask)
    candidates = _match_candidates(tokens, catalog)
    blockers: list[ContentIntakeBlocker] = []
    target_blocker = _target_blocker(tokens, candidates)
    if target_blocker is not None:
        blockers.append(target_blocker)
    inventory_blockers = _inventory_blockers(catalog, connector_freshness)
    blockers.extend(inventory_blockers)
    demand_blocker = _demand_blocker(connector_freshness)
    if demand_blocker is not None:
        blockers.append(demand_blocker)
    approved_facts = _approved_facts_for_candidates(candidates, source_facts)
    if candidates and not approved_facts:
        blockers.append(
            _blocker(
                "approved_source_facts_missing",
                "Wilku",
                "Brak zatwierdzonych faktów źródłowych dla dopasowanych stron; "
                "kolejka nie tworzy obietnic treści bez tego zatwierdzenia.",
            )
        )
    return ContentIntakeQueueItem(
        queue_id=f"content_intake_{digest[:24]}",
        request_id=request_id,
        input_digest=digest,
        status="blocked" if blockers else "queued",
        ask=normalized_ask,
        provenance=_provenance_entries(
            candidates,
            approved_facts,
            demand_blocker,
            target_is_current=not inventory_blockers,
        ),
        candidate_work_item_ids=tuple(item.work_item_id for item in candidates),
        candidate_paths=tuple(item.path for item in candidates),
        candidate_public_urls=tuple(item.url for item in candidates),
        blockers=tuple(blockers),
        safe_next_step=_safe_next_step(candidates, blockers),
        created_at=created_at,
    )


def _target_blocker(
    tokens: tuple[str, ...],
    candidates: tuple[ContentInventoryCatalogItem, ...],
) -> ContentIntakeBlocker | None:
    if not tokens:
        return _blocker(
            "intake_ask_too_generic",
            WORKFLOW_OWNER,
            "Prośba nie zawiera rozpoznawalnego adresu, tematu ani work itemu.",
        )
    if not candidates:
        return _blocker(
            "intake_target_missing",
            WORKFLOW_OWNER,
            "Brak elementu katalogu WILQ pasującego do rozpoznanych słów prośby.",
        )
    if len(candidates) > 1:
        return _blocker(
            "intake_target_ambiguous",
            WORKFLOW_OWNER,
            "Prośba pasuje do wielu bieżących elementów katalogu; wskaż dokładny URL.",
        )
    return None


def _inventory_blockers(
    catalog: ContentInventoryCatalogResponse,
    connector_freshness: Mapping[str, str],
) -> tuple[ContentIntakeBlocker, ...]:
    blockers: list[ContentIntakeBlocker] = []
    if catalog.status != "ready" or catalog.coverage.status != "complete":
        blockers.append(
            _blocker(
                "intake_inventory_incomplete",
                WORDPRESS_OWNER,
                "Bieżący katalog inventory WILQ nie jest kompletny.",
            )
        )
    if connector_freshness.get(WORDPRESS_CONNECTOR_ID) != "fresh":
        blockers.append(
            _blocker(
                "intake_inventory_not_current",
                WORDPRESS_OWNER,
                "Bieżący odczyt WordPress nie jest świeży.",
            )
        )
    return tuple(blockers)


def _provenance_entries(
    candidates: tuple[ContentInventoryCatalogItem, ...],
    approved_facts: tuple[ContentSourceFact, ...],
    demand_blocker: ContentIntakeBlocker | None,
    *,
    target_is_current: bool,
) -> tuple[ContentIntakeFieldProvenance, ...]:
    candidate_evidence = tuple(
        sorted({item.evidence_id for item in candidates if item.evidence_id})
    )
    if not candidates:
        target_detail = "Brak dopasowania do bieżącego katalogu WILQ."
    elif target_is_current:
        target_detail = "Dopasowanie z bieżącego katalogu WILQ."
    else:
        target_detail = (
            "Dopasowanie z ostatniego zaakceptowanego katalogu WILQ; bieżący odczyt "
            "WordPress nie jest potwierdzony."
        )
    return (
        ContentIntakeFieldProvenance(
            field="ask",
            provenance="user_input",
            detail="Dosłowna prośba operatora; bez dopisywania wymagań.",
        ),
        ContentIntakeFieldProvenance(
            field="target_path",
            provenance="evidence" if candidates else "unknown",
            detail=target_detail,
            evidence_ids=candidate_evidence,
        ),
        ContentIntakeFieldProvenance(
            field="demand",
            provenance="unknown",
            detail=(
                "Brak świeżych danych popytu; kolejka nie tworzy obietnicy popytu."
                if demand_blocker is not None
                else "Bieżące źródła popytu są świeże."
            ),
            evidence_ids=(),
        ),
        ContentIntakeFieldProvenance(
            field="source_facts",
            provenance="evidence" if approved_facts else "unknown",
            detail=(
                "Zatwierdzone fakty źródłowe dla dopasowanych stron."
                if approved_facts
                else "Brak zatwierdzonych faktów źródłowych dla dopasowanych stron."
            ),
            evidence_ids=tuple(
                sorted({value for fact in approved_facts for value in fact.evidence_ids})
            ),
        ),
    )


def demand_connector_freshness() -> dict[str, str]:
    """Return the current freshness state of the demand and WordPress connectors."""

    from wilq.connectors.registry import get_connector_status

    freshness: dict[str, str] = {}
    for connector_id in (*DEMAND_CONNECTOR_IDS, WORDPRESS_CONNECTOR_ID):
        status = get_connector_status(connector_id)
        freshness[connector_id] = "missing" if status is None else str(status.freshness.state)
    return freshness


def _ask_tokens(ask: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            token
            for token in _TOKEN_RE.findall(ask.lower().translate(_POLISH_TRANSLATION))
            if len(token) >= 3 and token not in _GENERIC_TOKENS
        )
    )


def _match_candidates(
    tokens: tuple[str, ...],
    catalog: ContentInventoryCatalogResponse,
) -> tuple[ContentInventoryCatalogItem, ...]:
    if not tokens:
        return ()
    matches: list[ContentInventoryCatalogItem] = []
    for item in catalog.items:
        haystack = (
            f"{item.url} {item.path} {item.content_type}".lower().translate(_POLISH_TRANSLATION)
        )
        if any(token in haystack for token in tokens):
            matches.append(item)
    return tuple(sorted(matches, key=lambda item: item.path))


def _demand_blocker(connector_freshness: Mapping[str, str]) -> ContentIntakeBlocker | None:
    stale = tuple(
        connector_id
        for connector_id in DEMAND_CONNECTOR_IDS
        if connector_freshness.get(connector_id) != "fresh"
    )
    if not stale:
        return None
    return _blocker(
        "demand_evidence_not_fresh",
        DEMAND_OWNER,
        "Bez świeżych danych popytu: " + ", ".join(stale) + ".",
    )


def _approved_facts_for_candidates(
    candidates: tuple[ContentInventoryCatalogItem, ...],
    source_facts: Sequence[ContentSourceFact],
) -> tuple[ContentSourceFact, ...]:
    paths = {content_normalized_path(item.path).casefold() for item in candidates}
    return tuple(
        fact
        for fact in source_facts
        if fact.review_status == "approved"
        and any(
            content_normalized_path(path).casefold() in paths
            for path in fact.applicable_canonical_paths
        )
    )


def _safe_next_step(
    candidates: tuple[ContentInventoryCatalogItem, ...],
    blockers: Sequence[ContentIntakeBlocker],
) -> str:
    codes = {blocker.code for blocker in blockers}
    if "intake_ask_too_generic" in codes:
        return "Doprecyzuj prośbę: podaj dokładny adres, temat albo work item."
    if "intake_target_missing" in codes:
        return "Wskaż istniejący adres albo work item z bieżącego katalogu WILQ."
    if "intake_target_ambiguous" in codes:
        return "Wskaż dokładnie jedną stronę z listy dopasowanych adresów."
    if "intake_inventory_incomplete" in codes:
        return "Odczekaj pełny bieżący odczyt inventory WILQ i ponów prośbę."
    if "intake_inventory_not_current" in codes:
        return "Odśwież bieżący odczyt WordPress przed przyjęciem prośby do kolejki."
    if "demand_evidence_not_fresh" in codes:
        return "Odśwież GSC, GA4 i Ahrefs przed obietnicą popytu dla tej prośby."
    if "approved_source_facts_missing" in codes:
        return "Zatwierdź exact fakty źródłowe dla dopasowanej strony przed briefem."
    if candidates:
        return "Otwórz dokładną stronę i przejdź bieżącą ścieżkę przygotowania treści."
    return "Doprecyzuj prośbę, aby WILQ mógł dopasować bieżący adres."


def _blocker(code: str, owner: str, detail: str) -> ContentIntakeBlocker:
    return ContentIntakeBlocker(code=code, owner=owner, detail=detail)


__all__ = [
    "ContentIntakeAskRequest",
    "ContentIntakeBlocker",
    "ContentIntakeFieldProvenance",
    "ContentIntakeQueueItem",
    "DEMAND_CONNECTOR_IDS",
    "WORDPRESS_CONNECTOR_ID",
    "build_content_intake_queue_item",
    "demand_connector_freshness",
]
