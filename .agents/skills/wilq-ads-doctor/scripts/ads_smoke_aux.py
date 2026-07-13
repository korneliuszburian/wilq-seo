from __future__ import annotations

from typing import Any

from ads_report_compaction import compact_ads_brief_items, compact_connector_statuses

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, validate_action_ids


def validate_auxiliary_contracts(
    api_base: str,
    pack: dict[str, Any],
    diagnostics: dict[str, Any],
    required_connectors: list[str],
    validated_action_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    action_ids = diagnostics.get("action_ids") or []
    if diagnostics.get("live_data_available") is True:
        missing = sorted(set(validated_action_ids) - set(action_ids))
        if missing:
            raise SystemExit(
                "Live Ads diagnostics must expose review actions for validation: "
                + ", ".join(missing)
            )
    validations = validate_action_ids(
        api_base,
        [action_id for action_id in validated_action_ids if action_id in action_ids],
        label="Ads",
    )
    if not has_polish_metric_source_guardrails(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    return (
        validations,
        compact_ads_brief_items(api_base, required_connectors),
        compact_connector_statuses(api_base, required_connectors),
    )
