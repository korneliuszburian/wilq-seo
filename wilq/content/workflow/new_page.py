from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.schemas.core import utc_now

if TYPE_CHECKING:
    from wilq.content.workflow.new_page_topics import ContentNewPageTopicCandidate


class ContentNewPageBriefInput(BaseModel):
    """The smallest marketer-owned statement of a page that does not exist yet."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=160)
    purpose: str = Field(min_length=8, max_length=800)
    service: str = Field(min_length=2, max_length=160)
    audience: str = Field(min_length=3, max_length=300)
    search_intent: str = Field(min_length=3, max_length=300)
    proposed_ia_location: str = Field(min_length=3, max_length=300)
    topic_candidate_id: str | None = Field(default=None, min_length=1)
    topic_candidate_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def require_complete_topic_candidate_identity(self) -> ContentNewPageBriefInput:
        if (self.topic_candidate_id is None) != (self.topic_candidate_digest is None):
            raise ValueError(
                "A source-backed topic needs both its candidate ID and exact digest."
            )
        return self


class ContentNewPageBrief(ContentNewPageBriefInput):
    model_config = ConfigDict(extra="forbid")

    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(min_length=64, max_length=64)
    created_at: datetime
    work_kind: Literal["new_page"] = "new_page"
    topic_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_topic_lineage_when_selected(self) -> ContentNewPageBrief:
        if self.topic_candidate_id is None and self.topic_evidence_ids:
            raise ValueError("A manual new-page brief cannot claim topic evidence.")
        if self.topic_candidate_id is not None and not self.topic_evidence_ids:
            raise ValueError("A selected topic candidate needs persisted evidence.")
        return self


class ContentNewPageOverlapCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    match_kind: Literal["same_title", "shared_intent", "shared_service"]
    evidence_ids: list[str] = Field(default_factory=list)


class ContentNewPageOverlapGuard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Literal[
        "no_conflict", "differentiate", "reuse", "merge", "human_decision_required"
    ]
    label: str
    reason: str
    caveat: str
    evidence_ids: list[str] = Field(default_factory=list)
    candidates: list[ContentNewPageOverlapCandidate] = Field(default_factory=list)


class ContentNewPageServiceOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_card_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentNewPageFoundationCommand(BaseModel):
    """Explicit human choice that may seed later planning, never a document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_overlap_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    service_card_id: str = Field(min_length=1)
    confirmed_by: str = Field(min_length=2, max_length=160)


class ContentNewPagePlanningFoundation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    foundation_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    overlap_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    overlap_evidence_ids: list[str] = Field(default_factory=list)
    service_card_id: str = Field(min_length=1)
    service_card_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    service_label: str = Field(min_length=1)
    service_evidence_ids: list[str] = Field(default_factory=list)
    confirmed_by: str = Field(min_length=2)
    created_at: datetime


class ContentNewPageDocumentIdentity(BaseModel):
    """The identity a new page has before any public document exists.

    This is intentionally not a source snapshot or a delivery record.  It
    makes the absence of a public page explicit while carrying the exact brief
    and foundation that future plan, document and review commands must bind.
    """

    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    work_kind: Literal["new_page"] = "new_page"
    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    foundation_id: str = Field(min_length=1)
    service_card_id: str = Field(min_length=1)
    service_card_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposed_ia_location: str = Field(min_length=3)
    public_source_status: Literal["not_applicable"] = "not_applicable"
    public_source_url: None = None
    public_source_evidence_ids: list[str] = Field(default_factory=list)
    document_status: Literal["not_created"] = "not_created"
    public_deployment_status: Literal["not_confirmed"] = "not_confirmed"
    public_deployment_id: None = None

    @model_validator(mode="after")
    def require_absent_public_identity(self) -> ContentNewPageDocumentIdentity:
        if not self.proposed_ia_location.strip():
            raise ValueError("New-page IA location cannot be blank.")
        if self.public_source_evidence_ids:
            raise ValueError("A new page cannot carry public-source evidence before deployment.")
        return self


class ContentNewPageFoundationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["created", "idempotent", "blocked", "conflict"]
    foundation: ContentNewPagePlanningFoundation | None = None
    reason: str
    safe_next_step: str


class ContentNewPageBriefWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_brief_workspace"] = "content_new_page_brief_workspace"
    contract_version: Literal["content_new_page_brief_workspace_v2"] = (
        "content_new_page_brief_workspace_v2"
    )
    brief: ContentNewPageBrief
    overlap_guard: ContentNewPageOverlapGuard
    overlap_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    service_options: list[ContentNewPageServiceOption] = Field(default_factory=list)
    foundation: ContentNewPagePlanningFoundation | None = None
    review_status: Literal["blocked"] = "blocked"
    review_reason: str
    next_action_label: str


