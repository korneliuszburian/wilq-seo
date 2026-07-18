from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardMatch,
    ContentKnowledgeServiceCandidate,
    match_content_knowledge_cards,
    required_content_knowledge_card_ids,
)
from wilq.content.knowledge.service_profile import (
    ContentServiceProfileReviewAction,
    ContentServiceProfileServiceSection,
    content_service_profile_response,
)
from wilq.content.knowledge.source_facts import ContentKnowledgeLifecycleStatus
from wilq.content.workflow.models import ContentWorkItem

ContentWorkItemServiceProfileBindingStatus = Literal["not_evaluated", "bound", "unbound"]
ContentWorkItemServiceProfileDecisionStatus = Literal[
    "not_evaluated",
    "ready",
    "review_required",
    "blocked",
]


class ContentWorkItemServiceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_card_id: str = Field(min_length=1)
    service_label: str = Field(min_length=1)
    lifecycle_status: ContentKnowledgeLifecycleStatus
    lifecycle_label: str = Field(min_length=1)
    matched_terms: list[str] = Field(min_length=1)
    match_reasons: list[str] = Field(min_length=1)
    recommended: bool


class ContentWorkItemServiceProfileContext(BaseModel):
    """Compact service/claim decision for one workflow snapshot.

    The context projects only the service card already selected by the typed
    knowledge matcher. It must not infer a service from enrichment prose.
    """

    model_config = ConfigDict(extra="forbid")

    binding_status: ContentWorkItemServiceProfileBindingStatus
    decision_status: ContentWorkItemServiceProfileDecisionStatus
    status_label: str
    reason: str
    service_card_id: str | None = None
    service_label: str | None = None
    service_status: str | None = None
    service_status_label: str = ""
    service_selection_confirmed: bool = False
    human_override_review_required: bool = False
    service_candidates: list[ContentWorkItemServiceCandidate] = Field(
        default_factory=list
    )
    freshness_label: str = ""
    freshness_as_of: str | None = None
    source_summary_label: str = ""
    allowed_claims: list[str] = Field(default_factory=list)
    claims_needing_review: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    claim_policy_scope_label: str = ""
    evidence_requirements: list[str] = Field(default_factory=list)
    missing_contracts: list[str] = Field(default_factory=list)
    safe_next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    review_action_id: str | None = None
    review_action_label: str | None = None

    @classmethod
    def not_evaluated(
        cls,
        *,
        reason: str = (
            "Workflow nie ma jeszcze bezpiecznego snapshotu do sprawdzenia "
            "usługi, więc WILQ nie przypisuje jej z samego tytułu."
        ),
        safe_next_step: str = "Najpierw usuń blocker workflow, potem sprawdź profil usługi.",
    ) -> ContentWorkItemServiceProfileContext:
        return cls(
            binding_status="not_evaluated",
            decision_status="not_evaluated",
            status_label="Profil usługi nie został jeszcze oceniony",
            reason=reason,
            claim_policy_scope_label=(
                "Nie ma jeszcze przypisanej karty usługi, więc WILQ nie pokazuje polityki "
                "twierdzeń dla tego work itemu."
            ),
            safe_next_step=safe_next_step,
        )


