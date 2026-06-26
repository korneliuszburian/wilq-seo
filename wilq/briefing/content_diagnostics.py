from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ContentAhrefsCandidateRow,
    ContentDecisionItem,
    ContentDiagnosticSection,
    ContentDiagnosticsResponse,
    ContentMarketerDecision,
    ContentOperatorSummary,
    ContentPreflightItem,
    ContentPreflightResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)
from wilq.storage.metric_store import metric_store

CONTENT_CONNECTOR_IDS = (
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
    "google_analytics_4",
    "ahrefs",
)
PRIMARY_CONTENT_CONNECTORS = ("google_search_console", "wordpress_ekologus")
CONTENT_METRIC_FACT_LIMIT = 300
CONTENT_GSC_METRIC_FACT_LIMIT = 1200
CONTENT_WORDPRESS_METRIC_FACT_LIMIT = 1200
CONTENT_SOURCE_SITE_HOSTS = {
    "www.ekologus.pl",
    "ekologus.pl",
    "sklep.ekologus.pl",
}
GSC_CONTENT_KNOWLEDGE_CARD_IDS = (
    "card_gsc_seo_content_playbook",
    "card_wordpress_content_refresh_playbook",
)
GSC_CONTENT_EXPERT_RULE_IDS = (
    "seo_gsc_opportunities_v1",
    "seo_query_page_matrix_v1",
    "seo_content_decay_v1",
    "seo_cannibalization_v1",
    "content_duplication_rules_v1",
    "content_brief_rules_v1",
)
AHREFS_CONTENT_KNOWLEDGE_CARD_IDS = (
    "card_ahrefs_content_gap_playbook",
    "card_gsc_seo_content_playbook",
    "card_wordpress_content_refresh_playbook",
)
AHREFS_CONTENT_EXPERT_RULE_IDS = (
    "content_brief_rules_v1",
    "content_duplication_rules_v1",
)
GA4_TRACKING_KNOWLEDGE_CARD_IDS = ("card_ga4_behavior_diagnostics_playbook",)
GA4_TRACKING_EXPERT_RULE_IDS = ("ga4_diagnostics_v1",)
ContentDecisionType = Literal[
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records",
]
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
class ContentDecisionMetrics:
    primary_query: str | None
    total_clicks: int | None
    total_impressions: int | None
    aggregate_ctr: float | None
    best_average_position: float | None


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


def build_content_diagnostics(
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> ContentDiagnosticsResponse:
    connectors = [
        connector
        for connector_id in CONTENT_CONNECTOR_IDS
        if (connector := get_connector_status(connector_id)) is not None
    ]
    latest_refreshes = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    metric_facts = (
        metric_facts
        if metric_facts is not None
        else _content_metric_facts(CONTENT_CONNECTOR_IDS)
    )
    live_data_available = _primary_content_data_available(metric_facts, latest_refreshes)
    trusted_facts = metric_facts if live_data_available else []
    all_tactical_items = (
        tactical_items if tactical_items is not None else build_tactical_queue().items
    )
    content_tactical_items = [
        item
        for item in all_tactical_items
        if item.domain == OpportunityDomain.gsc_seo
        or item.source_connectors.count("wordpress_ekologus") > 0
    ]
    action_ids = _content_action_ids(actions if actions is not None else list_actions())
    decision_queue = _content_decision_queue(
        all_tactical_items,
        trusted_facts,
        action_ids,
        latest_refreshes,
    )
    sections = [
        _query_page_section(latest_refreshes, trusted_facts, content_tactical_items, action_ids),
        _inventory_match_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
        ),
        _content_action_safety_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
        ),
    ]
    return ContentDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connectors=connectors,
        latest_refreshes=latest_refreshes,
        live_data_available=live_data_available,
        query_page_count=_query_page_count(content_tactical_items),
        matched_inventory_count=_matched_inventory_count(content_tactical_items),
        operator_summary=_operator_summary(decision_queue, sections, action_ids),
        marketer_decision=_content_marketer_decision(decision_queue, sections),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            [
                *(evidence_id for section in sections for evidence_id in section.evidence_ids),
                *(
                    evidence_id
                    for decision in decision_queue
                    for evidence_id in decision.evidence_ids
                ),
            ]
        ),
        action_ids=_unique(
            [
                *(action_id for section in sections for action_id in section.action_ids),
                *(action_id for decision in decision_queue for action_id in decision.action_ids),
            ]
        ),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def build_content_preflight(
    diagnostics: ContentDiagnosticsResponse | None = None,
) -> ContentPreflightResponse:
    diagnostics = diagnostics or build_content_diagnostics()
    items = [_content_preflight_item(decision) for decision in diagnostics.decision_queue]
    primary_item = next((item for item in items if item.status != "blocked"), None)
    return ContentPreflightResponse(
        strict_instruction=(
            "Bramka pisania działa przed briefem i szkicem. Nie wolno pisać "
            "ani przygotowywać szkicu bez wyniku bramki pisania, briefu, "
            "sprawdzenia ryzykownych obietnic i decyzji człowieka."
        ),
        primary_item=primary_item or (items[0] if items else None),
        items=items,
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        source_connectors=_unique(
            connector for item in items for connector in item.source_connectors
        ),
        blocker_count=sum(1 for item in items if item.status == "blocked"),
    )


def _operator_summary(
    decisions: list[ContentDecisionItem],
    sections: list[ContentDiagnosticSection],
    action_ids: list[str],
) -> ContentOperatorSummary:
    top_decisions = decisions[:4]
    current_site_match_count = sum(
        1
        for decision in decisions
        if _content_decision_has_public_final_canonical(decision)
    )
    return ContentOperatorSummary(
        title="Co marketer ma zrobić teraz z treściami",
        summary=(
            "WILQ łączy zapytania i URL-e z GSC ze spisem treści WordPress. "
            "Najpierw obsłuż istniejące URL-e i klastry zapytań, potem dopiero "
            "twórz nowe treści. Bez dowodów nie wolno twierdzić, że wzrosną "
            "leady, pozycje albo konwersje."
        ),
        next_step=(
            "Przejdź przez top decyzje contentowe: odśwież, scal, utwórz albo "
            "zablokuj. Potem sprawdź w WILQ tylko właściwą akcję."
        ),
        top_decision_ids=[decision.id for decision in top_decisions],
        confirmed_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "found"
        ),
        missing_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "missing"
        ),
        current_site_match_count=current_site_match_count,
        decision_type_labels=_unique(
            _content_decision_type_summary_label(decision.decision_type)
            for decision in decisions
        ),
        source_connectors=_unique(
            connector
            for decision in top_decisions
            for connector in decision.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id
            for decision in top_decisions
            for evidence_id in decision.evidence_ids
        ),
        action_ids=action_ids,
        blocked_claims=_unique(
            claim for section in sections for claim in section.blocked_claims
        ),
    )


