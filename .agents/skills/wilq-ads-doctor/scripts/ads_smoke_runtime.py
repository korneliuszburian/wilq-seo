from __future__ import annotations

import json
from typing import Any

from scripts.skill_smoke_harness import request_json


def load_ads_context(
    api_base: str,
    *,
    required_context_keys: set[str],
    max_context_pack_bytes: int,
) -> dict[str, Any]:
    health = request_json(api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")
    pack = request_json(api_base, "POST", "/api/codex/context-pack", {"skill": "wilq-ads-doctor"})
    pack_bytes = len(json.dumps(pack, ensure_ascii=False).encode())
    if pack_bytes >= max_context_pack_bytes:
        raise SystemExit(f"wilq-ads-doctor context-pack exceeds budget: {pack_bytes} bytes")
    missing = sorted(required_context_keys - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")
    ads_diagnostics = request_json(api_base, "GET", "/api/ads/diagnostics")
    full_pack = request_json(
        api_base,
        "POST",
        "/api/codex/context-pack",
        {"skill": "wilq-ads-doctor", "full_context": True},
    )
    _validate_diagnostics_baseline(pack, ads_diagnostics)
    return {
        "health": health,
        "pack": pack,
        "ads_diagnostics": ads_diagnostics,
        "full_pack": full_pack,
        "pack_bytes": pack_bytes,
        "blocked_handoff": ads_diagnostics.get("blocked_handoff"),
    }


def _validate_diagnostics_baseline(pack: dict[str, Any], ads_diagnostics: dict[str, Any]) -> None:
    if ads_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ads diagnostics language must be pl-PL")
    if not isinstance(ads_diagnostics.get("sections"), list) or not ads_diagnostics["sections"]:
        raise SystemExit("Ads diagnostics must expose sections")
    packed = pack.get("ads_diagnostics", {})
    if packed.get("evidence_ids") != ads_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack ads_diagnostics evidence IDs differ from endpoint")
    if packed.get("action_ids") != ads_diagnostics.get("action_ids"):
        raise SystemExit("Context pack ads_diagnostics action IDs differ from endpoint")
    blocked_handoff = ads_diagnostics.get("blocked_handoff")
    if ads_diagnostics.get("live_data_available") is True:
        if blocked_handoff is not None:
            raise SystemExit("Live Ads diagnostics must not expose OAuth blocked_handoff")
        return
    if not isinstance(blocked_handoff, dict) or blocked_handoff.get("status") != "blocked":
        raise SystemExit("Blocked Ads diagnostics must expose blocked handoff")
    if "google_ads" not in blocked_handoff.get("source_connectors", []):
        raise SystemExit("Ads blocked_handoff must include google_ads source connector")
    if not blocked_handoff.get("evidence_ids") or not blocked_handoff.get("action_ids"):
        raise SystemExit("Ads blocked_handoff must include evidence and action IDs")
    if not {"zwrot z reklam", "wyszukiwane hasła"} <= set(
        blocked_handoff.get("blocked_claims", [])
    ):
        raise SystemExit("Blocked Ads handoff must list blocked claims")