def build_content_work_item_service_profile_context(
    item: ContentWorkItem,
    *,
    knowledge_match: ContentKnowledgeCardMatch | None = None,
    service_selection_confirmed: bool = False,
    human_override_review_required: bool = False,
) -> ContentWorkItemServiceProfileContext:
    """Project one API-owned Service Profile decision for a selected work item."""
    match = knowledge_match or match_content_knowledge_cards(item)
    service_card = match.service_card
    if service_card is None:
        return _unbound_context(match)

    profile = content_service_profile_response()
    service_section = next(
        (
            section
            for section in profile.service_sections
            if section.card_id == service_card.id
        ),
        None,
    )
    if service_section is None:
        return _unbound_context(
            match,
            reason=(
                "WILQ znalazł kartę usługi dla tematu, ale nie ma jej w aktualnym "
                "Service Profile; nie wolno użyć jej jako podstawy claimów."
            ),
            missing_contracts=["Brakuje aktywnej sekcji Service Profile dla typed karty usługi."],
        )

    review_action = _review_action_for_card(profile.review_actions, service_card.id)
    freshness_label, freshness_as_of = _freshness_context(
        service_section.freshness_label,
        service_section.status,
    )
    decision_status = _decision_status(service_status=service_section.status)
    return ContentWorkItemServiceProfileContext(
        binding_status="bound",
        decision_status=decision_status,
        status_label=_decision_status_label(decision_status),
        reason=_decision_reason(service_section=service_section),
        service_card_id=service_section.card_id,
        service_label=service_section.title,
        service_status=service_section.status,
        service_status_label=service_section.status_label,
        service_selection_confirmed=service_selection_confirmed,
        human_override_review_required=human_override_review_required,
        service_candidates=_service_candidates(match),
        freshness_label=freshness_label,
        freshness_as_of=freshness_as_of,
        source_summary_label=_source_summary_label(service_section.source_connector_labels),
        allowed_claims=service_section.allowed_claims,
        claims_needing_review=[claim.label for claim in service_section.claims_needing_review],
        blocked_claims=_unique(
            [
                *(claim.label for claim in service_section.forbidden_claims),
                *(claim.label for claim in service_card.measurement_sensitive_claims),
            ]
        ),
        evidence_requirements=service_section.evidence_requirements,
        claim_policy_scope_label=(
            "Ten skrót dotyczy tylko dopasowanej karty usługi. Pełny rejestr twierdzeń "
            "dla szkicu jest niżej."
        ),
        missing_contracts=_missing_contracts(
            service_status=service_section.status,
            match=match,
        ),
        safe_next_step=_safe_next_step(service_section, review_action),
        source_connectors=service_section.source_connector_labels,
        source_fact_ids=service_section.source_fact_ids,
        source_material_ids=_source_material_ids_for_match(match),
        evidence_ids=service_section.evidence_ids,
        knowledge_card_ids=required_content_knowledge_card_ids(match),
        review_action_id=None if review_action is None else review_action.action_id,
        review_action_label=None if review_action is None else review_action.label,
    )


def _source_material_ids_for_match(match: ContentKnowledgeCardMatch) -> list[str]:
    cards = [
        match.service_card,
        *match.buyer_problem_cards,
        *match.cta_cards,
        *match.claim_policy_cards,
        *match.evidence_requirement_cards,
        *match.measurement_sensitive_cards,
    ]
    return list(
        dict.fromkeys(
            source_material_id
            for card in cards
            if card is not None
            for source_material_id in card.source_material_ids
        )
    )


def _unbound_context(
    match: ContentKnowledgeCardMatch,
    *,
    reason: str | None = None,
    missing_contracts: list[str] | None = None,
) -> ContentWorkItemServiceProfileContext:
    blockers = [blocker.label for blocker in match.blockers]
    return ContentWorkItemServiceProfileContext(
        binding_status="unbound",
        decision_status="blocked",
        status_label="Brakuje typed powiązania z usługą",
        reason=reason
        or (
            "WILQ nie ma dopasowanej typed karty usługi dla tego work itemu, "
            "więc nie użyje ogólnego opisu tematu jako podstawy claimów."
        ),
        missing_contracts=missing_contracts or blockers or ["Brakuje typed karty usługi."],
        service_candidates=_service_candidates(match),
        claim_policy_scope_label=(
            "Brakuje przypisanej karty usługi, więc WILQ nie pokazuje polityki twierdzeń "
            "dla tego work itemu."
        ),
        safe_next_step=(
            "Dodaj albo sprawdź kartę usługi i jej źródło w Service Profile przed szkicem."
        ),
    )


def _service_candidates(
    match: ContentKnowledgeCardMatch,
) -> list[ContentWorkItemServiceCandidate]:
    return [
        _service_candidate(
            candidate,
            recommended=candidate.card.id == match.recommended_service_card_id,
        )
        for candidate in match.service_candidates
    ]


