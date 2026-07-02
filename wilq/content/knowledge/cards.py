from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from functools import lru_cache
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.source_facts import (
    ContentKnowledgeLifecycleStatus,
    ContentSourceFact,
    ekologus_source_facts,
    knowledge_lifecycle_from_review_status,
)
from wilq.content.workflow.models import ContentWorkItem

ContentKnowledgeCardType = Literal[
    "service",
    "buyer_problem",
    "buyer_trigger",
    "cta_pattern",
    "claim_policy",
    "evidence_requirement",
    "measurement_sensitive_claim",
]
ContentKnowledgeClaimStatus = Literal[
    "allowed_with_evidence",
    "needs_human_review",
    "blocked",
    "blocked_until_measurement",
]
ContentKnowledgeProductionDepthStatus = Literal[
    "seeded_contract_proof",
    "source_backed_review_required",
    "production_depth",
]

BROAD_SERVICE_FIT_TERMS = frozenset({"obowiązk", "sprawozd", "środowisk", "zgodność"})


class ContentKnowledgeClaimRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    claim_type: str
    status: ContentKnowledgeClaimStatus
    label: str
    reason: str
    required_evidence_types: list[str] = Field(default_factory=list)


class ContentKnowledgeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    card_type: ContentKnowledgeCardType
    title: str
    summary: str
    service_fit_terms: list[str] = Field(default_factory=list)
    buyer_problem_terms: list[str] = Field(default_factory=list)
    buyer_triggers: list[str] = Field(default_factory=list)
    cta_patterns: list[str] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    claims_needing_review: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    forbidden_claims: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    measurement_sensitive_claims: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    source_lineage: list[str] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    lifecycle_status: ContentKnowledgeLifecycleStatus | None = None
    confidence: float
    freshness: str
    usage_notes: list[str] = Field(default_factory=list)


class ContentKnowledgeCardBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    reason: str
    next_step: str
    work_item_id: str | None = None
    required_card_type: ContentKnowledgeCardType | None = None


class ContentKnowledgeCardMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    service_card: ContentKnowledgeCard | None = None
    buyer_problem_cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    cta_cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    claim_policy_cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    evidence_requirement_cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    measurement_sensitive_cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    blockers: list[ContentKnowledgeCardBlocker] = Field(default_factory=list)


class ContentKnowledgeProductionDepthReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentKnowledgeProductionDepthStatus
    status_label: str
    ready_for_daily_content: bool
    seeded_card_count: int
    source_backed_review_required_count: int
    production_depth_card_count: int
    blocker_labels: list[str] = Field(default_factory=list)


class ContentKnowledgeCardsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[ContentKnowledgeCard] = Field(default_factory=list)
    card_count: int
    source_lineage: list[str] = Field(default_factory=list)
    production_depth_readiness: ContentKnowledgeProductionDepthReadiness


@lru_cache(maxsize=1)
def ekologus_content_knowledge_cards() -> tuple[ContentKnowledgeCard, ...]:
    return (
        *ekologus_seed_content_knowledge_cards(),
        *compile_source_facts_to_knowledge_cards(ekologus_source_facts()),
    )


@lru_cache(maxsize=1)
def ekologus_seed_content_knowledge_cards() -> tuple[ContentKnowledgeCard, ...]:
    return (
        _environmental_compliance_service_card(),
        _consultation_cta_card(),
        _live_evidence_requirement_card(),
    )


