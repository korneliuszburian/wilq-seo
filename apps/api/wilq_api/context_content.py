from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.schemas import MetricFact
from wilq.storage.metric_store import metric_store


def compact_content_diagnostics_for_context(
    content_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(context_compaction.without_metric_facts(content_diagnostics))
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            _compact_content_decision_for_context(decision)
            for decision in decision_queue
            if isinstance(decision, dict)
        ]
    sections = compact.pop("sections", [])
    connectors = compact.get("connectors")
    if isinstance(connectors, list):
        compact["connectors"] = [
            context_compaction.compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if isinstance(connector, dict)
        ]
    latest_refreshes = compact.get("latest_refreshes")
    if isinstance(latest_refreshes, list):
        compact["latest_refreshes"] = [
            context_compaction.compact_refresh_run_for_operator_context(refresh)
            for refresh in latest_refreshes
            if isinstance(refresh, dict)
        ]
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "connectors_compacted": True,
        "latest_refreshes_compacted": True,
        "full_endpoint": "/api/content/diagnostics",
    }
    return compact


def compact_gsc_content_diagnostics_for_context(
    content_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = compact_content_diagnostics_for_context(content_diagnostics)
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            decision
            for decision in decision_queue
            if isinstance(decision, dict)
            and decision.get("decision_type") != "review_ahrefs_gap_records"
            and "ahrefs" not in decision.get("source_connectors", [])
        ]
    compact["evidence_ids"] = [
        evidence_id
        for evidence_id in compact.get("evidence_ids", [])
        if isinstance(evidence_id, str) and not _is_ahrefs_evidence_id(evidence_id)
    ]
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        top_decision_ids = {
            str(decision.get("id"))
            for decision in compact.get("decision_queue", [])
            if isinstance(decision, dict) and decision.get("id")
        }
        operator_summary["top_decision_ids"] = [
            decision_id
            for decision_id in operator_summary.get("top_decision_ids", [])
            if decision_id in top_decision_ids
        ]
        operator_summary["source_connectors"] = [
            connector
            for connector in operator_summary.get("source_connectors", [])
            if connector != "ahrefs"
        ]
        operator_summary["evidence_ids"] = [
            evidence_id
            for evidence_id in operator_summary.get("evidence_ids", [])
            if isinstance(evidence_id, str) and not _is_ahrefs_evidence_id(evidence_id)
        ]
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        compaction["purpose"] = "gsc_content_doctor_context"
        compaction["ahrefs_decisions_removed"] = True
    return compact


def content_landing_context_for_campaign_builder() -> dict[str, Any]:
    diagnostics = build_content_diagnostics().model_dump(mode="json")
    diagnostic_candidates = [
        _campaign_builder_content_decision_candidate(decision)
        for decision in diagnostics.get("decision_queue", [])
        if isinstance(decision, dict)
        and "google_search_console" in decision.get("source_connectors", [])
        and decision.get("page")
        and (decision.get("primary_query") or decision.get("queries"))
        and decision.get("evidence_ids")
    ]
    if diagnostic_candidates:
        diagnostic_candidates.sort(
            key=lambda item: (
                context_compaction.numeric_or_zero(item.get("impressions")),
                context_compaction.numeric_or_zero(item.get("clicks")),
            ),
            reverse=True,
        )
        evidence_ids = sorted(
            {
                evidence_id
                for candidate in diagnostic_candidates
                for evidence_id in candidate["evidence_ids"]
            }
        )
        return _campaign_builder_landing_context(
            candidates=diagnostic_candidates,
            evidence_ids=evidence_ids,
            total_count=diagnostics.get("query_page_count", len(diagnostic_candidates)),
            source="content_decision_queue",
        )

    facts = [
        fact
        for fact in metric_store().list_metric_facts(
            connector_id="google_search_console",
            limit=500,
        )
        if {"query", "page"}.issubset(fact.dimensions)
    ]
    grouped: dict[tuple[str, str], list[MetricFact]] = {}
    for fact in facts:
        page = fact.dimensions.get("page")
        query = fact.dimensions.get("query")
        if page and query:
            grouped.setdefault((page, query), []).append(fact)

    candidates = [
        _campaign_builder_query_page_candidate(page, query, group_facts)
        for (page, query), group_facts in grouped.items()
    ]
    candidates.sort(
        key=lambda item: (
            context_compaction.numeric_or_zero(item.get("impressions")),
            context_compaction.numeric_or_zero(item.get("clicks")),
        ),
        reverse=True,
    )
    evidence_ids = sorted(
        {evidence_id for candidate in candidates for evidence_id in candidate["evidence_ids"]}
    )
    return _campaign_builder_landing_context(
        candidates=candidates,
        evidence_ids=evidence_ids,
        total_count=len(candidates),
        source="metric_facts",
    )


