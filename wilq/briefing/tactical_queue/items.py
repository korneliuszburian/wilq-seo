"""Decomposed tactical_queue items implementation."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from wilq.briefing.metric_fact_identity import latest_metric_facts_by_identity
from wilq.briefing.tactical_ahrefs import build_ahrefs_gap_items
from wilq.briefing.tactical_queue.labels import (
    _compact_tactical_diagnosis,
    _compact_tactical_title,
    _ga4_diagnosis,
    _gsc_diagnosis,
    _has_not_set_dimension,
    _priority_label,
    _short_path,
    _tactical_domain_label,
    _tactical_intent_label,
)
from wilq.briefing.tactical_queue.metrics import (
    _find_wordpress_match,
    _group_facts,
    _gsc_page_counts,
    _numeric_fact,
    _sum_metric_facts,
    _wordpress_content_index,
)
from wilq.briefing.tactical_queue.shared import (
    AHREFS_GAP_FACT_NAMES,
    AHREFS_GAP_TYPE_LABELS,
    AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS,
    AHREFS_OFF_TOPIC_TERMS,
    AHREFS_RELEVANT_COMPETITOR_DOMAINS,
    AHREFS_RELEVANT_TERMS,
    TACTICAL_QUEUE_DOMAIN_FLOOR,
    TacticalIntent,
    WordPressContentIndex,
    WordPressMatch,
    _normalize_path_key,
    _normalize_url_key,
    _stable_slug,
    _url_host,
)
from wilq.content.operator_copy import unique
from wilq.content.planning.ahrefs_overlap import AhrefsCrossSourceOverlap
from wilq.schemas import (
    ActionRisk,
    MetricFact,
    OpportunityDomain,
    TacticalQueueGroup,
    TacticalQueueItem,
)


def _compact_tactical_groups(items: list[TacticalQueueItem]) -> list[TacticalQueueGroup]:
    groups: dict[str, list[TacticalQueueItem]] = {}
    for item in items:
        key = _compact_tactical_group_key(item)
        groups.setdefault(key, []).append(item)
    return sorted(
        (_compact_tactical_group(group_items) for group_items in groups.values()),
        key=lambda group: (group.priority, group.id),
    )


def _compact_tactical_group_key(item: TacticalQueueItem) -> str:
    if item.domain == OpportunityDomain.gsc_seo and item.dimensions.get("page"):
        return f"{item.domain.value}:{item.intent}:{item.dimensions['page']}"
    if item.domain == OpportunityDomain.ga4:
        return (
            f"{item.domain.value}:{item.intent}:"
            f"{item.dimensions.get('landing_page', '')}:"
            f"{item.dimensions.get('source_medium', '')}"
        )
    if item.domain == OpportunityDomain.merchant:
        return (
            f"{item.domain.value}:{item.intent}:"
            f"{item.dimensions.get('issue_type', '')}:"
            f"{item.dimensions.get('affected_attribute', '')}:"
            f"{item.dimensions.get('country', '')}"
        )
    return item.id


def _compact_tactical_group(items: list[TacticalQueueItem]) -> TacticalQueueGroup:
    first = items[0]
    facts = [fact for item in items for fact in item.metric_facts]
    queries = unique(query for item in items if (query := item.dimensions.get("query")) is not None)
    clicks = _sum_metric_facts(facts, "clicks")
    impressions = _sum_metric_facts(facts, "impressions")
    return TacticalQueueGroup(
        id=_compact_tactical_group_key(first),
        title=_compact_tactical_title(first, len(items)),
        meta=(
            f"Obszar: {_tactical_domain_label(first.domain)}. "
            f"Zadanie: {_tactical_intent_label(first.intent)}. "
            f"Priorytet: {_priority_label(first.priority)}."
        ),
        diagnosis=_compact_tactical_diagnosis(
            first,
            queries,
            clicks,
            impressions,
            len(items),
        ),
        next_step=first.next_step,
        priority=first.priority,
        risk=first.risk,
        source_connectors=unique(
            connector for item in items for connector in item.source_connectors
        ),
        evidence_ids=unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=unique(action_id for item in items for action_id in item.action_ids),
        blocked_claims=unique(claim for item in items for claim in item.blocked_claims),
    )


def _balanced_tactical_items(
    items: list[TacticalQueueItem],
    *,
    limit: int,
) -> list[TacticalQueueItem]:
    sorted_items = sorted(items, key=_tactical_sort_key)
    selected: list[TacticalQueueItem] = []
    for domain in unique(item.domain.value for item in sorted_items):
        domain_items = [item for item in sorted_items if item.domain.value == domain]
        for item in domain_items[:TACTICAL_QUEUE_DOMAIN_FLOOR]:
            if item not in selected:
                selected.append(item)
    for item in sorted_items:
        if len(selected) >= limit:
            break
        if item not in selected:
            selected.append(item)
    return sorted(selected, key=_tactical_sort_key)[:limit]


def _tactical_sort_key(item: TacticalQueueItem) -> tuple[int, str]:
    return (item.priority, item.id)


def _gsc_content_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    wordpress_index: WordPressContentIndex,
    gsc_page_counts: dict[str, int],
) -> list[TacticalQueueItem]:
    grouped = _group_facts(
        fact
        for fact in facts
        if fact.source_connector == "google_search_console"
        and {"query", "page"}.issubset(fact.dimensions)
    )
    items: list[TacticalQueueItem] = []
    for index, ((query, page), group_facts) in enumerate(grouped.items(), start=1):
        clicks = _numeric_fact(group_facts, "clicks")
        impressions = _numeric_fact(group_facts, "impressions")
        ctr = _numeric_fact(group_facts, "ctr")
        position = _numeric_fact(group_facts, "average_position")
        wordpress_match = _find_wordpress_match(wordpress_index, page)
        wordpress_fact = wordpress_match.fact
        intent = _content_intent(
            clicks,
            impressions,
            ctr,
            position,
            wordpress_fact=wordpress_fact,
            page_query_count=gsc_page_counts.get(_normalize_url_key(page), 1),
        )
        priority = _content_priority(intent, impressions, position, index)
        item_facts = [*group_facts[:6], *([wordpress_fact] if wordpress_fact else [])]
        source_connectors = ["google_search_console"]
        if wordpress_fact:
            source_connectors.append(wordpress_fact.source_connector)
        items.append(
            TacticalQueueItem(
                id=f"tq_gsc_{_stable_slug(page)}_{_stable_slug(query)}",
                title=f"GSC: {query} -> {page}",
                domain=OpportunityDomain.gsc_seo,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=source_connectors,
                evidence_ids=unique(fact.evidence_id for fact in item_facts),
                metric_facts=item_facts,
                dimensions={
                    "query": query,
                    "page": page,
                    **_wordpress_match_dimensions(wordpress_match),
                    "gsc_page_query_count": str(gsc_page_counts.get(_normalize_url_key(page), 1)),
                },
                diagnosis=_gsc_diagnosis(
                    query,
                    page,
                    clicks,
                    impressions,
                    ctr,
                    position,
                    wordpress_match=wordpress_match,
                ),
                next_step=_content_next_step(intent),
                blocked_claims=["jakość leadów", "wzrost konwersji", "wpływ na przychód"],
                action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
            )
        )
    return items


def build_gsc_content_tactical_items(
    facts: list[MetricFact],
    *,
    wordpress_action_ids: Iterable[str] = (),
) -> list[TacticalQueueItem]:
    """Build the complete GSC/page inventory before any daily-queue limit.

    Content diagnostics needs every evidenced page so its own ranking can pick
    work items. The cross-domain tactical queue applies its balancing limit
    only after this complete page set exists.
    """
    current_facts = latest_metric_facts_by_identity(facts)
    return _gsc_content_items(
        current_facts,
        {"wordpress_ekologus": list(wordpress_action_ids)},
        _wordpress_content_index(current_facts),
        _gsc_page_counts(current_facts),
    )


def _ga4_quality_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    wordpress_index: WordPressContentIndex,
) -> list[TacticalQueueItem]:
    grouped = _group_facts(
        fact
        for fact in facts
        if fact.source_connector == "google_analytics_4"
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    )
    items: list[TacticalQueueItem] = []
    for index, ((landing_page, source_medium, campaign_name), group_facts) in enumerate(
        grouped.items(),
        start=1,
    ):
        active_users = _numeric_fact(group_facts, "active_users")
        sessions = _numeric_fact(group_facts, "sessions")
        engagement_rate = _numeric_fact(group_facts, "engagement_rate")
        has_not_set_dimension = _has_not_set_dimension(
            landing_page,
            source_medium,
            campaign_name,
        )
        wordpress_match = _find_wordpress_match(wordpress_index, landing_page)
        wordpress_fact = wordpress_match.fact
        intent: TacticalIntent
        if has_not_set_dimension:
            intent = "tracking_gap"
        elif engagement_rate is not None and engagement_rate < 0.2:
            intent = "landing_page_quality"
        else:
            intent = "traffic_quality_review"
        priority = _ga4_priority(active_users, engagement_rate, index)
        item_facts = [*group_facts[:6], *([wordpress_fact] if wordpress_fact else [])]
        source_connectors = ["google_analytics_4"]
        if wordpress_fact:
            source_connectors.append(wordpress_fact.source_connector)
        items.append(
            TacticalQueueItem(
                id=f"tq_ga4_{_stable_slug(landing_page)}_{_stable_slug(source_medium)}",
                title=(
                    f"Problem pomiaru GA4: {landing_page}; źródło ruchu: {source_medium}"
                    if has_not_set_dimension
                    else f"GA4: {landing_page}; źródło ruchu: {source_medium}"
                ),
                domain=OpportunityDomain.ga4,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=source_connectors,
                evidence_ids=unique(fact.evidence_id for fact in item_facts),
                metric_facts=item_facts,
                dimensions={
                    "landing_page": landing_page,
                    "source_medium": source_medium,
                    "campaign_name": campaign_name,
                    **_wordpress_match_dimensions(wordpress_match),
                },
                diagnosis=_ga4_diagnosis(
                    landing_page,
                    source_medium,
                    campaign_name,
                    active_users,
                    sessions,
                    engagement_rate,
                    wordpress_match=wordpress_match,
                ),
                next_step=_ga4_next_step(has_not_set_dimension),
                blocked_claims=[
                    "współczynnik konwersji",
                    "zwrot z reklam",
                    "przychód",
                    "opłacalność",
                ],
                action_ids=action_ids_by_connector.get("google_analytics_4", []),
            )
        )
    return items


def _ahrefs_gap_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    gsc_cross_check_facts: list[MetricFact],
    wordpress_cross_check_facts: list[MetricFact],
) -> list[TacticalQueueItem]:
    return build_ahrefs_gap_items(
        facts=facts,
        action_ids=action_ids_by_connector,
        gsc_facts=gsc_cross_check_facts,
        wordpress_facts=wordpress_cross_check_facts,
    )


def _group_ahrefs_gap_facts(facts: list[MetricFact]) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        if not is_reviewable_ahrefs_gap_fact(fact):
            continue
        dimensions = fact.dimensions
        gap_type = dimensions.get("gap_type") or _ahrefs_gap_type_for_fact(fact.name)
        key = (
            gap_type,
            dimensions.get("keyword", ""),
            dimensions.get("source_url", ""),
            dimensions.get("referenced_public_url", ""),
            _normalized_domain(dimensions.get("competitor_domain", "")),
        )
        if not any(key):
            continue
        grouped.setdefault(key, []).append(fact)
    return dict(sorted(grouped.items(), key=lambda item: _ahrefs_group_sort_key(item)))


def is_ahrefs_gap_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "ahrefs" and fact.name in AHREFS_GAP_FACT_NAMES


def is_reviewable_ahrefs_gap_fact(fact: MetricFact) -> bool:
    if not is_ahrefs_gap_fact(fact):
        return False
    dimensions = fact.dimensions
    if not any(
        dimensions.get(key)
        for key in (
            "gap_type",
            "keyword",
            "source_url",
            "referenced_public_url",
            "competitor_domain",
        )
    ):
        return False
    return not _is_ahrefs_off_topic(
        dimensions.get("keyword", ""),
        dimensions.get("source_url", ""),
        dimensions.get("referenced_public_url", ""),
        _normalized_domain(dimensions.get("competitor_domain", "")),
    )


def _ahrefs_group_sort_key(item: tuple[tuple[str, ...], list[MetricFact]]) -> tuple[int, str]:
    gap_type, keyword, source_url, referenced_public_url, competitor_domain = item[0]
    topic = _ahrefs_topic(keyword, source_url, referenced_public_url, competitor_domain)
    return (_ahrefs_gap_priority(gap_type, topic, competitor_domain, 0), topic)


def _ahrefs_gap_type_for_fact(name: str) -> str:
    if name == "ahrefs_competitor_page_count":
        return "competitor_page"
    if name == "ahrefs_content_gap_count":
        return "content_gap"
    if name in {"ahrefs_backlink_gap_count", "ahrefs_referring_domain_gap_count"}:
        return "backlink_gap"
    if name == "ahrefs_organic_keyword_gap_count":
        return "organic_keyword_gap"
    if name == "ahrefs_top_page_gap_count":
        return "top_page_gap"
    return "content_gap"


def _ahrefs_gap_type_label(gap_type: str) -> str:
    return AHREFS_GAP_TYPE_LABELS.get(gap_type, "rekord Ahrefs do sprawdzenia")


def _ahrefs_content_intent(gap_type: str) -> TacticalIntent:
    if gap_type == "backlink_gap":
        return "content_block"
    return "content_create"


def _ahrefs_gap_priority(
    gap_type: str,
    topic: str,
    competitor_domain: str,
    index: int,
) -> int:
    base_by_type = {
        "content_gap": 26,
        "organic_keyword_gap": 28,
        "top_page_gap": 30,
        "competitor_page": 34,
        "backlink_gap": 48,
    }
    base = base_by_type.get(gap_type, 40)
    normalized_topic = _normalize_ahrefs_text(topic)
    if any(term in normalized_topic for term in AHREFS_RELEVANT_TERMS):
        base -= 4
    if competitor_domain in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        base -= 3
    return max(1, min(base + index, 69))


def _ahrefs_topic(
    keyword: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
) -> str:
    if keyword:
        return keyword
    if referenced_public_url:
        return _short_path(referenced_public_url)
    if source_url:
        return _short_path(source_url)
    if competitor_domain:
        return competitor_domain
    return "rekord Ahrefs"


def _ahrefs_gap_diagnosis(
    gap_type: str,
    topic: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
    facts: list[MetricFact],
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    context = ", ".join(
        part
        for part in (
            f"konkurent: {competitor_domain}" if competitor_domain else None,
            f"adres źródłowy: {_short_path(source_url)}" if source_url else None,
            f"publiczny adres: {_short_path(referenced_public_url)}"
            if referenced_public_url
            else None,
        )
        if part is not None
    )
    context_text = f" Kontekst: {context}." if context else ""
    confirmation_text = _ahrefs_confirmation_text(confirmation)
    return (
        f"Ahrefs wskazuje: {_ahrefs_gap_type_label(gap_type)} dla tematu {topic}. "
        f"Fakty: {_ahrefs_fact_summary(facts)}.{context_text} "
        f"{confirmation_text} To jest sygnał do sprawdzenia contentu, "
        "nie samodzielna rekomendacja SEO."
    )


def _ahrefs_cross_check_label(
    source: str,
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    check = confirmation.gsc if source == "GSC" else confirmation.wordpress
    labels = {
        "exact": f"potwierdzone dopasowanie w {source}",
        "weak": f"słabe podobieństwo w {source} — sprawdź ręcznie",
        "missing": f"brak potwierdzonego dopasowania w {source}",
    }
    return labels[check.strength]


def _ahrefs_confirmation_text(confirmation: AhrefsCrossSourceOverlap) -> str:
    if confirmation.gsc.strength == "exact" and confirmation.wordpress.strength == "exact":
        return "GSC i WordPress potwierdzają dokładne dopasowanie tematu."
    if confirmation.gsc.strength == "exact":
        wordpress_note = (
            " WordPress ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if confirmation.wordpress.strength == "weak"
            else " WordPress wymaga sprawdzenia."
        )
        return f"GSC potwierdza dokładne dopasowanie tematu.{wordpress_note}"
    if confirmation.wordpress.strength == "exact":
        gsc_note = (
            " GSC ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if confirmation.gsc.strength == "weak"
            else " GSC wymaga sprawdzenia popytu."
        )
        return f"WordPress potwierdza dokładne dopasowanie tematu.{gsc_note}"
    if confirmation.gsc.strength == "weak" or confirmation.wordpress.strength == "weak":
        return (
            "WILQ widzi wyłącznie słabe podobieństwo w GSC lub WordPress; "
            "nie jest to potwierdzenie popytu ani istniejącej treści."
        )
    return "Brak potwierdzonego dopasowania z GSC i WordPress w bieżących dowodach."


def _ahrefs_gap_next_step(
    topic: str,
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    if confirmation.gsc.strength == "exact" and confirmation.wordpress.strength == "exact":
        return (
            f"Zweryfikuj `{topic}` na podstawie dokładnych dopasowań GSC i WordPress, potem "
            "wybierz odświeżenie, scalenie, nową treść albo blokadę. Nie traktuj Ahrefs jako "
            "samodzielnej obietnicy ruchu."
        )
    if confirmation.has_exact_match:
        return (
            f"Jedno źródło dokładnie potwierdza `{topic}`. Ręcznie sprawdź drugie źródło, "
            "potem wybierz odświeżenie, scalenie, nową treść albo blokadę."
        )
    if confirmation.gsc.strength == "weak" or confirmation.wordpress.strength == "weak":
        return (
            f"WILQ widzi tylko słabe podobieństwo dla `{topic}`. Sprawdź ręcznie GSC "
            "i spis WordPress; nie przygotowuj briefu ani decyzji o duplikacie na tej podstawie."
        )
    return (
        f"Sprawdź ręcznie `{topic}` w GSC i spisie treści WordPress, potem wybierz "
        "odświeżenie, scalenie, nową treść albo blokadę. Bez dopasowania nie twórz briefu tylko "
        "z Ahrefs."
    )


def _ahrefs_fact_summary(facts: list[MetricFact]) -> str:
    sorted_facts = sorted(facts, key=lambda item: item.name)
    return ", ".join(f"{fact.name}={fact.value}" for fact in sorted_facts)


def _is_ahrefs_off_topic(
    keyword: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
) -> bool:
    if competitor_domain in AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS:
        return True
    text = _normalize_ahrefs_text(
        " ".join((keyword, source_url, referenced_public_url, competitor_domain))
    )
    return any(term in text for term in AHREFS_OFF_TOPIC_TERMS)


def _normalize_ahrefs_text(value: str) -> str:
    replacements = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"}
    )
    return value.lower().translate(replacements)


def _normalized_domain(value: str) -> str:
    host = urlparse(value).netloc or value
    return host.removeprefix("www.").lower()


def _content_intent(
    clicks: float | int | None,
    impressions: float | int | None,
    ctr: float | int | None,
    position: float | int | None,
    *,
    wordpress_fact: MetricFact | None,
    page_query_count: int,
) -> TacticalIntent:
    if wordpress_fact is None:
        return "content_create"
    if page_query_count >= 3:
        return "content_merge"
    if (
        impressions
        and impressions >= 100
        and (not ctr or ctr < 0.03)
        and position
        and position <= 10
    ):
        return "content_refresh"
    if impressions and impressions >= 50 and position and position > 8:
        return "content_create"
    if clicks == 0 and impressions and impressions < 20:
        return "content_block"
    return "content_refresh"


def _content_priority(
    intent: str,
    impressions: float | int | None,
    position: float | int | None,
    index: int,
) -> int:
    base = 20 if intent == "content_refresh" else 28
    if impressions and impressions >= 100:
        base -= 5
    if position and position <= 3:
        base -= 3
    return max(1, min(base + index, 59))


def _ga4_priority(
    active_users: float | int | None,
    engagement_rate: float | int | None,
    index: int,
) -> int:
    base = 35
    if active_users and active_users >= 50:
        base -= 5
    if engagement_rate is not None and engagement_rate < 0.2:
        base -= 8
    return max(1, min(base + index, 69))


def _merchant_issue_priority(
    severity: str,
    product_count: float | int | None,
    index: int,
) -> int:
    base = 18 if severity == "DISAPPROVED" else 34
    if product_count and product_count >= 10:
        base -= 4
    return max(1, min(base + index, 59))


def _ga4_next_step(has_not_set_dimension: bool) -> str:
    if has_not_set_dimension:
        return (
            "Napraw pomiar GA4: sprawdź stronę wejścia, źródło i medium ruchu, "
            "UTM-y i konfigurację raportu. Nie traktuj tego jako rekomendacji "
            "marketingowej dla strony."
        )
    return (
        "Sprawdź stronę wejścia, dopasowanie komunikatu i pomiar. Nie oceniaj kampanii "
        "po samych użytkownikach bez konwersji."
    )


def _content_next_step(intent: TacticalIntent) -> str:
    if intent == "content_create":
        return (
            "Przygotuj brief nowej lub rozbudowanej sekcji, ale najpierw sprawdź "
            "duplikaty w WordPress."
        )
    if intent == "content_block":
        return "Oznacz jako niski priorytet; nie twórz zadania bez mocniejszego demand evidence."
    if intent == "content_merge":
        return (
            "Sprawdź overlap intencji i przygotuj plan scalenia z listą kontroli "
            "przekierowania i audytu."
        )
    return "Przygotuj odświeżenie istniejącej strony: tytuł, H1/H2, sekcje brakujące i CTA."


def _wordpress_match_dimensions(wordpress_match: WordPressMatch) -> dict[str, str]:
    wordpress_fact = wordpress_match.fact
    base_dimensions = {
        "wordpress_match_confidence": wordpress_match.confidence,
        "wordpress_requested_url_key": wordpress_match.requested_url_key,
        "wordpress_requested_path": wordpress_match.requested_path_key,
    }
    if wordpress_fact is None:
        return {
            **base_dimensions,
            "wordpress_match": "missing",
        }
    dimensions = wordpress_fact.dimensions
    return {
        **base_dimensions,
        "wordpress_match": "found",
        "wordpress_connector": wordpress_fact.source_connector,
        "wordpress_content_type": dimensions.get("content_type", ""),
        "wordpress_status": dimensions.get("status", ""),
        "wordpress_content_url": dimensions.get("content_url", ""),
        "wordpress_title_or_h1": dimensions.get("title_or_h1", ""),
        "wordpress_section_headings_json": dimensions.get("section_headings_json", ""),
        "wordpress_section_heading_count": dimensions.get("section_heading_count", ""),
        "wordpress_content_summary": dimensions.get("content_summary", ""),
        "wordpress_content_word_count": dimensions.get("content_word_count", ""),
        "wordpress_block_names_json": dimensions.get("block_names_json", ""),
        "wordpress_block_name_count": dimensions.get("block_name_count", ""),
        "wordpress_acf_field_count": dimensions.get("acf_field_count", ""),
        "wordpress_acf_section_headings_json": dimensions.get("acf_section_headings_json", ""),
        "wordpress_acf_section_count": dimensions.get("acf_section_count", ""),
        "wordpress_content_host": _url_host(dimensions.get("content_url", "")),
        "wordpress_matched_url_key": _normalize_url_key(dimensions.get("content_url", "")),
        "wordpress_matched_path": _normalize_path_key(dimensions.get("content_url", "")),
        "wordpress_host_alias_applied": str(
            wordpress_match.confidence == "host_alias_sitemap"
        ).lower(),
        "wordpress_modified_gmt": dimensions.get("modified_gmt", ""),
        "wordpress_inventory_source": dimensions.get("inventory_source", ""),
    }


def _tactical_action_ids_by_connector() -> dict[str, list[str]]:
    return {
        "ahrefs": ["act_prepare_content_refresh_queue"],
        "google_analytics_4": ["act_review_ga4_tracking_quality"],
        "google_merchant_center": ["act_review_merchant_feed_issues"],
        "wordpress_ekologus": ["act_prepare_content_refresh_queue"],
    }
