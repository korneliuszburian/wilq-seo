"""Decomposed service_profile review implementation."""

from __future__ import annotations

from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.private_source_proposals import PrivateSourceProposal
from wilq.content.knowledge.service_profile.contracts import (
    ContentServiceProfileApprovalReadiness,
    ContentServiceProfileApprovalReadinessItem,
    ContentServiceProfileCoverageGap,
    ContentServiceProfileCoverageSummary,
    ContentServiceProfilePrivateReviewQueueItem,
    ContentServiceProfilePrivateReviewValue,
    ContentServiceProfileReviewAction,
    ContentServiceProfileReviewActionSummary,
    ContentServiceProfileReviewQueueItem,
    ContentServiceProfileReviewRequirement,
    ContentServiceProfileServiceSection,
    ServiceProfileReviewActionPriority,
    ServiceProfileReviewActionScope,
    ServiceProfileReviewDecisionOption,
)
from wilq.content.knowledge.service_profile.shared import (
    _lifecycle,
    _priority_order,
    _review_scope_order,
    _risk_order,
    _source_scope_order,
)
from wilq.content.knowledge.source_facts import ContentSourceFact


def _approval_readiness(
    *,
    coverage_summary: ContentServiceProfileCoverageSummary,
    review_action_summary: ContentServiceProfileReviewActionSummary,
    private_proposals: list[PrivateSourceProposal],
) -> ContentServiceProfileApprovalReadiness:
    approved_current_count = coverage_summary.approved_current_count
    review_required_count = coverage_summary.source_backed_review_required_count
    private_pending_count = sum(
        1
        for proposal in private_proposals
        if proposal.retention_decision == "pending_owner_decision"
        or proposal.review_status == "review_required"
    )
    checklist = [
        ContentServiceProfileApprovalReadinessItem(
            code="public_service_review",
            label="Publiczne karty usług sprawdzone przez człowieka",
            status=(
                "ready_for_review"
                if review_action_summary.public_service_review_count
                else "blocked"
            ),
            blocking=approved_current_count == 0,
            detail=(
                f"{review_action_summary.public_service_review_count} publicznych kart "
                "czeka na decyzję review; żadna nie jest jeszcze zatwierdzona jako "
                "wiedza do finalnych treści."
                if approved_current_count == 0
                else f"{approved_current_count} kart ma status zatwierdzonej wiedzy."
            ),
            next_step=(
                "Zacznij od pierwszej publicznej karty usługi i zapisz decyzję: "
                "zatwierdź, popraw, oznacz jako nieaktualne albo odrzuć."
            ),
            related_action_id=review_action_summary.first_review_action_id,
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="source_trace_review",
            label="Ślad źródłowy i zablokowane twierdzenia sprawdzone",
            status=(
                "ready_for_review"
                if review_action_summary.first_review_required_fields
                else "blocked"
            ),
            blocking=True,
            detail=(
                "Review musi potwierdzić czytelny ślad źródłowy, zablokowane "
                "twierdzenia, notatkę review i decyzję człowieka."
            ),
            next_step=(
                "Użyj pól review z Service Profile zamiast ręcznie zgadywać, co Wilku ma podpisać."
            ),
            related_action_id=review_action_summary.first_review_action_id,
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="private_source_governance",
            label="Prywatne propozycje ekologus-ai mają decyzję ownera",
            status="blocked" if private_pending_count else "ready_for_review",
            blocking=private_pending_count > 0,
            detail=(
                f"{private_pending_count} prywatnych propozycji nadal wymaga decyzji "
                "review, retencji albo aktualności; nie może odblokować finalnych "
                "treści."
            )
            if private_pending_count
            else "Prywatne propozycje nie blokują obecnej ścieżki review.",
            next_step=(
                "Dla prywatnych propozycji potwierdź klasy danych, bloki źródła, "
                "aktualność, odbiorców, retencję, ścieżkę usunięcia i bramki ewaluacji."
            ),
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="promotion_request_packet",
            label="Osobny wniosek o zatwierdzenie jest gotowy do przygotowania",
            status="blocked",
            blocking=True,
            detail=(
                "WILQ nie ma jeszcze zatwierdzonego wyniku review, więc nie wolno "
                "przygotować wniosku jako gotowego do promocji wiedzy."
            ),
            next_step=(
                "Najpierw zapisz wynik rozmowy review skryptem "
                "record_service_profile_review_result.py; dopiero raport ready może "
                "zasilić osobny wniosek."
            ),
        ),
    ]
    blockers = [item.label for item in checklist if item.blocking]
    can_request_promotion = not blockers and approved_current_count > 0
    return ContentServiceProfileApprovalReadiness(
        status="ready_for_promotion_request" if can_request_promotion else "blocked",
        status_label=(
            "wniosek o zatwierdzenie można przygotować"
            if can_request_promotion
            else "wniosek o zatwierdzenie zablokowany"
        ),
        can_request_promotion=can_request_promotion,
        mutation_allowed=False,
        production_depth_unlocked=False,
        reviewed_output_required=True,
        approved_current_count=approved_current_count,
        review_required_count=review_required_count,
        first_action_id=review_action_summary.first_review_action_id,
        first_action_label=review_action_summary.first_review_action_label,
        blockers=blockers,
        checklist=checklist,
        safe_next_step=(
            "Przeprowadź review pierwszej karty Service Profile i zapisz wynik "
            "review; WILQ nadal nie zmieni kart ani source facts bez osobnej "
            "audytowanej ścieżki."
        ),
    )