def _environmental_compliance_service_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="ekologus_service_environmental_compliance",
        card_type="service",
        title="Obsługa środowiskowa i zgodność obowiązków",
        summary=(
            "Ekologus pomaga firmom porządkować obowiązki środowiskowe, "
            "w tym BDO, odpady i przygotowanie do konsultacji lub audytu."
        ),
        service_fit_terms=[
            "bdo",
            "odpady",
            "środowisk",
            "obowiązk",
            "zgodność",
            "zielony ład",
            "sprawozd",
        ],
        buyer_problem_terms=["nie wie", "obowiązki", "kontrola", "termin", "dokument", "ryzyko"],
        buyer_triggers=[
            "zbliżający się termin sprawozdawczy",
            "kontrola albo audyt środowiskowy",
            "porządkowanie dokumentów przed decyzją biznesową",
        ],
        cta_patterns=[
            "Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
            "Poproś o opis sytuacji firmy i dokumentów do sprawdzenia.",
        ],
        allowed_claims=[
            "Ekologus może pomóc firmie uporządkować obowiązki środowiskowe.",
            "Treść może edukacyjnie wskazywać, co warto sprawdzić przed konsultacją.",
        ],
        claims_needing_review=_environmental_review_claim_rules(),
        forbidden_claims=[
            _claim_rule(
                "knowledge_claim_no_guarantee",
                "guarantee_claim",
                "blocked",
                "Gwarancje efektu są zablokowane",
                "Nie wolno obiecywać uniknięcia kar, zgodności ani wyników SEO.",
                ["human_review"],
            )
        ],
        evidence_requirements=[
            "Dowód z GSC/WordPress/GA4/Ahrefs może uzasadnić kierunek treści.",
            "Dowód bieżący z connectora jest wymagany do rekomendacji.",
            "Karta wiedzy nie zastępuje live evidence ani source connectora.",
        ],
        measurement_sensitive_claims=[
            _claim_rule(
                "knowledge_claim_content_effect_waits_for_measurement",
                "business_outcome_claim",
                "blocked_until_measurement",
                "Twierdzenie o efekcie czeka na pomiar",
                "Nie wolno mówić o leadach, pozycjach ani konwersji przed oknem pomiaru.",
                ["measurement_window", "gsc_or_ga4_evidence"],
            )
        ],
        source_lineage=[
            "docs/goals/archive/004-goal.md",
            "docs/PROGRESS.md",
            "wilq/content/claims/ledger.py",
        ],
        source_connectors=["internal_wilq_contract"],
        lifecycle_status="seeded_contract_proof",
        confidence=0.88,
        freshness="seeded_goal_004",
        usage_notes=[
            "Używaj jako reguły interpretacji, nie jako dowodu bieżących metryk.",
            "Jeśli karta nie pasuje do tematu, zablokuj draft albo dodaj kartę po review.",
        ],
    )


def _environmental_review_claim_rules() -> list[ContentKnowledgeClaimRule]:
    return [
        _claim_rule(
            "knowledge_claim_environmental_review",
            "environmental_claim",
            "needs_human_review",
            "Twierdzenie środowiskowe wymaga sprawdzenia",
            "Zakres obowiązków środowiskowych zależy od sytuacji firmy.",
            ["service_card", "human_review"],
        ),
        _claim_rule(
            "knowledge_claim_legal_review",
            "legal_requirement_claim",
            "needs_human_review",
            "Twierdzenie prawne wymaga sprawdzenia",
            "WILQ nie może sam rozstrzygać obowiązku prawnego konkretnej firmy.",
            ["service_card", "human_review"],
        ),
    ]


def _consultation_cta_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="ekologus_cta_consultation_without_guarantee",
        card_type="cta_pattern",
        title="CTA: konsultacja bez gwarancji wyniku",
        summary=(
            "CTA ma pomagać użytkownikowi przejść od problemu do rozmowy, "
            "bez obietnicy uniknięcia kar, zgodności albo efektu SEO."
        ),
        service_fit_terms=[
            "bdo",
            "odpady",
            "magazynowanie odpadów",
            "magazynowanie odpadow",
            "operat wodnoprawny",
            "pozwolenie wodnoprawne",
            "zielony ład",
            "środowisk",
        ],
        cta_patterns=[
            "Skonsultuj obowiązki na podstawie sytuacji firmy.",
            "Przygotuj dokumenty i zapytaj Ekologus, co wymaga sprawdzenia.",
        ],
        forbidden_claims=[
            _claim_rule(
                "knowledge_cta_no_absolute_outcome",
                "guarantee_claim",
                "blocked",
                "CTA nie może obiecywać wyniku",
                "CTA nie może brzmieć jak gwarancja zgodności, leadów albo pozycji.",
                ["human_review"],
            )
        ],
        evidence_requirements=[
            "CTA musi wynikać z dopasowania usługi, intencji i claim policy.",
        ],
        source_lineage=["docs/goals/archive/004-goal.md", "wilq/content/quality/review.py"],
        source_connectors=["internal_wilq_contract"],
        lifecycle_status="seeded_contract_proof",
        confidence=0.84,
        freshness="seeded_goal_004",
        usage_notes=["CTA ma być konkretne, ale defensywne wobec claimów."],
    )


