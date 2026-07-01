#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any, cast

SKILL_NAME = "wilq-content-operator"
DEV_HOST = "ekologus.dev.proudsite.pl"


def request_json(
    api_base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: int = 180,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_enrichment(api_base: str, work_item_id: str) -> dict[str, Any]:
    try:
        return require_dict(
            request_json(api_base, "GET", f"/api/content/work-items/{work_item_id}/enrichment"),
            "content enrichment response",
        )
    except SystemExit as exc:
        return {
            "status": "blocked",
            "blocker": str(exc),
        }


def service_profile_uat_summary(api_base: str) -> dict[str, Any]:
    profile = require_dict(
        request_json(api_base, "GET", "/api/content/service-profile"),
        "service profile response",
    )
    coverage_summary = require_dict(
        profile.get("coverage_summary") or {},
        "service profile coverage summary",
    )
    private_summary = require_dict(
        profile.get("private_source_proposal_summary") or {},
        "private source proposal summary",
    )
    coverage_gaps = [
        {
            "gap_id": gap.get("gap_id"),
            "severity": gap.get("severity"),
            "label": gap.get("label"),
            "safe_next_step": gap.get("safe_next_step"),
        }
        for gap in as_list(profile.get("coverage_gaps"))
        if isinstance(gap, dict)
    ]
    private_review_actions = [
        {
            "action_id": action.get("action_id"),
            "label": action.get("label"),
            "reason": action.get("reason"),
            "blocked_write_claim": action.get("blocked_write_claim"),
            "required_human_role": action.get("required_human_role"),
            "target_card_id": action.get("target_card_id"),
        }
        for action in as_list(profile.get("review_actions"))
        if isinstance(action, dict)
        and str(action.get("action_id") or "").startswith(
            "service_profile_review_private_proposal_"
        )
    ]
    return {
        "endpoint": "/api/content/service-profile",
        "read_only": profile.get("read_only"),
        "production_depth_ready": coverage_summary.get("ready_for_daily_content"),
        "status_label": coverage_summary.get("status_label"),
        "safe_next_step": coverage_summary.get("safe_next_step"),
        "service_card_count": coverage_summary.get("service_card_count"),
        "approved_current_count": coverage_summary.get("approved_current_count"),
        "source_backed_review_required_count": coverage_summary.get(
            "source_backed_review_required_count"
        ),
        "coverage_gaps": coverage_gaps,
        "private_source_proposals": {
            "candidate_count": private_summary.get("candidate_count"),
            "review_required_count": private_summary.get("review_required_count"),
            "approved_count": private_summary.get("approved_count"),
            "promotion_ready": private_summary.get("promotion_ready"),
            "promotion_blocked_reason": private_summary.get("promotion_blocked_reason"),
            "promotion_checklist": private_summary.get("promotion_checklist") or [],
            "redacted": private_summary.get("redacted"),
        },
        "private_review_actions": private_review_actions,
    }


def packet_item(api_base: str, candidate: dict[str, Any]) -> dict[str, Any]:
    work_item_id = str(candidate.get("work_item_id") or "")
    enrichment_response: dict[str, Any] = (
        safe_enrichment(api_base, work_item_id) if work_item_id else {}
    )
    raw_enrichment = enrichment_response.get("enrichment")
    enrichment: dict[str, Any] = (
        cast(dict[str, Any], raw_enrichment)
        if isinstance(raw_enrichment, dict)
        else enrichment_response
    )
    response_blockers = enrichment_response.get("blockers") if isinstance(
        enrichment_response.get("blockers"), list
    ) else []
    final_url = candidate.get("final_canonical_url") or candidate.get("intended_final_url")
    preview_url = candidate.get("preview_url")
    final_url_status = (
        "blocked_dev_url"
        if isinstance(final_url, str) and DEV_HOST in final_url
        else "ready_or_missing"
    )
    return {
        "work_item_id": work_item_id,
        "title": candidate.get("title"),
        "topic": candidate.get("topic"),
        "recommended_mode": candidate.get("recommended_mode"),
        "recommended_mode_label": candidate.get("recommended_mode_label"),
        "status_label": candidate.get("status_label"),
        "reason": candidate.get("reason"),
        "safe_next_step": candidate.get("safe_next_step"),
        "evidence_ids": candidate.get("evidence_ids") or [],
        "source_connectors": candidate.get("source_connectors") or [],
        "final_canonical_url": final_url,
        "preview_url": preview_url,
        "final_url_status": final_url_status,
        "preflight_status": candidate.get("preflight_status"),
        "duplicate_canonical_risk_summary": candidate.get("duplicate_canonical_risk_summary"),
        "measurement_readiness": candidate.get("measurement_readiness"),
        "blockers": candidate.get("blockers") or [],
        "enrichment_summary": {
            "status": enrichment.get("status") or enrichment.get("enrichment_status"),
            "intent": enrichment.get("intent_label")
            or enrichment.get("intent")
            or enrichment.get("search_intent"),
            "service_fit": enrichment.get("service_fit")
            or enrichment.get("service_fit_label")
            or enrichment.get("service_fit_status"),
            "buyer_problem": enrichment.get("buyer_problem")
            or enrichment.get("buyer_problem_label"),
            "safe_next_step": enrichment.get("safe_next_step"),
            "blockers": enrichment.get("blockers") or response_blockers,
        },
    }


def uat_readiness(
    *,
    queue: dict[str, Any],
    service_profile: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    actionable_items = [
        item
        for item in items
        if item.get("recommended_mode") != "block" and not item.get("blockers")
    ]
    actionable_candidate_count = queue.get("actionable_candidate_count")
    if not isinstance(actionable_candidate_count, int):
        actionable_candidate_count = len(actionable_items)
    if actionable_candidate_count == 0:
        blockers.append("brak gotowego itemu contentowego bez blockerów")
    if service_profile.get("production_depth_ready") is not True:
        blockers.append("Service Profile nie jest production-depth")
    if service_profile.get("private_review_actions"):
        blockers.append("prywatne propozycje wymagają review Wilka/ownera")
    if queue.get("queue_status") == "blocked":
        blockers.append("kolejka content workflow ma status blocked")
    return {
        "status": "blocked_for_full_uat" if blockers else "ready_for_uat",
        "blockers": blockers,
        "recommended_scope": (
            "review/blokady i traceability"
            if blockers
            else "pełna sesja contentowa z briefem i wariantem szkicu"
        ),
        "actionable_candidate_count": actionable_candidate_count,
        "shown_actionable_item_ids": [item["work_item_id"] for item in actionable_items],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build {SKILL_NAME} Wilku UAT packet")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format for the live UAT packet.",
    )
    args = parser.parse_args()

    health = require_dict(request_json(args.api_base, "GET", "/api/health"), "health response")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    queue = require_dict(
        request_json(args.api_base, "GET", "/api/content/work-items/queue"),
        "content queue response",
    )
    candidates = [
        candidate
        for candidate in as_list(queue.get("candidates"))
        if isinstance(candidate, dict)
    ]
    service_profile = service_profile_uat_summary(args.api_base)
    items = [packet_item(args.api_base, candidate) for candidate in candidates[: args.limit]]
    readiness = uat_readiness(queue=queue, service_profile=service_profile, items=items)
    packet = {
        "skill": SKILL_NAME,
        "purpose": "UAT sesji pracy contentowej Wilka przez WILQ API dla 3-5 itemów",
        "queue_status": queue.get("queue_status"),
        "operator_summary": queue.get("operator_summary"),
        "candidate_count": queue.get("candidate_count"),
        "actionable_candidate_count": queue.get("actionable_candidate_count"),
        "service_profile": service_profile,
        "uat_readiness": readiness,
        "items": items,
        "uat_tasks": [
            (
                "Sprawdź Service Profile: powiedz, które luki i private review "
                "actions blokują production-depth."
            ),
            "Wybierz jeden item, który da się odświeżyć albo scalić bez tworzenia duplikatu.",
            "Wskaż blocker, który jasno mówi, dlaczego nie wolno jeszcze pisać.",
            "Sprawdź, czy final canonical nie jest adresem dev/staging.",
            "Powiedz, czy safe_next_step mówi dokładnie, co zrobić dalej.",
            "Potwierdź, czy measurement readiness blokuje zbyt wczesny claim sukcesu.",
            (
                "Zadaj pytanie 'skąd to wzięło?' i sprawdź, czy WILQ pokazuje "
                "evidence IDs oraz source connectors."
            ),
        ],
        "hard_rules": [
            "Brak evidence ID oznacza brak rekomendacji.",
            "Brak source connector oznacza brak rekomendacji.",
            "Review-required wiedza może wspierać UAT, ale nie odblokowuje production-depth.",
            "Private proposal review action nie promuje faktu ani karty wiedzy.",
            "Dev URL nie jest canonical ani SEO evidence.",
            "WordPress pozostaje draft-only albo podgląd zmian.",
            "Sukces lub porażka treści wymagają gotowego measurement outcome.",
        ],
    }

    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"# {packet['purpose']}")
    print()
    print(f"Status kolejki: {packet['queue_status']}")
    print(f"Podsumowanie: {packet['operator_summary']}")
    print()
    service_profile_raw = packet.get("service_profile")
    if not isinstance(service_profile_raw, dict):
        raise SystemExit("Service Profile UAT summary must be an object")
    service_profile_md = cast(dict[str, Any], service_profile_raw)
    readiness_raw = packet.get("uat_readiness")
    if not isinstance(readiness_raw, dict):
        raise SystemExit("UAT readiness must be an object")
    readiness_md = cast(dict[str, Any], readiness_raw)
    print("## Gotowość UAT")
    print(f"- status: {readiness_md['status']}")
    print(f"- zakres: {readiness_md['recommended_scope']}")
    readiness_blockers = [str(value) for value in readiness_md.get("blockers") or []]
    print(f"- blokady: {', '.join(readiness_blockers) or 'brak'}")
    print()
    print("## Service Profile")
    print(f"- endpoint: `{service_profile_md['endpoint']}`")
    print(f"- read-only: {service_profile_md['read_only']}")
    print(f"- production-depth: {service_profile_md['production_depth_ready']}")
    print(f"- status: {service_profile_md['status_label']}")
    print(f"- następny krok: {service_profile_md['safe_next_step']}")
    private_proposals = service_profile_md.get("private_source_proposals")
    if isinstance(private_proposals, dict):
        print(f"- promocja private proposals: {private_proposals.get('promotion_ready')}")
        blocked_reason = private_proposals.get("promotion_blocked_reason")
        if blocked_reason:
            print(f"- blokada promocji: {blocked_reason}")
        promotion_checklist = private_proposals.get("promotion_checklist")
        if isinstance(promotion_checklist, list) and promotion_checklist:
            print("- warunki przed reviewed source fact:")
            for item in promotion_checklist:
                print(f"  - {item}")
    gaps = service_profile_md.get("coverage_gaps")
    if isinstance(gaps, list) and gaps:
        print("- luki:")
        for raw_gap in gaps:
            if isinstance(raw_gap, dict):
                print(
                    f"  - `{raw_gap.get('gap_id')}`: {raw_gap.get('label')} "
                    f"({raw_gap.get('severity')})"
                )
    actions = service_profile_md.get("private_review_actions")
    if isinstance(actions, list) and actions:
        print("- private review actions:")
        for raw_action in actions:
            if isinstance(raw_action, dict):
                print(
                    f"  - `{raw_action.get('action_id')}`: "
                    f"{raw_action.get('label')} -> {raw_action.get('blocked_write_claim')}"
                )
    print()
    packet_items = packet.get("items")
    if not isinstance(packet_items, list):
        raise SystemExit("UAT packet items must be a list")
    for raw_item in packet_items:
        if not isinstance(raw_item, dict):
            raise SystemExit("UAT packet item must be an object")
        item = cast(dict[str, Any], raw_item)
        evidence_ids = [str(value) for value in item.get("evidence_ids") or []]
        source_connectors = [str(value) for value in item.get("source_connectors") or []]
        print(f"## {item['title'] or item['work_item_id']}")
        print(f"- work_item_id: `{item['work_item_id']}`")
        print(f"- tryb: {item['recommended_mode_label']} (`{item['recommended_mode']}`)")
        print(f"- status: {item['status_label']}")
        print(f"- dowody: {', '.join(evidence_ids) or 'brak'}")
        print(f"- źródła danych: {', '.join(source_connectors) or 'brak'}")
        print(f"- final canonical: {item['final_canonical_url'] or 'brak'}")
        print(f"- preview: {item['preview_url'] or 'brak'}")
        print(f"- następny krok: {item['safe_next_step']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
