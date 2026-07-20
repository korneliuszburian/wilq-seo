from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.content.planning.ahrefs_overlap import (
    AhrefsCrossSourceMatch,
    AhrefsCrossSourceMatcher,
    ahrefs_gap_mapping_key,
)
from wilq.content.planning.decisions import polish_count_word, slug
from wilq.schemas import (
    ActionRisk,
    ContentAhrefsCandidateRow,
    ContentAhrefsCrossCheck,
    ContentDecisionItem,
    MetricFact,
)

AHREFS_GAP_FACT_NAMES = {
    "ahrefs_content_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
    "ahrefs_competitor_page_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_backlink_gap_count",
}
AHREFS_EKOLOGUS_RELEVANCE_TERMS = (
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
    "wanna wychwytowa",
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
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
    "oc",
    "ac",
)
CONTENT_AHREFS_GAP_TYPE_LABELS = {
    "content_gap": "luka treści",
    "organic_keyword_gap": "luka fraz",
    "top_page_gap": "mocna strona konkurencji",
    "backlink_gap": "luka linków",
    "competitor_page": "strona konkurencji",
    "ahrefs_content_gap_count": "luka treści",
    "ahrefs_organic_keyword_gap_count": "luka fraz",
    "ahrefs_top_page_gap_count": "mocna strona konkurencji",
    "ahrefs_competitor_page_count": "strona konkurencji",
    "ahrefs_referring_domain_gap_count": "luka linków",
    "ahrefs_backlink_gap_count": "luka linków",
}
CONTENT_AHREFS_RELEVANCE_LABELS = {
    "relevant": "pasuje",
    "review": "do sprawdzenia",
    "off_topic": "poza tematem",
}
CONTENT_AHREFS_REASON_LABELS = {
    "ekologus_domain_term": "pasuje do zakresu Ekologus",
    "relevant_competitor_domain": "istotny konkurent",
    "gsc_overlap": "pokrywa się z GSC",
    "gsc_overlap_weak": "słabe podobieństwo do GSC",
    "wordpress_inventory_overlap": "pokrywa się z WordPress",
    "wordpress_inventory_overlap_weak": "słabe podobieństwo do WordPress",
    "content_candidate": "propozycja treści",
    "backlink_review_only": "sprawdzenie linków",
    "off_topic_phrase": "fraza poza tematem",
    "off_topic_competitor_domain": "konkurent poza tematem",
    "broad_backlink_domain": "szeroki backlink",
}
AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS = {
    "cuk.pl",
    "ltesty.pl",
}
AHREFS_BROAD_BACKLINK_DOMAINS = {
    "apple.com",
    "google.com",
    "waze.com",
    "wikipedia.org",
    "youtube.com",
    "businessinsider.com.pl",
    "wykop.pl",
}
AHREFS_RELEVANCE_STOPWORDS = {
    "https",
    "http",
    "www",
    "com",
    "pl",
    "dla",
    "oraz",
    "jest",
    "jak",
    "czy",
    "the",
}
POLISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ż": "z",
        "ź": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ż": "Z",
        "Ź": "Z",
    }
)


@dataclass(frozen=True)
class AhrefsGapFactScore:
    fact: MetricFact
    score: int
    status: Literal["relevant", "review", "off_topic"]
    reasons: tuple[str, ...]
    gsc_cross_check: AhrefsCrossSourceMatch
    wordpress_cross_check: AhrefsCrossSourceMatch


@dataclass(frozen=True)
class AhrefsGapDecisionAnalysis:
    gap_facts: list[MetricFact]
    gap_counts: dict[str, int]
    evidence_ids: list[str]
    relevant_scores: list[AhrefsGapFactScore]
    review_scores: list[AhrefsGapFactScore]
    off_topic_scores: list[AhrefsGapFactScore]
    candidate_scores: list[AhrefsGapFactScore]
    display_facts: list[MetricFact]
    sample_keywords: list[str]
    topic_hint: str
    content_action_ids: list[str]
    gsc_overlap_count: int
    wordpress_overlap_count: int