def _live_evidence_requirement_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="ekologus_evidence_live_connector_requirement",
        card_type="evidence_requirement",
        title="Live evidence i source connector są wymagane",
        summary=(
            "Knowledge card może powiedzieć jak interpretować temat, ale rekomendacja "
            "wymaga evidence IDs i source connectors z WILQ API."
        ),
        evidence_requirements=[
            "Brak evidence ID oznacza brak rekomendacji.",
            "Brak source connector oznacza brak rekomendacji.",
            "Dev preview URL nie jest historycznym dowodem SEO ani finalnym canonicalem.",
        ],
        forbidden_claims=[
            _claim_rule(
                "knowledge_no_prompt_only_recommendation",
                "performance_claim",
                "blocked",
                "Prompt-only rekomendacja jest zablokowana",
                "Nie wolno rekomendować treści na podstawie samej karty wiedzy.",
                ["evidence_id", "source_connector"],
            )
        ],
        source_lineage=[
            "AGENTS.md",
            "docs/goals/archive/004-goal.md",
            "wilq/content/enrichment/opportunity.py",
        ],
        source_connectors=["internal_wilq_contract"],
        lifecycle_status="seeded_contract_proof",
        confidence=0.95,
        freshness="seeded_goal_004",
        usage_notes=[
            "Ta karta jest twardą bramką anty-slop.",
            "Karta wiedzy nie zastępuje live evidence ani source connectora.",
        ],
    )


def compile_source_facts_to_knowledge_cards(
    facts: Iterable[ContentSourceFact],
) -> tuple[ContentKnowledgeCard, ...]:
    grouped: dict[str, list[ContentSourceFact]] = defaultdict(list)
    for fact in facts:
        if fact.review_status == "rejected":
            continue
        if fact.privacy_class != "commit_safe":
            continue
        grouped[fact.target_card_id].append(fact)

    cards: list[ContentKnowledgeCard] = []
    for card_id, card_facts in grouped.items():
        first = card_facts[0]
        lifecycle_status = _combined_lifecycle_status(card_facts)
        freshness_date = max(fact.freshness_date for fact in card_facts)
        freshness_prefix = {
            "approved_current": "reviewed",
            "stale": "stale",
            "source_backed_review_required": "public_site_review_required",
            "seeded_contract_proof": "seeded",
            "rejected": "rejected",
        }[lifecycle_status]
        cards.append(
            ContentKnowledgeCard(
                id=card_id,
                card_type=cast(ContentKnowledgeCardType, first.target_card_type),
                title=first.target_card_title,
                summary=_compile_summary(card_facts),
                service_fit_terms=_unique(
                    term for fact in card_facts for term in fact.service_fit_terms
                ),
                buyer_problem_terms=_unique(
                    term for fact in card_facts for term in fact.buyer_problem_terms
                ),
                buyer_triggers=_unique(
                    trigger for fact in card_facts for trigger in fact.buyer_triggers
                ),
                cta_patterns=_unique(
                    pattern for fact in card_facts for pattern in fact.cta_patterns
                ),
                allowed_claims=_unique(
                    claim for fact in card_facts for claim in fact.allowed_claims
                ),
                claims_needing_review=_source_fact_review_claim_rules(card_id, card_facts),
                forbidden_claims=_source_fact_forbidden_claim_rules(card_id, card_facts),
                evidence_requirements=_unique(
                    requirement
                    for fact in card_facts
                    for requirement in fact.evidence_requirements
                ),
                source_lineage=_unique(fact.source_url_or_path for fact in card_facts),
                source_fact_ids=[fact.source_id for fact in card_facts],
                source_connectors=_unique(
                    connector for fact in card_facts for connector in fact.source_connectors
                ),
                lifecycle_status=lifecycle_status,
                confidence=min(fact.confidence for fact in card_facts),
                freshness=f"{freshness_prefix}_{freshness_date}",
                usage_notes=_unique(
                    note for fact in card_facts for note in fact.usage_notes
                )
                + [
                    "Karta została skompilowana z source facts; nie zastępuje "
                    "live evidence IDs ani source connectors."
                ],
            )
        )
    return tuple(cards)


def content_knowledge_cards_response() -> ContentKnowledgeCardsResponse:
    cards = list(ekologus_content_knowledge_cards())
    return ContentKnowledgeCardsResponse(
        cards=cards,
        card_count=len(cards),
        source_lineage=_unique(line for card in cards for line in card.source_lineage),
        production_depth_readiness=content_knowledge_production_depth_readiness(cards),
    )


