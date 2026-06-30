from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.content.planning.decisions import polish_count_word, slug
from wilq.schemas import ActionRisk, ContentAhrefsCandidateRow, ContentDecisionItem, MetricFact

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
    "wordpress_inventory_overlap": "pokrywa się z WordPress",
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
    gsc_overlap_terms: tuple[str, ...] = ()
    wordpress_overlap_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContentSignal:
    label: str
    tokens: frozenset[str]


def ahrefs_gap_record_decisions(
    metric_facts: list[MetricFact],
    action_ids: list[str],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> list[ContentDecisionItem]:
    all_gap_facts = _unique_metric_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "ahrefs" and fact.name in AHREFS_GAP_FACT_NAMES
    )
    record_gap_facts = [fact for fact in all_gap_facts if _is_ahrefs_record_gap_fact(fact)]
    gap_facts = record_gap_facts or all_gap_facts
    if not gap_facts:
        return []

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
    content_action_ids = [
        action_id for action_id in action_ids if action_id == "act_prepare_content_refresh_queue"
    ]
    gsc_overlap_count = _ahrefs_relevance_reason_count(scored_facts, "gsc_overlap")
    wordpress_overlap_count = _ahrefs_relevance_reason_count(
        scored_facts,
        "wordpress_inventory_overlap",
    )
    decision_status: Literal["ready", "blocked"] = "ready" if candidate_scores else "blocked"
    relevant_label = polish_count_word(len(relevant_scores), "pasujący", "pasujące", "pasujących")
    review_label = polish_count_word(len(review_scores), "rekord", "rekordy", "rekordów")
    off_topic_label = polish_count_word(
        len(off_topic_scores),
        "rekord",
        "rekordy",
        "rekordów",
    )
    ahrefs_gap_record_label = polish_count_word(
        len(gap_facts),
        "rekord luk",
        "rekordy luk",
        "rekordów luk",
    )
    content_gap_label = polish_count_word(
        gap_counts["content_gap"],
        "luka treści",
        "luki treści",
        "luk treści",
    )
    organic_keyword_gap_label = polish_count_word(
        gap_counts["organic_keyword_gap"],
        "luka w słowach organicznych",
        "luki w słowach organicznych",
        "luk w słowach organicznych",
    )
    top_page_gap_label = polish_count_word(
        gap_counts["top_page_gap"],
        "luka w najlepszych stronach konkurencji",
        "luki w najlepszych stronach konkurencji",
        "luk w najlepszych stronach konkurencji",
    )
    backlink_gap_label = polish_count_word(
        gap_counts["backlink_gap"],
        "luka linków zwrotnych",
        "luki linków zwrotnych",
        "luk linków zwrotnych",
    )
    return [
        ContentDecisionItem(
            id="content_decision_ahrefs_gap_records_review",
            decision_type="review_ahrefs_gap_records",
            status=decision_status,
            title="Ahrefs: zweryfikuj luki SEO przed planem treści",
            summary=(
                f"WILQ ma {len(gap_facts)} {ahrefs_gap_record_label} Ahrefs: "
                f"{gap_counts['content_gap']} {content_gap_label}, "
                f"{gap_counts['organic_keyword_gap']} {organic_keyword_gap_label}, "
                f"{gap_counts['top_page_gap']} {top_page_gap_label} i "
                f"{gap_counts['backlink_gap']} {backlink_gap_label}. Ocena jakości wskazuje "
                f"{len(relevant_scores)} {relevant_label}, "
                f"{len(review_scores)} {review_label} do ręcznej oceny i "
                f"{len(off_topic_scores)} {off_topic_label} poza zakresem. "
                "To jest materiał do sprawdzenia z GSC i WordPress, nie obietnica wzrostu ruchu."
            ),
            priority=18 if relevant_scores else 32 if review_scores else 45,
            metric_tiles={
                "rekordy Ahrefs": len(gap_facts),
                "pasujące": len(relevant_scores),
                "do sprawdzenia": len(review_scores),
                "poza zakresem": len(off_topic_scores),
                "Powiązanie z GSC": gsc_overlap_count,
                "Powiązanie z WordPress": wordpress_overlap_count,
                "luki treści": gap_counts["content_gap"],
                "luki linków zwrotnych": gap_counts["backlink_gap"],
            },
            queries=sample_keywords,
            query_count=len(sample_keywords),
            primary_query=sample_keywords[0] if sample_keywords else None,
            source_connectors=["ahrefs"],
            evidence_ids=evidence_ids,
            metric_facts=display_facts,
            ahrefs_candidate_rows=_ahrefs_candidate_rows(candidate_scores),
            action_ids=content_action_ids,
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
                f"Najpierw przejrzyj pasujące rekordy: {topic_hint}. Odrzuć "
                f"{len(off_topic_scores)} rekordów poza zakresem i dopiero potem "
                "połącz sensowne tematy z GSC i WordPress jako odświeżenie, scalenie, "
                "zachowanie, utworzenie albo blokadę."
            ),
            risk=ActionRisk.medium if candidate_scores else ActionRisk.high,
        )
    ]


