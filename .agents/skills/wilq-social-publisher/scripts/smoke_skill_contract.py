#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-social-publisher"
REQUIRED_CONNECTORS = ["linkedin", "facebook"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
}
CORE_SOCIAL_ACTION_IDS = {
    "act_prepare_facebook_social_drafts",
    "act_prepare_linkedin_social_drafts",
}
EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL = (
    "https://www.linkedin.com/company/"
    "ekologus-esg-eko-audyt-ochrona-srodowiska-dokumentacje-srodowiskowe-"
    "szkolenia-sorbenty/posts/?feedView=all"
)


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

    social_draft_context = pack.get("social_draft_context")
    if not isinstance(social_draft_context, dict):
        raise SystemExit("Context pack missing social_draft_context")
    if social_draft_context.get("mode") != "review_only":
        raise SystemExit("Social draft context must be review_only")
    if social_draft_context.get("publish_allowed") is not False:
        raise SystemExit("Social draft context must keep publish_allowed=false")
    source_inputs = social_draft_context.get("source_inputs") or []
    draft_action_ids = set(social_draft_context.get("draft_action_ids") or [])
    pack_action_ids = {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    active_social_action_ids = CORE_SOCIAL_ACTION_IDS & pack_action_ids
    if (draft_action_ids or active_social_action_ids) and not source_inputs:
        raise SystemExit("Social draft context must expose source_inputs")
    if not social_draft_context.get("missing_publish_access"):
        raise SystemExit("Social draft context must expose missing publish access blockers")
    if social_draft_context.get("historical_social_inventory_status") != "missing":
        raise SystemExit("Social draft context must expose missing historical social inventory")
    if social_draft_context.get("duplicate_risk_status") != "blocked_until_social_history_review":
        raise SystemExit("Social draft context must block duplicate-free social claims")
    if social_draft_context.get("history_audit_endpoint") != (
        "/api/social/history-inventory/audit"
    ):
        raise SystemExit("Social draft context must expose social history audit endpoint")
    if social_draft_context.get("history_audit_contract") != "social_history_inventory_v1":
        raise SystemExit("Social draft context must expose social history audit contract")
    if "brak powtórzeń historycznych postów" not in (
        social_draft_context.get("blocked_claims") or []
    ):
        raise SystemExit("Social draft context must block historical duplicate-free claims")
    social_history_inventory = social_draft_context.get("social_history_inventory")
    if not isinstance(social_history_inventory, dict):
        raise SystemExit("Social draft context missing social_history_inventory")
    if social_history_inventory.get("contract") != "social_history_inventory_v1":
        raise SystemExit("Social history inventory contract must be versioned")
    if social_history_inventory.get("read_only") is not True:
        raise SystemExit("Social history inventory must be read-only")
    if social_history_inventory.get("status") != "missing":
        raise SystemExit("Social history inventory must expose missing status")
    if social_history_inventory.get("required_sources") != ["linkedin", "facebook"]:
        raise SystemExit("Social history inventory must require LinkedIn and Facebook")
    sources = social_history_inventory.get("sources") or []
    if {source.get("channel") for source in sources} != {"linkedin", "facebook"}:
        raise SystemExit("Social history inventory must expose channel requirements")
    required_metadata_fields = {
        field for source in sources for field in source.get("required_metadata_fields", [])
    }
    if not {
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id",
    }.issubset(required_metadata_fields):
        raise SystemExit("Social history inventory must expose metadata-only fields")
    if any(source.get("raw_post_body_allowed") for source in sources):
        raise SystemExit("Social history inventory must not require raw post bodies")
    access_statuses = {source.get("connector_access_status") for source in sources}
    if "[REDACTED]" in access_statuses or None in access_statuses:
        raise SystemExit("Social history inventory must expose non-secret access status")
    if any("credential_status" in source for source in sources):
        raise SystemExit("Social history inventory must avoid redacted credential_status key")
    _assert_public_discovery_seed(social_history_inventory)

    direct_inventory = request_json(args.api_base, "GET", "/api/social/history-inventory")
    if direct_inventory.get("contract") != "social_history_inventory_v1":
        raise SystemExit("Direct social history endpoint must expose the versioned contract")
    _assert_public_discovery_seed(direct_inventory)

    action_validations = validate_core_social_actions(args.api_base, pack)

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "brief_items": brief_items,
                "brief_item_count": len(brief_items),
                "brief_item_ids": [item.get("id") for item in brief_items[:8]],
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
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
                "social_draft_context": {
                    "mode": social_draft_context.get("mode"),
                    "publish_allowed": social_draft_context.get("publish_allowed"),
                    "missing_publish_access": social_draft_context.get("missing_publish_access"),
                    "historical_social_inventory_status": social_draft_context.get(
                        "historical_social_inventory_status"
                    ),
                    "duplicate_risk_status": social_draft_context.get(
                        "duplicate_risk_status"
                    ),
                    "missing_history_evidence": social_draft_context.get(
                        "missing_history_evidence"
                    ),
                    "history_audit_endpoint": social_draft_context.get(
                        "history_audit_endpoint"
                    ),
                    "history_audit_contract": social_draft_context.get(
                        "history_audit_contract"
                    ),
                    "social_history_inventory": social_history_inventory,
                    "direct_inventory_seed_count": len(
                        direct_inventory.get("discovery_seeds") or []
                    ),
                    "source_input_count": len(social_draft_context.get("source_inputs", [])),
                    "source_inputs": social_draft_context.get("source_inputs", [])[:4],
                    "draft_action_ids": social_draft_context.get("draft_action_ids", []),
                    "draft_constraints": social_draft_context.get("draft_constraints", []),
                    "blocked_claims": social_draft_context.get("blocked_claims", []),
                    "operator_next_step": social_draft_context.get("operator_next_step"),
                },
                "action_validations": action_validations,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def validate_core_social_actions(api_base: str, pack: dict[str, Any]) -> list[dict[str, Any]]:
    pack_action_ids = {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    action_validations = []
    available_action_ids = sorted(CORE_SOCIAL_ACTION_IDS & pack_action_ids)
    for action_id in available_action_ids:
        quoted_action = urllib.parse.quote(action_id, safe="")
        validation = request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Social action validation failed: {validation}")
    return action_validations


def _assert_public_discovery_seed(inventory: dict[str, Any]) -> None:
    seeds = inventory.get("discovery_seeds")
    if not isinstance(seeds, list) or not seeds:
        raise SystemExit("Social history inventory must expose public discovery seeds")
    linkedin_seed = next(
        (seed for seed in seeds if seed.get("channel") == "linkedin"),
        None,
    )
    if not isinstance(linkedin_seed, dict):
        raise SystemExit("Social history inventory must expose a LinkedIn discovery seed")
    if linkedin_seed.get("source_url") != EKOLOGUS_LINKEDIN_PUBLIC_POSTS_URL:
        raise SystemExit("LinkedIn discovery seed URL does not match the public Ekologus posts URL")
    if linkedin_seed.get("safe_collection_mode") != "metadata_only":
        raise SystemExit("LinkedIn discovery seed must remain metadata_only")
    if linkedin_seed.get("raw_post_body_allowed") is not False:
        raise SystemExit("LinkedIn discovery seed must not allow raw post bodies")


if __name__ == "__main__":
    raise SystemExit(main())