def _private_review_queue(
    proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfilePrivateReviewQueueItem]:
    queue = [
        ContentServiceProfilePrivateReviewQueueItem(
            proposal_id=proposal.proposal_id,
            source_id=proposal.source_id,
            scope=proposal.scope,
            target_card_id=proposal.target_card_id,
            target_card_title=proposal.target_card_title,
            risk_tier=proposal.risk_tier,
            freshness_status=proposal.freshness_status,
            audience=proposal.audience,
            review_status=proposal.review_status,
            promotion_allowed=False,
            blocked_claim_count=len(proposal.blocked_claims),
            data_classes=proposal.data_classes,
            source_block_refs=proposal.source_block_refs,
            retention_decision=proposal.retention_decision,
            deletion_path=proposal.deletion_path,
            eval_case_ids=proposal.eval_case_ids,
            source_locator_label=proposal.source_locator_label,
            owner_role=proposal.owner_role,
            redacted=True,
            source_trace_ready=bool(proposal.source_block_refs and proposal.eval_case_ids),
            safe_next_step=proposal.safe_next_step,
        )
        for proposal in proposals
    ]
    return sorted(
        queue,
        key=lambda item: (
            _risk_order(item.risk_tier),
            _source_scope_order(item.scope),
            item.target_card_title,
        ),
    )


def _private_review_value_summary(
    *,
    facts: list[ContentSourceFact],
    private_review_queue: list[ContentServiceProfilePrivateReviewQueueItem],
) -> ContentServiceProfilePrivateReviewValue:
    private_source_ids = {item.source_id for item in private_review_queue}
    private_facts = [fact for fact in facts if fact.source_id in private_source_ids]
    proposal_count = len(private_review_queue)
    blocked_claim_proposal_count = sum(
        1 for item in private_review_queue if item.blocked_claim_count > 0
    )
    cta_pattern_proposal_count = sum(1 for fact in private_facts if fact.cta_patterns)
    buyer_trigger_proposal_count = sum(
        1 for fact in private_facts if fact.buyer_triggers or fact.buyer_problem_terms
    )
    promotion_allowed_count = sum(1 for item in private_review_queue if item.promotion_allowed)
    review_value_points: list[str] = []
    review_questions: list[str] = []
    if cta_pattern_proposal_count:
        review_value_points.append(
            "Prywatne propozycje dodają CTA albo kierunek rozmowy do oceny przez Wilka."
        )
        review_questions.append(
            "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?"
        )
    if buyer_trigger_proposal_count:
        review_value_points.append(
            "Prywatne propozycje doprecyzowują problemy i triggery kupującego."
        )
        review_questions.append(
            "Czy opisany problem kupującego faktycznie pasuje do rozmów z klientami Ekologus?"
        )
    if blocked_claim_proposal_count:
        review_value_points.append(
            "Każda propozycja niesie jawne zablokowane twierdzenia, więc może pomagać "
            "w Claim Ledgerze bez luzowania bezpieczeństwa."
        )
        review_questions.append(
            "Czy zablokowane twierdzenia są kompletne, szczególnie dla prawa, "
            "kar, zgodności i efektów?"
        )
    if promotion_allowed_count == 0 and proposal_count:
        review_value_points.append(
            "Żadna prywatna propozycja nie może wejść do production-depth bez review człowieka."
        )
        review_questions.append(
            "Które propozycje odrzucić, oznaczyć jako nieaktualne albo zostawić "
            "tylko jako tło do UAT?"
        )
    operator_value_score = 0
    if proposal_count:
        operator_value_score += 2
    if cta_pattern_proposal_count:
        operator_value_score += 2
    if buyer_trigger_proposal_count:
        operator_value_score += 2
    if blocked_claim_proposal_count == proposal_count and proposal_count:
        operator_value_score += 2
    if promotion_allowed_count == 0:
        operator_value_score += 1
    return ContentServiceProfilePrivateReviewValue(
        proposal_count=proposal_count,
        promotion_allowed_count=promotion_allowed_count,
        blocked_claim_proposal_count=blocked_claim_proposal_count,
        cta_pattern_proposal_count=cta_pattern_proposal_count,
        buyer_trigger_proposal_count=buyer_trigger_proposal_count,
        operator_value_score=min(operator_value_score, 9),
        value_summary=(
            "Prywatne propozycje ekologus-ai dają materiał do review i mogą poprawić "
            "konkretność Service Profile, ale nie odblokowują production-depth, "
            "publikacji ani gotowych twierdzeń bez decyzji człowieka."
        ),
        review_value_points=review_value_points,
        review_questions=review_questions,
    )