def content_knowledge_production_depth_readiness(
    cards: Iterable[ContentKnowledgeCard],
) -> ContentKnowledgeProductionDepthReadiness:
    card_list = list(cards)
    seeded_cards = [
        card for card in card_list if _card_lifecycle_status(card) == "seeded_contract_proof"
    ]
    review_required_cards = [
        card
        for card in card_list
        if _card_lifecycle_status(card) in {"source_backed_review_required", "stale"}
    ]
    production_cards = [
        card for card in card_list if _card_lifecycle_status(card) == "approved_current"
    ]
    blockers: list[str] = []
    if seeded_cards:
        blockers.append("Część kart to seed/contract proof, nie zatwierdzona wiedza usługowa.")
    if review_required_cards:
        blockers.append("Część kart ma źródła publiczne, ale nadal wymaga review Wilka/ownera.")
    if not production_cards:
        blockers.append("Brakuje zatwierdzonych production-depth kart usług Ekologus.")

    if production_cards and not seeded_cards and not review_required_cards:
        status: ContentKnowledgeProductionDepthStatus = "production_depth"
        label = "wiedza usługowa zatwierdzona"
        ready = True
    elif review_required_cards:
        status = "source_backed_review_required"
        label = "źródła są, wymagają review"
        ready = False
    else:
        status = "seeded_contract_proof"
        label = "seed proof, nie produkcyjna wiedza"
        ready = False

    return ContentKnowledgeProductionDepthReadiness(
        status=status,
        status_label=label,
        ready_for_daily_content=ready,
        seeded_card_count=len(seeded_cards),
        source_backed_review_required_count=len(review_required_cards),
        production_depth_card_count=len(production_cards),
        blocker_labels=blockers,
    )


def match_content_knowledge_cards(item: ContentWorkItem) -> ContentKnowledgeCardMatch:
    cards = list(ekologus_content_knowledge_cards())
    text = _search_text(
        [
            item.topic,
            item.source_public_url,
            item.final_canonical_url,
            *item.evidence_ids,
            *item.source_connectors,
        ]
    )
    service_cards = _matching_cards(cards, text, "service")
    cta_cards = _matching_cards(cards, text, "cta_pattern")
    claim_policy_cards = [
        card
        for card in cards
        if card.claims_needing_review
        or card.forbidden_claims
        or card.measurement_sensitive_claims
    ]
    evidence_requirement_cards = [
        card for card in cards if card.card_type == "evidence_requirement"
    ]
    measurement_cards = [
        card for card in cards if card.measurement_sensitive_claims
    ]
    match = ContentKnowledgeCardMatch(
        work_item_id=item.id,
        service_card=service_cards[0] if service_cards else None,
        buyer_problem_cards=service_cards,
        cta_cards=cta_cards,
        claim_policy_cards=claim_policy_cards,
        evidence_requirement_cards=evidence_requirement_cards,
        measurement_sensitive_cards=measurement_cards,
    )
    return match.model_copy(update={"blockers": content_knowledge_card_blockers(match)})


def content_knowledge_card_blockers(
    match: ContentKnowledgeCardMatch,
) -> list[ContentKnowledgeCardBlocker]:
    blockers: list[ContentKnowledgeCardBlocker] = []
    if match.service_card is None:
        blockers.append(
            _blocker(
                "missing_service_card",
                "Brakuje karty usługi",
                "WILQ nie może przygotować briefu bez typed service card dla tematu.",
                "Dodaj albo dopasuj kartę usługi Ekologus przed szkicem.",
                match.work_item_id,
                "service",
            )
        )
    if not match.cta_cards:
        blockers.append(
            _blocker(
                "missing_cta_card",
                "Brakuje karty CTA",
                "Brief musi wiedzieć, jaki typ wezwania do działania jest bezpieczny.",
                "Dodaj CTA pattern card albo zablokuj szkic.",
                match.work_item_id,
                "cta_pattern",
            )
        )
    if not match.claim_policy_cards:
        blockers.append(
            _blocker(
                "missing_claim_policy_card",
                "Brakuje polityki claimów",
                "Claim gate musi wynikać z typed knowledge card, nie z promptu.",
                "Dodaj claim policy card przed draftem.",
                match.work_item_id,
                "claim_policy",
            )
        )
    if not match.evidence_requirement_cards:
        blockers.append(
            _blocker(
                "missing_evidence_requirement_card",
                "Brakuje wymagań dowodowych",
                "WILQ musi wiedzieć, jakie dowody są wymagane i czego nie zastępuje karta.",
                "Dodaj evidence requirement card.",
                match.work_item_id,
                "evidence_requirement",
            )
        )
    return blockers


