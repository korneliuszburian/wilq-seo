from __future__ import annotations

import json
from typing import Any


def validate_readiness(
    pack: dict[str, Any], action_id: str, preview_contract: str
) -> tuple[
    dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]
]:
    readiness = pack.get("demand_gen_readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("Context pack demand_gen_readiness must be an object")
    _validate_contract_lists(readiness)
    missing = readiness["missing_read_contracts"]
    available = readiness["available_read_contracts"]
    rows = _validate_rows(readiness, missing)
    tiles = readiness.get("metric_tiles")
    campaigns = readiness.get("campaign_rows_evaluated")
    channels = readiness.get("campaign_channel_counts")
    if (
        not isinstance(tiles, dict)
        or not isinstance(campaigns, int)
        or not isinstance(channels, dict)
    ):
        raise SystemExit("Demand Gen readiness metric fields must be typed")
    if readiness.get("status") != "blocked" or not str(readiness.get("title", "")).startswith(
        "Demand Gen:"
    ):
        raise SystemExit("Demand Gen must stay blocked with marketer-facing title")
    if tiles.get("kampanie Ads") != campaigns or tiles.get("braki") != len(missing):
        raise SystemExit("Demand Gen metric tiles must include campaign and missing counts")
    if campaigns > 0 and (not channels or "demand_gen_campaign_rows" in missing):
        raise SystemExit("Demand Gen campaign channel readiness is inconsistent")
    payload = readiness.get("payload_preview")
    if (
        not isinstance(payload, list)
        or not payload
        or payload[0].get("preview_contract") != preview_contract
    ):
        raise SystemExit("Demand Gen readiness change preview uses wrong contract")
    if payload[0].get("api_mutation_ready") is not False or "[REDACTED]" in json.dumps(readiness):
        raise SystemExit("Demand Gen readiness preview must be validation-only and traceable")
    active = pack.get("active_action_objects") or []
    if [item.get("id") for item in active] != [action_id]:
        raise SystemExit("Demand Gen context must expose only its review action")
    preview = (active[0].get("action_plan") or {}).get("preview_items") or []
    if (
        not preview
        or preview[0].get("apply_status_label") != "zablokowane do sprawdzenia"
        or preview[0].get("write_status_label") != "bez zapisu automatycznego"
    ):
        raise SystemExit("Demand Gen action plan must keep apply and write disabled")
    return (
        readiness,
        tiles,
        rows,
        active[0],
        {"available": available, "missing": missing, "campaigns": campaigns, "channels": channels},
    )


def _validate_contract_lists(readiness: dict[str, Any]) -> None:
    missing = readiness.get("missing_read_contracts")
    available = readiness.get("available_read_contracts")
    if not isinstance(missing, list) or not isinstance(available, list):
        raise SystemExit("Demand Gen readiness must expose read contract lists")
    if "demand_gen_asset_group_rows" in missing:
        raise SystemExit("Demand Gen readiness must not use obsolete asset group rows contract")
    contracts = (
        "demand_gen_ad_group_ad_rows",
        "demand_gen_creative_asset_rows",
        "demand_gen_landing_quality_by_campaign",
        "demand_gen_campaign_mode_review",
    )
    for contract in contracts:
        if (contract in missing) == (contract in available):
            raise SystemExit(f"Demand Gen contract {contract} must be either available or missing")


def _validate_rows(readiness: dict[str, Any], missing: list[str]) -> list[dict[str, Any]]:
    fields = (
        "demand_gen_campaign_rows",
        "demand_gen_ad_group_ad_rows",
        "demand_gen_creative_asset_rows",
        "demand_gen_landing_quality_rows",
        "demand_gen_campaign_mode_review_rows",
    )
    rows = []
    for field in fields:
        value = readiness.get(field)
        if not isinstance(value, list):
            raise SystemExit(f"Demand Gen readiness must expose {field} list")
        rows.append(value)
    return rows