def ahrefs_gap_record_decisions(
    metric_facts: list[MetricFact],
    action_ids: list[str],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> list[ContentDecisionItem]:
    analysis = _analyse_ahrefs_gap_decision(metric_facts, action_ids)
    if analysis is None:
        return []
    return [
        _ahrefs_gap_decision_item(
            analysis,
            knowledge_card_ids=knowledge_card_ids,
            expert_rule_ids=expert_rule_ids,
        )
    ]


def _analyse_ahrefs_gap_decision(
    metric_facts: list[MetricFact],
    action_ids: list[str],
) -> AhrefsGapDecisionAnalysis | None:
    all_gap_facts = _unique_metric_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "ahrefs" and fact.name in AHREFS_GAP_FACT_NAMES
    )
    record_gap_facts = [fact for fact in all_gap_facts if _is_ahrefs_record_gap_fact(fact)]
    gap_facts = record_gap_facts or all_gap_facts
    if not gap_facts:
        return None

    gap_counts = _ahrefs_gap_fact_counts(gap_facts)
    evidence_ids = _unique(fact.evidence_id for fact in gap_facts)
    scored_facts = _score_ahrefs_gap_facts(gap_facts, metric_facts)
    relevant_scores = [score for score in scored_facts if score.status == "relevant"]
    review_scores = [score for score in scored_facts if score.status == "review"]
    off_topic_scores = [score for score in scored_facts if score.status == "off_topic"]
    candidate_scores = [*relevant_scores, *review_scores]
    display_scores = candidate_scores or scored_facts
    display_facts = [score.fact for score in display_scores[:8]]
    sample_keywords = _ahrefs_gap_sample_keywords([score.fact for score in candidate_scores])
    competitor_domains = _unique(
        fact.dimensions.get("competitor_domain")
        for fact in gap_facts
        if fact.dimensions.get("competitor_domain")
    )
    topic_hint = ", ".join(sample_keywords[:4])
    if not topic_hint:
        topic_hint = ", ".join(competitor_domains[:4]) if competitor_domains else "brak próbek"
    has_exact_cross_source_match = any(
        score.gsc_cross_check.strength == "exact"
        or score.wordpress_cross_check.strength == "exact"
        for score in candidate_scores
    )
    content_action_ids = (
        [
            action_id
            for action_id in action_ids
            if action_id == "act_prepare_content_refresh_queue"
        ]
        if has_exact_cross_source_match
        else []
    )
    gsc_overlap_count = _ahrefs_relevance_reason_count(scored_facts, "gsc_overlap")
    wordpress_overlap_count = _ahrefs_relevance_reason_count(
        scored_facts,
        "wordpress_inventory_overlap",
    )
    return AhrefsGapDecisionAnalysis(
        gap_facts=gap_facts,
        gap_counts=gap_counts,
        evidence_ids=evidence_ids,
        relevant_scores=relevant_scores,
        review_scores=review_scores,
        off_topic_scores=off_topic_scores,
        candidate_scores=candidate_scores,
        display_facts=display_facts,
        sample_keywords=sample_keywords,
        topic_hint=topic_hint,
        content_action_ids=content_action_ids,
        gsc_overlap_count=gsc_overlap_count,
        wordpress_overlap_count=wordpress_overlap_count,
    )


