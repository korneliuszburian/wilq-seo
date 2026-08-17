from __future__ import annotations

from typing import Any

from wilq.content.operator_copy import unique
from wilq.schemas import MetricFact

from .review import (
    _content_contract_label,
    _content_contract_labels,
    _content_gate_status_for_brief,
    content_url_review_contract,
)
from .shared import (
    AHREFS_GAP_FACT_NAMES,
    CONTENT_BLOCKED_CLAIMS,
    CONTENT_BRIEF_PREVIEW_CONTRACT,
    CONTENT_REFRESH_ACTION_TYPE,
    CONTENT_SOURCE_CONNECTORS,
    GSC_METRIC_NAMES,
    _ahrefs_content_angle,
    _ahrefs_content_intent,
    _ahrefs_preview_score,
    _ahrefs_source_facts,
    _ahrefs_topic,
    _brand_voice_notes,
    _brief_outline,
    _candidate_slug_for_page,
    _content_angle,
    _content_audience,
    _content_intent,
    _content_preview_url_semantics,
    _cta_direction,
    _faq_direction,
    _gsc_brief_goal,
    _gsc_metric_snapshot,
    _gsc_metric_snapshot_labels,
    _gsc_missing_evidence,
    _gsc_required_validation,
    _gsc_source_facts,
    _h1_direction,
    _h2_direction,
    _internal_link_direction,
    _key_objections,
    _legal_review_notes,
    _meta_description_direction,
    _metric_numeric_sort_value,
    _metric_sum,
    _normalized_path,
    _publication_blockers,
    _schema_direction,
    _seo_title_direction,
    _short_path,
    _slug,
)
from .store import _wordpress_inventory_urls_by_path

__all__ = [
    "_empty_content_brief_preview",
    "content_refresh_payload_from_metric_facts",
    "_gsc_content_brief_previews",
    "_ahrefs_content_brief_previews",
]


