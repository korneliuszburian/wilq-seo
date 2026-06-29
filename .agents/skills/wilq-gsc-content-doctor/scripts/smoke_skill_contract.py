#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-gsc-content-doctor"
REQUIRED_CONNECTORS = ["google_search_console", "wordpress_ekologus", "wordpress_sklep"]
CONTENT_ACTION_ID = "act_prepare_content_refresh_queue"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "content_diagnostics",
}


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc



def has_polish_metric_source_guardrails(value: str) -> bool:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized

def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    content_diagnostics = request_json(args.api_base, "GET", "/api/content/diagnostics")
    if content_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Content diagnostics language must be pl-PL")
    sections = content_diagnostics.get("sections")
    if not isinstance(sections, list) or not sections:
        raise SystemExit("Content diagnostics must expose sections")
    decision_queue = content_diagnostics.get("decision_queue")
    if not isinstance(decision_queue, list):
        raise SystemExit("Content diagnostics must expose decision_queue")
    packed_content = pack.get("content_diagnostics", {})
    packed_evidence_ids = packed_content.get("evidence_ids") or []
    endpoint_evidence_ids = content_diagnostics.get("evidence_ids") or []
    if not set(packed_evidence_ids).issubset(set(endpoint_evidence_ids)):
        raise SystemExit("Context pack content_diagnostics evidence IDs are not endpoint subset")
    if any("_ahrefs" in str(evidence_id) for evidence_id in packed_evidence_ids):
        raise SystemExit("GSC context pack must not include Ahrefs evidence IDs")
    if packed_content.get("action_ids") != content_diagnostics.get("action_ids"):
        raise SystemExit("Context pack content_diagnostics action IDs differ from endpoint")
    packed_decision_trace = _decision_trace(packed_content.get("decision_queue"))
    endpoint_decision_trace = _decision_trace(content_diagnostics.get("decision_queue"))
    if not packed_decision_trace:
        raise SystemExit("GSC context pack must expose scoped content decisions")
    endpoint_decision_ids = {str(item.get("id")) for item in endpoint_decision_trace}
    if any(str(item.get("id")) not in endpoint_decision_ids for item in packed_decision_trace):
        raise SystemExit("GSC context pack decision_queue must be endpoint subset")
    if any(
        item.get("decision_type") == "review_ahrefs_gap_records"
        or "ahrefs" in item.get("source_connectors", [])
        for item in packed_decision_trace
    ):
        raise SystemExit("GSC context pack must not include Ahrefs decisions")
    compaction = packed_content.get("context_pack_compaction") or {}
    if compaction.get("purpose") != "gsc_content_doctor_context":
        raise SystemExit("GSC context pack compaction purpose is missing")
    if compaction.get("ahrefs_decisions_removed") is not True:
        raise SystemExit("GSC context pack must mark removed Ahrefs decisions")

    gsc_metric_facts = request_json(
        args.api_base,
        "GET",
        "/api/metrics?connector_id=google_search_console&limit=2000",
    )
    gsc_query_page_fact_count = sum(
        1
        for fact in gsc_metric_facts
        if {"query", "page"}.issubset(set((fact.get("dimensions") or {}).keys()))
    )
    if gsc_query_page_fact_count:
        if not content_diagnostics.get("query_page_count"):
            raise SystemExit(
                "GSC query/page metric facts exist but content diagnostics has query_page_count=0"
            )
        if not decision_queue:
            raise SystemExit(
                "GSC query/page metric facts exist but content diagnostics has no decision_queue"
            )
        decision_types = {
            item.get("decision_type") for item in decision_queue if item.get("decision_type")
        }
        content_decision_types = {
            "refresh_or_merge",
            "merge_create_after_inventory_check",
            "inventory_check_before_create",
        }
        if not decision_types.intersection(content_decision_types):
            raise SystemExit(
                "Content diagnostics decision_queue must contain concrete "
                "refresh/merge/create inventory decisions"
            )
        if not any(item.get("page") and item.get("queries") for item in decision_queue):
            raise SystemExit("Content decisions must include concrete page and query values")

    action_ids = content_diagnostics.get("action_ids") or []
    if (
        content_diagnostics.get("live_data_available") is True
        and CONTENT_ACTION_ID not in action_ids
    ):
        raise SystemExit("Live GSC content diagnostics must expose content refresh action")
    action_validations = []
    if CONTENT_ACTION_ID in action_ids:
        quoted_action = urllib.parse.quote(CONTENT_ACTION_ID, safe="")
        validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"GSC content action validation failed: {validation}")

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "kind": item.get("kind"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
            "metric_facts": item.get("metric_facts", []),
        }
        for section in brief.get("sections", [])
        for item in section.get("items", [])
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ][:8]

    connector_results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(args.api_base, "GET", f"/api/connectors/{quoted}/status")
        connector_results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "action_validations": action_validations,
                "content_diagnostics": {
                    "live_data_available": content_diagnostics.get("live_data_available"),
                    "query_page_count": content_diagnostics.get("query_page_count"),
                    "matched_inventory_count": content_diagnostics.get("matched_inventory_count"),
                    "decision_count": len(decision_queue),
                    "decision_types": sorted(
                        str(item.get("decision_type"))
                        for item in decision_queue
                        if item.get("decision_type")
                    ),
                    "top_decisions": [
                        {
                            "id": item.get("id"),
                            "decision_type": item.get("decision_type"),
                            "page": item.get("page"),
                            "queries": item.get("queries", [])[:4],
                            "wordpress_match": item.get("wordpress_match"),
                        }
                        for item in decision_queue[:5]
                    ],
                    "context_pack_decision_count": len(packed_decision_trace),
                    "context_pack_decision_types": sorted(
                        str(item.get("decision_type"))
                        for item in packed_decision_trace
                        if item.get("decision_type")
                    ),
                    "context_pack_top_decisions": [
                        {
                            "id": item.get("id"),
                            "decision_type": item.get("decision_type"),
                            "page": item.get("page"),
                            "queries": item.get("queries", [])[:4],
                            "source_connectors": item.get("source_connectors", []),
                        }
                        for item in packed_decision_trace[:5]
                    ],
                    "context_pack_has_ahrefs_evidence": any(
                        "_ahrefs" in str(evidence_id) for evidence_id in packed_evidence_ids
                    ),
                    "gsc_query_page_metric_fact_count": gsc_query_page_fact_count,
                    "blocker_count": content_diagnostics.get("blocker_count"),
                    "section_ids": [
                        section.get("id") for section in content_diagnostics.get("sections", [])
                    ],
                    "evidence_ids": content_diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": content_diagnostics.get("action_ids", []),
                    "tactical_item_ids": [
                        item.get("id")
                        for section in content_diagnostics.get("sections", [])
                        for item in section.get("tactical_items", [])
                        if item.get("id")
                    ][:20],
                    "blocked_claims": [
                        claim
                        for section in content_diagnostics.get("sections", [])
                        for claim in section.get("blocked_claims", [])
                    ][:20],
                },
                "evidence_ids": [
                    item.get("id")
                    for item in (pack.get("evidence_summaries") or [])
                    if item.get("id")
                ][:20],
                "opportunity_ids": [
                    item.get("id")
                    for item in (pack.get("top_opportunities") or [])
                    if item.get("id")
                ][:20],
                "action_ids": [
                    item.get("id")
                    for item in (pack.get("active_action_objects") or [])
                    if item.get("id")
                ][:20],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
