from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_API_BASE = "http://127.0.0.1:8000"

ENDPOINTS = {
    "command_center": "/api/dashboard/command-center",
    "merchant": "/api/merchant/diagnostics",
    "content": "/api/content/diagnostics",
    "ads": "/api/ads/diagnostics",
    "ga4": "/api/ga4/diagnostics",
}

UAT_ROUTE_ORDER = [
    {
        "key": "command_center",
        "label": "Centrum pracy",
        "route": "/command-center",
        "operator_task": "Wskaż jedną decyzję dnia i powiedz, co sprawdzisz dalej.",
        "pass_condition": "Marketer rozumie następny krok bez tłumaczenia developera.",
        "fail_condition": "Marketer widzi statusy techniczne, ale nie wie, co kliknąć.",
    },
    {
        "key": "merchant",
        "label": "Merchant",
        "route": "/merchant",
        "operator_task": "Wskaż jeden problem feedu albo blocker.",
        "pass_condition": (
            "Marketer rozumie, że zgłoszenia problemów nie są automatycznie "
            "unikalnymi SKU i że feed write/approval recovery nie są obiecane."
        ),
        "fail_condition": "Marketer oczekuje automatycznej naprawy feedu albo approval recovery.",
    },
    {
        "key": "content",
        "label": "Treści",
        "route": "/content-planner",
        "operator_task": "Wybierz jeden istniejący temat do zachowania, odświeżenia albo scalenia.",
        "pass_condition": (
            "Marketer widzi publiczny URL na ekologus.pl, dowody z GSC, WordPress i Ahrefs, "
            "bramki jakości, H1/H2/FAQ/CTA, brakujące dowody i zakazane obietnice."
        ),
        "fail_condition": (
            "Marketer uważa, że WILQ już wygenerował publish-ready artykuł albo "
            "że opcjonalny podgląd projektu jest źródłem historycznej skuteczności "
            "albo finalnym URL-em SEO."
        ),
    },
    {
        "key": "ads",
        "label": "Google Ads",
        "route": "/ads-doctor",
        "operator_task": "Wskaż jedną kolejkę Ads review.",
        "pass_condition": (
            "Marketer rozumie, że CPA/ROAS/wasted budget/budget scaling/apply są "
            "zablokowane bez targetów, review i audit contract."
        ),
        "fail_condition": "Marketer oczekuje automatycznego optimizera albo werdyktu opłacalności.",
    },
    {
        "key": "ga4",
        "label": "GA4",
        "route": "/ga4",
        "operator_task": "Wskaż jeden problem pomiaru.",
        "pass_condition": (
            "Marketer rozumie, że `(not set)` to problem tracking/attribution, "
            "nie dowód złej kampanii albo złego landingu."
        ),
        "fail_condition": (
            "Marketer interpretuje tracking gap jako rekomendację contentową "
            "lub Adsową."
        ),
    },
]

FINAL_QUESTIONS = [
    "Czy wiesz, co zrobić jako następny krok?",
    "Który ekran dał Ci największy realny zysk?",
    "Gdzie musiałeś zgadywać znaczenie statusu albo pola?",
    (
        "Czy widok Treści oszczędza Ci czas przy decyzji, co zachować, "
        "odświeżyć albo scalić na ekologus.pl?"
    ),
    "Ile czasu realnie oszczędza ta ścieżka: 0, 15, 30, 60+ minut?",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export a live Ekologus marketer UAT packet from WILQ API. "
            "The packet records what to test and what evidence/blockers are visible; "
            "it does not claim that UAT has happened."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format. Markdown is easiest for a live UAT session.",
    )
    args = parser.parse_args()

    try:
        surfaces = fetch_surfaces(args.api_base)
        packet = build_marketer_uat_packet(surfaces, api_base=args.api_base)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(packet))
    return 0


def fetch_surfaces(api_base: str) -> dict[str, dict[str, Any]]:
    return {key: fetch_json(api_base, path) for key, path in ENDPOINTS.items()}


def fetch_json(api_base: str, path: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}{path}"
    try:
        with urlopen(url, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except URLError as error:
        raise RuntimeError(f"Could not fetch {url}: {error}") from error

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Endpoint {url} did not return JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"Endpoint {url} returned non-object JSON")
    return payload