def _ahrefs_candidate_rows(
    scores: list[AhrefsGapFactScore],
) -> list[ContentAhrefsCandidateRow]:
    return [_ahrefs_candidate_row(score) for score in scores[:6]]


def _ahrefs_candidate_row(score: AhrefsGapFactScore) -> ContentAhrefsCandidateRow:
    fact = score.fact
    dimensions = fact.dimensions
    topic = _ahrefs_candidate_topic(fact)
    gsc_overlap = "gsc_overlap" in score.reasons
    wordpress_overlap = "wordpress_inventory_overlap" in score.reasons
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
        gsc_demand_label="jest w GSC" if gsc_overlap else "brak dopasowania w GSC",
        wordpress_inventory_match="present" if wordpress_overlap else "missing",
        wordpress_inventory_match_label=(
            "jest w WordPress" if wordpress_overlap else "brak dopasowania w WordPress"
        ),
        gsc_overlap_terms=list(score.gsc_overlap_terms),
        wordpress_overlap_urls=list(score.wordpress_overlap_urls),
        keyword=dimensions.get("keyword") or None,
        competitor_domain=dimensions.get("competitor_domain") or None,
        source_url=dimensions.get("source_url") or None,
        referenced_public_url=dimensions.get("referenced_public_url") or None,
        metric_name=fact.name,
        metric_value=fact.value,
        evidence_ids=[fact.evidence_id],
        next_step=_ahrefs_candidate_next_step(score, topic),
    )


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
    if score.gsc_overlap_terms:
        overlap_labels.append(f"GSC: {', '.join(score.gsc_overlap_terms[:2])}")
    if score.wordpress_overlap_urls:
        overlap_labels.append(f"WP: {len(score.wordpress_overlap_urls)} URL")
    overlap_context = f" Wspólne sygnały: {'; '.join(overlap_labels)}." if overlap_labels else ""
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
    gsc_signals = _content_signals(
        all_content_facts,
        source_connector="google_search_console",
        dimension_keys=("query", "page"),
        label_keys=("query", "page"),
    )
    wordpress_signals = _content_signals(
        all_content_facts,
        source_connector_prefix="wordpress",
        dimension_keys=("content_url", "title", "slug", "path"),
        label_keys=("content_url", "title", "slug", "path"),
    )
    scored = [
        _score_ahrefs_gap_fact(
            fact,
            gsc_signals=gsc_signals,
            wordpress_signals=wordpress_signals,
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
    gsc_signals: tuple[ContentSignal, ...],
    wordpress_signals: tuple[ContentSignal, ...],
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
    gsc_overlap_terms = _matching_content_signal_labels(tokens, gsc_signals)
    wordpress_overlap_urls = _matching_content_signal_labels(tokens, wordpress_signals)
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
    if gsc_overlap_terms:
        score += 2
        reasons.append("gsc_overlap")
    if wordpress_overlap_urls:
        score += 2
        reasons.append("wordpress_inventory_overlap")

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
        gsc_overlap_terms=gsc_overlap_terms,
        wordpress_overlap_urls=wordpress_overlap_urls,
    )


def _content_signals(
    facts: list[MetricFact],
    *,
    dimension_keys: tuple[str, ...],
    label_keys: tuple[str, ...],
    source_connector: str | None = None,
    source_connector_prefix: str | None = None,
) -> tuple[ContentSignal, ...]:
    signal_tokens: dict[str, set[str]] = {}
    for fact in facts:
        if source_connector is not None and fact.source_connector != source_connector:
            continue
        if source_connector_prefix is not None and not fact.source_connector.startswith(
            source_connector_prefix
        ):
            continue
        label = _first_dimension_value(fact, label_keys)
        if not label:
            continue
        tokens: set[str] = set()
        for key in dimension_keys:
            tokens.update(_tokens_from_text(fact.dimensions.get(key, "")))
        if tokens:
            signal_tokens.setdefault(label, set()).update(tokens)
    return tuple(
        ContentSignal(label=label, tokens=frozenset(tokens))
        for label, tokens in signal_tokens.items()
    )


def _first_dimension_value(fact: MetricFact, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = fact.dimensions.get(key)
        if value:
            return value
    return None


def _matching_content_signal_labels(
    tokens: set[str],
    signals: tuple[ContentSignal, ...],
    *,
    limit: int = 4,
) -> tuple[str, ...]:
    return tuple(_unique(signal.label for signal in signals if tokens & signal.tokens)[:limit])


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
