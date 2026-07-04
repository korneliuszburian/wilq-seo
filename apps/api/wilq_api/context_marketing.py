from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction
from wilq.schemas import ActionObject, ConnectorStatus, MarketingBrief, TacticalQueueResponse
from wilq.social.history import (
    build_social_history_inventory_from_env,
)


def compact_marketing_brief_for_daily_context(brief: MarketingBrief) -> dict[str, Any]:
    dumped = brief.model_dump(mode="json")
    compact_sections = []
    for section in dumped["sections"]:
        compact_items = []
        for item in section["items"]:
            item_copy = dict(item)
            metric_facts = item_copy.get("metric_facts", [])
            item_copy["metric_fact_count"] = len(metric_facts)
            item_copy["metric_facts"] = [
                context_compaction.compact_metric_fact_for_context(fact)
                for fact in metric_facts[:3]
            ]
            compact_items.append(item_copy)
        section_copy = dict(section)
        section_copy["items"] = compact_items
        compact_sections.append(section_copy)
    return {
        "generated_at": dumped["generated_at"],
        "language": dumped["language"],
        "strict_instruction": dumped["strict_instruction"],
        "connector_summary": dumped["connector_summary"],
        "sections": compact_sections,
        "top_metric_facts": [
            context_compaction.compact_metric_fact_for_context(fact)
            for fact in dumped.get("top_metric_facts", [])[:8]
        ],
        "evidence_ids": dumped["evidence_ids"],
        "action_ids": dumped["action_ids"],
        "blocker_count": dumped["blocker_count"],
        "recommendation_count": dumped["recommendation_count"],
    }


def compact_marketing_brief_for_skill_context(
    brief: MarketingBrief,
    *,
    include_top_metric_facts: bool = True,
) -> dict[str, Any]:
    dumped = brief.model_dump(mode="json")
    compact_sections = []
    item_total = 0
    for section in dumped.get("sections", []):
        items = section.get("items", []) if isinstance(section, dict) else []
        item_total += len(items)
        compact_items = []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            metric_facts = item.get("metric_facts")
            compact_items.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "kind": item.get("kind"),
                    "priority": item.get("priority"),
                    "source_connectors": item.get("source_connectors") or [],
                    "evidence_ids": (item.get("evidence_ids") or [])[:6],
                    "action_ids": item.get("action_ids") or [],
                    "summary": context_compaction.context_pack_text(item.get("summary"), limit=180),
                    "next_step": context_compaction.context_pack_text(
                        item.get("next_step"), limit=180
                    ),
                    "risk": item.get("risk"),
                    "metric_fact_count": (
                        len(metric_facts) if isinstance(metric_facts, list) else 0
                    ),
                }
            )
        compact_sections.append(
            {
                "id": section.get("id"),
                "title": section.get("title"),
                "description": context_compaction.context_pack_text(
                    section.get("description"), limit=180
                ),
                "items": compact_items,
                "items_total": len(items),
                "items_included": len(compact_items),
            }
        )
    return {
        "generated_at": dumped.get("generated_at"),
        "language": dumped.get("language"),
        "strict_instruction": dumped.get("strict_instruction"),
        "connector_summary": dumped.get("connector_summary"),
        "sections": compact_sections,
        "top_metric_facts": [
            context_compaction.compact_metric_fact_for_context(fact)
            for fact in dumped.get("top_metric_facts", [])[:5]
            if isinstance(fact, dict)
        ]
        if include_top_metric_facts
        else [],
        "evidence_ids": (dumped.get("evidence_ids") or [])[:20],
        "action_ids": dumped.get("action_ids") or [],
        "blocker_count": dumped.get("blocker_count"),
        "recommendation_count": dumped.get("recommendation_count"),
        "context_pack_compaction": {
            "sections_compacted": True,
            "items_total": item_total,
            "items_per_section_limit": 3,
            "top_metric_facts_limit": 5 if include_top_metric_facts else 0,
            "full_endpoint": "/api/marketing/brief",
        },
    }