def build_new_page_brief(
    input: ContentNewPageBriefInput,
    *,
    topic_candidate: ContentNewPageTopicCandidate | None = None,
) -> ContentNewPageBrief:
    if input.topic_candidate_id is None:
        if topic_candidate is not None:
            raise ValueError("A manual brief cannot carry an unselected topic candidate.")
        topic_evidence_ids: list[str] = []
    else:
        if (
            topic_candidate is None
            or topic_candidate.candidate_id != input.topic_candidate_id
            or topic_candidate.candidate_digest != input.topic_candidate_digest
            or topic_candidate.title != input.title
        ):
            raise ValueError(
                "Wybrany temat zmienił się; odczytaj aktualne rekomendacje przed zapisem briefu."
            )
        topic_evidence_ids = list(topic_candidate.evidence_ids)
    payload = input.model_dump(mode="json")
    digest = sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return ContentNewPageBrief(
        **payload,
        brief_id=f"content_new_page_brief_{uuid4().hex}",
        brief_digest=digest,
        created_at=utc_now(),
        topic_evidence_ids=topic_evidence_ids,
    )


def build_new_page_brief_workspace(
    brief: ContentNewPageBrief,
    *,
    catalog: ContentInventoryCatalogResponse | None = None,
    foundation: ContentNewPagePlanningFoundation | None = None,
) -> ContentNewPageBriefWorkspace:
    guard = build_new_page_overlap_guard(
        brief,
        catalog=catalog or build_content_inventory_catalog_cached(),
    )
    return ContentNewPageBriefWorkspace(
        brief=brief,
        overlap_guard=guard,
        overlap_digest=new_page_overlap_digest(guard),
        service_options=new_page_service_options(),
        foundation=foundation,
        review_reason=(
            "Brief opisuje nową stronę, ale nie jest jeszcze dokumentem do review. "
            "Kolejny etap przygotuje dokument bez zmiany istniejących stron."
        ),
        next_action_label=(
            "Podstawa planowania została zapisana dla tej dokładnej wersji briefu."
            if foundation is not None
            else "Po kontroli pokrycia wybierz zatwierdzoną kartę usługi."
        ),
    )


def new_page_overlap_digest(guard: ContentNewPageOverlapGuard) -> str:
    return _digest(guard.model_dump(mode="json"))


def new_page_service_options() -> list[ContentNewPageServiceOption]:
    """Expose only approved service knowledge; never auto-match free-form brief text."""

    return [
        ContentNewPageServiceOption(
            service_card_id=card.id,
            label=card.title,
            summary=card.summary,
            evidence_ids=card.evidence_ids,
        )
        for card in ekologus_content_knowledge_cards()
        if card.card_type == "service" and card.lifecycle_status == "approved_current"
    ]


def new_page_service_card(service_card_id: str) -> ContentKnowledgeCard | None:
    return next(
        (
            card
            for card in ekologus_content_knowledge_cards()
            if card.id == service_card_id
            and card.card_type == "service"
            and card.lifecycle_status == "approved_current"
        ),
        None,
    )


def build_new_page_planning_foundation(
    *,
    brief: ContentNewPageBrief,
    guard: ContentNewPageOverlapGuard,
    command: ContentNewPageFoundationCommand,
    service_card: ContentKnowledgeCard,
) -> ContentNewPagePlanningFoundation:
    if command.expected_brief_digest != brief.brief_digest:
        raise ValueError("Brief zmienił się przed zapisaniem podstawy planowania.")
    if command.expected_overlap_digest != new_page_overlap_digest(guard):
        raise ValueError("Kontrola pokrycia zmieniła się; odczytaj ją ponownie.")
    if guard.disposition != "no_conflict":
        raise ValueError("Kontrola pokrycia nie pozwala jeszcze rozpocząć nowej strony.")
    if (
        service_card.id != command.service_card_id
        or service_card.lifecycle_status != "approved_current"
    ):
        raise ValueError("Wybrana karta usługi nie jest zatwierdzona do użycia.")
    suffix = brief.brief_id.removeprefix("content_new_page_brief_")
    return ContentNewPagePlanningFoundation(
        foundation_id=f"content_new_page_foundation_{uuid4().hex}",
        work_item_id=f"content_work_item_new_page_{suffix}",
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        overlap_digest=command.expected_overlap_digest,
        overlap_evidence_ids=guard.evidence_ids,
        service_card_id=service_card.id,
        service_card_digest=_digest(service_card.model_dump(mode="json")),
        service_label=service_card.title,
        service_evidence_ids=service_card.evidence_ids,
        confirmed_by=command.confirmed_by,
        created_at=utc_now(),
    )