def _content_marketer_decision(
    decisions: list[ContentDecisionItem],
    sections: list[ContentDiagnosticSection],
) -> ContentMarketerDecision | None:
    if not decisions:
        return None
    decision = decisions[0]
    blocked_claims = _content_marketer_blocked_claims(
        [
            *decision.blocked_claims,
            *(claim for section in sections for claim in section.blocked_claims),
        ]
    )
    source_public_url = decision.source_public_url or decision.page
    preview_url = decision.preview_url
    intended_final_url = decision.intended_final_url or source_public_url
    final_canonical_url = _content_decision_final_canonical_url(decision)
    missing_inputs = _content_marketer_missing_inputs(
        decision,
        final_canonical_url=final_canonical_url,
    )
    return ContentMarketerDecision(
        id=f"marketer_{decision.id}",
        technical_decision_id=decision.id,
        status=decision.status,
        decision=_content_marketer_decision_text(decision),
        mode_label=_content_marketer_mode_label(decision.decision_type),
        why_it_matters=_content_marketer_why(decision),
        safe_next_action=_content_marketer_next_action(decision),
        blocked_claims=blocked_claims,
        missing_inputs=missing_inputs,
        evidence_summary=_content_marketer_evidence_summary(decision),
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        measurement_plan=_content_marketer_measurement_plan(decision),
        source_public_url=source_public_url,
        preview_url=preview_url,
        intended_final_url=intended_final_url,
        final_canonical_url=final_canonical_url,
    )


def _content_decision_final_canonical_url(decision: ContentDecisionItem) -> str | None:
    if decision.final_canonical_url:
        return decision.final_canonical_url
    return decision.intended_final_url or decision.source_public_url or decision.page


def _content_preflight_item(decision: ContentDecisionItem) -> ContentPreflightItem:
    recommended_mode = _content_preflight_mode(decision)
    status = _content_preflight_status(decision, recommended_mode)
    source_public_url = decision.source_public_url or decision.page
    final_canonical_url = _content_decision_final_canonical_url(decision)
    missing_inputs = _content_marketer_missing_inputs(
        decision,
        final_canonical_url=final_canonical_url,
    )
    claim_gate_status = (
        "needs_claim_review" if decision.blocked_claims else "ready_for_claim_review"
    )
    service_mapping_status = (
        "needs_service_review"
        if decision.decision_type in {"review_ahrefs_gap_records", "inventory_check_before_create"}
        else "ready_for_service_review"
    )
    return ContentPreflightItem(
        id=f"preflight_{decision.id}",
        technical_decision_id=decision.id,
        recommended_mode=recommended_mode,
        status=status,
        create_allowed=recommended_mode == "create" and status == "allowed",
        draft_allowed=False,
        wordpress_draft_allowed=False,
        sales_brief_allowed=status in {"allowed", "review_required"}
        and recommended_mode in {"preserve", "refresh", "merge"},
        source_public_url=source_public_url,
        preview_url=decision.preview_url,
        intended_final_url=decision.intended_final_url or source_public_url,
        final_canonical_url=final_canonical_url,
        inventory_gate_status=decision.inventory_gate_status,
        canonical_gate_status=decision.canonical_gate_status,
        duplicate_gate_status=decision.duplicate_gate_status,
        claim_gate_status=claim_gate_status,
        service_mapping_status=service_mapping_status,
        similar_existing_urls=_content_preflight_similar_urls(decision),
        query_overlap_summary=_content_preflight_query_overlap(decision),
        blocked_claims=_content_marketer_blocked_claims(decision.blocked_claims),
        missing_inputs=missing_inputs,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        next_step=_content_preflight_next_step(decision, recommended_mode, status),
    )


def _content_preflight_mode(
    decision: ContentDecisionItem,
) -> Literal["preserve", "refresh", "merge", "create", "block"]:
    if decision.decision_type == "refresh_or_merge":
        return "refresh"
    if decision.decision_type == "merge_create_after_inventory_check":
        return "merge"
    if decision.decision_type == "inventory_check_before_create":
        return "block"
    return "block"


def _content_preflight_status(
    decision: ContentDecisionItem,
    recommended_mode: Literal["preserve", "refresh", "merge", "create", "block"],
) -> Literal["allowed", "review_required", "blocked"]:
    if decision.status == "blocked" or recommended_mode == "block":
        return "blocked"
    return "review_required"


def _content_preflight_similar_urls(decision: ContentDecisionItem) -> list[str]:
    urls = []
    if decision.wordpress_match == "found":
        urls.append(_content_decision_final_canonical_url(decision) or decision.source_public_url)
    urls.extend(
        url
        for row in decision.ahrefs_candidate_rows
        for url in row.wordpress_overlap_urls
    )
    return _unique(url for url in urls if url)


def _content_preflight_query_overlap(decision: ContentDecisionItem) -> str:
    if decision.query_count <= 0:
        return "Brak potwierdzonych wspólnych zapytań."
    primary = f"; główne zapytanie: {decision.primary_query}" if decision.primary_query else ""
    return f"{decision.query_count} zapytań z GSC{primary}."


def _content_preflight_next_step(
    decision: ContentDecisionItem,
    recommended_mode: Literal["preserve", "refresh", "merge", "create", "block"],
    status: Literal["allowed", "review_required", "blocked"],
) -> str:
    if status == "blocked":
        return decision.next_step
    if recommended_mode == "refresh":
        return "Przygotuj brief odświeżenia dopiero po sprawdzeniu ryzykownych obietnic."
    if recommended_mode == "merge":
        return "Najpierw sprawdź duplikaty i zdecyduj, które sekcje scalić."
    return decision.next_step


def _content_decision_url_semantics(
    *,
    source_url: str,
    wordpress_content_url: str | None,
) -> dict[str, str | None]:
    source_public_url = source_url
    intended_final_url = (
        wordpress_content_url
        if _content_url_host(wordpress_content_url) in CONTENT_SOURCE_SITE_HOSTS
        else source_public_url
    )
    return {
        "source_public_url": source_public_url,
        "preview_url": None,
        "intended_final_url": intended_final_url,
        "final_canonical_url": intended_final_url,
    }


