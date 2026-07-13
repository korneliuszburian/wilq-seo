from __future__ import annotations

from typing import Any


def validate_context_lineage(pack: dict[str, Any]) -> None:
    decisions = pack.get("ads_diagnostics", {}).get("decision_queue") or []
    card_ids = {
        card_id
        for decision in decisions
        if isinstance(decision, dict)
        for card_id in decision.get("knowledge_card_ids", [])
    }
    rule_ids = {
        rule_id
        for decision in decisions
        if isinstance(decision, dict)
        for rule_id in decision.get("expert_rule_ids", [])
    }
    if not card_ids:
        raise SystemExit("Ads context-pack decisions must expose knowledge card IDs")
    if not rule_ids:
        raise SystemExit("Ads context-pack decisions must expose expert rule IDs")
    context_cards = {
        card.get("id")
        for card in pack.get("knowledge_card_summaries", [])
        if isinstance(card, dict)
    }
    context_rules = {
        rule.get("id") for rule in pack.get("expert_rule_summaries", []) if isinstance(rule, dict)
    }
    missing_cards = card_ids - context_cards
    missing_rules = rule_ids - context_rules
    if missing_cards:
        raise SystemExit(
            "Ads context-pack lacks knowledge card summaries for: "
            + ", ".join(sorted(missing_cards))
        )
    if missing_rules:
        raise SystemExit(
            "Ads context-pack lacks expert rule summaries for: " + ", ".join(sorted(missing_rules))
        )