def _review_action_queue(
    *,
    review_actions: list[ContentServiceProfileReviewAction],
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
    first_review_action_id: str | None,
) -> list[ContentServiceProfileReviewQueueItem]:
    title_by_card_id = _target_title_lookup(service_sections, private_proposals)
    queue = [
        ContentServiceProfileReviewQueueItem(
            action_id=action.action_id,
            review_scope=action.review_scope,
            priority=action.priority,
            target_card_id=action.target_card_id,
            target_card_title=(
                title_by_card_id.get(action.target_card_id or "")
                or action.target_card_id
                or "ogólny przegląd wiedzy"
            ),
            decision_options=action.decision_options,
        )
        for action in review_actions
    ]
    queue = sorted(
        queue,
        key=lambda item: (
            _priority_order(item.priority),
            _review_scope_order(item.review_scope),
            item.target_card_title,
            item.action_id,
        ),
    )
    if not first_review_action_id:
        return queue
    first_items = [item for item in queue if item.action_id == first_review_action_id]
    if not first_items:
        return queue
    return [
        first_items[0],
        *(item for item in queue if item.action_id != first_review_action_id),
    ]


def _target_title_lookup(
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
) -> dict[str, str]:
    lookup = {section.card_id: section.title for section in service_sections}
    lookup.update(
        {proposal.target_card_id: proposal.target_card_title for proposal in private_proposals}
    )
    return lookup