def _ahrefs_gap_decision_item(
    analysis: AhrefsGapDecisionAnalysis,
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> ContentDecisionItem:
    labels = _ahrefs_gap_decision_labels(analysis)
    return ContentDecisionItem(
        id="content_decision_ahrefs_gap_records_review",
        decision_type="review_ahrefs_gap_records",
        status="ready" if analysis.candidate_scores else "blocked",
        title="Ahrefs: zweryfikuj luki SEO przed planem treści",
        summary=(
            f"WILQ ma {len(analysis.gap_facts)} {labels['records']} Ahrefs: "
            f"{analysis.gap_counts['content_gap']} {labels['content_gap']}, "
            f"{analysis.gap_counts['organic_keyword_gap']} {labels['organic_keyword_gap']}, "
            f"{analysis.gap_counts['top_page_gap']} {labels['top_page_gap']} i "
            f"{analysis.gap_counts['backlink_gap']} {labels['backlink_gap']}. "
            "Ocena jakości wskazuje "
            f"{len(analysis.relevant_scores)} {labels['relevant']}, "
            f"{len(analysis.review_scores)} {labels['review']} do ręcznej oceny i "
            f"{len(analysis.off_topic_scores)} {labels['off_topic']} poza zakresem. "
            "To jest materiał do sprawdzenia z GSC i WordPress, nie obietnica wzrostu ruchu."
        ),
        priority=18 if analysis.relevant_scores else 32 if analysis.review_scores else 45,
        metric_tiles={
            "rekordy Ahrefs": len(analysis.gap_facts),
            "pasujące": len(analysis.relevant_scores),
            "do sprawdzenia": len(analysis.review_scores),
            "poza zakresem": len(analysis.off_topic_scores),
            "Powiązanie z GSC": analysis.gsc_overlap_count,
            "Powiązanie z WordPress": analysis.wordpress_overlap_count,
            "luki treści": analysis.gap_counts["content_gap"],
            "luki linków zwrotnych": analysis.gap_counts["backlink_gap"],
        },
        queries=analysis.sample_keywords,
        query_count=len(analysis.sample_keywords),
        primary_query=analysis.sample_keywords[0] if analysis.sample_keywords else None,
        source_connectors=["ahrefs"],
        evidence_ids=analysis.evidence_ids,
        metric_facts=analysis.display_facts,
        ahrefs_candidate_rows=_ahrefs_candidate_rows(analysis.candidate_scores),
        action_ids=analysis.content_action_ids,
        knowledge_card_ids=list(knowledge_card_ids),
        expert_rule_ids=list(expert_rule_ids),
        blocked_claims=[
            "rekomendacja treści poza zakresem",
            "plan treści bez kontroli trafności",
            "wzrost ruchu",
            "wzrost autorytetu",
            "gwarancja pozycji",
            "wzrost liczby leadów",
        ],
        rationale=(
            "Ahrefs wskazuje luki względem konkurencji, ale ocena jakości rozdziela "
            "rekordy pasujące do zakresu Ekologus od tematów szerokich i poza zakresem. "
            "WILQ nie może zrobić planu treści z rekordu bez filtrowania, popytu z GSC "
            "i dopasowania w spisie treści WordPress."
        ),
        next_step=(
            f"Najpierw przejrzyj pasujące rekordy: {analysis.topic_hint}. Odrzuć "
            f"{len(analysis.off_topic_scores)} rekordów poza zakresem i dopiero potem "
            "połącz sensowne tematy z GSC i WordPress jako odświeżenie, scalenie, "
            "zachowanie, utworzenie albo blokadę."
        ),
        risk=ActionRisk.medium if analysis.candidate_scores else ActionRisk.high,
    )


def _ahrefs_gap_decision_labels(analysis: AhrefsGapDecisionAnalysis) -> dict[str, str]:
    return {
        "records": polish_count_word(
            len(analysis.gap_facts),
            "rekord luk",
            "rekordy luk",
            "rekordów luk",
        ),
        "content_gap": polish_count_word(
            analysis.gap_counts["content_gap"],
            "luka treści",
            "luki treści",
            "luk treści",
        ),
        "organic_keyword_gap": polish_count_word(
            analysis.gap_counts["organic_keyword_gap"],
            "luka w słowach organicznych",
            "luki w słowach organicznych",
            "luk w słowach organicznych",
        ),
        "top_page_gap": polish_count_word(
            analysis.gap_counts["top_page_gap"],
            "luka w najlepszych stronach konkurencji",
            "luki w najlepszych stronach konkurencji",
            "luk w najlepszych stronach konkurencji",
        ),
        "backlink_gap": polish_count_word(
            analysis.gap_counts["backlink_gap"],
            "luka linków zwrotnych",
            "luki linków zwrotnych",
            "luk linków zwrotnych",
        ),
        "relevant": polish_count_word(
            len(analysis.relevant_scores),
            "pasujący",
            "pasujące",
            "pasujących",
        ),
        "review": polish_count_word(
            len(analysis.review_scores),
            "rekord",
            "rekordy",
            "rekordów",
        ),
        "off_topic": polish_count_word(
            len(analysis.off_topic_scores),
            "rekord",
            "rekordy",
            "rekordów",
        ),
    }


def _ahrefs_candidate_rows(
    scores: list[AhrefsGapFactScore],
) -> list[ContentAhrefsCandidateRow]:
    return [_ahrefs_candidate_row(score) for score in scores[:6]]


def ahrefs_cross_source_candidate_rows(
    gap_facts: list[MetricFact],
    all_content_facts: list[MetricFact],
    *,
    limit: int | None = 6,
) -> list[ContentAhrefsCandidateRow]:
    scored_facts = _score_ahrefs_gap_facts(gap_facts, all_content_facts)
    reviewable_scores = [
        score for score in scored_facts if score.status in {"relevant", "review"}
    ]
    selected_scores = reviewable_scores if limit is None else reviewable_scores[:limit]
    return [_ahrefs_candidate_row(score) for score in selected_scores]


def _ahrefs_candidate_row(score: AhrefsGapFactScore) -> ContentAhrefsCandidateRow:
    fact = score.fact
    dimensions = fact.dimensions
    topic = _ahrefs_candidate_topic(fact)
    gsc_cross_check = score.gsc_cross_check
    wordpress_cross_check = score.wordpress_cross_check
    gsc_overlap = gsc_cross_check.strength == "exact"
    wordpress_overlap = wordpress_cross_check.strength == "exact"
    return ContentAhrefsCandidateRow(
        id=f"ahrefs_candidate_{slug(f'{topic}_{fact.name}_{fact.evidence_id}')}",
        topic=topic,
        gap_type=dimensions.get("gap_type") or fact.name,
        gap_type_label=_content_ahrefs_gap_type_label(dimensions.get("gap_type") or fact.name),
        relevance_status=score.status,
        relevance_status_label=_content_ahrefs_relevance_label(score.status),
        relevance_score=score.score,
        business_relevance_reasons=list(score.reasons),
        business_relevance_reason_labels=[
            _content_ahrefs_reason_label(reason) for reason in score.reasons
        ],
        gsc_demand="present" if gsc_overlap else "missing",
        gsc_demand_label=_gsc_demand_label(gsc_cross_check),
        gsc_cross_check=_cross_check_view(gsc_cross_check, source="GSC"),
        wordpress_inventory_match="present" if wordpress_overlap else "missing",
        wordpress_inventory_match_label=_wordpress_inventory_match_label(wordpress_cross_check),
        wordpress_cross_check=_cross_check_view(wordpress_cross_check, source="WordPress"),
        gsc_overlap_terms=list(gsc_cross_check.matching_labels) if gsc_overlap else [],
        wordpress_overlap_urls=(
            list(wordpress_cross_check.matching_labels) if wordpress_overlap else []
        ),
        keyword=dimensions.get("keyword") or None,
        competitor_domain=dimensions.get("competitor_domain") or None,
        source_url=dimensions.get("source_url") or None,
        referenced_public_url=dimensions.get("referenced_public_url") or None,
        mapping_key=ahrefs_gap_mapping_key(
            gap_type=dimensions.get("gap_type") or fact.name,
            source_url=dimensions.get("source_url") or None,
            competitor_domain=dimensions.get("competitor_domain") or None,
            keyword=dimensions.get("keyword") or None,
        ),
        metric_name=fact.name,
        metric_value=fact.value,
        source_connectors=_unique(
            [
                fact.source_connector,
                *gsc_cross_check.source_connectors,
                *wordpress_cross_check.source_connectors,
            ]
        ),
        evidence_ids=_unique(
            [
                fact.evidence_id,
                *gsc_cross_check.evidence_ids,
                *wordpress_cross_check.evidence_ids,
            ]
        ),
        next_step=_ahrefs_candidate_next_step(score, topic),
    )


def _cross_check_view(
    check: AhrefsCrossSourceMatch,
    *,
    source: str,
) -> ContentAhrefsCrossCheck:
    labels = {
        "exact": f"potwierdzone dopasowanie w {source}",
        "weak": f"słabe podobieństwo w {source} — sprawdź ręcznie",
        "missing": f"brak potwierdzonego dopasowania w {source}",
    }
    return ContentAhrefsCrossCheck(
        strength=check.strength,
        label=labels[check.strength],
        matching_labels=list(check.matching_labels),
        source_connectors=list(check.source_connectors),
        evidence_ids=list(check.evidence_ids),
    )


def _gsc_demand_label(check: AhrefsCrossSourceMatch) -> str:
    if check.strength == "exact":
        return "jest w GSC"
    if check.strength == "weak":
        return "słabe podobieństwo GSC — sprawdź ręcznie"
    return "brak potwierdzenia w GSC"


def _wordpress_inventory_match_label(check: AhrefsCrossSourceMatch) -> str:
    if check.strength == "exact":
        return "jest w WordPress"
    if check.strength == "weak":
        return "słabe podobieństwo WordPress — sprawdź ręcznie"
    return "brak potwierdzenia w WordPress"


def _content_ahrefs_gap_type_label(value: str) -> str:
    return CONTENT_AHREFS_GAP_TYPE_LABELS.get(value, _content_contract_label(value))


def _content_ahrefs_relevance_label(value: str) -> str:
    return CONTENT_AHREFS_RELEVANCE_LABELS.get(value, _content_contract_label(value))


def _content_ahrefs_reason_label(value: str) -> str:
    return CONTENT_AHREFS_REASON_LABELS.get(value, _content_contract_label(value))


def _content_contract_label(_value: str) -> str:
    return "warunek treści do sprawdzenia"


def _ahrefs_candidate_topic(fact: MetricFact) -> str:
    dimensions = fact.dimensions
    for key in ("keyword", "source_url", "competitor_domain"):
        value = dimensions.get(key)
        if value:
            return value
    referenced_public_url = dimensions.get("referenced_public_url")
    if referenced_public_url:
        return referenced_public_url
    return fact.name


def _ahrefs_candidate_next_step(score: AhrefsGapFactScore, topic: str) -> str:
    overlap_labels = []
    if score.gsc_cross_check.strength == "exact":
        overlap_labels.append(f"GSC: {', '.join(score.gsc_cross_check.matching_labels[:2])}")
    if score.wordpress_cross_check.strength == "exact":
        overlap_labels.append(f"WP: {len(score.wordpress_cross_check.matching_labels)} URL")
    overlap_context = f" Wspólne sygnały: {'; '.join(overlap_labels)}." if overlap_labels else ""
    if (
        score.gsc_cross_check.strength == "weak"
        or score.wordpress_cross_check.strength == "weak"
    ):
        return (
            f"WILQ widzi tylko słabe podobieństwo dla `{topic}`. Sprawdź ręcznie GSC "
            "i spis WordPress; nie traktuj go jako potwierdzenia popytu ani duplikatu."
        )
    if score.status == "relevant":
        return (
            f"Zweryfikuj `{topic}` z GSC i spisem treści WordPress, potem zdecyduj: "
            f"odświeżenie, scalenie, utworzenie albo blokada.{overlap_context}"
        )
    if score.status == "review":
        return (
            f"Sprawdź ręcznie, czy `{topic}` pasuje do Ekologus; bez pokrycia w GSC/WP "
            "nie twórz planu treści."
        )
    return f"Odrzuć `{topic}` jako poza zakresem, chyba że operator poda biznesowy wyjątek."


def _ahrefs_gap_fact_counts(metric_facts: list[MetricFact]) -> dict[str, int]:
    counts = {
        "content_gap": 0,
        "organic_keyword_gap": 0,
        "top_page_gap": 0,
        "competitor_page": 0,
        "backlink_gap": 0,
    }
    for fact in metric_facts:
        gap_type = fact.dimensions.get("gap_type")
        if gap_type in counts:
            counts[gap_type] += 1
            continue
        if fact.name == "ahrefs_content_gap_count":
            counts["content_gap"] += 1
        elif fact.name == "ahrefs_organic_keyword_gap_count":
            counts["organic_keyword_gap"] += 1
        elif fact.name == "ahrefs_top_page_gap_count":
            counts["top_page_gap"] += 1
        elif fact.name == "ahrefs_competitor_page_count":
            counts["competitor_page"] += 1
        elif fact.name in {"ahrefs_referring_domain_gap_count", "ahrefs_backlink_gap_count"}:
            counts["backlink_gap"] += 1
    return counts


def _is_ahrefs_record_gap_fact(fact: MetricFact) -> bool:
    return any(
        fact.dimensions.get(key)
        for key in (
            "gap_type",
            "keyword",
            "source_url",
            "referenced_public_url",
            "competitor_domain",
        )
    )


def _score_ahrefs_gap_facts(
    gap_facts: list[MetricFact],
    all_content_facts: list[MetricFact],
) -> list[AhrefsGapFactScore]:
    gsc_facts = [
        fact for fact in all_content_facts if fact.source_connector == "google_search_console"
    ]
    wordpress_facts = [
        fact for fact in all_content_facts if fact.source_connector.startswith("wordpress")
    ]
    cross_source_matcher = AhrefsCrossSourceMatcher.from_metric_facts(
        gsc_facts=gsc_facts,
        wordpress_facts=wordpress_facts,
    )
    scored = [
        _score_ahrefs_gap_fact(
            fact,
            cross_source_matcher=cross_source_matcher,
        )
        for fact in gap_facts
    ]
    return sorted(
        scored,
        key=lambda item: (
            {"relevant": 0, "review": 1, "off_topic": 2}[item.status],
            -item.score,
            item.fact.name,
            item.fact.dimensions.get("keyword", ""),
            item.fact.dimensions.get("source_url", ""),
        ),
    )


def _score_ahrefs_gap_fact(
    fact: MetricFact,
    *,
    cross_source_matcher: AhrefsCrossSourceMatcher,
) -> AhrefsGapFactScore:
    dimensions = fact.dimensions
    keyword = dimensions.get("keyword", "")
    source_url = dimensions.get("source_url", "")
    referenced_public_url = dimensions.get("referenced_public_url", "")
    competitor_domain = _normalized_domain(dimensions.get("competitor_domain"))
    source_domain = _normalized_domain(dimensions.get("referring_domain") or source_url)
    text = " ".join(
        value
        for value in (
            keyword,
            source_url,
            referenced_public_url,
            competitor_domain or "",
            dimensions.get("best_position_url", ""),
        )
        if value
    )
    normalized_text = _normalize_text(text)
    tokens = _tokens_from_text(text)
    cross_source_overlap = cross_source_matcher.assess(
        keyword=keyword,
        referenced_public_url=referenced_public_url or None,
    )
    score = 0
    reasons: list[str] = []

    if any(
        _matches_normalized_term(normalized_text, tokens, term)
        for term in AHREFS_EKOLOGUS_RELEVANCE_TERMS
    ):
        score += 4
        reasons.append("ekologus_domain_term")
    if competitor_domain in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        score += 3
        reasons.append("relevant_competitor_domain")
    if cross_source_overlap.gsc.strength == "exact":
        score += 2
        reasons.append("gsc_overlap")
    elif cross_source_overlap.gsc.strength == "weak":
        reasons.append("gsc_overlap_weak")
    if cross_source_overlap.wordpress.strength == "exact":
        score += 2
        reasons.append("wordpress_inventory_overlap")
    elif cross_source_overlap.wordpress.strength == "weak":
        reasons.append("wordpress_inventory_overlap_weak")

    gap_type = dimensions.get("gap_type", "")
    if gap_type in {"content_gap", "organic_keyword_gap", "top_page_gap"}:
        score += 1
        reasons.append("content_candidate")
    elif gap_type == "backlink_gap":
        score -= 1
        reasons.append("backlink_review_only")

    hard_off_topic = False
    if any(
        _matches_normalized_term(normalized_text, tokens, term) for term in AHREFS_OFF_TOPIC_TERMS
    ):
        score -= 6
        hard_off_topic = True
        reasons.append("off_topic_phrase")
    if competitor_domain in AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS:
        score -= 4
        hard_off_topic = True
        reasons.append("off_topic_competitor_domain")
    if source_domain in AHREFS_BROAD_BACKLINK_DOMAINS:
        score -= 3
        reasons.append("broad_backlink_domain")

    if hard_off_topic or score < 0:
        status: Literal["relevant", "review", "off_topic"] = "off_topic"
    elif score >= 4:
        status = "relevant"
    else:
        status = "review"
    return AhrefsGapFactScore(
        fact=fact,
        score=score,
        status=status,
        reasons=tuple(reasons),
        gsc_cross_check=cross_source_overlap.gsc,
        wordpress_cross_check=cross_source_overlap.wordpress,
    )


def _ahrefs_relevance_reason_count(
    scores: list[AhrefsGapFactScore],
    reason: str,
) -> int:
    return sum(1 for score in scores if reason in score.reasons)


def _tokens_from_text(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", _normalize_text(text))
        if len(token) > 2 and token not in AHREFS_RELEVANCE_STOPWORDS
    }


def _matches_normalized_term(normalized_text: str, tokens: set[str], term: str) -> bool:
    normalized_term = _normalize_text(term)
    if " " in normalized_term:
        return normalized_term in normalized_text
    return normalized_term in tokens


def _normalize_text(text: str) -> str:
    translated = text.translate(POLISH_ASCII_TRANSLATION)
    ascii_text = unicodedata.normalize("NFKD", translated).encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _normalized_domain(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _normalize_text(value).replace("https://", "").replace("http://", "")
    normalized = normalized.split("/", maxsplit=1)[0].removeprefix("www.")
    return normalized or None


def _ahrefs_gap_sample_keywords(metric_facts: list[MetricFact]) -> list[str]:
    return _unique(
        fact.dimensions.get("keyword") for fact in metric_facts if fact.dimensions.get("keyword")
    )[:6]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _unique_metric_facts(values: Iterable[MetricFact]) -> list[MetricFact]:
    unique_facts: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in values:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted((str(key), str(value)) for key, value in fact.dimensions.items())),
        )
        unique_facts.setdefault(key, fact)
    return list(unique_facts.values())