def build_marketer_uat_packet(
    surfaces: dict[str, dict[str, Any]],
    *,
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    missing = [key for key in ENDPOINTS if key not in surfaces]
    if missing:
        raise RuntimeError(f"Missing UAT surfaces: {', '.join(missing)}")

    command_center = _mapping(surfaces["command_center"])
    route_checks = [
        build_route_check(route, _mapping(surfaces.get(route["key"])))
        for route in UAT_ROUTE_ORDER
    ]

    return {
        "packet_type": "ekologus_marketer_uat_packet_v1",
        "api_base": api_base.rstrip("/"),
        "generated_at": command_center.get("generated_at"),
        "time_limit_minutes": 15,
        "strict_instruction": command_center.get("strict_instruction"),
        "primary_next_step": command_center.get("primary_next_step"),
        "route_order": [route["route"] for route in UAT_ROUTE_ORDER],
        "route_checks": route_checks,
        "final_questions": FINAL_QUESTIONS,
        "result_template": {
            "date": "<YYYY-MM-DD>",
            "person": "<marketer>",
            "command_center": "<pass|fail + note>",
            "merchant": "<pass|fail + note>",
            "content": "<pass|fail + note>",
            "ads": "<pass|fail + note>",
            "ga4": "<pass|fail + note>",
            "biggest_real_boost": "<free text>",
            "biggest_confusion": "<free text>",
            "new_tasks": ["<task from feedback>"],
            "ready_without_developer": "<yes|no>",
        },
        "safety_note": (
            "Ten pakiet nie jest dowodem wykonanego UAT. Służy do zebrania "
            "realnej informacji zwrotnej marketera i zamiany niezrozumiałych miejsc na "
            "zadania. Nie odblokowuje publikacji ani zapisu zmian, automatycznej "
            "optymalizacji Ads, naprawy feedu, obietnic wzrostu Localo, CPA/ROAS "
            "ani twierdzeń o przychodach."
        ),
    }


def build_route_check(
    route: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    key = route["key"]
    return {
        "key": key,
        "label": route["label"],
        "route": route["route"],
        "operator_task": route["operator_task"],
        "pass_condition": route["pass_condition"],
        "fail_condition": route["fail_condition"],
        "live_snapshot": live_snapshot_for(key, payload),
        "record_after_session": {
            "result": "<pass|fail>",
            "marketer_next_step": "<what marketer says they would do next>",
            "confusion": "<what was unclear>",
            "tasks_to_create": ["<task if any>"],
        },
    }


def live_snapshot_for(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    if key == "command_center":
        decisions = _list(payload.get("daily_decisions"))
        return {
            "primary_next_step": payload.get("primary_next_step"),
            "blocker_count": payload.get("blocker_count"),
            "tactical_item_count": payload.get("tactical_item_count"),
            "daily_decisions": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "domain": item.get("domain"),
                    "route": item.get("route"),
                    "status": item.get("status"),
                    "priority": item.get("priority"),
                    "metric_tiles": item.get("metric_tiles"),
                }
                for item in (_mapping(item) for item in decisions[:5])
            ],
        }
    if key == "content":
        summary = _mapping(payload.get("operator_summary"))
        decisions = _list(payload.get("decision_queue"))
        return {
            "confirmed_wordpress_count": summary.get("confirmed_wordpress_count"),
            "missing_wordpress_count": summary.get("missing_wordpress_count"),
            "current_site_match_count": summary.get("current_site_match_count"),
            "decision_type_labels": summary.get("decision_type_labels"),
            "top_decisions": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "decision_type": item.get("decision_type"),
                    "source_public_url": item.get("source_public_url"),
                    "intended_final_url": item.get("intended_final_url"),
                    "final_canonical_url": item.get("final_canonical_url"),
                    "preview_url": item.get("preview_url"),
                    "next_step": item.get("next_step"),
                    "blocked_claims": item.get("blocked_claims"),
                }
                for item in (_mapping(item) for item in decisions[:5])
            ],
            "blocked_claims": _list(payload.get("blocked_claims")),
            "action_ids": _list(payload.get("action_ids")),
        }
    if key in {"merchant", "ads", "ga4"}:
        summary = _mapping(payload.get("operator_summary"))
        return {
            "generated_at": payload.get("generated_at"),
            "summary": _compact_summary(summary),
            "decision_queue": _compact_decision_queue(payload.get("decision_queue")),
            "blocked_claims": _list(payload.get("blocked_claims")),
            "action_ids": _list(payload.get("action_ids")),
        }
    return {"generated_at": payload.get("generated_at")}


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Pakiet UAT dla marketera Ekologus",
        "",
        f"- Typ: `{packet.get('packet_type')}`",
        f"- Wygenerowano: `{packet.get('generated_at') or 'brak daty'}`",
        f"- API: `{packet.get('api_base')}`",
        f"- Limit: `{packet.get('time_limit_minutes')}` minut",
        f"- Następny krok: {packet.get('primary_next_step') or 'brak'}",
        "",
        packet.get("safety_note") or "",
        "",
        "## Ścieżka UAT",
        "",
    ]
    for index, route in enumerate(_list(packet.get("route_checks")), start=1):
        route = _mapping(route)
        lines.extend(
            [
                f"### {index}. {route.get('label')}",
                "",
                f"- Widok: `{route.get('route')}`",
                f"- Zadanie marketera: {route.get('operator_task')}",
                f"- Warunek zaliczenia: {route.get('pass_condition')}",
                f"- Warunek niezaliczenia: {route.get('fail_condition')}",
                "",
                "Podgląd z WILQ:",
                "",
                "```json",
                json.dumps(route.get("live_snapshot") or {}, ensure_ascii=False, indent=2),
                "```",
                "",
                "Do uzupełnienia po sesji:",
                "",
                "```json",
                json.dumps(
                    route.get("record_after_session") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )
    lines.extend(["## Pytania końcowe", ""])
    for question in _list(packet.get("final_questions")):
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Wynik do zapisania",
            "",
            "```json",
            json.dumps(packet.get("result_template") or {}, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "status",
        "freshness_state",
        "latest_refresh_completed_at",
        "decision_queue_count",
        "reported_issue_occurrences",
        "unique_products",
        "product_count",
        "campaign_count",
        "tracking_gap_count",
        "measurement_issue_count",
        "ready_review_count",
        "blocked_claim_count",
    }
    return {key: value for key, value in summary.items() if key in allowed}


def _compact_decision_queue(value: Any) -> list[dict[str, Any]]:
    queue = []
    for item in (_mapping(item) for item in _list(value)[:5]):
        queue.append(
            {
                "id": item.get("id") or item.get("decision_id"),
                "title": item.get("title"),
                "decision_type": item.get("decision_type") or item.get("type"),
                "status": item.get("status"),
                "next_step": item.get("next_step"),
                "blocked_claims": item.get("blocked_claims"),
            }
        )
    return queue


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    sys.exit(main())
