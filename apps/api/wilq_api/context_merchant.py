from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction


def compact_merchant_diagnostics_for_context(
    merchant_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(context_compaction.without_metric_facts(merchant_diagnostics))
    sections = compact.pop("sections", [])
    issue_clusters = compact.pop("issue_clusters", [])
    decision_queue = compact.pop("decision_queue", [])
    product_performance = compact.get("product_performance_readiness")
    if isinstance(product_performance, dict):
        performance_rows = product_performance.get("performance_rows")
        if isinstance(performance_rows, list):
            product_performance["performance_rows_total"] = len(performance_rows)
            product_performance["performance_rows"] = []
            product_performance["performance_rows_included"] = 0
    price_impact = compact.get("price_impact_readiness")
    if isinstance(price_impact, dict):
        change_preview = price_impact.get("change_preview")
        if isinstance(change_preview, list):
            price_impact["change_preview_total"] = len(change_preview)
            price_impact["change_preview"] = [
                compact_merchant_price_impact_preview_for_context(preview)
                for preview in change_preview[:2]
                if isinstance(preview, dict)
            ]
            price_impact["change_preview_included"] = len(price_impact["change_preview"])
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        operator_summary.pop("top_decision_ids", None)
        operator_summary.pop("top_issue_cluster_ids", None)
        operator_summary.pop("top_tactical_item_ids", None)
        operator_summary["decision_source"] = "kolejka decyzji Merchant"
        operator_summary["drilldown_source"] = "szczegóły problemów feedu"
        operator_summary["count_semantics"] = "zgłoszenia problemów, nie unikalne produkty"
    compact["issue_cluster_summaries"] = compact_merchant_issue_clusters_for_context(
        issue_clusters
    )
    compact["decision_queue"] = compact_merchant_decision_queue_for_context(decision_queue)
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "issue_clusters_total": len(issue_clusters) if isinstance(issue_clusters, list) else 0,
        "issue_clusters_included": len(compact["issue_cluster_summaries"]),
        "decision_queue_total": len(decision_queue) if isinstance(decision_queue, list) else 0,
        "decision_queue_included": len(compact["decision_queue"]),
        "raw_merchant_vendor_values_removed": True,
        "full_endpoint": "/api/merchant/diagnostics",
    }
    return compact


def compact_merchant_issue_clusters_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compact_clusters: list[dict[str, Any]] = []
    for cluster in value[:4]:
        if not isinstance(cluster, dict):
            continue
        compact_clusters.append(
            {
                "problem": cluster.get("issue_type_label") or "problem feedu",
                "atrybut": cluster.get("affected_attribute_label") or "atrybut",
                "kontekst": cluster.get("reporting_context_label") or "kontekst raportowania",
                "status": cluster.get("severity_label") or cluster.get("risk"),
                "rozwiązanie": cluster.get("resolution_label") or "wymaga sprawdzenia w Merchant",
                "zgłoszenia": cluster.get("product_count"),
                "country": cluster.get("country"),
                "next_step": context_compaction.context_pack_text(
                    cluster.get("next_step"), limit=180
                ),
                "evidence_ids": (cluster.get("evidence_ids") or [])[:3],
                "action_id": cluster.get("action_id"),
            }
        )
    return compact_clusters


