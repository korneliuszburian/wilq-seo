from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from wilq.schemas import MetricFact

CONTENT_REFRESH_ACTION_TYPE = "wordpress_content_refresh"
CONTENT_BRIEF_PREVIEW_CONTRACT = "content_brief_preview_v1"
CONTENT_URL_REVIEW_CONTRACT = "content_url_preflight_review_v1"
WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT = "wordpress_draft_payload_preview_v1"
POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT = "post_publication_measurement_plan_v1"
CONTENT_SOURCE_SITE_HOSTS = {
    "www.ekologus.pl",
    "ekologus.pl",
    "sklep.ekologus.pl",
}

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
    "wzrost liczby leadów",
    "wpływ na przychód",
    "gwarancja pozycji",
    "wzrost ruchu",
    "wzrost autorytetu",
    "automatyczna publikacja WordPress",
]

CONTENT_CONTRACT_LABELS = {
    "api_mutation_ready_false": "zapis zmian nie jest gotowy",
    "approve_outline_for_editorial_review": "zatwierdź plan do redakcji",
    "automatic_wordpress_write": "automatyczny zapis WordPress",
    "block_until_public_inventory_known": "blokada do czasu spisu publicznych treści",
    "blocked_preview_only": "zablokowane do czasu kontroli",
    "business_relevance_review": "sprawdzenie dopasowania biznesowego",
    "canonical_review": "kontrola URL-a kanonicznego",
    "canonical_needs_target_confirmation": "trzeba potwierdzić URL kanoniczny",
    "canonical_review_outcome": "wynik kontroli URL-a kanonicznego",
    "candidate_id": "ID wybranej propozycji",
    "confirm_existing_public_url": "potwierdź istniejący publiczny URL",
    "confirm_final_canonical_url": "potwierdź finalny URL kanoniczny",
    "content_draft_readiness_review": "kontrola gotowości szkicu",
    "content_draft_generation_v1": "generowanie szkicu",
    "content_url_preflight_review": "potwierdzenie publicznego URL-a",
    "content_url_preflight_review_v1": "potwierdzenie publicznego URL-a",
    "content_url_review_recorded_review_only": "kontrola URL-a zapisana do sprawdzenia",
    "duplicate_free_claim_without_review": "obietnica braku duplikacji bez kontroli",
    "duplicate_free_claim": "obietnica braku duplikacji",
    "duplicate_or_cannibalization_check": "kontrola duplikacji i kanibalizacji",
    "duplicate_review_outcome": "wynik kontroli duplikacji",
    "evidence_ids_present": "dowody są podpięte",
    "final_canonical_review": "kontrola URL-a kanonicznego",
    "legal_factual_review": "kontrola prawna i faktograficzna",
    "legal_factual_review_outcome": "wynik kontroli prawnej i faktograficznej",
    "human_confirm_before_wordpress_write": "potwierdzenie człowieka przed zapisem WordPress",
    "mark_preview_design_context_not_required": "podgląd projektu nie jest wymagany",
    "operator_review_approved_for_prepare": "operator zatwierdził przygotowanie",
    "merge_required_before_draft": "najpierw trzeba rozstrzygnąć scalenie",
    "needs_canonical_fix": "trzeba poprawić kanoniczny URL",
    "needs_duplicate_resolution": "trzeba rozstrzygnąć duplikację",
    "needs_expert_review": "wymaga kontroli eksperta",
    "new_content_without_inventory_check": "nowa treść bez sprawdzenia spisu",
    "notes": "notatki",
    "outline_only_until_gates_pass": "plan treści do czasu kontroli",
    "prepare_only_review_recorded": "zapisano ocenę przygotowania",
    "preview_url_as_final_canonical": "adres podglądu jako finalny URL kanoniczny",
    "publish_ready_claim": "obietnica gotowości do publikacji",
    "production_wordpress_write": "zapis na produkcyjnym WordPressie",
    "public_content_inventory_required": "wymagany spis publicznych treści",
    "ready_for_review": "gotowe do sprawdzenia",
    "ranking_guarantee": "gwarancja pozycji",
    "review_only": "do kontroli",
    "wordpress_draft_handoff_action_required": "wymagany osobny krok WordPress",
    "wordpress_draft_handoff_v1": "zapis szkicu WordPress",
    "wordpress_draft_payload_preview": "podgląd wpisu WordPress",
    "wordpress_draft_payload_preview_required": "wymagany podgląd wpisu WordPress",
    "wordpress_draft_payload_review": "kontrola podglądu wpisu WordPress",
    "wordpress_draft_write": "zapis szkicu WordPress",
    "wordpress_draft_write_not_requested": "zapis szkicu WordPress nie został zlecony",
    "wordpress_publish": "publikacja WordPress",
    "wordpress_write_not_requested": "zapis WordPress nie został zlecony",
    "gsc_query_page_check": "sprawdzenie zapytań i URL-i z GSC",
    "gsc_demand_check": "sprawdzenie popytu w GSC",
    "wordpress_existing_url_confirmed": "istniejący URL potwierdzony w WordPress",
    "wordpress_inventory_check": "sprawdzenie spisu treści WordPress",
    "source_connectors_present": "źródła danych są podpięte",
    "source_public_url": "publiczny URL źródłowy",
    "final_canonical_url": "finalny URL kanoniczny",
    "intended_final_url": "docelowy URL publiczny",
    "confirmed_current_inventory": "spis potwierdzony na obecnej stronie",
    "current_url_confirmed": "obecny URL potwierdzony",
    "refresh_or_merge_required": "odśwież albo scal zamiast pisać od nowa",
    "missing_inventory_match": "brak dopasowania w spisie treści",
    "blocked_until_inventory_review": "zablokowane do sprawdzenia spisu",
    "blocked_until_content_url_review": "zablokowane do sprawdzenia URL-a",
    "blocked_until_relevance_review": "zablokowane do sprawdzenia dopasowania",
    "create_blocked_until_duplicate_check": "utworzenie zablokowane do kontroli duplikacji",
    "manual_merge_or_create_review": "ręcznie rozstrzygnij scalenie albo utworzenie",
    "not_applicable": "nie dotyczy",
    "28d_before_publish": "28 dni przed publikacją",
    "7d_after_publish": "7 dni po publikacji",
    "28d_after_publish": "28 dni po publikacji",
    "90d_after_publish": "90 dni po publikacji",
    "google_search_console": "Google Search Console",
    "google_analytics_4": "GA4",
    "wordpress_ekologus": "WordPress Ekologus",
    "ranking_gain_claim": "obietnica wzrostu pozycji",
    "lead_uplift_claim": "obietnica wzrostu leadów",
    "revenue_impact_claim": "obietnica wpływu na przychód",
    "content_success_verdict": "werdykt skuteczności treści",
    "automatic_refresh_followup": "automatyczne odświeżenie po publikacji",
    "published_url_confirmed": "opublikowany URL potwierdzony",
    "baseline_window_captured": "punkt odniesienia zapisany",
    "followup_window_captured": "okno pomiaru po publikacji zapisane",
    "same_url_or_redirect_mapping_confirmed": "ten sam URL albo przekierowanie potwierdzone",
    "tracking_quality_review": "kontrola jakości pomiaru",
    "gsc_query_page_clicks_impressions_ctr_position": "kliknięcia, wyświetlenia, CTR i pozycja z GSC",
    "ga4_landing_engagement_and_key_events": "zaangażowanie i zdarzenia GA4",
    "wordpress_publish_metadata": "metadane publikacji WordPress",
    "reviewable_polish_draft_preview": "polska wersja robocza do kontroli",
    "legal_compliance_guarantee": "gwarancja zgodności prawnej",
    "lead_or_revenue_uplift_claim": "obietnica wzrostu leadów albo przychodu",
    "ranking_or_lead_uplift_claim": "obietnica wzrostu pozycji albo leadów",
    "request_duplicate_or_canonical_review": "poproś o kontrolę duplikacji albo URL-a kanonicznego",
    "review_outcome": "wynik sprawdzenia",
    "human_review_outcome": "wynik decyzji człowieka",
    "reviewed_by": "sprawdzający",
    "reject_until_source_evidence": "odrzuć do czasu uzupełnienia dowodów",
    "needs_legal_review": "wymaga kontroli prawnej",
}


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
            "sprawdź intencję query/topic",
            "potwierdź dopasowanie w spisie treści WordPress",
            "potwierdź publiczny URL kanoniczny",
            "sprawdź duplikaty i kanibalizację",
            "zatwierdź brief przed jakąkolwiek zmianą WordPress",
        ],
        "blocked_claims": CONTENT_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def content_url_review_contract() -> dict[str, Any]:
    allowed_outcomes = [
        "confirm_existing_public_url",
        "confirm_final_canonical_url",
        "request_duplicate_or_canonical_review",
        "block_until_public_inventory_known",
        "mark_preview_design_context_not_required",
    ]
    required_fields = [
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "review_outcome",
        "reviewed_by",
        "notes",
    ]
    blocked_outputs = [
        "wordpress_draft_write",
        "wordpress_publish",
        "preview_url_as_final_canonical",
        "new_content_without_inventory_check",
        "duplicate_free_claim",
        "ranking_or_lead_uplift_claim",
    ]
    return {
        "contract": CONTENT_URL_REVIEW_CONTRACT,
        "scope": "review_only",
        "canonical_home": "ekologus.pl",
        "preview_url_policy": "optional_only_when_explicitly_configured",
        "allowed_outcomes": allowed_outcomes,
        "allowed_outcome_labels": _content_contract_labels(allowed_outcomes),
        "required_fields": required_fields,
        "required_field_labels": _content_contract_labels(required_fields),
        "blocked_outputs": blocked_outputs,
        "blocked_output_labels": _content_contract_labels(blocked_outputs),
    }


