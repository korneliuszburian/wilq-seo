from __future__ import annotations

from typing import Any


def validate_gsc_context_parity(
    pack: dict[str, Any], content_diagnostics: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    packed = pack.get("content_diagnostics", {})
    packed_evidence_ids = packed.get("evidence_ids") or []
    endpoint_evidence_ids = content_diagnostics.get("evidence_ids") or []
    if not set(packed_evidence_ids).issubset(set(endpoint_evidence_ids)):
        raise SystemExit("Context pack content_diagnostics evidence IDs are not endpoint subset")
    if any("_ahrefs" in str(evidence_id) for evidence_id in packed_evidence_ids):
        raise SystemExit("GSC context pack must not include Ahrefs evidence IDs")
    if packed.get("action_ids") != content_diagnostics.get("action_ids"):
        raise SystemExit("Context pack content_diagnostics action IDs differ from endpoint")
    packed_trace = _decision_trace(packed.get("decision_queue"))
    endpoint_trace = _decision_trace(content_diagnostics.get("decision_queue"))
    if not packed_trace:
        raise SystemExit("GSC context pack must expose scoped content decisions")
    endpoint_ids = {str(item.get("id")) for item in endpoint_trace}
    if any(str(item.get("id")) not in endpoint_ids for item in packed_trace):
        raise SystemExit("GSC context pack decision_queue must be endpoint subset")
    if any(
        item.get("decision_type") == "review_ahrefs_gap_records"
        or "ahrefs" in item.get("source_connectors", [])
        for item in packed_trace
    ):
        raise SystemExit("GSC context pack must not include Ahrefs decisions")
    compaction = packed.get("context_pack_compaction") or {}
    if compaction.get("purpose") != "gsc_content_doctor_context":
        raise SystemExit("GSC context pack compaction purpose is missing")
    if compaction.get("ahrefs_decisions_removed") is not True:
        raise SystemExit("GSC context pack must mark removed Ahrefs decisions")
    return packed, packed_trace, endpoint_trace


def _decision_trace(decisions: Any) -> list[dict[str, Any]]:
    if not isinstance(decisions, list):
        return []
    return [
        {
            "id": item.get("id"),
            "decision_type": item.get("decision_type"),
            "page": item.get("page"),
            "normalized_page_path": item.get("normalized_page_path"),
            "queries": item.get("queries", []),
            "wordpress_match": item.get("wordpress_match"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
        }
        for item in decisions
        if isinstance(item, dict)
    ]