def build_new_page_document_identity(
    *,
    foundation: ContentNewPagePlanningFoundation,
    proposed_ia_location: str,
) -> ContentNewPageDocumentIdentity:
    """Build the pre-document identity without fabricating a public source."""

    return ContentNewPageDocumentIdentity(
        work_item_id=foundation.work_item_id,
        brief_id=foundation.brief_id,
        brief_digest=foundation.brief_digest,
        foundation_id=foundation.foundation_id,
        service_card_id=foundation.service_card_id,
        service_card_digest=foundation.service_card_digest,
        proposed_ia_location=proposed_ia_location,
    )


def build_new_page_overlap_guard(
    brief: ContentNewPageBrief,
    *,
    catalog: ContentInventoryCatalogResponse,
) -> ContentNewPageOverlapGuard:
    """Return only observed inventory signals; never infer a match from a URL slug."""

    catalog_evidence_ids = _catalog_evidence_ids(catalog)
    if not catalog.items or not catalog_evidence_ids:
        return ContentNewPageOverlapGuard(
            disposition="human_decision_required",
            label="Nie można jeszcze ocenić pokrycia serwisu",
            reason=(
                "Aktualny katalog stron nie zawiera materiału z potwierdzonym źródłem, "
                "z którym można porównać brief."
            ),
            caveat="Brak katalogu lub dowodów nie jest zgodą na tworzenie duplikatu.",
            evidence_ids=catalog_evidence_ids,
        )

    exact_title = _normalized(brief.title)
    title_matches = [
        _candidate(item, "same_title")
        for item in catalog.items
        if item.title and _normalized(item.title) == exact_title
    ]
    if title_matches:
        return ContentNewPageOverlapGuard(
            disposition="reuse",
            label="Istnieje strona o tym samym tytule",
            reason=(
                "W aktualnym katalogu jest strona o dokładnie takim samym tytule. "
                "Zanim powstanie nowa, sprawdź wykorzystanie istniejącej."
            ),
            caveat=(
                "To porównanie dotyczy obserwowanego tytułu, nie układu WordPressa "
                "ani gotowości do dostawy."
            ),
            evidence_ids=_evidence_ids(title_matches),
            candidates=title_matches,
        )

    signals = [
        ("shared_intent", _normalized(brief.search_intent)),
        ("shared_service", _normalized(brief.service)),
    ]
    candidates = _shared_phrase_candidates(catalog.items, signals)
    if candidates:
        return ContentNewPageOverlapGuard(
            disposition="human_decision_required",
            label="Pokrycie wymaga decyzji człowieka",
            reason=(
                "W aktualnym katalogu znaleźliśmy strony z bezpośrednio wspólną intencją "
                "lub usługą. Wybierz później, czy nowa strona ma się wyraźnie odróżniać, "
                "zostać połączona czy wykorzystać istniejący materiał."
            ),
            caveat=(
                "Wspólne słowa są sygnałem do sprawdzenia, a nie automatycznym dowodem "
                "duplikacji."
            ),
            evidence_ids=_evidence_ids(candidates),
            candidates=candidates,
        )

    return ContentNewPageOverlapGuard(
        disposition="no_conflict",
        label="Nie znaleziono bezpośredniego pokrycia",
        reason=(
            "Aktualny katalog nie pokazuje strony z tym samym tytułem ani bezpośrednio "
            "wspólną intencją lub usługą."
        ),
        caveat=(
            "To wynik porównania z aktualnym katalogiem, nie dowód braku wszystkich "
            "możliwych duplikatów."
        ),
        evidence_ids=catalog_evidence_ids,
    )


def _shared_phrase_candidates(
    items: list[ContentInventoryCatalogItem],
    signals: list[tuple[Literal["shared_intent", "shared_service"], str]],
) -> list[ContentNewPageOverlapCandidate]:
    candidates: list[ContentNewPageOverlapCandidate] = []
    for item in items:
        if not item.title:
            continue
        observed_title = _normalized(item.title)
        for kind, phrase in signals:
            # Short terms create broad, weak matches. They must not drive a disposition.
            if len(phrase) >= 5 and phrase in observed_title:
                candidates.append(_candidate(item, kind))
                break
    return candidates


def _candidate(
    item: ContentInventoryCatalogItem,
    match_kind: Literal["same_title", "shared_intent", "shared_service"],
) -> ContentNewPageOverlapCandidate:
    return ContentNewPageOverlapCandidate(
        title=item.title or item.path,
        url=item.url,
        match_kind=match_kind,
        evidence_ids=[item.evidence_id],
    )


def _evidence_ids(candidates: list[ContentNewPageOverlapCandidate]) -> list[str]:
    return sorted(
        {
            evidence_id
            for candidate in candidates
            for evidence_id in candidate.evidence_ids
        }
    )


def _catalog_evidence_ids(catalog: ContentInventoryCatalogResponse) -> list[str]:
    """Keep the guard tied to every inventory record actually inspected."""

    return sorted(
        {
            *catalog.evidence_ids,
            *(item.evidence_id for item in catalog.items),
        }
    )


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