def _review_actions(
    *,
    cards: list[ContentKnowledgeCard],
    coverage_gaps: list[ContentServiceProfileCoverageGap],
    private_proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfileReviewAction]:
    decision_options = _review_decision_options()
    review_requirements = _review_requirements()
    private_review_requirements = _private_review_requirements()
    actions = [
        ContentServiceProfileReviewAction(
            action_id="service_profile_request_knowledge_review",
            mode="review_request",
            review_scope="general_knowledge_review",
            priority="medium",
            decision_options=decision_options,
            review_requirements=review_requirements,
            label="Poproś o review wiedzy usługowej",
            reason=(
                "Karty review-required nie mogą odblokować production-depth bez decyzji człowieka."
            ),
            blocked_write_claim="To nie zapisuje zmian w kartach wiedzy.",
            required_human_role="Wilku albo owner wiedzy Ekologus",
        )
    ]
    for card in cards:
        if (
            card.card_type == "service"
            and _lifecycle(card) == "source_backed_review_required"
            and "public_site" in card.source_connectors
        ):
            actions.append(
                ContentServiceProfileReviewAction(
                    action_id=f"service_profile_review_card_{card.id}",
                    mode="review_request",
                    review_scope="public_service_card",
                    priority="medium",
                    decision_options=decision_options,
                    review_requirements=review_requirements,
                    label=f"Sprawdź kartę usługi: {card.title}",
                    reason=(
                        "Karta ma publiczne źródło, ale wymaga decyzji człowieka "
                        "zanim stanie się approved-current."
                    ),
                    blocked_write_claim=(
                        "To nie promuje source fact ani knowledge card; "
                        "potrzebna jest osobna zatwierdzona akcja i audyt."
                    ),
                    required_human_role="Wilku albo owner wiedzy Ekologus",
                    target_card_id=card.id,
                )
            )
    for gap in coverage_gaps:
        actions.append(
            ContentServiceProfileReviewAction(
                action_id=f"service_profile_review_{gap.gap_id}",
                mode="prepare",
                review_scope="coverage_gap",
                priority="high" if gap.severity == "blocker" else "medium",
                decision_options=decision_options,
                review_requirements=review_requirements,
                label=f"Przygotuj review: {gap.label}",
                reason=gap.reason,
                blocked_write_claim="To jest przygotowanie review, nie edycja knowledge base.",
                required_human_role="Wilku albo owner wiedzy Ekologus",
                gap_id=gap.gap_id,
            )
        )
    for proposal in private_proposals:
        if proposal.review_status != "review_required":
            continue
        actions.append(
            ContentServiceProfileReviewAction(
                action_id=f"service_profile_review_{proposal.proposal_id}",
                mode="review_request",
                review_scope=_private_review_action_scope(proposal),
                priority=_private_review_action_priority(proposal),
                decision_options=decision_options,
                review_requirements=private_review_requirements,
                label=f"Sprawdź prywatną propozycję: {proposal.target_card_title}",
                reason=(
                    f"{proposal.source_locator_label} jest redacted i review-required; "
                    "może wspierać pytania UAT, ale nie production-depth."
                ),
                blocked_write_claim=(
                    "To nie promuje private proposal do source fact ani knowledge card."
                ),
                required_human_role=proposal.owner_role,
                target_card_id=proposal.target_card_id,
            )
        )
    return actions


def _review_decision_options() -> list[ServiceProfileReviewDecisionOption]:
    return ["approve", "needs_changes", "stale", "reject"]


def _review_requirements() -> list[ContentServiceProfileReviewRequirement]:
    return [
        ContentServiceProfileReviewRequirement(
            field="action_id",
            label="action ID z live Service Profile",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="target_card_id",
            label="target card ID zgodny z action_id",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="decision",
            label="decyzja review",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="source_trace_clear",
            label="czy ślad źródłowy jest czytelny",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="blocked_claims_reviewed",
            label="czy claimy zablokowane zostały sprawdzone",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="notes",
            label="notatki review",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="follow_up_beads",
            label="follow-up Beads",
            requirement_type="follow_up",
            required=False,
            blocking_rule=(
                "Wymagane, gdy decision != approve albo source_trace_clear/"
                "blocked_claims_reviewed nie są true."
            ),
        ),
    ]


def _private_review_requirements() -> list[ContentServiceProfileReviewRequirement]:
    return [
        *_review_requirements(),
        ContentServiceProfileReviewRequirement(
            field="data_classes_confirmed",
            label="czy klasy danych prywatnego źródła są poprawne",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="source_block_refs_confirmed",
            label="czy source block refs są wystarczające do śladu źródłowego",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="freshness_status_confirmed",
            label="czy aktualność prywatnego źródła została potwierdzona",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy freshness_status "
                "nie został potwierdzony przez ownera/reviewera."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="audience_scope_confirmed",
            label="czy zakres dostępu/audience prywatnego źródła jest poprawny",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy audience/scope "
                "nie został potwierdzony dla użycia marketingowego."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="retention_decision_confirmed",
            label="czy decyzja retencji została podjęta albo świadomie zablokowana",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy retention_decision "
                "pozostaje pending_owner_decision bez świadomej decyzji ownera."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="deletion_path_confirmed",
            label="czy ścieżka usunięcia/odrzucenia proposal jest jasna",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="eval_gates_confirmed",
            label="czy eval gates blokujące unsafe claimy są wskazane",
            requirement_type="boolean",
            required=True,
        ),
    ]


def _private_review_action_scope(
    proposal: PrivateSourceProposal,
) -> ServiceProfileReviewActionScope:
    if proposal.scope == "service":
        return "private_service_proposal"
    if proposal.scope == "evidence_requirement":
        return "private_evidence_policy_proposal"
    return "private_claim_policy_proposal"


