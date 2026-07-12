from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
from urllib.parse import urlparse

from wilq.content.planning.ahrefs_overlap import AhrefsCrossSourceMatcher, AhrefsCrossSourceOverlap
from wilq.schemas import ActionRisk, MetricFact, OpportunityDomain, TacticalQueueItem

TacticalIntent = Literal["content_refresh", "content_create", "content_merge", "content_block"]
_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
}
_TYPE_LABELS = {
    "competitor_page": "strona konkurencji",
    "content_gap": "luka treści",
    "backlink_gap": "luka linków",
    "organic_keyword_gap": "luka słów organicznych",
    "top_page_gap": "luka najlepszych stron konkurencji",
}
_OFF_TOPIC_DOMAINS = {"cuk.pl", "ltesty.pl"}
_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
)
_RELEVANT_DOMAINS = {"denios.pl", "dla-przemyslu.pl", "manutan.pl"}
_RELEVANT_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "zielony lad",
    "ppwr",
    "audyt",
    "beczka",
    "sorbent",
)


def build_ahrefs_gap_items(
    *,
    facts: list[MetricFact],
    action_ids: dict[str, list[str]],
    gsc_facts: Iterable[MetricFact],
    wordpress_facts: Iterable[MetricFact],
) -> list[TacticalQueueItem]:
    matcher = AhrefsCrossSourceMatcher.from_metric_facts(
        gsc_facts=gsc_facts, wordpress_facts=wordpress_facts
    )
    items: list[TacticalQueueItem] = []
    for index, (key, group_facts) in enumerate(_groups(facts).items(), start=1):
        gap_type, keyword, source_url, public_url, competitor = key
        topic = keyword or _short_path(public_url or source_url) or competitor or "rekord Ahrefs"
        confirmation = matcher.assess(keyword=keyword, referenced_public_url=public_url or None)
        if _off_topic(keyword, source_url, public_url, competitor):
            continue
        exact_gsc = confirmation.gsc.strength == "exact"
        exact_wp = confirmation.wordpress.strength == "exact"
        items.append(
            TacticalQueueItem(
                id=f"tq_ahrefs_{_slug(gap_type)}_{_slug(topic)}",
                title=f"Ahrefs: sprawdź lukę treści `{topic}`",
                domain=OpportunityDomain.content,
                intent=_intent(gap_type),
                priority=_priority(gap_type, topic, competitor, index),
                risk=ActionRisk.medium,
                source_connectors=_unique(
                    [
                        "ahrefs",
                        *confirmation.gsc.source_connectors,
                        *confirmation.wordpress.source_connectors,
                    ]
                ),
                evidence_ids=_unique(
                    [
                        *(f.evidence_id for f in group_facts),
                        *confirmation.gsc.evidence_ids,
                        *confirmation.wordpress.evidence_ids,
                    ]
                ),
                metric_facts=group_facts[:6],
                dimensions={
                    "gap_type": gap_type,
                    "topic": topic,
                    "keyword": keyword,
                    "source_url": source_url,
                    "referenced_public_url": public_url,
                    "competitor_domain": competitor,
                    "gsc_demand": "present" if exact_gsc else "missing",
                    "wordpress_inventory_match": "present" if exact_wp else "missing",
                    "gsc_cross_check_strength": confirmation.gsc.strength,
                    "gsc_cross_check_label": _label("GSC", confirmation),
                    "wordpress_cross_check_strength": confirmation.wordpress.strength,
                    "wordpress_cross_check_label": _label("WordPress", confirmation),
                    "gsc_overlap_terms": ", ".join(confirmation.gsc.matching_labels)
                    if exact_gsc
                    else "",
                    "wordpress_overlap_urls": ", ".join(confirmation.wordpress.matching_labels)
                    if exact_wp
                    else "",
                },
                diagnosis=_diagnosis(
                    gap_type, topic, source_url, public_url, competitor, group_facts, confirmation
                ),
                next_step=_next_step(topic, confirmation),
                blocked_claims=[
                    "wzrost ruchu",
                    "wzrost autorytetu",
                    "gwarancja pozycji",
                    "wzrost liczby leadów",
                    "plan treści bez sprawdzenia GSC i WordPress",
                ],
                action_ids=action_ids.get("ahrefs", []) if confirmation.has_exact_match else [],
            )
        )
    return items


def _groups(facts: list[MetricFact]) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "ahrefs" or fact.name not in _GAP_FACT_NAMES:
            continue
        d = fact.dimensions
        key = (
            d.get("gap_type") or _gap_type(fact.name),
            d.get("keyword", ""),
            d.get("source_url", ""),
            d.get("referenced_public_url", ""),
            _domain(d.get("competitor_domain", "")),
        )
        if any(key) and not _off_topic(*key[1:]):
            grouped.setdefault(key, []).append(fact)
    return dict(
        sorted(
            grouped.items(),
            key=lambda item: (
                _priority(item[0][0], item[0][1] or _short_path(item[0][2]), item[0][4], 0),
                item[0][1],
            ),
        )
    )


def _gap_type(name: str) -> str:
    return {
        "ahrefs_competitor_page_count": "competitor_page",
        "ahrefs_content_gap_count": "content_gap",
        "ahrefs_backlink_gap_count": "backlink_gap",
        "ahrefs_referring_domain_gap_count": "backlink_gap",
        "ahrefs_organic_keyword_gap_count": "organic_keyword_gap",
        "ahrefs_top_page_gap_count": "top_page_gap",
    }.get(name, "content_gap")