def _content_marketer_decision_text(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "block_until_vendor_read":
        return (
            "Nie podejmuj decyzji contentowej, dopóki WILQ nie ma świeżych "
            "danych z GSC i WordPress."
        )
    if decision.decision_type == "refresh_or_merge":
        return (
            "Zachowaj istniejącą treść i przygotuj odświeżenie albo scalenie, "
            "zamiast pisać nowy tekst od zera."
        )
    if decision.decision_type == "merge_create_after_inventory_check":
        return (
            "Najpierw sprawdź, czy temat nie dubluje istniejącej treści; "
            "dopiero potem wybierz scalenie albo utworzenie nowej treści."
        )
    if decision.decision_type == "inventory_check_before_create":
        return (
            "Nie pisz jeszcze nowej treści; najpierw potwierdź, czy temat "
            "nie istnieje już w WordPress."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "To wygląda jak problem pomiaru GA4, nie zadanie do pisania treści."
    return (
        "Sprawdź lukę contentową z Ahrefs tylko jako materiał do oceny, "
        "nie jako samodzielny powód do publikacji."
    )


def _content_marketer_mode_label(decision_type: ContentDecisionType) -> str:
    labels: dict[ContentDecisionType, str] = {
        "block_until_vendor_read": "blokada danych",
        "refresh_or_merge": "zachować i odświeżyć",
        "merge_create_after_inventory_check": "sprawdzić duplikację",
        "inventory_check_before_create": "sprawdzić istniejącą treść",
        "block_as_tracking_not_content": "naprawić pomiar",
        "review_ahrefs_gap_records": "sprawdzić lukę",
    }
    return labels[decision_type]


def _content_marketer_why(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "refresh_or_merge":
        query = f" dla zapytania `{decision.primary_query}`" if decision.primary_query else ""
        return (
            f"WordPress potwierdza istniejący URL{query}, więc bezpieczniej wzmocnić "
            "obecną treść niż tworzyć konkurującą stronę."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            "GSC pokazuje popyt, ale WILQ nie ma pełnego potwierdzenia, że temat "
            "nie istnieje już w treściach. Pisanie bez tej kontroli grozi duplikacją."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return (
            "Braki w wymiarach GA4 mogą fałszować ocenę strony wejścia, więc najpierw "
            "trzeba poprawić pomiar."
        )
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            "Ahrefs może wskazać temat do sprawdzenia, ale sam gap konkurencji nie "
            "wystarcza do decyzji o nowej publikacji bez GSC i inventory."
        )
    return (
        "Brakuje podstawowych danych z GSC lub WordPress, więc WILQ może pokazać "
        "tylko blocker, nie rekomendację."
    )


def _content_marketer_next_action(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "refresh_or_merge":
        return (
            "Przejrzyj wskazany URL, zachowaj sekcje nadal aktualne, wypisz braki "
            "w H1/H2/FAQ/CTA i dopiero potem przygotuj brief do sprawdzenia."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            "Potwierdź istniejący URL, kanoniczny adres i ryzyko duplikacji. Jeśli "
            "kontrola przejdzie, WILQ może przygotować brief; jeśli nie, temat zostaje zablokowany."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "Napraw lub potwierdź tracking GA4, a potem wróć do oceny treści."
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            "Porównaj gap z GSC i WordPress; traktuj go jako inspirację "
            "do sprawdzenia, nie gotową decyzję."
        )
    return "Uruchom odczyt danych GSC i spisu treści WordPress, potem odśwież Content Planner."


def _content_marketer_missing_inputs(
    decision: ContentDecisionItem,
    *,
    final_canonical_url: str | None,
) -> list[str]:
    values: list[str] = []
    if decision.wordpress_match == "missing":
        values.append("potwierdzenie, czy temat istnieje już w WordPress")
    if decision.inventory_gate_status and decision.inventory_gate_status not in {
        "confirmed_current_inventory",
        "not_applicable",
    }:
        values.append("kontrola spisu treści i istniejącego URL")
    if decision.canonical_gate_status and decision.canonical_gate_status not in {
        "current_url_confirmed",
        "not_applicable",
    }:
        values.append("potwierdzony adres kanoniczny na ekologus.pl")
    if decision.duplicate_gate_status and decision.duplicate_gate_status not in {
        "refresh_or_merge_required",
        "not_applicable",
    }:
        values.append("kontrola duplikacji i kanibalizacji")
    if not decision.evidence_ids:
        values.append("dowód źródłowy w WILQ")
    return _unique(values) or ["brak dodatkowych danych przed sprawdzeniem"]


def _content_marketer_blocked_claims(claims: Iterable[str]) -> list[str]:
    labels = {
        "auto publish": "automatyczna publikacja",
        "content recommendation": "rekomendacja bez danych źródłowych",
        "duplicate-free guarantee": "gwarancja braku duplikatów",
        "lead quality": "jakość leadów",
        "lead uplift": "obietnica wzrostu leadów",
        "new article without inventory check": "nowy artykuł bez kontroli spisu treści",
        "ranking uplift": "obietnica wzrostu pozycji",
        "revenue impact": "wpływ na przychód",
        "conversion uplift": "obietnica wzrostu konwersji",
        "wordpress_publish": "publikacja w WordPress bez sprawdzenia",
        "wordpress_write": "zapis do WordPress bez potwierdzenia",
        "wordpress_draft_ready_claim": "twierdzenie, że szkic jest gotowy do sprawdzenia",
    }
    return _unique(labels.get(claim, claim.replace("_", " ")) for claim in claims)


def _content_marketer_evidence_summary(decision: ContentDecisionItem) -> str:
    connector_count = len(decision.source_connectors)
    evidence_count = len(decision.evidence_ids)
    if decision.primary_query:
        return (
            f"Decyzja opiera się na {evidence_count} dowodach z {connector_count} źródeł; "
            f"główne zapytanie: {decision.primary_query}."
        )
    return f"Decyzja opiera się na {evidence_count} dowodach z {connector_count} źródeł."


def _content_marketer_measurement_plan(decision: ContentDecisionItem) -> str:
    url = decision.final_canonical_url or decision.source_public_url or decision.page
    url_part = f" dla {url}" if url else ""
    return (
        f"Po publikacji lub odświeżeniu porównaj GSC i GA4 przed/po{url_part}. "
        "Bez okna pomiarowego WILQ nie może twierdzić, że zmiana poprawiła "
        "pozycje, leady albo konwersje."
    )


def _content_decision_has_public_final_canonical(decision: ContentDecisionItem) -> bool:
    return _content_url_host(_content_decision_final_canonical_url(decision)) in (
        CONTENT_SOURCE_SITE_HOSTS
    )


def _content_decision_type_summary_label(decision_type: ContentDecisionType) -> str:
    if decision_type == "block_until_vendor_read":
        return "blokada do czasu odczytu danych"
    if decision_type == "refresh_or_merge":
        return "odświeżenie albo scalenie"
    if decision_type == "merge_create_after_inventory_check":
        return "scalenie albo nowa treść po kontroli spisu"
    if decision_type == "inventory_check_before_create":
        return "kontrola spisu przed nową treścią"
    if decision_type == "review_ahrefs_gap_records":
        return "sprawdzenie luk Ahrefs"
    return "blokada pomiaru, nie zadanie contentowe"


def _content_metric_facts(connector_ids: Iterable[str]) -> list[MetricFact]:
    facts_by_connector = metric_store().list_metric_facts_by_connector(
        list(connector_ids),
        limit_per_connector=CONTENT_WORDPRESS_METRIC_FACT_LIMIT,
    )
    facts: list[MetricFact] = []
    for connector_id in connector_ids:
        connector_limit = _content_connector_metric_fact_limit(connector_id)
        facts.extend(facts_by_connector.get(connector_id, [])[:connector_limit])
    return facts


def _content_connector_metric_fact_limit(connector_id: str) -> int:
    if connector_id == "google_search_console":
        return CONTENT_GSC_METRIC_FACT_LIMIT
    if connector_id.startswith("wordpress"):
        return CONTENT_WORDPRESS_METRIC_FACT_LIMIT
    return CONTENT_METRIC_FACT_LIMIT


def _latest_refreshes(connector_ids: Iterable[str]) -> list[ConnectorRefreshRun]:
    latest: list[ConnectorRefreshRun] = []
    for connector_id in connector_ids:
        runs = list_connector_refresh_runs(connector_id=connector_id)
        if runs:
            latest.append(runs[0])
    return latest


def _primary_content_data_available(
    facts: list[MetricFact],
    latest_refreshes: list[ConnectorRefreshRun],
) -> bool:
    fact_connectors = {fact.source_connector for fact in facts}
    if not set(PRIMARY_CONTENT_CONNECTORS).issubset(fact_connectors):
        return False
    latest_by_connector = {run.connector_id: run for run in latest_refreshes}
    for connector_id in PRIMARY_CONTENT_CONNECTORS:
        latest = latest_by_connector.get(connector_id)
        if latest is None:
            continue
        if latest.status != ConnectorRefreshStatus.completed or not latest.vendor_data_collected:
            return False
    return True


def _content_action_ids(actions: list[ActionObject]) -> list[str]:
    return [
        action.id
        for action in actions
        if action.id == "act_prepare_content_refresh_queue"
        or action.domain == OpportunityDomain.content
    ]


def _query_page_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    gsc_items = [item for item in tactical_items if item.domain == OpportunityDomain.gsc_seo]
    gsc_facts = [
        fact
        for fact in facts
        if fact.source_connector == "google_search_console"
        and {"query", "page"}.issubset(fact.dimensions)
    ]
    if not gsc_items and not gsc_facts:
        return ContentDiagnosticSection(
            id="content_query_page_matrix",
            title="GSC: brak metryk zapytań i URL",
            status="blocked",
            summary=_content_blocker_reason(latest_refreshes, "google_search_console"),
            diagnosis=(
                "WILQ nie ma metryk zapytań i URL-i z Google Search Console, więc nie może "
                "wskazać odświeżenia, nowej treści ani scalenia bez zmyślania intencji."
            ),
            next_step=(
                "Uruchom odczyt danych z GSC i dopiero potem buduj "
                "kolejkę treści."
            ),
            source_connectors=["google_search_console"],
            evidence_ids=_refresh_or_connector_evidence_ids(
                latest_refreshes,
                "google_search_console",
            ),
            action_ids=action_ids,
            knowledge_card_ids=["card_gsc_seo_content_playbook"],
            expert_rule_ids=[
                "seo_gsc_opportunities_v1",
                "seo_query_page_matrix_v1",
            ],
            blocked_claims=["CTR opportunity", "ranking win", "content intent"],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_query_page_matrix",
        title="GSC: zapytania i URL-e",
        status="ready",
        summary=(
            f"WILQ ma {len(gsc_items)} zadań GSC i "
            f"{len(gsc_facts)} metryk zapytań i URL-i."
        ),
        diagnosis=(
            "Macierz zapytań i URL-i pozwala wskazać konkretne strony do "
            "odświeżenia, scalenia albo kontroli. To nie jest ogólny brainstorming tematów."
        ),
        next_step="Otwórz najwyższe priorytety i sprawdź intencję oraz dopasowanie WordPress.",
        source_connectors=["google_search_console"],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in gsc_facts),
                *(evidence_id for item in gsc_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=gsc_facts[:10],
        tactical_items=gsc_items[:8],
        action_ids=action_ids,
        knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
        expert_rule_ids=[
            "seo_gsc_opportunities_v1",
            "seo_query_page_matrix_v1",
        ],
        blocked_claims=["lead uplift", "conversion uplift", "revenue impact"],
        risk=ActionRisk.low,
    )


def _inventory_match_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    inventory_facts = [
        fact
        for fact in facts
        if fact.source_connector.startswith("wordpress")
        and fact.name
        in {"content_object_count", "content_object_seen", "pages_total", "posts_total"}
    ]
    matched_items = [
        item
        for item in tactical_items
        if item.dimensions.get("wordpress_match") == "found"
    ]
    missing_items = [
        item
        for item in tactical_items
        if item.dimensions.get("wordpress_match") == "missing"
    ]
    if not inventory_facts:
        return ContentDiagnosticSection(
            id="content_inventory_match",
            title="WordPress: brak spisu treści",
            status="blocked",
            summary=_content_blocker_reason(latest_refreshes, "wordpress_ekologus"),
            diagnosis=(
                "WILQ nie ma spisu treści WordPress, więc nie może odróżnić "
                "odświeżenia albo scalenia od nowej treści bez ryzyka duplikacji."
            ),
            next_step="Odśwież spis treści WordPress i dopiero potem generuj briefy treści.",
            source_connectors=["wordpress_ekologus", "wordpress_sklep"],
            evidence_ids=_refresh_or_connector_evidence_ids(
                latest_refreshes,
                "wordpress_ekologus",
            ),
            action_ids=action_ids,
            knowledge_card_ids=["card_wordpress_content_refresh_playbook"],
            expert_rule_ids=["content_duplication_rules_v1", "content_brief_rules_v1"],
            blocked_claims=["duplicate avoidance", "refresh plan", "merge plan"],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_inventory_match",
        title="WordPress: ochrona przed duplikacją",
        status="ready",
        summary=(
            f"WILQ ma {len(inventory_facts)} metryk spisu treści, "
            f"{len(matched_items)} potwierdzonych dopasowań i "
            f"{len(missing_items)} braków dopasowania."
        ),
        diagnosis=(
            "Spis treści WordPress chroni marketera przed pisaniem drugi raz tego samego. "
            "Potwierdzone dopasowania idą w odświeżenie lub scalenie, a brak "
            "dopasowania wymaga ręcznej kontroli przed nowym briefem."
        ),
        next_step=(
            "Najpierw obsłuż potwierdzone odświeżenia i scalenia; nowe treści "
            "twórz tylko po kontroli duplikacji."
        ),
        source_connectors=_unique(fact.source_connector for fact in inventory_facts),
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in inventory_facts),
                *(evidence_id for item in matched_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=inventory_facts[:10],
        tactical_items=[*matched_items[:5], *missing_items[:3]],
        action_ids=action_ids,
        knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
        expert_rule_ids=[
            "content_duplication_rules_v1",
            "content_brief_rules_v1",
        ],
        blocked_claims=["new article without inventory check", "duplicate-free guarantee"],
        risk=ActionRisk.low,
    )


def _content_action_safety_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    return ContentDiagnosticSection(
        id="content_action_safety",
        title="Bezpieczeństwo akcji contentowych",
        status="ready" if facts or tactical_items else "blocked",
        summary=(
            "Akcje contentowe pozostają w trybie przygotowania do czasu sprawdzenia "
            "podglądu zmian i audytu."
        ),
        diagnosis=(
            "WILQ może przygotować kolejkę odświeżenia, tworzenia, scalania albo "
            "blokowania oraz podgląd zmian, ale nie może publikować ani zmieniać "
            "WordPress bez sprawdzenia i zgody operatora."
        ),
        next_step="Sprawdź `act_prepare_content_refresh_queue` w WILQ i pokaż podgląd zmian.",
        source_connectors=list(CONTENT_CONNECTOR_IDS),
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for refresh in latest_refreshes
                    for evidence_id in refresh.evidence_ids
                ),
                *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            ]
        )
        or [connector_evidence_id("google_search_console")],
        tactical_items=tactical_items[:6],
        action_ids=action_ids,
        knowledge_card_ids=["card_wordpress_content_refresh_playbook"],
        expert_rule_ids=["content_brief_rules_v1", "content_voice_rules_v1"],
        blocked_claims=["wordpress write", "auto publish", "ranking guarantee"],
        risk=ActionRisk.medium,
    )


def _query_page_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.domain == OpportunityDomain.gsc_seo)


