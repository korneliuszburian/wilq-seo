from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from wilq.schemas import MetricFact

CONTENT_REFRESH_ACTION_TYPE = "wordpress_content_refresh"
CONTENT_BRIEF_PREVIEW_CONTRACT = "content_brief_preview_v1"

CONTENT_SOURCE_CONNECTORS = {
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
    "google_analytics_4",
    "ahrefs",
}
GSC_METRIC_NAMES = {"clicks", "impressions", "ctr", "average_position"}
AHREFS_GAP_FACT_NAMES = {
    "ahrefs_content_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
    "ahrefs_competitor_page_count",
}
AHREFS_RELEVANCE_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "pozwolenie",
    "zintegrowane",
    "zielony lad",
    "ppwr",
    "recykling",
    "emisja",
    "esg",
    "beczka",
    "sorbent",
    "magazynowanie",
    "substancje",
    "chemiczne",
    "denios",
)
AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}
AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie",
    "samochod",
    "samochodu",
    "cuk.pl",
    "ltesty.pl",
)
CONTENT_BLOCKED_CLAIMS = [
    "lead uplift",
    "revenue impact",
    "ranking guarantee",
    "traffic uplift",
    "authority improvement",
    "automatic WordPress publish",
]


def content_refresh_payload_from_metric_facts(
    metric_facts: list[MetricFact],
) -> dict[str, Any] | None:
    facts = [
        fact
        for fact in metric_facts
        if fact.source_connector in CONTENT_SOURCE_CONNECTORS
    ]
    if not facts:
        return None
    content_brief_preview = [
        *_gsc_content_brief_previews(facts),
        *_ahrefs_content_brief_previews(facts),
    ][:8]
    return {
        "action_type": CONTENT_REFRESH_ACTION_TYPE,
        "connector": "wordpress_ekologus",
        "mode": "prepare_only",
        "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
        "source_connectors": _unique(fact.source_connector for fact in facts),
        "source_metric_names": _unique(fact.name for fact in facts),
        "content_brief_preview": content_brief_preview,
        "queue_steps": [
            "join_wordpress_inventory_with_gsc",
            "classify_refresh_create_merge_block",
            "prepare_brief_preview",
            "require_human_confirm_before_wordpress_write",
        ],
        "required_validation": [
            "gsc_query_page_check",
            "wordpress_inventory_check",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ],
        "operator_review_gates": [
            "sprawdź intencję query/topic",
            "potwierdź dopasowanie WordPress inventory",
            "sprawdź duplikaty i kanibalizację",
            "zatwierdź brief przed jakąkolwiek zmianą WordPress",
        ],
        "blocked_claims": CONTENT_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def _gsc_content_brief_previews(metric_facts: list[MetricFact]) -> list[dict[str, Any]]:
    wordpress_paths = _wordpress_inventory_paths(metric_facts)
    gsc_facts_by_page: dict[str, list[MetricFact]] = {}
    for fact in metric_facts:
        if fact.source_connector != "google_search_console":
            continue
        page = fact.dimensions.get("page")
        query = fact.dimensions.get("query")
        if not page or not query or fact.name not in GSC_METRIC_NAMES:
            continue
        gsc_facts_by_page.setdefault(page, []).append(fact)

    previews: list[dict[str, Any]] = []
    for page, page_facts in sorted(
        gsc_facts_by_page.items(),
        key=lambda item: _metric_sum(item[1], "impressions"),
        reverse=True,
    )[:4]:
        queries = _unique(
            fact.dimensions.get("query")
            for fact in page_facts
            if fact.dimensions.get("query")
        )
        primary_query = queries[0] if queries else _short_path(page)
        page_path = _normalized_path(page)
        wordpress_match = page_path in wordpress_paths
        mode = "refresh" if wordpress_match else "inventory_check"
        decision_options = ["refresh", "merge", "block"] if wordpress_match else [
            "merge",
            "create",
            "block",
        ]
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_gsc_{_slug(page_path or page)}",
                "source_type": "gsc_query_page",
                "mode": mode,
                "topic": primary_query,
                "target_url": page,
                "wordpress_inventory_match": "present" if wordpress_match else "missing",
                "decision_options": decision_options,
                "metric_snapshot": _gsc_metric_snapshot(page_facts),
                "brief_goal": _gsc_brief_goal(wordpress_match, primary_query),
                "brief_outline": _brief_outline(primary_query, wordpress_match),
                "required_validation": _gsc_required_validation(wordpress_match),
                "blocked_claims": CONTENT_BLOCKED_CLAIMS,
                "source_connectors": _unique(fact.source_connector for fact in page_facts),
                "evidence_ids": _unique(fact.evidence_id for fact in page_facts),
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    return previews


def _ahrefs_content_brief_previews(metric_facts: list[MetricFact]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    scored_facts = [
        (score, fact, topic)
        for fact in metric_facts
        if fact.source_connector == "ahrefs" and fact.name in AHREFS_GAP_FACT_NAMES
        for topic in [_ahrefs_topic(fact)]
        for score in [_ahrefs_preview_score(fact, topic)]
        if topic and score > 0
    ]
    for _score, fact, topic in sorted(
        scored_facts,
        key=lambda item: (item[0], _metric_numeric_sort_value(item[1])),
        reverse=True,
    ):
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_ahrefs_{_slug(topic)}",
                "source_type": "ahrefs_gap_review",
                "mode": "review",
                "topic": topic,
                "gap_type": fact.dimensions.get("gap_type") or fact.name,
                "competitor_domain": fact.dimensions.get("competitor_domain") or None,
                "source_url": fact.dimensions.get("source_url") or None,
                "target_url": fact.dimensions.get("target_url") or None,
                "wordpress_inventory_match": "unknown",
                "gsc_demand": "unknown",
                "decision_options": ["refresh", "merge", "create", "block"],
                "metric_snapshot": {
                    "metric_name": fact.name,
                    "metric_value": fact.value,
                },
                "brief_goal": (
                    "Zweryfikuj temat z Ahrefs przeciw GSC i WordPress, zanim "
                    "powstanie brief. To jest kandydat do review, nie decyzja create."
                ),
                "brief_outline": _brief_outline(topic, False),
                "required_validation": [
                    "business_relevance_review",
                    "gsc_demand_check",
                    "wordpress_inventory_check",
                    "duplicate_or_cannibalization_check",
                    "human_confirm_before_wordpress_write",
                ],
                "blocked_claims": CONTENT_BLOCKED_CLAIMS,
                "source_connectors": ["ahrefs"],
                "evidence_ids": [fact.evidence_id],
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
        if len(previews) >= 4:
            break
    return previews


def _wordpress_inventory_paths(metric_facts: list[MetricFact]) -> set[str]:
    paths: set[str] = set()
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        url = fact.dimensions.get("content_url")
        if not url:
            continue
        path = _normalized_path(url)
        if path:
            paths.add(path)
    return paths


def _gsc_metric_snapshot(page_facts: list[MetricFact]) -> dict[str, int | float | str]:
    return {
        "queries": len(
            _unique(
                fact.dimensions.get("query")
                for fact in page_facts
                if fact.dimensions.get("query")
            )
        ),
        "clicks": _metric_sum_or_missing(page_facts, "clicks"),
        "impressions": _metric_sum_or_missing(page_facts, "impressions"),
        "ctr": _first_metric_or_missing(page_facts, "ctr"),
        "average_position": _first_metric_or_missing(page_facts, "average_position"),
    }


def _gsc_brief_goal(wordpress_match: bool, primary_query: str) -> str:
    if wordpress_match:
        return (
            f"Przygotuj refresh/merge brief dla istniejącej treści pod temat "
            f"`{primary_query}`: title, H1/H2, braki w sekcjach, CTA i ryzyka claimów."
        )
    return (
        f"Sprawdź inventory i duplikaty przed briefem dla `{primary_query}`. "
        "Bez potwierdzenia URL nie twórz nowej strony."
    )


def _brief_outline(topic: str, wordpress_match: bool) -> list[dict[str, str]]:
    action = "odświeżenia istniejącej strony" if wordpress_match else "review tematu"
    return [
        {
            "section": "intent",
            "instruction": f"Opisz intencję użytkownika dla `{topic}` i zakres {action}.",
        },
        {
            "section": "title_h1",
            "instruction": "Zaproponuj kierunek title/H1 bez obietnic pozycji ani leadów.",
        },
        {
            "section": "missing_sections",
            "instruction": "Wskaż sekcje do sprawdzenia lub dopisania na podstawie evidence.",
        },
        {
            "section": "cta",
            "instruction": "Dopasuj CTA do usługi Ekologus, ale bez claimów revenue/lead uplift.",
        },
    ]


def _gsc_required_validation(wordpress_match: bool) -> list[str]:
    checks = [
        "gsc_query_page_check",
        "duplicate_or_cannibalization_check",
        "human_confirm_before_wordpress_write",
    ]
    if wordpress_match:
        return ["wordpress_existing_url_confirmed", *checks]
    return ["wordpress_inventory_check", *checks]


def _ahrefs_topic(fact: MetricFact) -> str | None:
    dimensions = fact.dimensions
    for key in ("keyword", "source_url", "target_url", "competitor_domain"):
        value = dimensions.get(key)
        if value:
            return value
    return None


def _ahrefs_preview_score(fact: MetricFact, topic: str | None) -> int:
    if not topic:
        return 0
    haystack = _normalize_text(
        " ".join(
            value
            for value in [
                topic,
                fact.dimensions.get("keyword"),
                fact.dimensions.get("source_url"),
                fact.dimensions.get("target_url"),
                fact.dimensions.get("competitor_domain"),
            ]
            if value
        )
    )
    if any(term in haystack for term in AHREFS_OFF_TOPIC_TERMS):
        return 0
    score = 0
    if any(term in haystack for term in AHREFS_RELEVANCE_TERMS):
        score += 4
    if fact.dimensions.get("competitor_domain") in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        score += 2
    if fact.dimensions.get("keyword"):
        score += 2
    if fact.dimensions.get("gap_type") in {
        "content_gap",
        "organic_keyword_gap",
        "top_page_gap",
    }:
        score += 2
    return score


def _metric_numeric_sort_value(fact: MetricFact) -> float:
    if isinstance(fact.value, int | float):
        return float(fact.value)
    return 0.0


def _normalize_text(value: str) -> str:
    replacements = {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
    }
    normalized = value.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _metric_sum(facts: list[MetricFact], metric_name: str) -> float:
    return sum(
        float(fact.value)
        for fact in facts
        if fact.name == metric_name and isinstance(fact.value, int | float)
    )


def _metric_sum_or_missing(facts: list[MetricFact], metric_name: str) -> int | float | str:
    value = _metric_sum(facts, metric_name)
    if value == 0 and not any(fact.name == metric_name for fact in facts):
        return "brak danych"
    return int(value) if value.is_integer() else value


def _first_metric_or_missing(facts: list[MetricFact], metric_name: str) -> int | float | str:
    for fact in facts:
        if fact.name == metric_name and isinstance(fact.value, int | float):
            value = float(fact.value)
            return int(value) if value.is_integer() else value
    return "brak danych"


def _normalized_path(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value
    normalized = "/" + path.strip("/")
    return "/" if normalized == "/" else normalized


def _short_path(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc:
        return f"{parsed.netloc}{parsed.path}".rstrip("/") or parsed.netloc
    return value


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower())[
        :96
    ].strip("_")


def _unique(items: Iterable[str | None]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
