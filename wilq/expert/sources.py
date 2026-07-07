from __future__ import annotations

from datetime import date

from wilq.expert.rules import list_expert_rules
from wilq.schemas import ExpertKnowledgeSource, KnowledgeTaxonomyType


_PLATFORM_SOURCE_BY_DOMAIN: dict[str, tuple[str, str, str]] = {
    "ads": (
        "src_google_ads_api_docs",
        "Google Ads API documentation and WILQ structured Ads rules",
        "google_ads_api",
    ),
    "analytics": (
        "src_ga4_data_api_docs",
        "GA4 Data API documentation and WILQ structured GA4 diagnostics rules",
        "ga4_data_api",
    ),
    "merchant": (
        "src_google_merchant_center_docs",
        "Google Merchant Center documentation and WILQ Merchant diagnostics rules",
        "merchant_center",
    ),
    "seo": (
        "src_google_search_console_docs",
        "Google Search Console documentation and WILQ SEO diagnostics rules",
        "search_console",
    ),
    "content": (
        "src_wilq_content_rules",
        "WILQ content workflow, claim ledger and WordPress inventory rules",
        "wilq_content_rules",
    ),
    "local": (
        "src_localo_and_gbp_rules",
        "Localo/GBP local visibility readiness rules represented through WILQ",
        "local_visibility_rules",
    ),
    "social": (
        "src_social_platform_review_rules",
        "LinkedIn/Facebook publishing readiness and duplicate-risk rules represented through WILQ",
        "social_review_rules",
    ),
}


def _source_for_domain(domain: str, rule_ids: list[str]) -> ExpertKnowledgeSource:
    source_id, reference, anchor = _PLATFORM_SOURCE_BY_DOMAIN.get(
        domain,
        (
            f"src_wilq_{domain}_rules",
            f"WILQ structured {domain} expert rules",
            f"wilq_{domain}_rules",
        ),
    )
    knowledge_type = (
        KnowledgeTaxonomyType.platform_trap
        if domain in {"ads", "analytics", "merchant", "seo"}
        else KnowledgeTaxonomyType.expert_operating
    )
    return ExpertKnowledgeSource(
        id=source_id,
        domain=domain,
        knowledge_type=knowledge_type,
        source_type="official_platform_doc"
        if knowledge_type == KnowledgeTaxonomyType.platform_trap
        else "repo_structured_rule",
        license_status="commit_safe",
        source_reference=reference,
        freshness_date=date(2026, 7, 7),
        reviewer="wilq_system",
        trust_level="high" if knowledge_type == KnowledgeTaxonomyType.platform_trap else "medium",
        allowed_usage=[
            "expert_rule_source_lineage",
            "daily_check_blockers",
            "diagnostic_explanation",
            anchor,
        ],
        forbidden_usage=[
            "raw_private_prompt_stuffing",
            "automatic_vendor_write",
            "success_claim_without_measurement_window",
        ],
        linked_rule_ids=rule_ids,
    )


def list_expert_knowledge_sources() -> tuple[ExpertKnowledgeSource, ...]:
    rule_ids_by_domain: dict[str, list[str]] = {}
    for rule in list_expert_rules():
        rule_ids_by_domain.setdefault(rule.domain, []).append(rule.id)
    return tuple(
        _source_for_domain(domain, sorted(rule_ids))
        for domain, rule_ids in sorted(rule_ids_by_domain.items())
    )


def expert_source_ids_for_rule(domain: str) -> list[str]:
    source = next(
        (source for source in list_expert_knowledge_sources() if source.domain == domain),
        None,
    )
    return [] if source is None else [source.id]
