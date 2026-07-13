from __future__ import annotations

from typing import Any


def validate_campaign_contract(
    campaign: dict[str, Any],
    triage: dict[str, Any],
    diagnostics: dict[str, Any],
    pack: dict[str, Any],
) -> None:
    if (
        campaign.get("status") == "ready"
        and campaign.get("campaign_rows")
        and "act_prepare_ads_campaign_review_queue" not in (diagnostics.get("action_ids") or [])
    ):
        raise SystemExit("Ready campaign diagnostics must expose campaign review action")
    if campaign.get("status") != "ready" or not campaign.get("campaign_rows"):
        return
    if triage.get("status") != "ready":
        raise SystemExit("Ready campaign diagnostics must expose campaign triage contract")
    if not triage.get("triage_rows"):
        raise SystemExit("Ready campaign triage contract must expose triage rows")
    if "zmarnowany budżet" not in triage.get("blocked_claims", []):
        raise SystemExit("Campaign triage contract must keep zmarnowany budżet blocked")
    packed = pack.get("ads_diagnostics", {}).get("campaign_triage_read_contract") or {}
    if packed.get("summary") != triage.get("summary"):
        raise SystemExit("Context pack campaign triage contract differs")
    if not packed.get("triage_rows"):
        raise SystemExit("Context pack must include campaign triage rows")
    if "act_prepare_ads_campaign_review_queue" not in (triage.get("action_ids") or []):
        raise SystemExit("Campaign triage contract must expose campaign review action")