def _empty_content_brief_preview(
    *, wordpress_evidence_id: str, gsc_evidence_id: str
) -> dict[str, Any]:
    return {
        "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
        "candidate_id": "content_brief_empty_state",
        "source_type": "empty_state",
        "mode": "block",
        "topic": "brak potwierdzonego tematu",
        "source_public_url": None,
        "preview_url": None,
        "intended_final_url": None,
        "final_canonical_url": None,
        "inventory_gate_status": "blocked_until_inventory_review",
        "canonical_gate_status": "blocked_until_inventory_review",
        "duplicate_gate_status": "create_blocked_until_duplicate_check",
        "content_gate_summary": (
            "Brak danych GSC dla zapytań i stron oraz spisu treści WordPress "
            "w świeżym odczycie. Najpierw zbierz dane źródłowe, potem oceniaj "
            "zachowanie, odświeżenie, scalenie albo utworzenie treści."
        ),
        "wordpress_inventory_match": "missing",
        "decision_options": ["block"],
        "metric_snapshot": {},
        "brief_goal": (
            "Zablokuj pisanie treści do czasu zebrania danych GSC i spisu treści WordPress."
        ),
        "intent": "brak intencji do pisania bez danych źródłowych",
        "content_angle": ("Nie przygotowuj tekstu bez potwierdzonego publicznego URL i dowodów."),
        "audience": ("Marketer Ekologus sprawdzający gotowość danych przed pracą nad treścią."),
        "key_objections": [
            "brak potwierdzonego tematu",
            "brak publicznego URL",
            "brak kontroli duplikacji",
        ],
        "h1_direction": "Nie ustalaj H1 bez potwierdzonego tematu i URL.",
        "seo_title_direction": "Nie ustalaj title bez potwierdzonego tematu i URL.",
        "meta_description_direction": (
            "Nie ustalaj meta description bez potwierdzonego tematu i URL."
        ),
        "h2_direction": ["najpierw zbierz dane GSC i WordPress"],
        "faq_direction": ["najpierw zbierz dane GSC i WordPress"],
        "schema_direction": "Nie planuj schema bez zatwierdzonego briefu.",
        "cta_direction": "Nie ustalaj CTA bez dopasowania usługi i intencji.",
        "internal_link_direction": ["najpierw potwierdź istniejące URL-e"],
        "legal_review_notes": ["brak treści do oceny prawnej przed zebraniem danych"],
        "brand_voice_notes": ["brak szkicu do oceny tonu przed zebraniem danych"],
        "publication_readiness_status": "blocked_until_review",
        "publication_blockers": [
            "content_url_preflight_review",
            "canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            "human_confirm_before_wordpress_write",
        ],
        "source_facts": [
            "brak danych GSC dla zapytań i stron",
            "brak spisu treści WordPress",
        ],
        "missing_evidence": [
            "brak publicznego URL",
            "brak danych GSC",
            "brak spisu treści WordPress",
        ],
        "forbidden_claims": [
            "wzrost liczby leadów",
            "wpływ na przychód",
            "gwarancja pozycji",
        ],
        "required_validation": [
            "gsc_query_page_check",
            "wordpress_inventory_check",
            "content_url_preflight_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ],
        "blocked_claims": [
            "wzrost liczby leadów",
            "wpływ na przychód",
            "gwarancja pozycji",
        ],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "evidence_ids": [wordpress_evidence_id, gsc_evidence_id],
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def content_refresh_payload_from_metric_facts(
    metric_facts: list[MetricFact],
) -> dict[str, Any] | None:
    facts = [fact for fact in metric_facts if fact.source_connector in CONTENT_SOURCE_CONNECTORS]
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
        "source_connectors": unique(fact.source_connector for fact in facts),
        "source_metric_names": unique(fact.name for fact in facts),
        "content_brief_preview": content_brief_preview,
        "content_url_review_contract": content_url_review_contract(),
        "queue_steps": [
            "join_wordpress_inventory_with_gsc",
            "classify_refresh_create_merge_block",
            "review_public_final_url",
            "prepare_brief_preview",
            "require_human_confirm_before_wordpress_write",
        ],
        "required_validation": [
            "gsc_query_page_check",
            "wordpress_inventory_check",
            "content_url_preflight_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ],
        "operator_review_gates": [
            "sprawdź intencję zapytania i tematu",
            "potwierdź dopasowanie w spisie treści WordPress",
            "potwierdź publiczny URL kanoniczny",
            "sprawdź duplikaty i kanibalizację",
            "zatwierdź plan treści przed jakąkolwiek zmianą WordPress",
        ],
        "blocked_claims": CONTENT_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def _gsc_content_brief_previews(metric_facts: list[MetricFact]) -> list[dict[str, Any]]:
    wordpress_urls_by_path = _wordpress_inventory_urls_by_path(metric_facts)
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
        queries = unique(
            fact.dimensions.get("query") for fact in page_facts if fact.dimensions.get("query")
        )
        primary_query = queries[0] if queries else _short_path(page)
        page_path = _normalized_path(page)
        wordpress_content_url = wordpress_urls_by_path.get(page_path)
        wordpress_match = wordpress_content_url is not None
        mode = "refresh" if wordpress_match else "inventory_check"
        decision_options = (
            ["refresh", "merge", "block"]
            if wordpress_match
            else [
                "merge",
                "create",
                "block",
            ]
        )
        content_gate_status = _content_gate_status_for_brief(
            source_type="gsc_query_page",
            mode=mode,
            wordpress_match=wordpress_match,
        )
        url_semantics = _content_preview_url_semantics(
            source_url=page,
            wordpress_content_url=wordpress_content_url,
        )
        publication_blockers = _publication_blockers()
        required_validation = _gsc_required_validation(wordpress_match)
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_gsc_{_candidate_slug_for_page(page)}",
                "source_type": "gsc_query_page",
                "source_type_label": _content_contract_label("gsc_query_page"),
                "mode": mode,
                "mode_label": _content_contract_label(mode),
                "topic": primary_query,
                **url_semantics,
                **content_gate_status,
                "wordpress_inventory_match": "present" if wordpress_match else "missing",
                "wordpress_inventory_match_label": _content_contract_label(
                    "present" if wordpress_match else "missing"
                ),
                "decision_options": decision_options,
                "decision_option_labels": _content_contract_labels(decision_options),
                "metric_snapshot": _gsc_metric_snapshot(page_facts),
                "metric_snapshot_labels": _gsc_metric_snapshot_labels(),
                "brief_goal": _gsc_brief_goal(wordpress_match, primary_query),
                "intent": _content_intent(primary_query, wordpress_match),
                "content_angle": _content_angle(primary_query, wordpress_match),
                "audience": _content_audience(primary_query),
                "key_objections": _key_objections(primary_query),
                "h1_direction": _h1_direction(primary_query, wordpress_match),
                "seo_title_direction": _seo_title_direction(primary_query, wordpress_match),
                "meta_description_direction": _meta_description_direction(
                    primary_query,
                    wordpress_match,
                ),
                "h2_direction": _h2_direction(primary_query),
                "faq_direction": _faq_direction(primary_query),
                "schema_direction": _schema_direction(primary_query),
                "cta_direction": _cta_direction(primary_query),
                "internal_link_direction": _internal_link_direction(primary_query),
                "legal_review_notes": _legal_review_notes(primary_query),
                "brand_voice_notes": _brand_voice_notes(primary_query),
                "publication_readiness_status": "blocked_until_review",
                "publication_readiness_status_label": _content_contract_label(
                    "blocked_until_review"
                ),
                "publication_blockers": publication_blockers,
                "publication_blocker_labels": _content_contract_labels(publication_blockers),
                "source_facts": _gsc_source_facts(page, page_facts, wordpress_match),
                "missing_evidence": _gsc_missing_evidence(wordpress_match),
                "forbidden_claims": CONTENT_BLOCKED_CLAIMS,
                "brief_outline": _brief_outline(primary_query, wordpress_match),
                "required_validation": required_validation,
                "required_validation_labels": _content_contract_labels(required_validation),
                "blocked_claims": CONTENT_BLOCKED_CLAIMS,
                "blocked_claim_labels": _content_contract_labels(CONTENT_BLOCKED_CLAIMS),
                "source_connectors": unique(fact.source_connector for fact in page_facts),
                "evidence_ids": unique(fact.evidence_id for fact in page_facts),
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
        publication_blockers = _publication_blockers()
        required_validation = [
            "business_relevance_review",
            "gsc_demand_check",
            "wordpress_inventory_check",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ]
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_ahrefs_{_slug(topic)}",
                "source_type": "ahrefs_gap_review",
                "source_type_label": _content_contract_label("ahrefs_gap_review"),
                "mode": "review",
                "mode_label": _content_contract_label("review"),
                "topic": topic,
                "gap_type": fact.dimensions.get("gap_type") or fact.name,
                "competitor_domain": fact.dimensions.get("competitor_domain") or None,
                "competitor_page": fact.dimensions.get("source_url") or None,
                **_content_gate_status_for_brief(
                    source_type="ahrefs_gap_review",
                    mode="review",
                    wordpress_match=False,
                ),
                "wordpress_inventory_match": "unknown",
                "gsc_demand": "unknown",
                "decision_options": ["refresh", "merge", "create", "block"],
                "decision_option_labels": _content_contract_labels(
                    ["refresh", "merge", "create", "block"]
                ),
                "metric_snapshot": {
                    "metric_name": fact.name,
                    "metric_value": fact.value,
                },
                "metric_snapshot_labels": {
                    "metric_name": "metryka",
                    "metric_value": "wartość",
                },
                "brief_goal": (
                    "Zweryfikuj temat z Ahrefs przeciw GSC i WordPress, zanim "
                    "powstanie plan treści. To jest temat do sprawdzenia, nie decyzja "
                    "utworzenia nowej treści."
                ),
                "intent": _ahrefs_content_intent(topic),
                "content_angle": _ahrefs_content_angle(topic),
                "audience": _content_audience(topic),
                "key_objections": _key_objections(topic),
                "h1_direction": _h1_direction(topic, False),
                "seo_title_direction": _seo_title_direction(topic, False),
                "meta_description_direction": _meta_description_direction(topic, False),
                "h2_direction": _h2_direction(topic),
                "faq_direction": _faq_direction(topic),
                "schema_direction": _schema_direction(topic),
                "cta_direction": _cta_direction(topic),
                "internal_link_direction": _internal_link_direction(topic),
                "legal_review_notes": _legal_review_notes(topic),
                "brand_voice_notes": _brand_voice_notes(topic),
                "publication_readiness_status": "blocked_until_review",
                "publication_readiness_status_label": _content_contract_label(
                    "blocked_until_review"
                ),
                "publication_blockers": publication_blockers,
                "publication_blocker_labels": _content_contract_labels(publication_blockers),
                "source_facts": _ahrefs_source_facts(fact, topic),
                "missing_evidence": [
                    "brak potwierdzenia popytu GSC dla tematu",
                    "brak potwierdzenia dopasowania w spisie treści WordPress",
                    "brak dowodu wpływu na ruch, leady albo przychód",
                ],
                "forbidden_claims": CONTENT_BLOCKED_CLAIMS,
                "brief_outline": _brief_outline(topic, False),
                "required_validation": required_validation,
                "required_validation_labels": _content_contract_labels(required_validation),
                "blocked_claims": CONTENT_BLOCKED_CLAIMS,
                "blocked_claim_labels": _content_contract_labels(CONTENT_BLOCKED_CLAIMS),
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