def _private_review_action_priority(
    proposal: PrivateSourceProposal,
) -> ServiceProfileReviewActionPriority:
    if proposal.scope in {"claim_policy", "evidence_requirement"}:
        return "high"
    return "medium"


def _review_action_summary(
    *,
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileReviewActionSummary:
    first_review_action = _first_review_action(review_actions)
    private_actions = [
        action
        for action in review_actions
        if action.review_scope
        in {
            "private_service_proposal",
            "private_claim_policy_proposal",
            "private_evidence_policy_proposal",
        }
    ]
    public_service_actions = [
        action for action in review_actions if action.review_scope == "public_service_card"
    ]
    private_service_actions = [
        action for action in private_actions if action.review_scope == "private_service_proposal"
    ]
    private_policy_actions = [
        action
        for action in private_actions
        if action.review_scope
        in {"private_claim_policy_proposal", "private_evidence_policy_proposal"}
    ]
    return ContentServiceProfileReviewActionSummary(
        total_count=len(review_actions),
        review_request_count=sum(1 for action in review_actions if action.mode == "review_request"),
        prepare_count=sum(1 for action in review_actions if action.mode == "prepare"),
        public_service_review_count=len(public_service_actions),
        private_review_count=len(private_actions),
        private_service_review_count=len(private_service_actions),
        private_policy_review_count=len(private_policy_actions),
        first_review_action_id=first_review_action.action_id
        if first_review_action is not None
        else None,
        first_review_action_label=first_review_action.label
        if first_review_action is not None
        else None,
        first_review_action_reason=first_review_action.reason
        if first_review_action is not None
        else None,
        first_review_action_scope=first_review_action.review_scope
        if first_review_action is not None
        else None,
        first_review_action_priority=first_review_action.priority
        if first_review_action is not None
        else None,
        first_review_action_target_card_id=first_review_action.target_card_id
        if first_review_action is not None
        else None,
        first_review_action_gap_id=first_review_action.gap_id
        if first_review_action is not None
        else None,
        first_review_required_fields=_required_review_fields(first_review_action)
        if first_review_action is not None
        else [],
        first_review_safe_next_step=_first_review_safe_next_step(first_review_action)
        if first_review_action is not None
        else None,
        safe_next_step=(
            "Najpierw przejrzyj publiczne karty usług, potem prywatne propozycje "
            "service i claim-policy; żadna akcja review nie promuje faktów bez "
            "osobnego prepare-only preview i audytu."
        ),
    )


def _first_review_action(
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileReviewAction | None:
    priority_order: dict[ServiceProfileReviewActionPriority, int] = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }
    scope_order: dict[ServiceProfileReviewActionScope, int] = {
        "public_service_card": 0,
        "private_service_proposal": 1,
        "private_claim_policy_proposal": 2,
        "private_evidence_policy_proposal": 3,
        "coverage_gap": 4,
        "general_knowledge_review": 5,
    }
    candidates = [
        action for action in review_actions if action.mode == "review_request"
    ] or review_actions
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda action: (
            scope_order[action.review_scope],
            priority_order[action.priority],
            action.label,
            action.action_id,
        ),
    )[0]


def _required_review_fields(action: ContentServiceProfileReviewAction) -> list[str]:
    return [requirement.field for requirement in action.review_requirements if requirement.required]


def _first_review_safe_next_step(
    action: ContentServiceProfileReviewAction,
) -> str:
    if action.review_scope == "public_service_card":
        return (
            "Weź tę publiczną kartę jako pierwszą: sprawdź źródło, zablokowane "
            "claimy i dopiero potem zdecyduj approve/needs_changes/stale/reject."
        )
    if action.review_scope == "private_service_proposal":
        return (
            "Pokaż redacted propozycję Wilkowi jako pytanie UAT; nie promuj jej "
            "do source fact bez potwierdzenia klas danych, aktualności i retencji."
        )
    if action.review_scope in {
        "private_claim_policy_proposal",
        "private_evidence_policy_proposal",
    }:
        return (
            "Sprawdź najpierw claim-policy/evidence-policy, bo od tego zależy, "
            "czego WILQ nie może powiedzieć w treściach."
        )
    if action.review_scope == "coverage_gap":
        return "Najpierw znajdź źródło dla luki, potem dopiero przygotuj kartę review."
    return "Zbierz decyzję review człowieka przed jakąkolwiek promocją wiedzy."
