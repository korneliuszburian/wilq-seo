from __future__ import annotations

import json
from typing import Any


def validate_ahrefs_contract(
    pack: dict[str, Any],
) -> tuple[
    dict[str, Any], dict[str, Any], set[str], list[dict[str, Any]], int, list[str], list[str]
]:
    diagnostics = _diagnostics(pack)
    decisions = _decision_ids(diagnostics)
    gap = _gap_contract(diagnostics, decisions)
    records, record_count = _records(gap)
    states, labels = _freshness(records)
    _lineage_guard(diagnostics)
    return diagnostics, gap, decisions, records, record_count, states, labels


def _diagnostics(pack: dict[str, Any]) -> dict[str, Any]:
    diagnostics = pack.get("ahrefs_diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit("Context pack ahrefs_diagnostics must be an object")
    if diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ahrefs diagnostics must use pl-PL language contract")
    summary = diagnostics.get("operator_summary") or {}
    if not isinstance(summary, dict):
        raise SystemExit("Ahrefs diagnostics operator_summary must be an object")
    if summary.get("review_card_label") != "Karta review Ahrefs":
        raise SystemExit("Ahrefs diagnostics must expose review_card_label")
    required = (
        "review_decision_after_review",
        "review_question_for_operator",
        "review_next_safe_click",
    )
    if any(not summary.get(field) for field in required):
        raise SystemExit("Ahrefs diagnostics must expose review card fields")
    if not isinstance(summary.get("review_action_ids"), list):
        raise SystemExit("Ahrefs diagnostics must expose review_action_ids")
    return diagnostics


def _decision_ids(diagnostics: dict[str, Any]) -> set[str]:
    decisions = {
        item.get("id")
        for item in diagnostics.get("decision_queue", [])
        if isinstance(item, dict) and item.get("id")
    }
    if not decisions:
        raise SystemExit("Ahrefs diagnostics must expose a decision_queue")
    return decisions


def _gap_contract(diagnostics: dict[str, Any], decisions: set[str]) -> dict[str, Any]:
    gap = diagnostics.get("gap_read_contract") or {}
    if not isinstance(gap, dict):
        raise SystemExit("Ahrefs diagnostics gap_read_contract must be an object")
    missing = gap.get("missing_read_contracts") or []
    missing_count = gap.get("missing_read_contracts_total")
    missing_count = missing_count if isinstance(missing_count, int) else len(missing)
    record_count = gap.get("gap_record_count")
    record_count = (
        record_count if isinstance(record_count, int) else len(gap.get("gap_records") or [])
    )
    if record_count and "ahrefs_review_gap_records" not in decisions:
        raise SystemExit("Ahrefs diagnostics must expose gap review decision")
    if missing_count and "ahrefs_block_gap_claims_without_records" not in decisions:
        raise SystemExit("Ahrefs diagnostics must block gap claims when contracts are missing")
    if not missing_count and gap.get("status") != "ready":
        raise SystemExit(
            "Ahrefs diagnostics gap contract must be ready when no contracts are missing"
        )
    if not missing_count and "ahrefs_review_gap_records" not in decisions:
        raise SystemExit("Ahrefs diagnostics must expose ready gap review decision")
    status = gap.get("cross_check_status")
    if status not in {"api_backed", "manual_required", "missing"}:
        raise SystemExit("Ahrefs diagnostics must expose cross_check_status")
    if not gap.get("cross_check_summary") or not gap.get("cross_check_next_step"):
        raise SystemExit("Ahrefs diagnostics must expose cross-check summary and next step")
    if record_count and not isinstance(gap.get("cross_check_candidates_total"), int):
        raise SystemExit("Ahrefs context pack must expose cross_check_candidates_total")
    return gap


def _records(gap: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    records = gap.get("gap_records") or []
    count = gap.get("gap_record_count")
    return records, count if isinstance(count, int) else len(records)


def _freshness(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    states = sorted(
        {
            str(fact.get("freshness_state"))
            for record in records
            if isinstance(record, dict)
            for fact in record.get("metric_facts", [])
            if isinstance(fact, dict) and fact.get("freshness_state")
        }
    )
    labels = sorted(
        {
            str(fact.get("freshness_label"))
            for record in records
            if isinstance(record, dict)
            for fact in record.get("metric_facts", [])
            if isinstance(fact, dict) and fact.get("freshness_label")
        }
    )
    if records and not states:
        raise SystemExit("Ahrefs gap data must expose freshness_state")
    return states, labels


def _lineage_guard(diagnostics: dict[str, Any]) -> None:
    serialized = json.dumps(diagnostics, ensure_ascii=False)
    for term in ("evidence_ids", "missing_read_contracts", "blocked_claims"):
        if term not in serialized:
            raise SystemExit(f"Ahrefs diagnostics missing {term}")