def compact_merchant_decision_queue_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    selected_decisions = selected_merchant_context_decisions(value)
    compact_decisions: list[dict[str, Any]] = []
    for index, decision in enumerate(selected_decisions, start=1):
        if not isinstance(decision, dict):
            continue
        change_preview = decision.get("change_preview")
        compact_decision = {
            "decision_ref": f"merchant_decision_{index}",
            "decision_type": decision.get("decision_type"),
            "status": decision.get("status"),
            "priority": decision.get("priority"),
            "problem": decision.get("issue_type_label") or "problem feedu",
            "atrybut": decision.get("affected_attribute_label") or "atrybut",
            "kontekst": (decision.get("reporting_context_label") or "kontekst raportowania"),
            "summary": context_compaction.context_pack_text(decision.get("summary"), limit=220),
            "next_step": context_compaction.context_pack_text(decision.get("next_step"), limit=200),
            "metric_tiles": decision.get("metric_tiles") or {},
            "change_preview_total": (
                len(change_preview) if isinstance(change_preview, list) else 0
            ),
            "change_preview": compact_merchant_issue_preview_for_context(
                change_preview if isinstance(change_preview, list) else []
            ),
            "evidence_ids": (decision.get("evidence_ids") or [])[:4],
            "source_connectors": decision.get("source_connectors") or [],
            "action_ids": decision.get("action_ids") or [],
            "blocked_claims": context_compaction.priority_limited_strings(
                decision.get("blocked_claims"),
                [
                    "wpływ zmiany ceny",
                    "zwrot z reklam na poziomie produktu",
                    "opłacalność produktu",
                    "zapis do feedu",
                    "odzyskany przychód produktu",
                    "efekt naprawy produktu",
                ],
                limit=6,
            ),
            "count_semantics": "zgłoszenia problemów, nie unikalne produkty",
        }
        safe_id = safe_merchant_context_id(decision.get("id"))
        if safe_id is not None:
            compact_decision["id"] = safe_id
        compact_decisions.append(compact_decision)
    return compact_decisions


def selected_merchant_context_decisions(value: list[Any]) -> list[Any]:
    required_ids = {
        "merchant_decision_review_ads_product_state_mapping",
        "merchant_decision_review_price_impact_readiness",
    }
    selected: list[Any] = []
    seen: set[int] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("id") in required_ids:
            selected.append(item)
            seen.add(id(item))
    for item in value:
        if len(selected) >= 6:
            break
        if not isinstance(item, dict) or id(item) in seen:
            continue
        selected.append(item)
        seen.add(id(item))
    return selected


def safe_merchant_context_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    blocked_fragments = {
        "landing_page_error",
        "shopping_ads",
        "merchant_action",
        "free_listings",
        "n_link",
    }
    lowered = value.lower()
    if any(fragment in lowered for fragment in blocked_fragments):
        return None
    return value


def compact_merchant_issue_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "operation_type",
        "country",
        "metric_snapshot",
        "sample_products_available",
        "sample_unavailable_reason",
        "reason",
        "required_validation_labels",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:4]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        compact_item["issue_summary"] = context_compaction.context_pack_text(
            item.get("reason"), limit=180
        )
        required_validation = compact_item.get("required_validation_labels")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation_labels"] = required_validation[:4]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:5]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:3]
        compact_items.append(compact_item)
    return compact_items


def compact_merchant_price_impact_preview_for_context(
    preview: dict[str, Any],
) -> dict[str, Any]:
    compact = {
        "preview_contract": preview.get("preview_contract"),
        "preview_contract_label": preview.get("preview_contract_label"),
        "reason": context_compaction.context_pack_text(preview.get("reason"), limit=180),
        "api_mutation_ready": preview.get("api_mutation_ready"),
        "apply_allowed": preview.get("apply_allowed"),
        "destructive": preview.get("destructive"),
    }
    products = preview.get("products")
    compact["products_total"] = len(products) if isinstance(products, list) else 0
    missing_read_contracts = preview.get("missing_read_contracts")
    if isinstance(missing_read_contracts, list):
        compact["missing_read_contracts_total"] = len(missing_read_contracts)
    required_validation = preview.get("required_validation_labels")
    if isinstance(required_validation, list):
        compact["required_validation_total"] = len(required_validation)
        compact["required_validation_labels"] = required_validation[:4]
    blocked_claims = preview.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact["blocked_claims"] = blocked_claims[:5]
    evidence_ids = preview.get("evidence_ids")
    if isinstance(evidence_ids, list):
        compact["evidence_ids"] = evidence_ids[:3]
    return compact
