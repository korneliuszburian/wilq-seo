from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from wilq.schemas import MetricFact

CONTENT_REFRESH_ACTION_TYPE = "wordpress_content_refresh"
CONTENT_BRIEF_PREVIEW_CONTRACT = "content_brief_preview_v1"
WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT = "wordpress_draft_payload_preview_v1"
CONTENT_TARGET_SITE_HOST = "ekologus.dev.proudsite.pl"
CONTENT_TARGET_SITE_SCHEME = "https"
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


def content_payload_with_reviewed_wordpress_draft_previews(
    payload: dict[str, Any],
    *,
    review_event_summaries: Iterable[str],
) -> dict[str, Any]:
    if payload.get("action_type") != CONTENT_REFRESH_ACTION_TYPE:
        return payload
    enriched_payload = dict(payload)
    enriched_payload.pop("wordpress_draft_payload_preview", None)
    reviewed_candidate_ids = _reviewed_candidate_ids(review_event_summaries)
    if not reviewed_candidate_ids:
        return enriched_payload
    brief_previews = [
        item
        for item in enriched_payload.get("content_brief_preview", [])
        if isinstance(item, dict)
    ]
    draft_previews = [
        _wordpress_draft_payload_preview(item)
        for item in brief_previews
        if isinstance(item.get("candidate_id"), str)
        and item["candidate_id"] in reviewed_candidate_ids
    ]
    if draft_previews:
        enriched_payload["wordpress_draft_payload_preview"] = draft_previews
    return enriched_payload