def compact_tactical_queue_for_skill_context(
    queue: TacticalQueueResponse,
) -> dict[str, Any]:
    dumped = queue.model_dump(mode="json")
    raw_items = dumped.get("items")
    items: list[Any] = raw_items if isinstance(raw_items, list) else []
    raw_groups = dumped.get("compact_groups")
    groups: list[Any] = raw_groups if isinstance(raw_groups, list) else []
    compact_items = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        metric_facts = item.get("metric_facts")
        compact_items.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "domain": item.get("domain"),
                "intent": item.get("intent"),
                "priority": item.get("priority"),
                "risk": item.get("risk"),
                "source_connectors": item.get("source_connectors") or [],
                "evidence_ids": (item.get("evidence_ids") or [])[:6],
                "action_ids": item.get("action_ids") or [],
                "diagnosis": context_compaction.context_pack_text(item.get("diagnosis"), limit=180),
                "next_step": context_compaction.context_pack_text(item.get("next_step"), limit=180),
                "blocked_claims": (item.get("blocked_claims") or [])[:6],
                "metric_fact_count": (len(metric_facts) if isinstance(metric_facts, list) else 0),
            }
        )
    compact_groups = []
    for group in groups[:8]:
        if not isinstance(group, dict):
            continue
        compact_groups.append(
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "meta": group.get("meta"),
                "diagnosis": context_compaction.context_pack_text(
                    group.get("diagnosis"), limit=180
                ),
                "next_step": context_compaction.context_pack_text(
                    group.get("next_step"), limit=180
                ),
                "priority": group.get("priority"),
                "risk": group.get("risk"),
                "source_connectors": group.get("source_connectors") or [],
                "evidence_ids": (group.get("evidence_ids") or [])[:6],
                "action_ids": group.get("action_ids") or [],
                "blocked_claims": (group.get("blocked_claims") or [])[:6],
            }
        )
    return {
        "generated_at": dumped.get("generated_at"),
        "language": dumped.get("language"),
        "strict_instruction": dumped.get("strict_instruction"),
        "items": compact_items,
        "compact_groups": compact_groups,
        "evidence_ids": (dumped.get("evidence_ids") or [])[:20],
        "action_ids": dumped.get("action_ids") or [],
        "context_pack_compaction": {
            "items_compacted": True,
            "items_total": len(items),
            "items_included": len(compact_items),
            "compact_groups_total": len(groups),
            "compact_groups_included": len(compact_groups),
            "metric_facts_removed": True,
            "full_endpoint": "/api/marketing/tactical-queue",
        },
    }


def social_draft_context_for_context(
    actions: list[ActionObject],
    connectors: list[ConnectorStatus],
) -> dict[str, Any]:
    social_actions = sorted(
        [
            action
            for action in actions
            if action.id
            in {
                "act_prepare_facebook_social_drafts",
                "act_prepare_linkedin_social_drafts",
            }
        ],
        key=lambda action: action.id,
    )
    connector_status_by_id = {connector.id: connector for connector in connectors}
    missing_publish_access = {
        connector_id: connector_status_by_id[connector_id].missing_credentials
        for connector_id in ("linkedin", "facebook")
        if connector_id in connector_status_by_id
        and connector_status_by_id[connector_id].missing_credentials
    }
    source_inputs: list[dict[str, Any]] = []
    draft_constraints: list[str] = []
    blocked_claims = [
        "opublikowanie posta",
        "wzrost skuteczności social",
        "brak powtórzeń historycznych postów",
    ]
    source_metric_names: list[str] = []
    source_connectors: list[str] = []
    evidence_ids: list[str] = []
    for action in social_actions:
        payload = action.payload
        if isinstance(payload, dict):
            source_inputs.extend(
                item for item in payload.get("source_inputs", []) if isinstance(item, dict)
            )
            draft_constraints.extend(
                str(item) for item in payload.get("draft_constraints", []) if item
            )
            blocked_claims.extend(str(item) for item in payload.get("blocked_claims", []) if item)
            source_metric_names.extend(
                str(item) for item in payload.get("source_metric_names", []) if item
            )
            source_connectors.extend(
                str(item) for item in payload.get("source_connectors", []) if item
            )
        evidence_ids.extend(action.evidence_ids)
    social_history_inventory = build_social_history_inventory_from_env(
        connector_status_by_id,
        missing_publish_access,
    ).model_dump(mode="json")
    return {
        "mode": "review_only",
        "publish_allowed": False,
        "missing_publish_access": missing_publish_access,
        "draft_action_ids": [action.id for action in social_actions],
        "source_inputs": source_inputs[:8],
        "draft_constraints": sorted(set(draft_constraints)),
        "blocked_claims": sorted(set(blocked_claims)),
        "source_metric_names": sorted(set(source_metric_names)),
        "source_connectors": sorted(set(source_connectors)),
        "evidence_ids": list(dict.fromkeys(evidence_ids))[:12],
        "historical_social_inventory_status": social_history_inventory["status"],
        "historical_social_inventory_status_label": social_history_inventory[
            "status_label"
        ],
        "duplicate_risk_status": social_history_inventory["duplicate_risk_status"],
        "duplicate_risk_status_label": (
            "nie oceniono ryzyka powtórzenia treści social"
        ),
        "required_history_sources": social_history_inventory["required_sources"],
        "missing_history_evidence": social_history_inventory["missing_evidence_ids"],
        "social_history_inventory": social_history_inventory,
        "history_audit_endpoint": "/api/social/history-inventory/audit",
        "history_audit_contract": "social_history_inventory_v1",
        "operator_next_step": (
            "Przygotuj szkice do sprawdzenia z dowodami; publikacja i claim "
            "o braku powtórzeń pozostają zablokowane do czasu konfiguracji "
            "uprawnień LinkedIn/Facebook oraz sprawdzenia historii postów."
        ),
    }
