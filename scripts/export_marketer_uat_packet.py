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
            "unikalnymi SKU i że zapis do feedu ani odzyskanie zatwierdzeń nie są obiecane."
        ),
        "fail_condition": "Marketer oczekuje automatycznej naprawy feedu albo odzyskania zatwierdzeń.",
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
            "Marketer uważa, że WILQ już wygenerował artykuł gotowy do publikacji albo "
            "że opcjonalny podgląd projektu jest źródłem historycznej skuteczności "
            "albo finalnym URL-em SEO."
        ),
    },
    {
        "key": "ads",
        "label": "Google Ads",
        "route": "/ads-doctor",
        "operator_task": "Wskaż jedną kolejkę sprawdzenia Ads.",
        "pass_condition": (
            "Marketer rozumie, że koszt pozyskania celu, zwrot z reklam, "
            "zmarnowany budżet, skalowanie budżetu i zapis zmian są zablokowane "
            "bez celów biznesowych, sprawdzenia i audytu."
        ),
        "fail_condition": "Marketer oczekuje automatycznego optymalizatora albo werdyktu opłacalności.",
    },
    {
        "key": "ga4",
        "label": "GA4",
        "route": "/ga4",
        "operator_task": "Wskaż jeden problem pomiaru.",
        "pass_condition": (
            "Marketer rozumie, że `(not set)` to problem pomiaru albo przypisania źródła, "
            "nie dowód złej kampanii albo złego landingu."
        ),
        "fail_condition": (
            "Marketer interpretuje tracking gap jako rekomendację contentową lub Adsową."
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
        build_route_check(route, _mapping(surfaces.get(route["key"]))) for route in UAT_ROUTE_ORDER
    ]

    return {
        "packet_type": "ekologus_marketer_uat_packet_v1",
        "api_base": api_base.rstrip("/"),
        "wygenerowano": command_center.get("generated_at"),
        "limit_minut": 15,
        "zasada_bezpieczeństwa": command_center.get("strict_instruction"),
        "następny_krok": command_center.get("primary_next_step"),
        "kolejność_widoków": [route["route"] for route in UAT_ROUTE_ORDER],
        "widoki": route_checks,
        "pytania_końcowe": FINAL_QUESTIONS,
        "szablon_wyniku": {
            "data": "<YYYY-MM-DD>",
            "osoba": "<marketer>",
            "centrum_pracy": "<zaliczone|niezaliczone + notatka>",
            "merchant": "<zaliczone|niezaliczone + notatka>",
            "treści": "<zaliczone|niezaliczone + notatka>",
            "google_ads": "<zaliczone|niezaliczone + notatka>",
            "ga4": "<zaliczone|niezaliczone + notatka>",
            "największy_realny_zysk": "<opis>",
            "największa_niejasność": "<opis>",
            "nowe_zadania": ["<zadanie z feedbacku>"],
            "gotowe_bez_developera": "<tak|nie>",
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
        "klucz": key,
        "etykieta": route["label"],
        "widok": route["route"],
        "zadanie_marketera": route["operator_task"],
        "warunek_zaliczenia": route["pass_condition"],
        "warunek_niezaliczenia": route["fail_condition"],
        "podgląd_z_wilq": live_snapshot_for(key, payload),
        "do_uzupełnienia_po_sesji": {
            "wynik": "<zaliczone|niezaliczone>",
            "następny_krok_marketera": "<co marketer mówi, że zrobi dalej>",
            "niejasność": "<co było niejasne>",
            "zadania_do_utworzenia": ["<zadanie, jeśli jest potrzebne>"],
        },
    }


def live_snapshot_for(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    if key == "command_center":
        decisions = _list(payload.get("daily_decisions"))
        return {
            "następny_krok": payload.get("primary_next_step"),
            "liczba_blokad": payload.get("blocker_count"),
            "liczba_zadań": payload.get("tactical_item_count"),
            "decyzje_dnia": [
                {
                    "decyzja": item.get("title"),
                    "widok": item.get("route_label") or item.get("route"),
                    "adres_widoku": item.get("route"),
                    "stan": item.get("decision_state_label")
                    or item.get("status_label")
                    or _operator_state_label(item.get("status")),
                    "priorytet": item.get("priority_label") or item.get("priority"),
                    "metryki": item.get("metric_tiles"),
                }
                for item in (_mapping(item) for item in decisions[:5])
            ],
        }
    if key == "content":
        summary = _mapping(payload.get("operator_summary"))
        decisions = _list(payload.get("decision_queue"))
        return {
            "potwierdzone_dopasowania_wordpress": summary.get("confirmed_wordpress_count"),
            "brakujące_dopasowania_wordpress": summary.get("missing_wordpress_count"),
            "dopasowania_obecnej_strony": summary.get("current_site_match_count"),
            "tryby_decyzji": summary.get("decision_type_labels"),
            "najważniejsze_decyzje": [
                {
                    "decyzja": item.get("title"),
                    "tryb": item.get("decision_type_label")
                    or _operator_decision_type_label(item.get("decision_type")),
                    "publiczny_url": item.get("source_public_url"),
                    "planowany_finalny_url": item.get("intended_final_url"),
                    "finalny_kanoniczny_url": item.get("final_canonical_url"),
                    "opcjonalny_podgląd": item.get("preview_url"),
                    "następny_krok": item.get("next_step"),
                    "czego_nie_obiecywać": _label_list(
                        item.get("blocked_claim_labels"), item.get("blocked_claims")
                    ),
                }
                for item in (_mapping(item) for item in decisions[:5])
            ],
            "czego_nie_obiecywać": _label_list(
                payload.get("blocked_claim_labels"), payload.get("blocked_claims")
            ),
            "akcje_do_sprawdzenia": payload.get("action_summary_label")
            or _count_label(_list(payload.get("action_ids")), "akcja do sprawdzenia"),
        }
    if key in {"merchant", "ads", "ga4"}:
        summary = _mapping(payload.get("operator_summary"))
        return {
            "wygenerowano": payload.get("generated_at"),
            "podsumowanie": _compact_summary(summary),
            "decyzje": _compact_decision_queue(payload.get("decision_queue")),
            "czego_nie_obiecywać": _label_list(
                payload.get("blocked_claim_labels"), payload.get("blocked_claims")
            ),
            "akcje_do_sprawdzenia": payload.get("action_summary_label")
            or _count_label(_list(payload.get("action_ids")), "akcja do sprawdzenia"),
        }
    return {"generated_at": payload.get("generated_at")}


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Pakiet UAT dla marketera Ekologus",
        "",
        f"- Wygenerowano: {packet.get('wygenerowano') or 'brak daty'}",
        f"- Limit: {packet.get('limit_minut')} minut",
        f"- Następny krok: {packet.get('następny_krok') or 'brak'}",
        "",
        packet.get("safety_note") or "",
        "",
        "## Ścieżka UAT",
        "",
    ]
    for index, route in enumerate(_list(packet.get("widoki")), start=1):
        route = _mapping(route)
        lines.extend(
            [
                f"### {index}. {route.get('etykieta')}",
                "",
                f"- Widok: `{route.get('widok')}`",
                f"- Zadanie marketera: {route.get('zadanie_marketera')}",
                f"- Warunek zaliczenia: {route.get('warunek_zaliczenia')}",
                f"- Warunek niezaliczenia: {route.get('warunek_niezaliczenia')}",
                "",
                "Podgląd z WILQ:",
                "",
                *render_readable_preview(route.get("podgląd_z_wilq")),
                "",
                "Karta odpowiedzi po sesji:",
                "",
                "- Wynik: zaliczone / niezaliczone",
                "- Co marketer mówi, że zrobi dalej: ...",
                "- Co było niejasne: ...",
                "- Zadania do utworzenia: ...",
                "",
            ]
        )
    lines.extend(["## Pytania końcowe", ""])
    for question in _list(packet.get("pytania_końcowe")):
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Wynik do zapisania po sesji",
            "",
            "- Data sesji: ...",
            "- Osoba: ...",
            "- Centrum pracy: zaliczone / niezaliczone + notatka",
            "- Merchant: zaliczone / niezaliczone + notatka",
            "- Treści: zaliczone / niezaliczone + notatka",
            "- Google Ads: zaliczone / niezaliczone + notatka",
            "- GA4: zaliczone / niezaliczone + notatka",
            "- Największy realny zysk: ...",
            "- Największa niejasność: ...",
            "- Nowe zadania z feedbacku: ...",
            "- Gotowe bez developera: tak / nie",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_readable_preview(value: Any) -> list[str]:
    lines = render_readable_value(value, indent=0)
    return lines if lines else ["- brak danych do pokazania"]


def render_readable_value(value: Any, *, indent: int) -> list[str]:
    if isinstance(value, dict):
        return render_readable_mapping(value, indent=indent)
    if isinstance(value, list):
        return render_readable_list(value, indent=indent)
    if value is None:
        return []
    return [f"{'  ' * indent}- {value}"]


def render_readable_mapping(value: dict[str, Any], *, indent: int) -> list[str]:
    lines: list[str] = []
    for key, item in value.items():
        label = _readable_packet_label(key)
        if label is None or item is None or item == [] or item == {}:
            continue
        prefix = "  " * indent
        if isinstance(item, dict):
            lines.append(f"{prefix}- {label}:")
            lines.extend(render_readable_mapping(item, indent=indent + 1))
        elif isinstance(item, list):
            lines.append(f"{prefix}- {label}:")
            lines.extend(render_readable_list(item, indent=indent + 1))
        else:
            lines.append(f"{prefix}- {label}: {item}")
    return lines


def render_readable_list(value: list[Any], *, indent: int) -> list[str]:
    lines: list[str] = []
    for item in value:
        prefix = "  " * indent
        if isinstance(item, dict):
            title = item.get("decyzja") or item.get("widok") or item.get("etykieta")
            if title:
                lines.append(f"{prefix}- {title}")
                nested = {key: nested_value for key, nested_value in item.items() if key != "decyzja"}
                lines.extend(render_readable_mapping(nested, indent=indent + 1))
            else:
                lines.extend(render_readable_mapping(item, indent=indent))
        elif item is not None:
            lines.append(f"{prefix}- {item}")
    return lines


def _readable_packet_label(key: str) -> str | None:
    labels = {
            "następny_krok": "następny krok",
            "liczba_blokad": "liczba blokad",
            "liczba_zadań": "liczba zadań",
            "zgłoszenia_problemów": "zgłoszenia problemów",
            "decyzje_do_sprawdzenia": "decyzje do sprawdzenia",
            "unikalne_produkty": "unikalne produkty",
            "produkty": "produkty",
            "kampanie": "kampanie",
            "problemy_pomiaru": "problemy pomiaru",
            "gotowe_do_sprawdzenia": "gotowe do sprawdzenia",
            "zablokowane_obietnice": "zablokowane obietnice",
            "decyzje_dnia": "decyzje dnia",
        "widok": "widok",
        "adres_widoku": "adres widoku",
        "stan": "stan",
        "priorytet": "priorytet",
        "metryki": "metryki",
        "wygenerowano": "wygenerowano",
        "podsumowanie": "podsumowanie",
        "decyzje": "decyzje",
        "tryb": "tryb",
        "czego_nie_obiecywać": "czego nie obiecywać",
        "akcje_do_sprawdzenia": "akcje do sprawdzenia",
        "potwierdzone_dopasowania_wordpress": "potwierdzone dopasowania WordPress",
        "brakujące_dopasowania_wordpress": "brakujące dopasowania WordPress",
        "dopasowania_obecnej_strony": "dopasowania obecnej strony",
        "tryby_decyzji": "tryby decyzji",
        "najważniejsze_decyzje": "najważniejsze decyzje",
        "publiczny_url": "publiczny URL",
        "planowany_finalny_url": "planowany finalny URL",
        "finalny_kanoniczny_url": "finalny kanoniczny URL",
        "opcjonalny_podgląd": "opcjonalny podgląd",
    }
    if key in labels:
        return labels[key]
    if "_" in key:
        return None
    return key


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    labels = {
        "status_label": "stan",
        "freshness_label": "świeżość",
        "latest_refresh_completed_at": "ostatni_udany_odczyt",
        "decision_queue_count": "decyzje_do_sprawdzenia",
        "reported_issue_occurrences": "zgłoszenia_problemów",
        "unique_products": "unikalne_produkty",
        "product_count": "produkty",
        "campaign_count": "kampanie",
        "tracking_gap_count": "problemy_pomiaru",
        "measurement_issue_count": "problemy_pomiaru",
        "ready_review_count": "gotowe_do_sprawdzenia",
        "blocked_claim_count": "zablokowane_obietnice",
    }
    return {
        label: summary[key]
        for key, label in labels.items()
        if key in summary and summary.get(key) is not None
    }


def _compact_decision_queue(value: Any) -> list[dict[str, Any]]:
    queue = []
    for item in (_mapping(item) for item in _list(value)[:5]):
        queue.append(
            {
                "decyzja": item.get("title"),
                "tryb": item.get("decision_type_label")
                or _operator_decision_type_label(item.get("decision_type") or item.get("type")),
                "stan": item.get("status_label") or _operator_state_label(item.get("status")),
                "następny_krok": item.get("next_step"),
                "czego_nie_obiecywać": _label_list(
                    item.get("blocked_claim_labels"), item.get("blocked_claims")
                ),
            }
        )
    return queue


def _label_list(preferred: Any, fallback: Any) -> list[Any]:
    labels = _list(preferred)
    return labels if labels else _list(fallback)


def _operator_state_label(value: Any) -> str | None:
    labels = {
        "ready": "gotowe",
        "review": "do sprawdzenia",
        "blocked": "zablokowane",
        "partial": "częściowe",
        "missing": "brak danych",
    }
    if not isinstance(value, str):
        return None
    return labels.get(value, "stan do sprawdzenia")


def _operator_decision_type_label(value: Any) -> str | None:
    labels = {
        "refresh_or_merge": "odświeżenie albo scalenie",
        "fix_measurement": "sprawdzenie pomiaru",
        "review_issue_cluster": "przegląd problemu feedu",
        "review_product_state_mapping": "sprawdzenie produktów",
        "review_price_impact_readiness": "sprawdzenie gotowości danych cenowych",
        "review_campaign_triage": "przegląd kampanii",
        "review_search_term_safety": "sprawdzenie wyszukiwanych haseł",
        "review_negative_keyword_safety": "sprawdzenie wykluczeń",
        "prepare_custom_segments": "przygotowanie segmentów do sprawdzenia",
    }
    if not isinstance(value, str):
        return None
    return labels.get(value, "decyzja do sprawdzenia")


def _count_label(items: list[Any], singular: str) -> str:
    count = len(items)
    if count == 1:
        return f"1 {singular}"
    if 2 <= count <= 4:
        return f"{count} akcje do sprawdzenia"
    return f"{count} akcji do sprawdzenia"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    sys.exit(main())