def _compact_content_decision_for_context(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    ahrefs_rows = compact.get("ahrefs_candidate_rows")
    if isinstance(ahrefs_rows, list):
        compact["ahrefs_candidate_rows_total"] = len(ahrefs_rows)
        compact["ahrefs_candidate_rows"] = [
            _compact_content_ahrefs_candidate_row_for_context(row)
            for row in ahrefs_rows[:4]
            if isinstance(row, dict)
        ]
        compact["ahrefs_candidate_rows_included"] = len(compact["ahrefs_candidate_rows"])
    return compact


def _compact_content_ahrefs_candidate_row_for_context(
    row: dict[str, Any],
) -> dict[str, Any]:
    keep_keys = {
        "topic",
        "gap_type_label",
        "relevance_status_label",
        "relevance_score",
        "business_relevance_reason_labels",
        "gsc_demand_label",
        "gsc_cross_check",
        "wordpress_inventory_match_label",
        "wordpress_cross_check",
        "gsc_overlap_terms",
        "wordpress_overlap_urls",
        "keyword",
        "competitor_domain",
        "source_url",
        "referenced_public_url",
        "metric_value",
        "source_connectors",
        "evidence_ids",
        "next_step",
    }
    compact = {key: row[key] for key in keep_keys if key in row}
    for key, limit in (
        ("business_relevance_reason_labels", 4),
        ("gsc_overlap_terms", 4),
        ("wordpress_overlap_urls", 3),
        ("source_connectors", 3),
        ("evidence_ids", 3),
    ):
        value = compact.get(key)
        if isinstance(value, list):
            compact[key] = value[:limit]
            compact[f"{key}_total"] = len(value)
    for key in ("gsc_cross_check", "wordpress_cross_check"):
        if key in compact:
            compact[key] = context_compaction.compact_ahrefs_cross_check_for_context(compact[key])
    return compact


def _is_ahrefs_evidence_id(evidence_id: str) -> bool:
    return "_ahrefs" in evidence_id


def _campaign_builder_landing_context(
    *,
    candidates: list[dict[str, Any]],
    evidence_ids: list[str],
    total_count: int,
    source: str,
) -> dict[str, Any]:
    return {
        "language": "pl-PL",
        "strict_instruction": (
            "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza "
            "blocker, nie domysł marketingowy."
        ),
        "live_data_available": bool(candidates),
        "source_connectors": ["google_search_console"],
        "evidence_ids": evidence_ids,
        "query_page_candidate_count": len(candidates),
        "query_page_candidates": candidates[:8],
        "blocked_claims": [
            "campaign performance",
            "conversion uplift",
            "lead quality",
            "ranking guarantee",
        ],
        "context_pack_compaction": {
            "full_endpoint": "/api/content/diagnostics",
            "metric_facts_removed": True,
            "purpose": "landing_context",
            "source": source,
            "query_page_candidates_total": total_count,
            "query_page_candidates_included": len(candidates[:8]),
        },
    }


def _campaign_builder_content_decision_candidate(decision: dict[str, Any]) -> dict[str, Any]:
    queries = decision.get("queries")
    query = decision.get("primary_query")
    if not query and isinstance(queries, list) and queries:
        query = queries[0]
    return {
        "page": decision.get("page"),
        "query": query,
        "queries": queries if isinstance(queries, list) else [],
        "query_count": decision.get("query_count"),
        "decision_type": decision.get("decision_type"),
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "clicks": decision.get("total_clicks"),
        "impressions": decision.get("total_impressions"),
        "ctr": decision.get("aggregate_ctr"),
        "average_position": decision.get("best_average_position"),
        "wordpress_match": decision.get("wordpress_match"),
        "evidence_ids": decision.get("evidence_ids", []),
        "source_connectors": ["google_search_console"],
        "blocked_claims": decision.get(
            "blocked_claims",
            ["campaign performance", "conversion uplift", "ranking guarantee"],
        ),
    }


def _campaign_builder_query_page_candidate(
    page: str,
    query: str,
    facts: list[MetricFact],
) -> dict[str, Any]:
    return {
        "page": page,
        "query": query,
        "clicks": context_compaction.metric_value(facts, "clicks"),
        "impressions": context_compaction.metric_value(facts, "impressions"),
        "ctr": context_compaction.metric_value(facts, "ctr"),
        "average_position": context_compaction.metric_value(facts, "average_position"),
        "evidence_ids": sorted({fact.evidence_id for fact in facts if fact.evidence_id}),
        "source_connectors": ["google_search_console"],
        "blocked_claims": [
            "campaign performance",
            "conversion uplift",
            "ranking guarantee",
        ],
    }