def _intent(gap_type: str) -> TacticalIntent:
    return "content_block" if gap_type == "backlink_gap" else "content_create"


def _priority(gap_type: str, topic: str, competitor: str, index: int) -> int:
    base = {
        "content_gap": 26,
        "organic_keyword_gap": 28,
        "top_page_gap": 30,
        "competitor_page": 34,
        "backlink_gap": 48,
    }.get(gap_type, 40)
    text = _norm(topic)
    if any(term in text for term in _RELEVANT_TERMS):
        base -= 4
    if competitor in _RELEVANT_DOMAINS:
        base -= 3
    return max(1, min(base + index, 69))


def _diagnosis(
    gap_type: str,
    topic: str,
    source_url: str,
    public_url: str,
    competitor: str,
    facts: list[MetricFact],
    c: AhrefsCrossSourceOverlap,
) -> str:
    context = ", ".join(
        x
        for x in (
            f"konkurent: {competitor}" if competitor else None,
            f"adres źródłowy: {_short_path(source_url)}" if source_url else None,
            f"publiczny adres: {_short_path(public_url)}" if public_url else None,
        )
        if x
    )
    fact_summary = ", ".join(f"{f.name}={f.value}" for f in sorted(facts, key=lambda x: x.name))
    context_text = f" Kontekst: {context}." if context else ""
    return (
        f"Ahrefs wskazuje: {_TYPE_LABELS.get(gap_type, 'rekord Ahrefs do sprawdzenia')} "
        f"dla tematu {topic}. Fakty: {fact_summary}.{context_text} "
        f"{_confirmation(c)} To jest sygnał do sprawdzenia contentu, "
        "nie samodzielna rekomendacja SEO."
    )


def _confirmation(c: AhrefsCrossSourceOverlap) -> str:
    if c.gsc.strength == "exact" and c.wordpress.strength == "exact":
        return "GSC i WordPress potwierdzają dokładne dopasowanie tematu."
    if c.gsc.strength == "exact":
        return "GSC potwierdza dokładne dopasowanie tematu." + (
            " WordPress ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if c.wordpress.strength == "weak"
            else " WordPress wymaga sprawdzenia."
        )
    if c.wordpress.strength == "exact":
        return "WordPress potwierdza dokładne dopasowanie tematu." + (
            " GSC ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if c.gsc.strength == "weak"
            else " GSC wymaga sprawdzenia popytu."
        )
    if c.gsc.strength == "weak" or c.wordpress.strength == "weak":
        return (
            "WILQ widzi wyłącznie słabe podobieństwo w GSC lub WordPress; nie jest to "
            "potwierdzenie popytu ani istniejącej treści."
        )
    return "Brak potwierdzonego dopasowania z GSC i WordPress w bieżących dowodach."


def _next_step(topic: str, c: AhrefsCrossSourceOverlap) -> str:
    if c.gsc.strength == "exact" and c.wordpress.strength == "exact":
        return (
            f"Zweryfikuj `{topic}` na podstawie dokładnych dopasowań GSC i WordPress, "
            "potem wybierz odświeżenie, scalenie, nową treść albo blokadę. Nie traktuj "
            "Ahrefs jako samodzielnej obietnicy ruchu."
        )
    if c.has_exact_match:
        return (
            f"Jedno źródło dokładnie potwierdza `{topic}`. Ręcznie sprawdź drugie źródło, "
            "potem wybierz odświeżenie, scalenie, nową treść albo blokadę."
        )
    if c.gsc.strength == "weak" or c.wordpress.strength == "weak":
        return (
            f"WILQ widzi tylko słabe podobieństwo dla `{topic}`. Sprawdź ręcznie GSC i spis "
            "WordPress; nie przygotowuj briefu ani decyzji o duplikacie na tej podstawie."
        )
    return (
        f"Sprawdź ręcznie `{topic}` w spisie treści GSC i WordPress, potem wybierz "
        "odświeżenie, scalenie, nową treść albo blokadę. Bez dopasowania nie twórz "
        "briefu tylko z Ahrefs."
    )


def _label(source: str, c: AhrefsCrossSourceOverlap) -> str:
    strength = c.gsc.strength if source == "GSC" else c.wordpress.strength
    return {
        "exact": f"potwierdzone dopasowanie w {source}",
        "weak": f"słabe podobieństwo w {source} — sprawdź ręcznie",
        "missing": f"brak potwierdzonego dopasowania w {source}",
    }[strength]


def _off_topic(keyword: str, source_url: str, public_url: str, competitor: str) -> bool:
    return competitor in _OFF_TOPIC_DOMAINS or any(
        term in _norm(" ".join((keyword, source_url, public_url, competitor)))
        for term in _OFF_TOPIC_TERMS
    )


def _norm(value: str) -> str:
    replacements: dict[str, str | int | None] = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    }
    return value.lower().translate(
        str.maketrans(replacements)
    )


def _domain(value: str) -> str:
    return (urlparse(value).netloc or value).removeprefix("www.").lower()


def _short_path(value: str) -> str:
    parsed = urlparse(value)
    return parsed.path.rstrip("/") or parsed.netloc or value


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in _norm(value)).strip("_")[:80] or "rekord"


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
