from __future__ import annotations

import json
from typing import Any

LINKEDIN_URL = "https://www.linkedin.com/company/ekologus-esg-eko-audyt-ochrona-srodowiska-dokumentacje-srodowiskowe-szkolenia-sorbenty/posts/?feedView=all"
FACEBOOK_URL = "https://www.facebook.com/ekologus/?locale=pl_PL"


def validate_social_context(pack: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    context = pack.get("social_draft_context")
    if (
        not isinstance(context, dict)
        or context.get("mode") != "review_only"
        or context.get("publish_allowed") is not False
    ):
        raise SystemExit("Social draft context must remain review_only with publish disabled")
    inventory = context.get("social_history_inventory")
    if not isinstance(inventory, dict):
        raise SystemExit("Social draft context missing social_history_inventory")
    if (
        context.get("historical_social_inventory_status") != "missing"
        or context.get("duplicate_risk_status") != "blocked_until_social_history_review"
    ):
        raise SystemExit(
            "Social draft context must block duplicate-free claims until history review"
        )
    if not context.get("missing_publish_access") or "brak powtórzeń historycznych postów" not in (
        context.get("blocked_claims") or []
    ):
        raise SystemExit("Social draft context must expose publish/history blockers")
    _validate_inventory(inventory)
    return context, inventory


def _validate_inventory(inventory: dict[str, Any]) -> None:
    if (
        inventory.get("contract") != "social_history_inventory_v1"
        or inventory.get("read_only") is not True
        or inventory.get("status") != "missing"
    ):
        raise SystemExit("Social history inventory must be versioned, read-only and missing")
    if inventory.get("required_sources") != ["linkedin", "facebook"]:
        raise SystemExit("Social history inventory must require LinkedIn and Facebook")
    sources = inventory.get("sources") or []
    if {source.get("channel") for source in sources} != {"linkedin", "facebook"}:
        raise SystemExit("Social history inventory must expose channel requirements")
    fields = {field for source in sources for field in source.get("required_metadata_fields", [])}
    required = {
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id",
    }
    if not required.issubset(fields) or any(
        source.get("raw_post_body_allowed") for source in sources
    ):
        raise SystemExit("Social history inventory must expose metadata-only fields")
    statuses = {source.get("connector_access_status") for source in sources}
    if statuses & {None, "[REDACTED]"} or any("credential_status" in source for source in sources):
        raise SystemExit("Social history inventory must expose non-secret access status")
    template = inventory.get("input_template")
    if not isinstance(template, dict) or template.get("contract") != "social_history_inventory_v1":
        raise SystemExit("Social history input_template must keep the versioned contract")
    if {item.get("channel") for item in template.get("items", []) if isinstance(item, dict)} != {
        "linkedin",
        "facebook",
    }:
        raise SystemExit("Social history input_template must include both channels")
    forbidden = {"raw_post_body", "post_body", "comments", "comment_text", "access_token"}
    if forbidden & set(
        json.dumps(template, ensure_ascii=False).split('"')
    ) or "metadata-only" not in str(template.get("_instruction") or ""):
        raise SystemExit("Social history input_template must avoid raw/private fields")
    _validate_seeds(inventory)


def _validate_seeds(inventory: dict[str, Any]) -> None:
    seeds = {
        str(seed.get("channel")): seed
        for seed in inventory.get("discovery_seeds", [])
        if isinstance(seed, dict)
    }
    for channel, url in {"linkedin": LINKEDIN_URL, "facebook": FACEBOOK_URL}.items():
        seed = seeds.get(channel)
        if (
            not seed
            or seed.get("source_url") != url
            or seed.get("safe_collection_mode") != "metadata_only"
            or seed.get("raw_post_body_allowed") is not False
        ):
            raise SystemExit(f"{channel} discovery seed must remain public metadata_only")