def _gsc_content_brief_previews(metric_facts: list[MetricFact]) -> list[dict[str, Any]]:
    wordpress_urls_by_path = _wordpress_inventory_urls_by_path(metric_facts)
    wordpress_details_by_path = _wordpress_inventory_details_by_path(metric_facts)
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
        wordpress_details = wordpress_details_by_path.get(page_path)
        wordpress_match = wordpress_target_url is not None
        mode = "refresh" if wordpress_match else "inventory_check"
        decision_options = ["refresh", "merge", "block"] if wordpress_match else [
            "merge",
            "create",
            "block",
        ]
        target_site_context = _target_site_context(
            source_url=page,
            target_site_url=wordpress_target_url,
            wordpress_match=wordpress_match,
        )
        target_site_inventory_context = _target_site_inventory_context(
            target_site_url=target_site_context.get("target_site_url"),
            inventory_details=wordpress_details,
        )
        content_gate_status = _content_gate_status_for_brief(
            source_type="gsc_query_page",
            mode=mode,
            wordpress_match=wordpress_match,
            target_site_adaptation_status=target_site_context.get(
                "target_site_adaptation_status"
            )
            if isinstance(target_site_context.get("target_site_adaptation_status"), str)
            else None,
        )
        previews.append(
            {
                "preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
                "candidate_id": f"content_brief_gsc_{_candidate_slug_for_page(page)}",
                "source_type": "gsc_query_page",
                "mode": mode,
                "topic": primary_query,
                "target_url": page,
                **target_site_context,
                **target_site_inventory_context,
                **content_gate_status,
                "wordpress_inventory_match": "present" if wordpress_match else "missing",
                "decision_options": decision_options,
                "metric_snapshot": _gsc_metric_snapshot(page_facts),
                "brief_goal": _gsc_brief_goal(wordpress_match, primary_query),
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
                "publication_blockers": _publication_blockers(),
                "source_facts": _gsc_source_facts(page, page_facts, wordpress_match),
                "missing_evidence": _gsc_missing_evidence(wordpress_match),
                "forbidden_claims": CONTENT_BLOCKED_CLAIMS,
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


def _wordpress_draft_payload_preview(preview: dict[str, Any]) -> dict[str, Any]:
    topic = str(preview.get("topic") or "Brief treści")
    mode = str(preview.get("mode") or "review")
    source_type = str(preview.get("source_type") or "unknown")
    target_url = preview.get("target_url") if isinstance(preview.get("target_url"), str) else None
    source_url = preview.get("source_url") if isinstance(preview.get("source_url"), str) else None
    target_site_url = (
        preview.get("target_site_url")
        if isinstance(preview.get("target_site_url"), str)
        else None
    )
    migration_candidate_url = (
        preview.get("target_site_migration_candidate_url")
        if isinstance(preview.get("target_site_migration_candidate_url"), str)
        else None
    )
    migration_status = (
        preview.get("target_site_migration_status")
        if isinstance(preview.get("target_site_migration_status"), str)
        else None
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
        migration_status,
        canonical_gate_status=canonical_gate_status,
        duplicate_gate_status=duplicate_gate_status,
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
        "target_url": target_url,
        "source_url": source_url,
        "target_site_url": target_site_url,
        "target_site_host": preview.get("target_site_host")
        if isinstance(preview.get("target_site_host"), str)
        else None,
        "source_site_host": preview.get("source_site_host")
        if isinstance(preview.get("source_site_host"), str)
        else None,
        "target_site_adaptation_status": preview.get("target_site_adaptation_status")
        if isinstance(preview.get("target_site_adaptation_status"), str)
        else None,
        "target_site_migration_candidate_url": migration_candidate_url,
        "target_site_migration_status": migration_status,
        "target_site_migration_summary": preview.get("target_site_migration_summary")
        if isinstance(preview.get("target_site_migration_summary"), str)
        else None,
        "target_site_review_requirements": _target_site_review_requirements(
            preview.get("target_site_migration_status")
            if isinstance(preview.get("target_site_migration_status"), str)
            else None,
        ),
        "target_site_inventory_content_type": preview.get(
            "target_site_inventory_content_type"
        )
        if isinstance(preview.get("target_site_inventory_content_type"), str)
        else None,
        "target_site_inventory_status": preview.get("target_site_inventory_status")
        if isinstance(preview.get("target_site_inventory_status"), str)
        else None,
        "target_site_inventory_source": preview.get("target_site_inventory_source")
        if isinstance(preview.get("target_site_inventory_source"), str)
        else None,
        "target_site_inventory_modified_gmt": preview.get(
            "target_site_inventory_modified_gmt"
        )
        if isinstance(preview.get("target_site_inventory_modified_gmt"), str)
        else None,
        "target_site_inventory_missing_fields": [
            item
            for item in preview.get("target_site_inventory_missing_fields", [])
            if isinstance(item, str)
        ],
        "target_site_inventory_summary": preview.get("target_site_inventory_summary")
        if isinstance(preview.get("target_site_inventory_summary"), str)
        else None,
        "inventory_gate_status": inventory_gate_status,
        "canonical_gate_status": canonical_gate_status,
        "duplicate_gate_status": duplicate_gate_status,
        "content_gate_summary": preview.get("content_gate_summary")
        if isinstance(preview.get("content_gate_summary"), str)
        else None,
        "draft_generation_status": draft_generation_status,
        "draft_blockers": _draft_blockers(draft_generation_status),
        "draft_payload": {
            "post_status": "draft",
            "post_title": _draft_title(topic, mode),
            "post_excerpt_direction": _draft_excerpt_direction(preview),
            "content_blocks": _draft_content_blocks(preview),
        },
        "required_validation": _unique(
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
        ),
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
    migration_status: str | None,
    *,
    canonical_gate_status: str | None,
    duplicate_gate_status: str | None,
) -> str:
    if migration_status == "confirmed_target_inventory":
        if canonical_gate_status in {
            "needs_target_canonical_review",
            "blocked_until_mapping_review",
            "blocked_until_inventory_review",
        } or duplicate_gate_status in {
            "refresh_or_merge_required",
            "manual_merge_or_create_review",
            "create_blocked_until_duplicate_check",
        }:
            return "blocked_pending_canonical_duplicate_review"
        return "ready_for_review"
    if migration_status == "needs_review":
        return "blocked_pending_target_mapping"
    if migration_status == "blocked_missing_inventory":
        return "blocked_missing_target_inventory"
    return "blocked_until_content_review"


def _draft_blockers(draft_generation_status: str) -> list[str]:
    blockers = [
        "wordpress_write_not_requested",
        "api_mutation_ready_false",
        "human_confirm_before_wordpress_write",
    ]
    if draft_generation_status == "ready_for_review":
        return [
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_target_mapping":
        return [
            "target_site_inventory_mapping_review",
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_canonical_duplicate_review":
        return [
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_missing_target_inventory":
        return [
            "target_site_inventory_required",
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    return [
        "business_relevance_review",
        "wordpress_inventory_check",
        "duplicate_or_cannibalization_check",
        *blockers,
    ]


def _draft_title(topic: str, mode: str) -> str:
    prefix = "Refresh" if mode in {"refresh", "merge"} else "Brief"
    return f"{prefix}: {topic}"


def _draft_excerpt_direction(preview: dict[str, Any]) -> str:
    goal = preview.get("brief_goal")
    if isinstance(goal, str) and goal:
        return goal
    return "Szkic briefu do review. Nie publikować bez walidacji operatora."


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
            blocks.append({"section": section, "instruction": instruction})
    return blocks


def _content_gate_status_for_brief(
    *,
    source_type: str,
    mode: str,
    wordpress_match: bool,
    target_site_adaptation_status: str | None,
) -> dict[str, str]:
    if source_type == "gsc_query_page" and mode == "refresh" and wordpress_match:
        if target_site_adaptation_status == "target_site_alias_match":
            return {
                "inventory_gate_status": "confirmed_target_inventory",
                "canonical_gate_status": "needs_target_canonical_review",
                "duplicate_gate_status": "refresh_or_merge_required",
                "content_gate_summary": (
                    "Inventory potwierdza docelową stronę na target site. Brief może "
                    "iść do refresh/merge review, ale canonical i duplikaty wymagają "
                    "ręcznego potwierdzenia przed draftem albo stagingiem."
                ),
            }
        return {
            "inventory_gate_status": "confirmed_current_inventory",
            "canonical_gate_status": "current_url_confirmed",
            "duplicate_gate_status": "refresh_or_merge_required",
            "content_gate_summary": (
                "Inventory potwierdza istniejący URL. WILQ traktuje to jako "
                "refresh/merge, nie nowy artykuł; create pozostaje zablokowane "
                "przed kontrolą duplikacji."
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
            "To jest kandydat z Ahrefs do review, nie decyzja create. Najpierw "
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
                **_content_gate_status_for_brief(
                    source_type="ahrefs_gap_review",
                    mode="review",
                    wordpress_match=False,
                    target_site_adaptation_status=None,
                ),
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
                "publication_blockers": _publication_blockers(),
                "source_facts": _ahrefs_source_facts(fact, topic),
                "missing_evidence": [
                    "brak potwierdzenia popytu GSC dla tematu",
                    "brak potwierdzenia dopasowania WordPress inventory",
                    "brak dowodu wpływu na ruch, leady albo revenue",
                ],
                "forbidden_claims": CONTENT_BLOCKED_CLAIMS,
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


def _wordpress_inventory_urls_by_path(metric_facts: list[MetricFact]) -> dict[str, str]:
    urls_by_path: dict[str, str] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        url = fact.dimensions.get("content_url")
        if not url:
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
        path = _normalized_path(url)
        if not path:
            continue
        details_by_path.setdefault(
            path,
            {
                "content_type": fact.dimensions.get("content_type", ""),
                "status": fact.dimensions.get("status", ""),
                "inventory_source": fact.dimensions.get("inventory_source", ""),
                "modified_gmt": fact.dimensions.get("modified_gmt", ""),
            },
        )
    return details_by_path


def _target_site_context(
    *,
    source_url: str,
    target_site_url: str | None,
    wordpress_match: bool,
) -> dict[str, str | None]:
    source_host = _url_host(source_url)
    target_host = _url_host(target_site_url) if target_site_url else None
    if not wordpress_match:
        status = "needs_inventory_match"
    elif target_host and source_host and target_host != source_host:
        status = "target_site_alias_match"
    else:
        status = "current_site_match"
    migration_candidate_url = _target_site_migration_candidate_url(
        source_url=source_url,
        target_site_url=target_site_url,
        target_site_adaptation_status=status,
    )
    migration_status = _target_site_migration_status(
        target_site_adaptation_status=status,
        migration_candidate_url=migration_candidate_url,
    )
    review_requirements = _target_site_review_requirements(migration_status)
    return {
        "source_url": source_url,
        "source_site_host": source_host,
        "target_site_url": target_site_url,
        "target_site_host": target_host,
        "target_site_adaptation_status": status,
        "target_site_migration_candidate_url": migration_candidate_url,
        "target_site_migration_status": migration_status,
        "target_site_migration_summary": _target_site_migration_summary(
            migration_status,
            migration_candidate_url,
        ),
        "target_site_review_requirements": review_requirements,
    }


def _target_site_inventory_context(
    *,
    target_site_url: str | None,
    inventory_details: dict[str, str] | None,
) -> dict[str, object]:
    if not target_site_url:
        return {
            "target_site_inventory_missing_fields": [
                "target_site_url",
                "title_or_h1",
                "canonical_url",
            ],
            "target_site_inventory_summary": (
                "Brak target URL w inventory. Nie przygotowuj draftu ani stagingu "
                "bez ręcznego mapowania."
            ),
        }

    if inventory_details is None:
        return {
            "target_site_inventory_missing_fields": [
                "content_type",
                "status",
                "inventory_source",
                "modified_gmt",
                "title_or_h1",
                "canonical_url",
            ],
            "target_site_inventory_summary": (
                "Brak szczegółu inventory dla target URL. WILQ może pokazać "
                "kandydata mapowania, ale draft i staging wymagają potwierdzenia."
            ),
        }

    missing = [
        field
        for field in ("content_type", "status", "inventory_source", "modified_gmt")
        if not inventory_details.get(field)
    ]
    missing.extend(["title_or_h1", "canonical_url"])
    content_type = inventory_details.get("content_type") or None
    status = inventory_details.get("status") or None
    inventory_source = inventory_details.get("inventory_source") or None
    modified_gmt = inventory_details.get("modified_gmt") or None
    known_parts = _unique(
        [
            f"type={content_type}" if content_type else "",
            f"status={status}" if status else "",
            f"source={inventory_source}" if inventory_source else "",
            f"modified_gmt={modified_gmt}" if modified_gmt else "",
        ]
    )
    summary = "Inventory potwierdza target URL"
    if known_parts:
        summary = f"{summary}: {', '.join(known_parts)}"
    summary = (
        f"{summary}. Przed draftem/stagingiem nadal sprawdź: "
        f"{', '.join(missing)}."
    )
    return {
        "target_site_inventory_content_type": content_type,
        "target_site_inventory_status": status,
        "target_site_inventory_source": inventory_source,
        "target_site_inventory_modified_gmt": modified_gmt,
        "target_site_inventory_missing_fields": missing,
        "target_site_inventory_summary": summary,
    }


def _target_site_migration_candidate_url(
    *,
    source_url: str,
    target_site_url: str | None,
    target_site_adaptation_status: str,
) -> str | None:
    if target_site_adaptation_status == "target_site_alias_match":
        return target_site_url
    parsed = urlparse(source_url)
    source_host = parsed.netloc.lower()
    if source_host not in CONTENT_SOURCE_SITE_HOSTS:
        return None
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{CONTENT_TARGET_SITE_SCHEME}://{CONTENT_TARGET_SITE_HOST}{path}{query}"


def _target_site_migration_status(
    *,
    target_site_adaptation_status: str,
    migration_candidate_url: str | None,
) -> str:
    if target_site_adaptation_status == "target_site_alias_match":
        return "confirmed_target_inventory"
    if target_site_adaptation_status == "needs_inventory_match":
        return "blocked_missing_inventory"
    if migration_candidate_url:
        return "needs_review"
    return "not_applicable"


def _target_site_migration_summary(
    migration_status: str,
    migration_candidate_url: str | None,
) -> str:
    if migration_status == "confirmed_target_inventory":
        return (
            "Inventory potwierdza URL na target site; przed draftem nadal sprawdź "
            "canonical, duplikaty i review."
        )
    if migration_status == "needs_review" and migration_candidate_url:
        return (
            "WILQ wskazuje kandydata old-to-new na target site, ale inventory go "
            "nie potwierdza w tym payloadzie. Wymagane ręczne mapowanie przed "
            "draftem albo stagingiem."
        )
    if migration_status == "blocked_missing_inventory":
        return (
            "Brak potwierdzenia inventory. Nie twórz draftu ani nowej strony przed "
            "kontrolą sitemap, canonical i duplikatów."
        )
    return "Brak kandydata migracji na target site dla tej pozycji."


def _target_site_review_requirements(migration_status: str | None) -> list[str]:
    if migration_status == "confirmed_target_inventory":
        return [
            "target_site_inventory_confirmed",
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ]
    if migration_status == "needs_review":
        return [
            "target_site_inventory_mapping_review",
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ]
    if migration_status == "blocked_missing_inventory":
        return [
            "target_site_inventory_required",
            "target_site_canonical_review",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write",
        ]
    return [
        "business_relevance_review",
        "wordpress_inventory_check",
        "duplicate_or_cannibalization_check",
        "human_confirm_before_wordpress_write",
    ]


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


def _ahrefs_content_angle(topic: str) -> str:
    return (
        f"Potraktuj `{topic}` jako inspirację konkurencyjną do review, nie jako gotowy "
        "temat publikacji, dopóki GSC i WordPress nie potwierdzą sensu biznesowego."
    )


def _content_audience(topic: str) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return "Przedsiębiorca lub osoba operacyjna sprawdzająca obowiązki BDO i ryzyka formalne."
    if "zielony lad" in normalized or "esg" in normalized:
        return "Decydent lub specjalista środowiskowy szukający prostego wyjaśnienia regulacji."
    if "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        return "Firma potrzebująca bezpiecznego procesu, produktu albo konsultacji w obszarze odpadów."
    return "Marketer i ekspert Ekologus powinni doprecyzować odbiorcę przed pisaniem treści."


def _key_objections(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    objections = [
        "czy temat jest aktualny prawnie i zgodny z realną usługą Ekologus",
        "czy nie istnieje już strona, którą trzeba odświeżyć zamiast tworzyć nową",
    ]
    if "bdo" in normalized:
        objections.append("czy użytkownik potrzebuje definicji, checklisty obowiązków czy konsultacji")
    elif "zielony lad" in normalized or "esg" in normalized:
        objections.append("czy tekst ma wyjaśniać pojęcie, obowiązki firmy czy wpływ na procesy")
    else:
        objections.append("czy intencja jest edukacyjna, zakupowa czy konsultacyjna")
    return objections


def _h1_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return f"H1 powinien jasno odpowiadać na intencję `{topic}` i nie sugerować nowej, osobnej strony."
    return f"H1 roboczy dla `{topic}` dopiero po potwierdzeniu kanonicznego URL i braku duplikatu."


def _seo_title_direction(topic: str, wordpress_match: bool) -> str:
    action = "odświeżany URL" if wordpress_match else "kanoniczny URL po review"
    return (
        f"Title powinien zawierać intencję `{topic}`, jasno opisywać {action} "
        "i nie obiecywać pozycji, leadów ani kompletnej zgodności prawnej."
    )


def _meta_description_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"Meta description ma streścić odpowiedź na `{topic}` i kierować do "
            "konsultacji Ekologus bez claimów wyniku."
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
        "Jakie informacje trzeba potwierdzić przed wdrożeniem?",
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
        return "CTA do rozmowy o wpływie regulacji na firmę, bez claimów revenue albo lead uplift."
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
        "target_site_mapping_or_inventory_review",
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
        "wordpress_inventory_match=present" if wordpress_match else "wordpress_inventory_match=missing",
    ]


def _gsc_missing_evidence(wordpress_match: bool) -> list[str]:
    missing = [
        "brak dowodu lead quality, revenue impact i wzrostu pozycji",
        "brak zatwierdzonego payloadu WordPress write",
    ]
    if not wordpress_match:
        missing.insert(0, "brak potwierdzonego kanonicznego URL w WordPress inventory")
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
