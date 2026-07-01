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
    packet = {
        "skill": SKILL_NAME,
        "purpose": "UAT sesji pracy contentowej Wilka przez WILQ API dla 3-5 itemów",
        "queue_status": queue.get("queue_status"),
        "operator_summary": queue.get("operator_summary"),
        "candidate_count": queue.get("candidate_count"),
        "actionable_candidate_count": queue.get("actionable_candidate_count"),
        "items": [packet_item(args.api_base, candidate) for candidate in candidates[: args.limit]],
        "uat_tasks": [
            "Wybierz jeden item, który da się odświeżyć albo scalić bez tworzenia duplikatu.",
            "Wskaż blocker, który jasno mówi, dlaczego nie wolno jeszcze pisać.",
            "Sprawdź, czy final canonical nie jest adresem dev/staging.",
            "Powiedz, czy safe_next_step mówi dokładnie, co zrobić dalej.",
            "Potwierdź, czy measurement readiness blokuje zbyt wczesny claim sukcesu.",
        ],
        "hard_rules": [
            "Brak evidence ID oznacza brak rekomendacji.",
            "Brak source connector oznacza brak rekomendacji.",
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