def required_content_knowledge_card_ids(match: ContentKnowledgeCardMatch) -> list[str]:
    ids: list[str] = []
    if match.service_card is not None:
        ids.append(match.service_card.id)
    ids.extend(card.id for card in match.cta_cards[:1])
    ids.extend(card.id for card in match.claim_policy_cards[:1])
    ids.extend(card.id for card in match.evidence_requirement_cards[:1])
    return _unique(ids)


def _combined_lifecycle_status(
    facts: Iterable[ContentSourceFact],
) -> ContentKnowledgeLifecycleStatus:
    statuses = {knowledge_lifecycle_from_review_status(fact.review_status) for fact in facts}
    if "source_backed_review_required" in statuses:
        return "source_backed_review_required"
    if "stale" in statuses:
        return "stale"
    if statuses == {"approved_current"}:
        return "approved_current"
    return "source_backed_review_required"


def _compile_summary(facts: Iterable[ContentSourceFact]) -> str:
    fact_list = list(facts)
    if len(fact_list) == 1:
        return fact_list[0].extracted_fact
    return " ".join(fact.extracted_fact for fact in fact_list)


def _source_fact_review_claim_rules(
    card_id: str,
    facts: Iterable[ContentSourceFact],
) -> list[ContentKnowledgeClaimRule]:
    rules: list[ContentKnowledgeClaimRule] = []
    for fact in facts:
        lifecycle_status = knowledge_lifecycle_from_review_status(fact.review_status)
        if lifecycle_status != "approved_current":
            rules.append(
                _claim_rule(
                    f"{card_id}_{fact.source_id}_requires_review",
                    "source_backed_knowledge_claim",
                    "needs_human_review",
                    "Source fact wymaga review",
                    "Publiczne źródło Ekologus wspiera analizę, ale nie odblokowuje "
                    "production-depth briefu bez review Wilka/ownera.",
                    ["source_fact", "human_review"],
                )
            )
    return rules


def _source_fact_forbidden_claim_rules(
    card_id: str,
    facts: Iterable[ContentSourceFact],
) -> list[ContentKnowledgeClaimRule]:
    return [
        _claim_rule(
            f"{card_id}_blocked_{_slug(blocked_claim)}",
            "blocked_source_fact_claim",
            "blocked",
            "Claim zablokowany przez source fact",
            blocked_claim,
            ["human_review"],
        )
        for fact in facts
        for blocked_claim in fact.blocked_claims
    ]


def _card_lifecycle_status(card: ContentKnowledgeCard) -> ContentKnowledgeLifecycleStatus:
    if card.lifecycle_status is not None:
        return card.lifecycle_status
    if card.freshness == "seeded_goal_004":
        return "seeded_contract_proof"
    if "review_required" in card.freshness:
        return "source_backed_review_required"
    if card.freshness.startswith("reviewed_"):
        return "approved_current"
    if card.freshness.startswith("stale_"):
        return "stale"
    return "source_backed_review_required"


def _matching_cards(
    cards: Iterable[ContentKnowledgeCard],
    search_text: str,
    card_type: ContentKnowledgeCardType,
) -> list[ContentKnowledgeCard]:
    matches = [
        card
        for card in cards
        if card.card_type == card_type
        and any(
            term.lower() in search_text
            for term in card.service_fit_terms
            if term.lower() not in BROAD_SERVICE_FIT_TERMS
        )
    ]
    return sorted(matches, key=_match_rank)


def _match_rank(card: ContentKnowledgeCard) -> tuple[int, float]:
    lifecycle_rank = {
        "approved_current": 0,
        "source_backed_review_required": 1,
        "stale": 2,
        "seeded_contract_proof": 3,
        "rejected": 4,
    }[_card_lifecycle_status(card)]
    return (lifecycle_rank, -card.confidence)


def _claim_rule(
    rule_id: str,
    claim_type: str,
    status: ContentKnowledgeClaimStatus,
    label: str,
    reason: str,
    required_evidence_types: list[str],
) -> ContentKnowledgeClaimRule:
    return ContentKnowledgeClaimRule(
        id=rule_id,
        claim_type=claim_type,
        status=status,
        label=label,
        reason=reason,
        required_evidence_types=required_evidence_types,
    )


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    work_item_id: str | None,
    required_card_type: ContentKnowledgeCardType,
) -> ContentKnowledgeCardBlocker:
    return ContentKnowledgeCardBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        work_item_id=work_item_id,
        required_card_type=required_card_type,
    )


def _search_text(values: Iterable[object]) -> str:
    return " ".join(str(value).lower() for value in values if value)


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result