def _service_candidate(
    candidate: ContentKnowledgeServiceCandidate,
    *,
    recommended: bool,
) -> ContentWorkItemServiceCandidate:
    lifecycle = candidate.card.lifecycle_status or "source_backed_review_required"
    lifecycle_labels = {
        "seeded_contract_proof": "seed kontraktu",
        "source_backed_review_required": "źródło wymaga review",
        "approved_current": "zatwierdzona i aktualna",
        "stale": "źródło nieaktualne",
        "rejected": "karta odrzucona",
    }
    return ContentWorkItemServiceCandidate(
        service_card_id=candidate.card.id,
        service_label=candidate.card.title,
        lifecycle_status=lifecycle,
        lifecycle_label=lifecycle_labels[lifecycle],
        matched_terms=candidate.matched_terms,
        match_reasons=[
            f"Temat lub adres strony zawiera dokładną frazę „{term}”."
            for term in candidate.matched_terms
        ],
        recommended=recommended,
    )


def _review_action_for_card(
    actions: list[ContentServiceProfileReviewAction],
    card_id: str,
) -> ContentServiceProfileReviewAction | None:
    return next((action for action in actions if action.target_card_id == card_id), None)


def _decision_status(
    *,
    service_status: str,
) -> ContentWorkItemServiceProfileDecisionStatus:
    if service_status in {"seeded_contract_proof", "stale", "rejected"}:
        return "blocked"
    if service_status == "approved_current":
        return "ready"
    return "review_required"


def _decision_status_label(status: ContentWorkItemServiceProfileDecisionStatus) -> str:
    return {
        "not_evaluated": "Profil usługi nie został jeszcze oceniony",
        "ready": "Usługa ma zatwierdzony kontekst",
        "review_required": "Usługa wymaga review przed finalnym użyciem",
        "blocked": "Kontekst usługi nie jest zatwierdzony do finalnych treści",
    }[status]


def _decision_reason(
    *,
    service_section: ContentServiceProfileServiceSection,
) -> str:
    return (
        f"WILQ dopasował typed kartę „{service_section.title}”; "
        f"jej status: {service_section.status_label}."
    )


def _freshness_context(source_freshness: str, service_status: str) -> tuple[str, str | None]:
    freshness_as_of = _freshness_as_of(source_freshness)
    label = {
        "seeded_goal_004": "seed kontraktu, nie źródło produkcyjne",
    }.get(source_freshness)
    if label is None:
        label = {
            "seeded_contract_proof": "seed kontraktu, nie źródło produkcyjne",
            "source_backed_review_required": "publiczna strona wymaga review",
            "approved_current": "źródło zatwierdzone jako aktualne",
            "stale": "źródło wymaga odświeżenia",
            "rejected": "źródło odrzucone, nie używaj",
        }.get(service_status, "świeżość profilu wymaga sprawdzenia")
    if freshness_as_of is not None:
        label = f"{label} (ostatni sygnał: {freshness_as_of})"
    return label, freshness_as_of


def _freshness_as_of(source_freshness: str) -> str | None:
    freshness_date = source_freshness.rsplit("_", 1)[-1]
    if len(freshness_date) != 10:
        return None
    if freshness_date[4] != "-" or freshness_date[7] != "-":
        return None
    year, month, day = freshness_date[:4], freshness_date[5:7], freshness_date[8:]
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return None
    return freshness_date


def _source_summary_label(source_connectors: list[str]) -> str:
    labels = {
        "public_site": "publiczna strona Ekologus",
        "internal_wilq_contract": "kontrakt WILQ (seed proof)",
    }
    source_labels = [labels.get(connector, connector) for connector in source_connectors]
    if not source_labels:
        return "Brakuje źródła profilu usługi"
    return f"Źródło profilu: {', '.join(_unique(source_labels))}"


def _missing_contracts(
    *,
    service_status: str,
    match: ContentKnowledgeCardMatch,
) -> list[str]:
    contracts: list[str] = []
    if service_status == "seeded_contract_proof":
        contracts.append("Karta ma seed proof, ale nie reviewed source fact.")
    if service_status == "source_backed_review_required":
        contracts.append("Karta usługi wymaga review przed użyciem w finalnym szkicu.")
    contracts.extend(blocker.label for blocker in match.blockers)
    return _unique(contracts)


def _safe_next_step(
    service_section: ContentServiceProfileServiceSection,
    review_action: ContentServiceProfileReviewAction | None,
) -> str:
    if review_action is not None:
        return f"{review_action.label}: {service_section.safe_next_step}"
    return service_section.safe_next_step


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