def _content_contract_label(value: str) -> str:
    return CONTENT_CONTRACT_LABELS.get(value, value.replace("_", " "))


def _content_contract_labels(values: Iterable[str]) -> list[str]:
    return [_content_contract_label(value) for value in values if value]


def _prefixed_labels(prefix: str, values: Iterable[str]) -> list[str]:
    return [f"{prefix}: {label}" for label in _content_contract_labels(values)]


def content_payload_with_reviewed_wordpress_draft_previews(
    payload: dict[str, Any],
    *,
    review_event_summaries: Iterable[str],
    review_event_details: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if payload.get("action_type") != CONTENT_REFRESH_ACTION_TYPE:
        return payload
    enriched_payload = dict(payload)
    enriched_payload.pop("wordpress_draft_payload_preview", None)
    summary_list = list(review_event_summaries)
    reviewed_candidate_ids = _reviewed_candidate_ids(summary_list)
    detail_list = list(review_event_details or [])
    url_reviews = {
        **_reviewed_candidate_url_reviews(summary_list),
        **_reviewed_candidate_url_reviews_from_details(detail_list),
    }
    draft_readiness_reviews = _reviewed_candidate_draft_readiness_from_details(detail_list)
    if not reviewed_candidate_ids:
        return enriched_payload
    brief_previews = [
        item
        for item in enriched_payload.get("content_brief_preview", [])
        if isinstance(item, dict)
    ]
    draft_previews = [
        _wordpress_draft_payload_preview(
            item,
            url_review=url_reviews.get(str(item.get("candidate_id") or "")),
            draft_readiness_review=draft_readiness_reviews.get(
                str(item.get("candidate_id") or "")
            ),
        )
        for item in brief_previews
        if isinstance(item.get("candidate_id"), str)
        and item["candidate_id"] in reviewed_candidate_ids
    ]
    if draft_previews:
        enriched_payload["wordpress_draft_payload_preview"] = draft_previews
    return enriched_payload


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
        queries = _unique(
            fact.dimensions.get("query")
            for fact in page_facts
            if fact.dimensions.get("query")
        )
        primary_query = queries[0] if queries else _short_path(page)
        page_path = _normalized_path(page)
        wordpress_target_url = wordpress_urls_by_path.get(page_path)
        wordpress_match = wordpress_target_url is not None
        mode = "refresh" if wordpress_match else "inventory_check"
        decision_options = ["refresh", "merge", "block"] if wordpress_match else [
            "merge",
            "create",
            "block",
        ]
        content_gate_status = _content_gate_status_for_brief(
            source_type="gsc_query_page",
            mode=mode,
            wordpress_match=wordpress_match,
        )
        url_semantics = _content_preview_url_semantics(
            source_url=page,
            wordpress_content_url=wordpress_target_url,
        )
        publication_blockers = _publication_blockers()
        required_validation = _gsc_required_validation(wordpress_match)
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_gsc_{_candidate_slug_for_page(page)}",
                "source_type": "gsc_query_page",
                "mode": mode,
                "topic": primary_query,
                **url_semantics,
                **content_gate_status,
                "wordpress_inventory_match": "present" if wordpress_match else "missing",
                "decision_options": decision_options,
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
                "publication_blockers": publication_blockers,
                "publication_blocker_labels": _content_contract_labels(publication_blockers),
                "source_facts": _gsc_source_facts(page, page_facts, wordpress_match),
                "missing_evidence": _gsc_missing_evidence(wordpress_match),
                "forbidden_claims": CONTENT_BLOCKED_CLAIMS,
                "brief_outline": _brief_outline(primary_query, wordpress_match),
                "required_validation": required_validation,
                "required_validation_labels": _content_contract_labels(required_validation),
                "blocked_claims": CONTENT_BLOCKED_CLAIMS,
                "source_connectors": _unique(fact.source_connector for fact in page_facts),
                "evidence_ids": _unique(fact.evidence_id for fact in page_facts),
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    return previews


def _reviewed_candidate_ids(review_event_summaries: Iterable[str]) -> set[str]:
    candidate_ids: set[str] = set()
    for summary in review_event_summaries:
        if "candidate:" not in summary:
            continue
        for fragment in summary.split("candidate:")[1:]:
            candidate_id = fragment.split(",", 1)[0].split(".", 1)[0].strip()
            if candidate_id:
                candidate_ids.add(candidate_id)
    return candidate_ids


def _reviewed_candidate_url_reviews(
    review_event_summaries: Iterable[str],
) -> dict[str, dict[str, str]]:
    url_reviews: dict[str, dict[str, str]] = {}
    for summary in review_event_summaries:
        candidate_id = _review_summary_token(summary, "candidate")
        if not candidate_id:
            continue
        outcome = _review_summary_token(summary, "url_review_outcome")
        reviewed_url = _review_summary_token(summary, "reviewed_url")
        notes = _review_summary_token(summary, "review_notes")
        if outcome or reviewed_url or notes:
            url_reviews[candidate_id] = {
                "url_review_outcome": outcome,
                "reviewed_url": reviewed_url,
                "review_notes": notes,
            }
    return url_reviews


def _reviewed_candidate_url_reviews_from_details(
    review_event_details: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    url_reviews: dict[str, dict[str, str]] = {}
    for details in review_event_details:
        url_review = details.get("content_url_review")
        if not isinstance(url_review, Mapping):
            continue
        candidate_id = url_review.get("candidate")
        if not isinstance(candidate_id, str) or not candidate_id:
            continue
        url_reviews[candidate_id] = {
            "url_review_outcome": str(url_review.get("url_review_outcome") or ""),
            "reviewed_url": str(url_review.get("reviewed_url") or ""),
            "review_notes": str(url_review.get("review_notes") or ""),
        }
    return url_reviews


def _reviewed_candidate_draft_readiness_from_details(
    review_event_details: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    draft_reviews: dict[str, dict[str, str]] = {}
    for details in review_event_details:
        review = details.get("content_draft_readiness_review")
        if not isinstance(review, Mapping):
            continue
        candidate_id = review.get("candidate")
        if not isinstance(candidate_id, str) or not candidate_id:
            continue
        draft_reviews[candidate_id] = {
            "draft_readiness_outcome": str(review.get("draft_readiness_outcome") or ""),
            "canonical_review_outcome": str(review.get("canonical_review_outcome") or ""),
            "duplicate_review_outcome": str(review.get("duplicate_review_outcome") or ""),
            "legal_factual_review_outcome": str(
                review.get("legal_factual_review_outcome") or ""
            ),
            "human_review_outcome": str(review.get("human_review_outcome") or ""),
            "draft_readiness_notes": str(review.get("draft_readiness_notes") or ""),
        }
    return draft_reviews


def _review_summary_token(summary: str, key: str) -> str:
    marker = f"{key}:"
    if marker not in summary:
        return ""
    fragment = summary.split(marker, 1)[1]
    return fragment.split(",", 1)[0].split(".", 1)[0].strip()


def _wordpress_draft_payload_preview(
    preview: dict[str, Any],
    *,
    url_review: dict[str, str] | None = None,
    draft_readiness_review: dict[str, str] | None = None,
) -> dict[str, Any]:
    topic = str(preview.get("topic") or "Brief treści")
    mode = str(preview.get("mode") or "review")
    source_type = str(preview.get("source_type") or "unknown")
    source_public_url = (
        preview.get("source_public_url")
        if isinstance(preview.get("source_public_url"), str)
        else None
    )
    intended_final_url = (
        preview.get("intended_final_url")
        if isinstance(preview.get("intended_final_url"), str)
        else source_public_url
    )
    final_canonical_url = (
        preview.get("final_canonical_url")
        if isinstance(preview.get("final_canonical_url"), str)
        else intended_final_url
    )
    inventory_gate_status = (
        preview.get("inventory_gate_status")
        if isinstance(preview.get("inventory_gate_status"), str)
        else None
    )
    canonical_gate_status = (
        preview.get("canonical_gate_status")
        if isinstance(preview.get("canonical_gate_status"), str)
        else None
    )
    duplicate_gate_status = (
        preview.get("duplicate_gate_status")
        if isinstance(preview.get("duplicate_gate_status"), str)
        else None
    )
    draft_generation_status = _draft_generation_status(
        inventory_gate_status=inventory_gate_status,
        canonical_gate_status=canonical_gate_status,
        duplicate_gate_status=duplicate_gate_status,
    )
    draft_blockers = _draft_blockers(draft_generation_status)
    wordpress_draft_final_url = final_canonical_url or intended_final_url or source_public_url
    wordpress_draft_handoff_status = _wordpress_draft_handoff_status(
        draft_generation_status=draft_generation_status,
        draft_readiness_outcome=(draft_readiness_review or {}).get(
            "draft_readiness_outcome"
        ),
    )
    wordpress_draft_handoff_blockers = _wordpress_draft_handoff_blockers(
        wordpress_draft_handoff_status
    )
    draft_generation_contract = _draft_generation_contract(
        draft_generation_status=draft_generation_status,
        draft_blockers=draft_blockers,
    )
    draft_readiness_review_contract = _draft_readiness_review_contract()
    wordpress_draft_handoff_contract = _wordpress_draft_handoff_contract(
        wordpress_draft_handoff_status=wordpress_draft_handoff_status,
        wordpress_draft_handoff_blockers=wordpress_draft_handoff_blockers,
        final_canonical_url=wordpress_draft_final_url,
    )
    post_publication_plan = post_publication_measurement_plan(
        final_canonical_url=wordpress_draft_final_url,
    )
    required_validation = _unique(
        [
            "operator_review_approved_for_prepare",
            *[
                item
                for item in preview.get("required_validation", [])
                if isinstance(item, str)
            ],
            "wordpress_draft_payload_review",
            "human_confirm_before_wordpress_write",
        ]
    )
    candidate_id = str(preview["candidate_id"])
    return {
        "preview_contract": WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT,
        "source_preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
        "candidate_id": candidate_id,
        "source_type": source_type,
        "mode": mode,
        "connector": "wordpress_ekologus",
        "operation_type": _wordpress_draft_operation(mode),
        "post_status": "draft",
        "topic": topic,
        "intent": preview.get("intent") if isinstance(preview.get("intent"), str) else None,
        "source_public_url": source_public_url,
        "preview_url": preview.get("preview_url")
        if isinstance(preview.get("preview_url"), str)
        else None,
        "intended_final_url": intended_final_url,
        "final_canonical_url": final_canonical_url,
        "content_url_review_recorded_outcome": (
            (url_review or {}).get("url_review_outcome") or None
        ),
        "content_url_review_reviewed_url": (
            (url_review or {}).get("reviewed_url") or None
        ),
        "content_url_review_notes": (
            (url_review or {}).get("review_notes") or None
        ),
        "inventory_gate_status": inventory_gate_status,
        "canonical_gate_status": canonical_gate_status,
        "duplicate_gate_status": duplicate_gate_status,
        "content_gate_summary": preview.get("content_gate_summary")
        if isinstance(preview.get("content_gate_summary"), str)
        else None,
        "content_gate_status_summary": _content_gate_status_summary(
            inventory_gate_status=inventory_gate_status,
            canonical_gate_status=canonical_gate_status,
            duplicate_gate_status=duplicate_gate_status,
            content_gate_summary=preview.get("content_gate_summary")
            if isinstance(preview.get("content_gate_summary"), str)
            else None,
        ),
        "draft_generation_status": draft_generation_status,
        "draft_blockers": draft_blockers,
        "draft_blocker_labels": _content_contract_labels(draft_blockers),
        "draft_generation_contract": draft_generation_contract,
        "draft_generation_summary": _draft_generation_summary(draft_generation_contract),
        "draft_readiness_review_contract": draft_readiness_review_contract,
        "draft_readiness_review_contract_summary": _draft_readiness_review_contract_summary(
            draft_readiness_review_contract
        ),
        "draft_readiness_review_recorded_outcome": (
            (draft_readiness_review or {}).get("draft_readiness_outcome") or None
        ),
        "canonical_review_recorded_outcome": (
            (draft_readiness_review or {}).get("canonical_review_outcome") or None
        ),
        "duplicate_review_recorded_outcome": (
            (draft_readiness_review or {}).get("duplicate_review_outcome") or None
        ),
        "legal_factual_review_recorded_outcome": (
            (draft_readiness_review or {}).get("legal_factual_review_outcome") or None
        ),
        "human_review_recorded_outcome": (
            (draft_readiness_review or {}).get("human_review_outcome") or None
        ),
        "draft_readiness_review_notes": (
            (draft_readiness_review or {}).get("draft_readiness_notes") or None
        ),
        "draft_readiness_review_summary": _draft_readiness_review_summary(
            draft_readiness_review or {}
        ),
        "wordpress_draft_handoff_status": wordpress_draft_handoff_status,
        "wordpress_draft_handoff_blockers": wordpress_draft_handoff_blockers,
        "wordpress_draft_handoff_blocker_labels": _content_contract_labels(
            wordpress_draft_handoff_blockers
        ),
        "wordpress_draft_handoff_summary": _wordpress_draft_handoff_summary(
            wordpress_draft_handoff_status,
            wordpress_draft_handoff_blockers,
        ),
        "wordpress_draft_handoff_contract": wordpress_draft_handoff_contract,
        "wordpress_draft_handoff_contract_summary": (
            _wordpress_draft_handoff_contract_summary(wordpress_draft_handoff_contract)
        ),
        "post_publication_measurement_plan": post_publication_plan,
        "post_publication_measurement_summary": _post_publication_measurement_summary(
            post_publication_plan
        ),
        "draft_payload": {
            "post_status": "draft",
            "post_title": _draft_title(topic, mode),
            "post_excerpt_direction": _draft_excerpt_direction(preview),
            "content_blocks": _draft_content_blocks(preview),
        },
        "required_validation": required_validation,
        "required_validation_labels": _content_contract_labels(required_validation),
        "blocked_claims": _unique(
            [
                item
                for item in preview.get("blocked_claims", [])
                if isinstance(item, str)
            ]
        ),
        "source_connectors": _unique(
            [
                item
                for item in preview.get("source_connectors", [])
                if isinstance(item, str)
            ]
        ),
        "evidence_ids": _unique(
            [
                item
                for item in preview.get("evidence_ids", [])
                if isinstance(item, str)
            ]
        ),
        "mutation_allowed": False,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def _wordpress_draft_operation(mode: str) -> str:
    if mode in {"refresh", "merge"}:
        return "prepare_existing_content_draft"
    return "prepare_new_content_draft_review"


def _draft_generation_status(
    *,
    inventory_gate_status: str | None,
    canonical_gate_status: str | None,
    duplicate_gate_status: str | None,
) -> str:
    if inventory_gate_status == "missing_inventory_match":
        return "blocked_missing_public_inventory"
    if canonical_gate_status in {
        "needs_final_canonical_review",
        "blocked_until_content_url_review",
        "blocked_until_inventory_review",
    } or duplicate_gate_status in {
        "refresh_or_merge_required",
        "manual_merge_or_create_review",
        "create_blocked_until_duplicate_check",
    }:
        return "blocked_pending_canonical_duplicate_review"
    if inventory_gate_status == "confirmed_current_inventory":
        return "ready_for_review"
    return "blocked_until_content_review"


def _draft_blockers(draft_generation_status: str) -> list[str]:
    blockers = [
        "wordpress_write_not_requested",
        "api_mutation_ready_false",
        "human_confirm_before_wordpress_write",
    ]
    if draft_generation_status == "ready_for_review":
        return [
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_until_content_review":
        return [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_canonical_duplicate_review":
        return [
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_canonical_duplicate_review_after_url_review":
        return [
            "content_url_review_recorded_review_only",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_missing_public_inventory":
        return [
            "public_content_inventory_required",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    return [
        "business_relevance_review",
        "wordpress_inventory_check",
        "duplicate_or_cannibalization_check",
        *blockers,
    ]


def _draft_generation_contract(
    *,
    draft_generation_status: str,
    draft_blockers: list[str],
) -> dict[str, Any]:
    output_kind = (
        "reviewable_polish_draft_preview"
        if draft_generation_status == "ready_for_review"
        else "outline_only_until_gates_pass"
    )
    return {
        "contract_version": "content_draft_generation_v1",
        "language": "pl-PL",
        "status": draft_generation_status,
        "allowed_output_kind": output_kind,
        "blocked_until": draft_blockers,
        "requires_passed_gates": [
            "evidence_ids_present",
            "source_connectors_present",
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            "human_confirm_before_wordpress_write",
        ],
        "output_must_include": [
            "seo_title_direction",
            "meta_description_direction",
            "h1_direction",
            "h2_direction",
            "faq_direction",
            "cta_direction",
            "internal_link_direction",
            "source_facts",
            "missing_evidence",
            "forbidden_claims",
        ],
        "forbidden_outputs": [
            "publish_ready_claim",
            "automatic_wordpress_write",
            "ranking_guarantee",
            "lead_or_revenue_uplift_claim",
            "legal_compliance_guarantee",
        ],
    }


def _draft_readiness_review_contract() -> dict[str, Any]:
    return {
        "contract_version": "content_draft_readiness_review_v1",
        "scope": "review_only",
        "allowed_outcomes": [
            "approve_outline_for_editorial_review",
            "needs_canonical_fix",
            "needs_duplicate_resolution",
            "needs_legal_review",
            "reject_until_source_evidence",
        ],
        "required_fields": [
            "candidate_id",
            "canonical_review_outcome",
            "duplicate_review_outcome",
            "legal_factual_review_outcome",
            "human_review_outcome",
            "reviewed_by",
            "notes",
        ],
        "blocked_outputs": [
            "wordpress_draft_write",
            "wordpress_publish",
            "publish_ready_claim",
            "duplicate_free_claim_without_review",
            "legal_compliance_guarantee",
            "ranking_or_lead_uplift_claim",
        ],
    }


def _wordpress_draft_handoff_status(
    *,
    draft_generation_status: str,
    draft_readiness_outcome: str | None,
) -> str:
    if draft_generation_status != "ready_for_review":
        return "blocked_until_draft_gates_pass"
    if draft_readiness_outcome != "approve_outline_for_editorial_review":
        return "blocked_until_draft_readiness_review"
    return "blocked_until_wordpress_draft_handoff_action"


def _wordpress_draft_handoff_blockers(wordpress_draft_handoff_status: str) -> list[str]:
    blockers = [
        "wordpress_draft_write_not_requested",
        "api_mutation_ready_false",
        "human_confirm_before_wordpress_write",
    ]
    if wordpress_draft_handoff_status == "blocked_until_draft_gates_pass":
        return [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            *blockers,
        ]
    if wordpress_draft_handoff_status == "blocked_until_draft_readiness_review":
        return [
            "content_draft_readiness_review",
            *blockers,
        ]
    return [
        "wordpress_draft_handoff_action_required",
        "wordpress_draft_payload_preview_required",
        *blockers,
    ]


def _wordpress_draft_handoff_contract(
    *,
    wordpress_draft_handoff_status: str,
    wordpress_draft_handoff_blockers: list[str],
    final_canonical_url: str | None,
) -> dict[str, Any]:
    return {
        "contract_version": "wordpress_draft_handoff_v1",
        "scope": "blocked_preview_only",
        "final_canonical_url": final_canonical_url,
        "status": wordpress_draft_handoff_status,
        "blocked_until": wordpress_draft_handoff_blockers,
        "requires_passed_gates": [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            "content_draft_readiness_review",
            "human_confirm_before_wordpress_write",
        ],
        "required_next_action_contract": "wordpress_draft_handoff_v1",
        "blocked_outputs": [
            "wordpress_draft_write",
            "wordpress_publish",
            "production_wordpress_write",
            "publish_ready_claim",
            "ranking_or_lead_uplift_claim",
        ],
    }


def post_publication_measurement_plan(
    *,
    final_canonical_url: str | None,
) -> dict[str, Any]:
    return {
        "contract_version": POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT,
        "scope": "blocked_preview_only",
        "final_canonical_url": final_canonical_url,
        "status": "blocked_until_publish_and_followup_data",
        "baseline_window": "28d_before_publish",
        "followup_windows": ["7d_after_publish", "28d_after_publish", "90d_after_publish"],
        "required_source_connectors": [
            "google_search_console",
            "google_analytics_4",
            "wordpress_ekologus",
        ],
        "required_metric_groups": [
            "gsc_query_page_clicks_impressions_ctr_position",
            "ga4_landing_engagement_and_key_events",
            "wordpress_publish_metadata",
        ],
        "requires_before_claims": [
            "published_url_confirmed",
            "baseline_window_captured",
            "followup_window_captured",
            "same_url_or_redirect_mapping_confirmed",
            "tracking_quality_review",
        ],
        "blocked_outputs": [
            "ranking_gain_claim",
            "lead_uplift_claim",
            "revenue_impact_claim",
            "content_success_verdict",
            "automatic_refresh_followup",
        ],
    }


def _draft_generation_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    output_kind = contract.get("allowed_output_kind")
    if isinstance(output_kind, str) and output_kind:
        values.append(f"wynik: {_content_contract_label(output_kind)}")
    values.extend(_prefixed_labels("warunek", _string_list(contract.get("requires_passed_gates"))[:3]))
    values.extend(_prefixed_labels("zakaz", _string_list(contract.get("forbidden_outputs"))[:3]))
    return values


def _content_gate_status_summary(
    *,
    inventory_gate_status: str | None,
    canonical_gate_status: str | None,
    duplicate_gate_status: str | None,
    content_gate_summary: str | None,
) -> list[str]:
    values = [
        f"spis treści: {_content_contract_label(inventory_gate_status)}"
        if inventory_gate_status
        else "",
        f"URL kanoniczny: {_content_contract_label(canonical_gate_status)}"
        if canonical_gate_status
        else "",
        f"duplikaty: {_content_contract_label(duplicate_gate_status)}"
        if duplicate_gate_status
        else "",
        content_gate_summary or "",
    ]
    return [value for value in values if value.strip()]


def _draft_readiness_review_contract_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = contract.get("scope")
    if isinstance(scope, str) and scope:
        values.append(f"zakres: {_content_contract_label(scope)}")
    values.extend(_prefixed_labels("wynik", _string_list(contract.get("allowed_outcomes"))[:3]))
    required_fields = [
        value
        for value in _string_list(contract.get("required_fields"))
        if value != "candidate_id"
    ]
    values.extend(_prefixed_labels("wymaga", required_fields[:4]))
    values.extend(_prefixed_labels("blokuje", _string_list(contract.get("blocked_outputs"))[:4]))
    return values


def _draft_readiness_review_summary(review: Mapping[str, Any]) -> list[str]:
    values = [
        ("szkic", review.get("draft_readiness_outcome")),
        ("kanoniczny URL", review.get("canonical_review_outcome")),
        ("duplikaty", review.get("duplicate_review_outcome")),
        ("legal/fakty", review.get("legal_factual_review_outcome")),
        ("człowiek", review.get("human_review_outcome")),
    ]
    return [
        f"{prefix}: {_content_contract_label(value)}"
        for prefix, value in values
        if isinstance(value, str) and value
    ]


def _wordpress_draft_handoff_summary(status: str, blockers: Iterable[str]) -> list[str]:
    return [
        f"status: {_content_wordpress_draft_handoff_status_label(status)}",
        *_prefixed_labels("blokada", list(blockers)[:5]),
    ]


def _wordpress_draft_handoff_contract_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = contract.get("scope")
    if isinstance(scope, str) and scope:
        values.append(f"zakres: {_content_contract_label(scope)}")
    next_action = contract.get("required_next_action_contract")
    if isinstance(next_action, str) and next_action:
        values.append(f"następny krok: {_content_contract_label(next_action)}")
    values.extend(_prefixed_labels("warunek", _string_list(contract.get("requires_passed_gates"))[:4]))
    values.extend(_prefixed_labels("blokuje", _string_list(contract.get("blocked_outputs"))[:4]))
    return values


def _post_publication_measurement_summary(plan: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    status = plan.get("status")
    if isinstance(status, str) and status:
        values.append(f"status: {_post_publication_measurement_status_label(status)}")
    baseline_window = plan.get("baseline_window")
    if isinstance(baseline_window, str) and baseline_window:
        values.append(f"punkt odniesienia: {_content_contract_label(baseline_window)}")
    values.extend(_prefixed_labels("sprawdzenie", _string_list(plan.get("followup_windows"))[:3]))
    values.extend(_prefixed_labels("źródło", _string_list(plan.get("required_source_connectors"))[:3]))
    values.extend(_prefixed_labels("blokuje", _string_list(plan.get("blocked_outputs"))[:3]))
    return values


def _content_wordpress_draft_handoff_status_label(value: str) -> str:
    labels = {
        "blocked_until_draft_gates_pass": "zablokowany do przejścia kontroli szkicu",
        "blocked_until_draft_readiness_review": "zablokowany do sprawdzenia gotowości szkicu",
        "blocked_until_wordpress_draft_handoff_action": "zablokowany do osobnego kroku WordPress",
    }
    return labels.get(value, _content_contract_label(value))


def _post_publication_measurement_status_label(value: str) -> str:
    labels = {
        "blocked_until_publish_and_followup_data": "zablokowany do publikacji i danych po publikacji",
    }
    return labels.get(value, _content_contract_label(value))


def _string_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _draft_title(topic: str, mode: str) -> str:
    prefix = "Odświeżenie" if mode in {"refresh", "merge"} else "Brief"
    return f"{prefix}: {topic}"


def _draft_excerpt_direction(preview: dict[str, Any]) -> str:
    goal = preview.get("brief_goal")
    if isinstance(goal, str) and goal:
        return goal
    return "Szkic briefu do sprawdzenia. Nie publikować bez sprawdzenia operatora."


def _draft_content_blocks(preview: dict[str, Any]) -> list[dict[str, str]]:
    outline = preview.get("brief_outline")
    if not isinstance(outline, list):
        return []
    blocks: list[dict[str, str]] = []
    for item in outline[:8]:
        if not isinstance(item, dict):
            continue
        section = item.get("section")
        instruction = item.get("instruction")
        if isinstance(section, str) and isinstance(instruction, str):
            blocks.append(
                {
                    "section": section,
                    "section_label": _draft_content_block_label(section),
                    "instruction": instruction,
                }
            )
    return blocks


def _draft_content_block_label(section: str) -> str:
    labels = {
        "intent": "intencja",
        "title_h1": "title i H1",
        "missing_sections": "brakujące sekcje",
        "cta": "wezwanie do działania",
        "faq": "FAQ",
        "internal_links": "linkowanie wewnętrzne",
        "legal_review": "kontrola prawna",
    }
    return labels.get(section, section.replace("_", " "))


def _content_gate_status_for_brief(
    *,
    source_type: str,
    mode: str,
    wordpress_match: bool,
) -> dict[str, str]:
    if source_type == "gsc_query_page" and mode == "refresh" and wordpress_match:
        return {
            "inventory_gate_status": "confirmed_current_inventory",
            "canonical_gate_status": "current_url_confirmed",
            "duplicate_gate_status": "refresh_or_merge_required",
            "content_gate_summary": (
                "Spis treści potwierdza istniejący URL. WILQ traktuje to jako "
                "odświeżenie albo scalenie, nie nowy artykuł; nowa treść pozostaje "
                "zablokowana przed kontrolą duplikacji."
            ),
        }
    if source_type == "gsc_query_page":
        return {
            "inventory_gate_status": "missing_inventory_match",
            "canonical_gate_status": "blocked_until_inventory_review",
            "duplicate_gate_status": "create_blocked_until_duplicate_check",
            "content_gate_summary": (
                "GSC pokazuje popyt, ale WordPress nie potwierdza URL. Brief create "
                "jest zablokowany do czasu kontroli inventory, canonical i duplikatów."
            ),
        }
    return {
        "inventory_gate_status": "not_applicable",
        "canonical_gate_status": "blocked_until_relevance_review",
        "duplicate_gate_status": "manual_merge_or_create_review",
        "content_gate_summary": (
            "To jest propozycja z Ahrefs do sprawdzenia, nie decyzja create. Najpierw "
            "potwierdź popyt GSC, inventory WordPress i duplikaty."
        ),
    }


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
                "mode": "review",
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
                    "powstanie brief. To jest temat do sprawdzenia, nie decyzja "
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


def _wordpress_inventory_urls_by_path(metric_facts: list[MetricFact]) -> dict[str, str]:
    urls_by_path: dict[str, str] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        url = fact.dimensions.get("content_url")
        if not url:
            continue
        if _url_host(url) not in CONTENT_SOURCE_SITE_HOSTS:
            continue
        path = _normalized_path(url)
        if path:
            urls_by_path.setdefault(path, url)
    return urls_by_path


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
        if _url_host(url) not in CONTENT_SOURCE_SITE_HOSTS:
            continue
        path = _normalized_path(url)
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
        normalized_url = _normalized_url(fact.dimensions.get("content_url"))
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


def _normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = _normalized_path(value)
    if not host or not path:
        return ""
    return f"{parsed.scheme.lower() or 'https'}://{host}{path}"


def _content_preview_url_semantics(
    *,
    source_url: str,
    wordpress_content_url: str | None,
) -> dict[str, str | bool | None]:
    source_public_url = source_url
    intended_final_url = (
        wordpress_content_url
        if _url_host(wordpress_content_url) in CONTENT_SOURCE_SITE_HOSTS
        else source_public_url
    )
    return {
        "source_public_url": source_public_url,
        "preview_url": None,
        "intended_final_url": intended_final_url,
        "final_canonical_url": intended_final_url,
    }


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


def _gsc_metric_snapshot_labels() -> dict[str, str]:
    return {
        "queries": "zapytania",
        "clicks": "kliknięcia",
        "impressions": "wyświetlenia",
        "ctr": "CTR",
        "average_position": "pozycja",
    }


def _gsc_brief_goal(wordpress_match: bool, primary_query: str) -> str:
    if wordpress_match:
        return (
            f"Przygotuj brief odświeżenia albo scalenia istniejącej treści pod temat "
            f"`{primary_query}`: title, H1/H2, braki w sekcjach, CTA i ryzykowne obietnice."
        )
    return (
        f"Sprawdź spis treści i duplikaty przed briefem dla `{primary_query}`. "
        "Bez potwierdzenia URL nie twórz nowej strony."
    )


def _content_angle(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"Odśwież istniejącą treść tak, żeby szybciej odpowiadała na intencję "
            f"`{topic}` i prowadziła do właściwej usługi Ekologus bez obietnic wyniku."
        )
    return (
        f"Najpierw potwierdź, czy temat `{topic}` nie ma już kanonicznej strony; "
        "dopiero potem przygotuj nowy lub scalony brief."
    )


def _content_intent(topic: str, wordpress_match: bool) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        base = (
            "informacyjno-konsultacyjna: użytkownik chce szybko zrozumieć "
            "obowiązek BDO i sprawdzić, czy potrzebuje wsparcia eksperta"
        )
    elif "zielony lad" in normalized or "esg" in normalized:
        base = (
            "edukacyjno-regulacyjna: użytkownik szuka prostego wyjaśnienia "
            "regulacji i konsekwencji dla firmy"
        )
    elif "operat" in normalized or "pozwolen" in normalized:
        base = (
            "konsultacyjna: użytkownik chce ustalić wymagania formalne i "
            "kolejny krok postępowania"
        )
    elif "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        base = (
            "produktowo-procesowa: użytkownik sprawdza rozwiązanie lub proces "
            "dla bezpiecznej gospodarki odpadami"
        )
    else:
        base = (
            "do potwierdzenia: WILQ ma sygnał popytu, ale ekspert musi "
            "doprecyzować intencję przed pisaniem"
        )
    if wordpress_match:
        return f"{base}; tryb odświeżenia albo scalenia istniejącej strony"
    return f"{base}; nowa treść zablokowana do kontroli spisu treści i duplikatów"


def _ahrefs_content_angle(topic: str) -> str:
    return (
        f"Potraktuj `{topic}` jako inspirację konkurencyjną do sprawdzenia, nie jako gotowy "
        "temat publikacji, dopóki GSC i WordPress nie potwierdzą sensu biznesowego."
    )


def _ahrefs_content_intent(topic: str) -> str:
    return (
        f"konkurencyjny sygnał do sprawdzenia: `{topic}` wymaga potwierdzenia "
        "popytu w GSC, dopasowania WordPress i braku duplikacji przed briefem"
    )


def _content_audience(topic: str) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return "Przedsiębiorca lub osoba operacyjna sprawdzająca obowiązki BDO i ryzyka formalne."
    if "zielony lad" in normalized or "esg" in normalized:
        return "Decydent lub specjalista środowiskowy szukający prostego wyjaśnienia regulacji."
    if "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        return (
            "Firma potrzebująca bezpiecznego procesu, produktu albo konsultacji "
            "w obszarze odpadów."
        )
    return "Marketer i ekspert Ekologus powinni doprecyzować odbiorcę przed pisaniem treści."


def _key_objections(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    objections = [
        "czy temat jest aktualny prawnie i zgodny z realną usługą Ekologus",
        "czy nie istnieje już strona, którą trzeba odświeżyć zamiast tworzyć nową",
    ]
    if "bdo" in normalized:
        objections.append(
            "czy użytkownik potrzebuje definicji, checklisty obowiązków czy "
            "konsultacji"
        )
    elif "zielony lad" in normalized or "esg" in normalized:
        objections.append("czy tekst ma wyjaśniać pojęcie, obowiązki firmy czy wpływ na procesy")
    else:
        objections.append("czy intencja jest edukacyjna, zakupowa czy konsultacyjna")
    return objections


def _h1_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"H1 powinien jasno odpowiadać na intencję `{topic}` i nie sugerować "
            "nowej, osobnej strony."
        )
    return (
        f"H1 roboczy dla `{topic}` dopiero po potwierdzeniu kanonicznego URL "
        "i braku duplikatu."
    )


def _seo_title_direction(topic: str, wordpress_match: bool) -> str:
    action = "odświeżany URL" if wordpress_match else "kanoniczny URL po sprawdzeniu"
    return (
        f"Title powinien zawierać intencję `{topic}`, jasno opisywać {action} "
        "i nie obiecywać pozycji, leadów ani kompletnej zgodności prawnej."
    )


def _meta_description_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"Meta description ma streścić odpowiedź na `{topic}` i kierować do "
            "konsultacji Ekologus bez obietnicy wyniku."
        )
    return (
        f"Meta description dla `{topic}` dopiero po potwierdzeniu inventory, "
        "kanonicznego URL i decyzji create/merge."
    )


def _h2_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    sections = [
        f"krótka odpowiedź: czym jest `{topic}`",
        "co firma powinna sprawdzić przed decyzją",
        "kiedy warto porozmawiać z ekspertem Ekologus",
    ]
    if "bdo" in normalized:
        sections.insert(1, "obowiązki BDO przedsiębiorcy w praktyce")
        sections.insert(2, "najczęstsze błędy i ryzyka formalne")
    elif "zielony lad" in normalized or "esg" in normalized:
        sections.insert(1, "wpływ regulacji na przedsiębiorstwo")
        sections.insert(2, "co zmienia się w obowiązkach środowiskowych")
    elif "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        sections.insert(1, "bezpieczny proces magazynowania lub obsługi")
        sections.insert(2, "dobór rozwiązania do ryzyka i miejsca pracy")
    return sections


def _faq_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return [
            "Co to jest BDO?",
            "Kto musi mieć wpis do BDO?",
            "Kiedy warto skonsultować obowiązki BDO z ekspertem?",
        ]
    if "zielony lad" in normalized or "esg" in normalized:
        return [
            "Co oznacza Zielony Ład dla firmy?",
            "Jakie obowiązki środowiskowe warto sprawdzić?",
            "Czy Ekologus może pomóc w ocenie wpływu regulacji?",
        ]
    return [
        f"Co oznacza `{topic}` dla firmy?",
        "Jakie informacje trzeba potwierdzić przed zapisem zmian?",
        "Kiedy warto skontaktować się z Ekologus?",
    ]


def _schema_direction(topic: str) -> str:
    return (
        f"FAQ schema można rozważyć tylko dla pytań faktycznie użytych w treści "
        f"o `{topic}` i po ręcznej kontroli zgodności odpowiedzi."
    )


def _cta_direction(topic: str) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return "CTA do konsultacji lub weryfikacji obowiązków BDO, bez obietnicy uniknięcia kar."
    if "zielony lad" in normalized or "esg" in normalized:
        return "CTA do rozmowy o wpływie regulacji na firmę, bez obietnicy przychodu ani wzrostu leadów."
    return "CTA do kontaktu z ekspertem Ekologus po ręcznym potwierdzeniu intencji tematu."


def _legal_review_notes(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    notes = [
        "potwierdź aktualność regulacji i zakres usługi z ekspertem Ekologus",
        "nie obiecuj uniknięcia kar, leadów, pozycji ani pełnej zgodności bez audytu",
    ]
    if "bdo" in normalized:
        notes.append("sprawdź, czy opis obowiązków BDO nie zastępuje indywidualnej konsultacji")
    if "zielony lad" in normalized or "esg" in normalized:
        notes.append("oddziel wyjaśnienie regulacji od interpretacji prawnej dla konkretnej firmy")
    return notes


def _brand_voice_notes(topic: str) -> list[str]:
    return [
        f"pisz konkretnie dla przedsiębiorcy szukającego odpowiedzi na `{topic}`",
        "unikaj clickbaitowych obietnic i generycznego poradnikowego tonu",
        "prowadź do konsultacji lub weryfikacji, gdy temat wymaga danych firmy",
    ]


def _publication_blockers() -> list[str]:
    return [
        "content_url_preflight_review",
        "canonical_review",
        "duplicate_or_cannibalization_check",
        "legal_factual_review",
        "human_confirm_before_wordpress_write",
    ]


def _internal_link_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    links = ["strona główna Ekologus lub główna strona usługowa potwierdzona w WordPress"]
    if "bdo" in normalized:
        links.append("powiązane treści o obowiązkach przedsiębiorcy i gospodarce odpadami")
    if "zielony lad" in normalized or "esg" in normalized:
        links.append("powiązane treści o regulacjach środowiskowych i ESG")
    if "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        links.append("powiązane treści lub kategorie dotyczące magazynowania i obsługi odpadów")
    return links


def _gsc_source_facts(page: str, page_facts: list[MetricFact], wordpress_match: bool) -> list[str]:
    snapshot = _gsc_metric_snapshot(page_facts)
    return [
        f"GSC page={page}",
        f"queries={snapshot['queries']}",
        f"clicks={snapshot['clicks']}",
        f"impressions={snapshot['impressions']}",
        f"ctr={snapshot['ctr']}",
        f"average_position={snapshot['average_position']}",
        (
            "wordpress_inventory_match=present"
            if wordpress_match
            else "wordpress_inventory_match=missing"
        ),
    ]


def _gsc_missing_evidence(wordpress_match: bool) -> list[str]:
    missing = [
        "brak dowodu jakości leadów, wpływu na przychód i wzrostu pozycji",
        "brak zatwierdzonego szkicu zmian WordPress",
    ]
    if not wordpress_match:
        missing.insert(0, "brak potwierdzonego kanonicznego URL w spisie treści WordPress")
    return missing


def _ahrefs_source_facts(fact: MetricFact, topic: str) -> list[str]:
    dimensions = fact.dimensions
    facts = [
        f"ahrefs_topic={topic}",
        f"metric_name={fact.name}",
        f"metric_value={fact.value}",
    ]
    for key in ("gap_type", "keyword", "competitor_domain", "source_url", "target_url"):
        value = dimensions.get(key)
        if value:
            facts.append(f"{key}={value}")
    return facts


def _brief_outline(topic: str, wordpress_match: bool) -> list[dict[str, str]]:
    action = "odświeżenia istniejącej strony" if wordpress_match else "sprawdzenia tematu"
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
            "instruction": "Dopasuj CTA do usługi Ekologus, ale bez obietnicy przychodu ani wzrostu leadów.",
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


def _url_host(value: str | None) -> str | None:
    if not value:
        return None
    host = urlparse(value).netloc.lower()
    return host or None


def _candidate_slug_for_page(value: str) -> str:
    path = _normalized_path(value)
    if path and path != "/":
        return _slug(path)
    parsed = urlparse(value)
    if parsed.netloc:
        return _slug(parsed.netloc)
    return _slug(value) or "homepage"


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
