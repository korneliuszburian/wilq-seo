from __future__ import annotations

from apps.api.wilq_api.context_scopes import (
    SKILL_EXPERT_RULE_IDS,
    SKILL_KEYWORD_SCOPES,
    SKILL_KNOWLEDGE_CARD_IDS,
)
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ekologus_content_knowledge_cards,
)
from wilq.expert.rules import list_expert_rule_summaries
from wilq.knowledge.compilers.playbook_compiler import compile_playbook_cards
from wilq.schemas import ExpertRuleSummary, KnowledgeCard

CONTENT_KNOWLEDGE_SKILLS = frozenset(
    {
        "wilq-content-operator",
        "wilq-content-strategist",
        "wilq-gsc-content-doctor",
    }
)


def knowledge_cards_for_skill(skill: str) -> list[KnowledgeCard]:
    explicit_ids = SKILL_KNOWLEDGE_CARD_IDS.get(skill, [])
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    cards = compile_playbook_cards()
    explicit_cards = [card for card in cards if card.id in explicit_ids]
    scoped_cards = [
        card
        for card in cards
        if card.id not in explicit_ids
        and text_matches_scope(
            [card.id, card.card_type, card.title, card.summary, card.source_id],
            keywords,
        )
    ]
    return [*explicit_cards, *scoped_cards][:8]


def content_knowledge_cards_for_skill(skill: str) -> list[ContentKnowledgeCard]:
    """Return lineage-preserving Ekologus cards for content workflows.

    Content creation must use the reviewed source-fact compiler rather than
    generic marketing playbook summaries.  The API still compacts the result
    before exposing it to Codex, but keeps the actual source/material/evidence
    identity visible.
    """
    if skill not in CONTENT_KNOWLEDGE_SKILLS:
        return []
    type_order = {
        "service": 0,
        "buyer_problem": 1,
        "buyer_trigger": 2,
        "cta_pattern": 3,
        "claim_policy": 4,
        "evidence_requirement": 5,
        "measurement_sensitive_claim": 6,
    }
    cards = list(ekologus_content_knowledge_cards())
    cards.sort(
        key=lambda card: (
            0 if card.lifecycle_status == "approved_current" else 1,
            type_order.get(card.card_type, 99),
            card.title,
        )
    )
    return cards[:12]


def knowledge_card_ids_from_diagnostics(diagnostics: dict[str, object]) -> set[str]:
    """Collect decision card lineage at the API context boundary."""
    ids: set[str] = set()
    content = diagnostics.get("content_diagnostics")
    if not isinstance(content, dict):
        return ids
    queue = content.get("decision_queue")
    if not isinstance(queue, list):
        return ids
    for decision in queue:
        if not isinstance(decision, dict):
            continue
        card_ids = decision.get("knowledge_card_ids")
        if isinstance(card_ids, list):
            ids.update(card_id for card_id in card_ids if isinstance(card_id, str))
    return ids


def content_context_card_sets(
    skill: str, diagnostics: dict[str, object]
) -> tuple[list[ContentKnowledgeCard], list[KnowledgeCard]]:
    """Return source-backed cards plus only the playbooks referenced by decisions."""
    content_cards = content_knowledge_cards_for_skill(skill)
    content_card_ids = {card.id for card in content_cards}
    referenced_ids = knowledge_card_ids_from_diagnostics(diagnostics)
    playbook_cards = [
        card
        for card in knowledge_cards_for_skill(skill)
        if card.id in referenced_ids and card.id not in content_card_ids
    ]
    return content_cards, playbook_cards


def expert_rules_for_skill(skill: str) -> list[ExpertRuleSummary]:
    explicit_ids = SKILL_EXPERT_RULE_IDS.get(skill, [])
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    rules = list_expert_rule_summaries(limit=50)
    explicit_rules = [rule for rule in rules if rule.id in explicit_ids]
    scoped_rules = [
        rule
        for rule in rules
        if rule.id not in explicit_ids
        and text_matches_scope(
            [
                rule.id,
                rule.name,
                rule.domain,
                rule.source_anchor,
                rule.output_contract,
            ],
            keywords,
        )
    ]
    return [*explicit_rules, *scoped_rules][:8]


def text_matches_scope(values: list[str], keywords: set[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(values).lower()
    return any(keyword.lower() in haystack for keyword in keywords)