def _matched_inventory_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.dimensions.get("wordpress_match") == "found")


def _content_blocker_reason(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> str:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest and latest.errors:
        return latest.errors[0]
    if latest and latest.summary:
        return latest.summary
    return f"Brak wykonanego odczytu danych dla {connector_id}."


def _refresh_or_connector_evidence_ids(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> list[str]:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest:
        return latest.evidence_ids
    return [connector_evidence_id(connector_id)]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _content_decision_queue(
    items: list[TacticalQueueItem],
    metric_facts: list[MetricFact],
    action_ids: list[str],
    latest_refreshes: list[ConnectorRefreshRun],
) -> list[ContentDecisionItem]:
    decisions = [
        *_gsc_content_decisions(items, inventory_metric_facts=metric_facts),
        *_ga4_tracking_gap_decisions(items),
        *_ahrefs_gap_record_decisions(metric_facts, action_ids),
    ]
    if decisions:
        return sorted(decisions, key=_content_decision_sort_key)[:5]
    return [_content_vendor_read_blocker_decision(latest_refreshes, action_ids)]


def _content_vendor_read_blocker_decision(
    latest_refreshes: list[ConnectorRefreshRun],
    action_ids: list[str],
) -> ContentDecisionItem:
    gsc_reason = _content_blocker_reason(latest_refreshes, "google_search_console")
    wordpress_reason = _content_blocker_reason(latest_refreshes, "wordpress_ekologus")
    return ContentDecisionItem(
        id="content_block_vendor_read",
        decision_type="block_until_vendor_read",
        status="blocked",
        title="Content: odczyt GSC i WordPress wymagany przed decyzją",
        summary=(
            "WILQ nie ma faktów query/page z Google Search Console ani spisu "
            "treści WordPress wystarczających do decyzji: odświeżyć, scalić albo utworzyć."
        ),
        priority=5,
        metric_tiles={"blockery": 2},
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=_unique(
            [
                *_refresh_or_connector_evidence_ids(
                    latest_refreshes,
                    "google_search_console",
                ),
                *_refresh_or_connector_evidence_ids(
                    latest_refreshes,
                    "wordpress_ekologus",
                ),
            ]
        ),
        action_ids=action_ids,
        knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
        expert_rule_ids=list(GSC_CONTENT_EXPERT_RULE_IDS),
        blocked_claims=[
            "content recommendation",
            "ranking uplift",
            "lead uplift",
            "auto publish",
        ],
        rationale=(
            f"GSC blocker: {gsc_reason} WordPress blocker: {wordpress_reason} "
            "Bez tych odczytów WILQ może tylko wskazać brak danych, nie decyzję SEO."
        ),
        next_step=(
            "Uruchom odczyt danych z Google Search Console i WordPress, "
            "potem wróć do diagnozy treści."
        ),
        risk=ActionRisk.medium,
    )


def _gsc_content_decisions(
    items: list[TacticalQueueItem],
    *,
    inventory_metric_facts: list[MetricFact],
) -> list[ContentDecisionItem]:
    page_groups: dict[str, list[TacticalQueueItem]] = {}
    for item in _unique_tactical_items(items):
        if item.domain != OpportunityDomain.gsc_seo:
            continue
        page = item.dimensions.get("page")
        if page:
            page_groups.setdefault(page, []).append(item)

    decisions: list[ContentDecisionItem] = []
    for page, page_items in page_groups.items():
        first = page_items[0]
        wordpress_match = first.dimensions.get("wordpress_match", "missing")
        query_count = _int_dimension(first, "gsc_page_query_count", len(page_items))
        queries = _unique(
            item.dimensions.get("query")
            for item in page_items
            if item.dimensions.get("query")
        )
        metric_facts = _unique_metric_facts(
            fact for item in page_items for fact in item.metric_facts
        )
        wordpress_content_url = first.dimensions.get("wordpress_content_url")
        metrics = _content_decision_metrics(metric_facts, queries)
        decision_type: ContentDecisionType
        if wordpress_match == "found":
            decision_type = "refresh_or_merge"
            title = _content_decision_title(decision_type, page, query_count, metrics)
            summary = _content_decision_summary(decision_type, metrics, wordpress_match)
            next_step = (
                "Przygotuj brief odświeżenia albo scalenia: title, H1/H2, sekcje "
                "brakujące wobec zapytania i CTA. Nie obiecuj leadów ani wzrostów pozycji."
            )
            rationale = (
                "Spis treści WordPress potwierdza istniejący URL, więc WILQ kieruje "
                "to do odświeżenia albo scalenia zamiast tworzenia nowej treści."
            )
        elif query_count > 1:
            decision_type = "merge_create_after_inventory_check"
            title = _content_decision_title(decision_type, page, query_count, metrics)
            summary = _content_decision_summary(decision_type, metrics, wordpress_match)
            next_step = (
                "Sprawdź mapowanie URL, sitemap i duplikaty w WordPress. Dopiero potem "
                "wybierz scalenie, nową treść albo przywrócenie."
            )
            rationale = (
                "Wiele zapytań prowadzi do jednego URL, ale spis treści nie potwierdza "
                "strony, więc nowy brief bez kontroli grozi duplikacją."
            )
        else:
            decision_type = "inventory_check_before_create"
            title = _content_decision_title(decision_type, page, query_count, metrics)
            summary = _content_decision_summary(decision_type, metrics, wordpress_match)
            next_step = (
                "Najpierw potwierdź, czy URL istnieje w WordPress lub sitemap. "
                "Jeśli nie istnieje, przygotuj brief dopiero po kontroli duplikatów."
            )
            rationale = (
                "GSC pokazuje popyt, ale spis treści WordPress nie potwierdza URL, "
                "więc WILQ blokuje automatyczne tworzenie nowej treści."
            )
        url_semantics = _content_decision_url_semantics(
            source_url=page,
            wordpress_content_url=wordpress_content_url,
        )
        gate_status = _content_gate_status(
            decision_type=decision_type,
            wordpress_match=wordpress_match,
        )
        decisions.append(
            ContentDecisionItem(
                id=f"content_decision_{_slug(page)}",
                decision_type=decision_type,
                status=_content_decision_status(decision_type),
                title=title,
                summary=summary,
                priority=_content_decision_priority(
                    decision_type,
                    metrics,
                    query_count,
                ),
                metric_tiles=_content_decision_metric_tiles(
                    decision_type,
                    metrics,
                    query_count,
                    wordpress_match,
                ),
                page=page,
                normalized_page_path=first.dimensions.get("wordpress_requested_path"),
                queries=queries,
                query_count=query_count,
                primary_query=metrics.primary_query,
                total_clicks=metrics.total_clicks,
                total_impressions=metrics.total_impressions,
                aggregate_ctr=metrics.aggregate_ctr,
                best_average_position=metrics.best_average_position,
                wordpress_match=wordpress_match,
                wordpress_match_confidence=first.dimensions.get("wordpress_match_confidence"),
                source_public_url=url_semantics["source_public_url"],
                preview_url=url_semantics["preview_url"],
                intended_final_url=url_semantics["intended_final_url"],
                final_canonical_url=url_semantics["final_canonical_url"],
                inventory_gate_status=gate_status["inventory_gate_status"],
                canonical_gate_status=gate_status["canonical_gate_status"],
                duplicate_gate_status=gate_status["duplicate_gate_status"],
                content_gate_summary=gate_status["content_gate_summary"],
                source_connectors=_unique(
                    connector for item in page_items for connector in item.source_connectors
                ),
                evidence_ids=_unique(
                    evidence_id for item in page_items for evidence_id in item.evidence_ids
                ),
                metric_facts=metric_facts[:8],
                action_ids=_unique(
                    action_id for item in page_items for action_id in item.action_ids
                ),
                knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
                expert_rule_ids=list(GSC_CONTENT_EXPERT_RULE_IDS),
                blocked_claims=_unique(
                    claim for item in page_items for claim in item.blocked_claims
                ),
                rationale=rationale,
                next_step=next_step,
                risk=ActionRisk.medium if wordpress_match == "missing" else ActionRisk.low,
            )
        )
    return decisions


def _wordpress_inventory_details_by_path(
    metric_facts: list[MetricFact],
) -> dict[str, dict[str, str]]:
    details_by_path: dict[str, dict[str, str]] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        if fact.name != "content_object_seen":
            continue
        url = fact.dimensions.get("content_url")
        if not url:
            continue
        path = _content_normalized_path(url)
        if not path:
            continue
        candidate = {
            "content_type": fact.dimensions.get("content_type", ""),
            "status": fact.dimensions.get("status", ""),
            "inventory_source": fact.dimensions.get("inventory_source", ""),
            "modified_gmt": fact.dimensions.get("modified_gmt", ""),
            "title_or_h1": fact.dimensions.get("title_or_h1", ""),
            "canonical_url": fact.dimensions.get("canonical_url", ""),
        }
        current = details_by_path.get(path)
        if current is None or _inventory_detail_score(candidate) > _inventory_detail_score(current):
            details_by_path[path] = candidate
    return details_by_path


def _wordpress_inventory_details_by_url(
    metric_facts: list[MetricFact],
) -> dict[str, dict[str, str]]:
    details_by_url: dict[str, dict[str, str]] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        if fact.name != "content_object_seen":
            continue
        url = fact.dimensions.get("content_url")
        normalized_url = _content_normalized_url(url)
        if not normalized_url:
            continue
        candidate = {
            "content_type": fact.dimensions.get("content_type", ""),
            "status": fact.dimensions.get("status", ""),
            "inventory_source": fact.dimensions.get("inventory_source", ""),
            "modified_gmt": fact.dimensions.get("modified_gmt", ""),
            "title_or_h1": fact.dimensions.get("title_or_h1", ""),
            "canonical_url": fact.dimensions.get("canonical_url", ""),
        }
        current = details_by_url.get(normalized_url)
        if current is None or _inventory_detail_score(candidate) > _inventory_detail_score(current):
            details_by_url[normalized_url] = candidate
    return details_by_url


def _inventory_detail_score(details: dict[str, str]) -> int:
    return sum(1 for value in details.values() if value)


def _content_normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = _content_normalized_path(value)
    if not host or not path:
        return ""
    return f"{parsed.scheme.lower() or 'https'}://{host}{path}"


def _content_gate_status(
    *,
    decision_type: ContentDecisionType,
    wordpress_match: str,
) -> dict[str, str]:
    if decision_type == "refresh_or_merge" and wordpress_match == "found":
        return {
            "inventory_gate_status": "confirmed_current_inventory",
            "canonical_gate_status": "current_url_confirmed",
            "duplicate_gate_status": "refresh_or_merge_required",
            "content_gate_summary": (
                "Spis treści potwierdza istniejący URL. WILQ traktuje to jako "
                "odświeżenie albo scalenie, nie nowy artykuł; nowa treść pozostaje zablokowana "
                "przed kontrolą duplikacji."
            ),
        }
    if decision_type == "merge_create_after_inventory_check":
        return {
            "inventory_gate_status": "missing_inventory_match",
            "canonical_gate_status": "blocked_until_content_url_review",
            "duplicate_gate_status": "manual_merge_or_create_review",
            "content_gate_summary": (
                "GSC pokazuje klaster zapytań bez potwierdzonego inventory. "
                "Najpierw potrzebna kontrola URL i duplikatów; dopiero potem "
                "scalenie albo nowa treść."
            ),
        }
    if decision_type == "inventory_check_before_create":
        return {
            "inventory_gate_status": "missing_inventory_match",
            "canonical_gate_status": "blocked_until_inventory_review",
            "duplicate_gate_status": "create_blocked_until_duplicate_check",
            "content_gate_summary": (
                "GSC pokazuje popyt, ale WordPress nie potwierdza URL. "
                "Brief nowej treści jest zablokowany do czasu kontroli inventory, canonical "
                "i duplikatów."
            ),
        }
    return {
        "inventory_gate_status": "not_applicable",
        "canonical_gate_status": "not_applicable",
        "duplicate_gate_status": "not_applicable",
        "content_gate_summary": (
            "Ta decyzja nie jest bezpośrednim briefem contentowym; wymaga osobnego "
            "sprawdzenia przed użyciem w planie treści."
        ),
    }


def _content_url_host(value: str | None) -> str | None:
    if not value:
        return None
    return urlparse(value).netloc.lower() or None


def _content_normalized_path(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    return path or "/"


def _ga4_tracking_gap_decisions(items: list[TacticalQueueItem]) -> list[ContentDecisionItem]:
    tracking_gaps = [
        item
        for item in _unique_tactical_items(items)
        if item.domain == OpportunityDomain.ga4 and item.intent == "tracking_gap"
    ]
    if not tracking_gaps:
        return []
    evidence_ids = _unique(
        evidence_id for item in tracking_gaps for evidence_id in item.evidence_ids
    )
    metric_facts = _unique_metric_facts(
        fact for item in tracking_gaps for fact in item.metric_facts
    )
    return [
        ContentDecisionItem(
            id="content_decision_ga4_tracking_gap_block",
            decision_type="block_as_tracking_not_content",
            status="blocked",
            title="Zablokuj GA4 tracking gaps jako zadania contentowe",
            priority=12,
            metric_tiles={
                "blokady": len(tracking_gaps),
                "dowody": len(evidence_ids),
                "braki pomiaru": len(tracking_gaps),
            },
            source_connectors=["google_analytics_4"],
            evidence_ids=evidence_ids,
            metric_facts=metric_facts[:8],
            action_ids=_unique(
                action_id for item in tracking_gaps for action_id in item.action_ids
            ),
            knowledge_card_ids=list(GA4_TRACKING_KNOWLEDGE_CARD_IDS),
            expert_rule_ids=list(GA4_TRACKING_EXPERT_RULE_IDS),
            blocked_claims=_unique(
                [
                    *(claim for item in tracking_gaps for claim in item.blocked_claims),
                    "content rewrite",
                    "conversion uplift",
                    "ROAS",
                ]
            ),
            rationale=(
                "GA4 `(not set)` i tracking_gap wskazują problem pomiaru, "
                "nie gotową rekomendację treści."
            ),
            next_step="Przekaż do sprawdzenia trackingu GA4 zamiast tworzyć rewrite treści.",
            risk=ActionRisk.medium,
        )
    ]


def _ahrefs_gap_record_decisions(
    metric_facts: list[MetricFact],
    action_ids: list[str],
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
    relevant_label = _polish_count_word(len(relevant_scores), "pasujący", "pasujące", "pasujących")
    review_label = _polish_count_word(len(review_scores), "rekord", "rekordy", "rekordów")
    off_topic_label = _polish_count_word(
        len(off_topic_scores),
        "rekord",
        "rekordy",
        "rekordów",
    )
    return [
        ContentDecisionItem(
            id="content_decision_ahrefs_gap_records_review",
            decision_type="review_ahrefs_gap_records",
            status=decision_status,
            title="Ahrefs: zweryfikuj luki SEO przed briefem contentowym",
            summary=(
                f"WILQ ma {len(gap_facts)} rekordów luk Ahrefs: "
                f"luki treści={gap_counts['content_gap']}, "
                f"słowa organiczne={gap_counts['organic_keyword_gap']}, "
                f"najlepsze strony konkurencji={gap_counts['top_page_gap']}, "
                f"luki backlinków={gap_counts['backlink_gap']}. Ocena jakości wskazuje "
                f"{len(relevant_scores)} {relevant_label}, "
                f"{len(review_scores)} {review_label} do ręcznej oceny i "
                f"{len(off_topic_scores)} {off_topic_label} poza zakresem. "
                "To jest materiał do sprawdzenia z GSC/WordPress, nie obietnica wzrostu ruchu."
            ),
            priority=18 if relevant_scores else 32 if review_scores else 45,
            metric_tiles={
                "rekordy Ahrefs": len(gap_facts),
                "pasujące": len(relevant_scores),
                "do sprawdzenia": len(review_scores),
                "poza zakresem": len(off_topic_scores),
                "GSC overlap": gsc_overlap_count,
                "WP overlap": wordpress_overlap_count,
                "luki treści": gap_counts["content_gap"],
                "luki backlinków": gap_counts["backlink_gap"],
            },
            queries=sample_keywords,
            query_count=len(sample_keywords),
            primary_query=sample_keywords[0] if sample_keywords else None,
            source_connectors=["ahrefs"],
            evidence_ids=evidence_ids,
            metric_facts=display_facts,
            ahrefs_candidate_rows=_ahrefs_candidate_rows(candidate_scores),
            action_ids=content_action_ids,
            knowledge_card_ids=list(AHREFS_CONTENT_KNOWLEDGE_CARD_IDS),
            expert_rule_ids=list(AHREFS_CONTENT_EXPERT_RULE_IDS),
            blocked_claims=[
                "off-topic content recommendation",
                "content brief without relevance check",
                "traffic uplift",
                "authority improvement",
                "ranking guarantee",
                "lead uplift",
            ],
            rationale=(
                "Ahrefs wskazuje luki względem konkurencji, ale ocena jakości rozdziela "
                "rekordy pasujące do zakresu Ekologus od tematów szerokich i poza zakresem. "
                "WILQ nie może zrobić briefu z rekordu bez filtrowania, GSC demand "
                "i dopasowania w spisie treści WordPress."
            ),
            next_step=(
                f"Najpierw przejrzyj pasujące rekordy: {topic_hint}. Odrzuć "
                f"{len(off_topic_scores)} rekordów poza zakresem i dopiero potem "
                "połącz sensowne tematy z GSC/WordPress jako odświeżenie, scalenie, "
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
        id=f"ahrefs_candidate_{_slug(f'{topic}_{fact.name}_{fact.evidence_id}')}",
        topic=topic,
        gap_type=dimensions.get("gap_type") or fact.name,
        relevance_status=score.status,
        relevance_score=score.score,
        business_relevance_reasons=list(score.reasons),
        gsc_demand="present" if gsc_overlap else "missing",
        wordpress_inventory_match="present" if wordpress_overlap else "missing",
        gsc_overlap_terms=list(score.gsc_overlap_terms),
        wordpress_overlap_urls=list(score.wordpress_overlap_urls),
        keyword=dimensions.get("keyword") or None,
        competitor_domain=dimensions.get("competitor_domain") or None,
        source_url=dimensions.get("source_url") or None,
        target_url=dimensions.get("target_url") or None,
        metric_name=fact.name,
        metric_value=fact.value,
        evidence_ids=[fact.evidence_id],
        next_step=_ahrefs_candidate_next_step(score, topic),
    )


def _ahrefs_candidate_topic(fact: MetricFact) -> str:
    dimensions = fact.dimensions
    for key in ("keyword", "source_url", "target_url", "competitor_domain"):
        value = dimensions.get(key)
        if value:
            return value
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
            "nie twórz briefu."
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
            "target_url",
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
    target_url = dimensions.get("target_url", "")
    competitor_domain = _normalized_domain(dimensions.get("competitor_domain"))
    source_domain = _normalized_domain(dimensions.get("referring_domain") or source_url)
    text = " ".join(
        value
        for value in (
            keyword,
            source_url,
            target_url,
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
        _matches_normalized_term(normalized_text, tokens, term)
        for term in AHREFS_OFF_TOPIC_TERMS
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
    return tuple(
        _unique(signal.label for signal in signals if tokens & signal.tokens)[:limit]
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
        fact.dimensions.get("keyword")
        for fact in metric_facts
        if fact.dimensions.get("keyword")
    )[:6]


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    unique_items: dict[str, TacticalQueueItem] = {}
    for item in items:
        unique_items.setdefault(item.id, item)
    return list(unique_items.values())


def _unique_metric_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    unique_facts: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted((str(key), str(value)) for key, value in fact.dimensions.items())),
        )
        unique_facts.setdefault(key, fact)
    return list(unique_facts.values())


def _content_decision_metrics(
    metric_facts: list[MetricFact],
    queries: list[str],
) -> ContentDecisionMetrics:
    click_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "clicks"
        and (numeric_value := _numeric_metric_value(fact)) is not None
    ]
    impression_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "impressions"
        and (numeric_value := _numeric_metric_value(fact)) is not None
    ]
    position_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "average_position"
        and (numeric_value := _numeric_metric_value(fact)) is not None
    ]
    total_clicks = int(sum(click_values)) if click_values else None
    total_impressions = int(sum(impression_values)) if impression_values else None
    return ContentDecisionMetrics(
        primary_query=_primary_query(metric_facts, queries),
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        aggregate_ctr=(
            total_clicks / total_impressions
            if total_clicks is not None and total_impressions
            else None
        ),
        best_average_position=min(position_values) if position_values else None,
    )


def _primary_query(metric_facts: list[MetricFact], queries: list[str]) -> str | None:
    query_scores: dict[str, tuple[float, float]] = {}
    for fact in metric_facts:
        if fact.source_connector != "google_search_console":
            continue
        query = fact.dimensions.get("query")
        value = _numeric_metric_value(fact)
        if not query or value is None:
            continue
        impressions, clicks = query_scores.get(query, (0.0, 0.0))
        if fact.name == "impressions":
            impressions += value
        elif fact.name == "clicks":
            clicks += value
        query_scores[query] = (impressions, clicks)
    if query_scores:
        return max(query_scores.items(), key=lambda item: (item[1][0], item[1][1]))[0]
    return queries[0] if queries else None


def _content_decision_status(
    decision_type: ContentDecisionType,
) -> Literal["ready", "blocked"]:
    if decision_type in {"inventory_check_before_create", "block_as_tracking_not_content"}:
        return "blocked"
    return "ready"


def _content_decision_priority(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    query_count: int,
) -> int:
    base_priority = {
        "refresh_or_merge": 20,
        "merge_create_after_inventory_check": 24,
        "inventory_check_before_create": 28,
        "block_as_tracking_not_content": 12,
    }[decision_type]
    impression_score = metrics.total_impressions or 0
    if impression_score >= 1000:
        evidence_bonus = 0
    elif impression_score >= 500:
        evidence_bonus = 2
    elif impression_score >= 100:
        evidence_bonus = 4
    else:
        evidence_bonus = 7
    query_bonus = min(query_count, 5)
    return max(1, base_priority + evidence_bonus - query_bonus)


def _content_decision_metric_tiles(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    query_count: int,
    wordpress_match: str,
) -> dict[str, int | float | str]:
    tiles: dict[str, int | float | str] = {
        "zapytania": query_count,
        "WP": _wordpress_match_tile(wordpress_match),
    }
    if metrics.total_impressions is not None:
        tiles["wyświetlenia"] = metrics.total_impressions
    if metrics.total_clicks is not None:
        tiles["kliknięcia"] = metrics.total_clicks
    if metrics.aggregate_ctr is not None:
        tiles["CTR"] = _format_percent(metrics.aggregate_ctr)
    if metrics.best_average_position is not None:
        tiles["pozycja"] = round(metrics.best_average_position, 2)
    if decision_type != "refresh_or_merge":
        tiles["tryb"] = _content_decision_mode_tile(decision_type)
    return tiles


def _wordpress_match_tile(wordpress_match: str) -> str:
    if wordpress_match == "found":
        return "znaleziono"
    if wordpress_match == "missing":
        return "brak"
    return "niepewne"


def _content_decision_mode_tile(decision_type: ContentDecisionType) -> str:
    if decision_type == "merge_create_after_inventory_check":
        return "sprawdź scalenie albo nową treść"
    if decision_type == "inventory_check_before_create":
        return "blokada nowej treści"
    if decision_type == "block_as_tracking_not_content":
        return "GA4 tracking"
    return "odświeżenie albo scalenie"


def _numeric_metric_value(fact: MetricFact) -> float | None:
    if isinstance(fact.value, int | float):
        return float(fact.value)
    return None


def _content_decision_title(
    decision_type: ContentDecisionType,
    page: str,
    query_count: int,
    metrics: ContentDecisionMetrics,
) -> str:
    topic = _content_topic_label(page, metrics.primary_query)
    query_label = _query_count_label(query_count)
    if decision_type == "refresh_or_merge":
        return f"SEO: odśwież lub scal {topic} ({query_label})"
    if decision_type == "merge_create_after_inventory_check":
        return f"SEO: sprawdź klaster {topic} przed tworzeniem ({query_label})"
    return f"SEO: sprawdź spis treści dla {topic} ({query_label})"


def _content_topic_label(page: str, primary_query: str | None) -> str:
    if primary_query:
        return f'"{primary_query}"'
    if page.rstrip("/") == "https://www.ekologus.pl":
        return "stronę główną"
    return page.rstrip("/").rsplit("/", maxsplit=1)[-1].replace("-", " ")


def _content_decision_summary(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    wordpress_match: str,
) -> str:
    metric_sentence = _content_metric_sentence(metrics)
    if decision_type == "refresh_or_merge":
        return (
            f"{metric_sentence} WordPress potwierdza istniejącą stronę, więc "
            "to jest decyzja odświeżenia albo scalenia, nie nowy artykuł."
        )
    if decision_type == "merge_create_after_inventory_check":
        return (
            f"{metric_sentence} WordPress nie potwierdza strony dla tego klastra, "
            "więc najpierw trzeba sprawdzić mapowanie i duplikaty."
        )
    match_label = "nie potwierdza" if wordpress_match == "missing" else "nie daje pewności"
    return (
        f"{metric_sentence} WordPress {match_label} URL, więc WILQ blokuje "
        "brief nowej treści do czasu kontroli inventory."
    )


def _content_metric_sentence(metrics: ContentDecisionMetrics) -> str:
    parts: list[str] = []
    if metrics.total_impressions is not None:
        impression_word = _polish_count_word(
            metrics.total_impressions,
            "wyświetlenie",
            "wyświetlenia",
            "wyświetleń",
        )
        parts.append(f"{metrics.total_impressions} {impression_word}")
    if metrics.total_clicks is not None:
        click_word = _polish_count_word(
            metrics.total_clicks,
            "kliknięcie",
            "kliknięcia",
            "kliknięć",
        )
        parts.append(f"{metrics.total_clicks} {click_word}")
    if metrics.aggregate_ctr is not None:
        parts.append(f"CTR {_format_percent(metrics.aggregate_ctr)}")
    if metrics.best_average_position is not None:
        parts.append(f"najlepsza średnia pozycja {_format_decimal(metrics.best_average_position)}")
    prefix = "GSC: " + ", ".join(parts) if parts else "GSC ma evidence dla tej strony."
    if metrics.primary_query:
        return f'{prefix}; główne zapytanie: "{metrics.primary_query}".'
    return prefix


def _content_decision_sort_key(decision: ContentDecisionItem) -> tuple[int, int, int, int, str]:
    status_rank = 1 if decision.status == "blocked" else 0
    return (
        status_rank,
        decision.priority,
        -(decision.total_impressions or 0),
        -decision.query_count,
        decision.id,
    )


def _query_count_label(query_count: int) -> str:
    if query_count == 1:
        return "1 zapytanie"
    return f"{query_count} zapytań"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_decimal(value: float) -> str:
    return f"{value:.2f}"


def _polish_count_word(value: int, one: str, few: str, many: str) -> str:
    absolute = abs(value)
    if absolute == 1:
        return one
    if 2 <= absolute % 10 <= 4 and not 12 <= absolute % 100 <= 14:
        return few
    return many


def _int_dimension(item: TacticalQueueItem, key: str, fallback: int) -> int:
    try:
        return int(item.dimensions.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower()).strip(
        "_"
    )[:80]
