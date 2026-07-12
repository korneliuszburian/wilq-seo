from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction


def compact_ahrefs_diagnostics_for_context(
    ahrefs_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(context_compaction.without_metric_facts(ahrefs_diagnostics))
    sections = compact.pop("sections", [])
    connector = compact.get("connector")
    if isinstance(connector, dict):
        compact["connector"] = context_compaction.compact_connector_status_for_operator_context(
            connector
        )
    connector_status = compact.get("connector_status")
    if isinstance(connector_status, dict):
        compact["connector_status"] = (
            context_compaction.compact_connector_status_for_operator_context(
                connector_status
            )
        )
    latest_refresh = compact.get("latest_refresh")
    if isinstance(latest_refresh, dict):
        compact["latest_refresh"] = context_compaction.compact_refresh_run_for_operator_context(
            latest_refresh
        )
    gap_contract = compact.get("gap_read_contract")
    if isinstance(gap_contract, dict):
        context_compaction.compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="available_read_contracts",
            label_key="available_read_contract_labels",
        )
        context_compaction.compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="allowed_evidence",
            label_key="allowed_evidence_labels",
        )
        context_compaction.compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="missing_read_contracts",
            label_key="missing_read_contract_labels",
        )
        gap_records = gap_contract.pop("gap_records", [])
        gap_record_count = gap_contract.get("gap_record_count")
        if gap_record_count is None:
            gap_contract["gap_record_count"] = (
                len(gap_records) if isinstance(gap_records, list) else 0
            )
        cross_check_candidates = gap_contract.get("cross_check_candidates")
        if isinstance(cross_check_candidates, list):
            gap_contract["cross_check_candidates_total"] = len(cross_check_candidates)
            gap_contract["cross_check_candidates"] = [
                compact_ahrefs_cross_check_candidate_for_context(candidate)
                for candidate in cross_check_candidates[:4]
                if isinstance(candidate, dict)
            ]
            gap_contract["cross_check_candidates_included"] = len(
                gap_contract["cross_check_candidates"]
            )
        gap_contract["gap_records_omitted"] = True
        gap_contract["gap_records_total"] = len(gap_records) if isinstance(gap_records, list) else 0
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        context_compaction.compact_labelled_contract_list_for_context(
            operator_summary,
            raw_key="available_read_contracts",
            label_key="available_read_contract_labels",
        )
        context_compaction.compact_labelled_contract_list_for_context(
            operator_summary,
            raw_key="missing_read_contracts",
            label_key="missing_read_contract_labels",
        )
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            compact_ahrefs_decision_for_context(decision)
            for decision in decision_queue
            if isinstance(decision, dict)
        ]
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "latest_refresh_compacted": isinstance(latest_refresh, dict),
        "gap_records_omitted": isinstance(gap_contract, dict),
        "full_endpoint": "/api/ahrefs/diagnostics",
    }
    return compact


def compact_ahrefs_cross_check_candidate_for_context(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    compact = {
        key: candidate[key]
        for key in (
            "topic",
            "gap_type_label",
            "relevance_status_label",
            "gsc_demand_label",
            "gsc_cross_check",
            "wordpress_inventory_match_label",
            "wordpress_cross_check",
            "gsc_overlap_terms",
            "wordpress_overlap_urls",
            "source_connectors",
            "next_step",
            "evidence_ids",
        )
        if key in candidate
    }
    for key in ("gsc_cross_check", "wordpress_cross_check"):
        if key in compact:
            compact[key] = context_compaction.compact_ahrefs_cross_check_for_context(compact[key])
    for key, limit in (("source_connectors", 3), ("evidence_ids", 3)):
        value = compact.get(key)
        if isinstance(value, list):
            compact[key] = value[:limit]
            compact[f"{key}_total"] = len(value)
    return compact


def compact_ahrefs_decision_for_context(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    context_compaction.compact_labelled_contract_list_for_context(
        compact,
        raw_key="allowed_evidence",
        label_key="allowed_evidence_labels",
    )
    context_compaction.compact_labelled_contract_list_for_context(
        compact,
        raw_key="missing_read_contracts",
        label_key="missing_read_contract_labels",
    )
    metric_fact_labels = compact.get("metric_fact_labels")
    if isinstance(metric_fact_labels, dict):
        labels = list(metric_fact_labels.values())
        compact["metric_fact_labels_total"] = len(labels)
        compact["metric_fact_labels"] = labels[:8]
        compact["metric_fact_labels_included"] = len(compact["metric_fact_labels"])
    return compact
