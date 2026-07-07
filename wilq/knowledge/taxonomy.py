from __future__ import annotations

from wilq.schemas import KnowledgeTaxonomyEntry, KnowledgeTaxonomyType


_TAXONOMY: tuple[KnowledgeTaxonomyEntry, ...] = (
    KnowledgeTaxonomyEntry(
        id=KnowledgeTaxonomyType.client_truth,
        definition=(
            "Reviewed facts about Ekologus: services, CTAs, buyer problems, claim policy, "
            "source lineage and owner-approved wording."
        ),
        owned_by="source_fact_compiler",
        allowed_usage=[
            "service fit and CTA matching",
            "claim ledger allow/block decisions",
            "content brief grounding",
        ],
        forbidden_usage=[
            "diagnostic thresholds",
            "platform API constraints",
            "proof of marketing outcome without measurement evidence",
        ],
        example_records=[
            "content_source_fact:ekologus_public_bdo_faq",
            "content_knowledge_card:claim_policy",
        ],
    ),
    KnowledgeTaxonomyEntry(
        id=KnowledgeTaxonomyType.expert_operating,
        definition=(
            "Reusable marketing/operator rules that say when a signal matters, what must "
            "be checked, what can be recommended and what conclusion is blocked."
        ),
        owned_by="expert_rule_compiler",
        allowed_usage=[
            "diagnostic decision ranking",
            "safe next action templates",
            "false-positive checks",
        ],
        forbidden_usage=[
            "claiming Ekologus-specific service facts",
            "overriding source freshness or evidence gates",
            "vendor writes without ActionObject flow",
        ],
        example_records=[
            "expert_rule:ga4_diagnostics_v1",
            "expert_rule:merchant_feed_rules_v1",
        ],
    ),
    KnowledgeTaxonomyEntry(
        id=KnowledgeTaxonomyType.platform_trap,
        definition=(
            "Rules from platform documentation and known API behavior: GAQL constraints, "
            "GA4 measurement caveats, Merchant issue semantics, GSC data limits and "
            "WordPress inventory/canonical traps."
        ),
        owned_by="platform_rule_pack",
        allowed_usage=[
            "blocking unsupported platform conclusions",
            "explaining missing contracts",
            "shaping read-only diagnostics",
        ],
        forbidden_usage=[
            "business strategy on its own",
            "client-specific service claims",
            "success claims without observed outcome evidence",
        ],
        example_records=[
            "platform_rule:google_ads_gaql_validator",
            "platform_rule:gsc_baseline_required",
        ],
    ),
    KnowledgeTaxonomyEntry(
        id=KnowledgeTaxonomyType.workspace_memory,
        definition=(
            "Account/workspace memory for a concrete client: business brief, known "
            "false positives, previous checks, open blockers, reviewed exclusions and "
            "recommendation history."
        ),
        owned_by="workspace_dossier",
        allowed_usage=[
            "daily-check prioritization",
            "known false-positive suppression",
            "handoff and review continuity",
        ],
        forbidden_usage=[
            "global expert rules",
            "new source facts without review",
            "measurement success without observation window",
        ],
        example_records=[
            "workspace_dossier:ekologus",
            "known_false_positive:holiday_low_volume",
        ],
    ),
    KnowledgeTaxonomyEntry(
        id=KnowledgeTaxonomyType.observed_outcome,
        definition=(
            "Measured post-action or post-publication result from an observation window. "
            "It can create learning proposals, but does not rewrite knowledge automatically."
        ),
        owned_by="measurement_loop",
        allowed_usage=[
            "learning proposal evidence",
            "monthly review context",
            "recommendation follow-up",
        ],
        forbidden_usage=[
            "automatic promotion of knowledge to approved-current",
            "future success guarantees",
            "ROAS/revenue claims without matching contracts",
        ],
        example_records=[
            "measurement_window:content_refresh_bdo",
            "learning_proposal:ctr_title_refresh",
        ],
    ),
)


def list_knowledge_taxonomy() -> tuple[KnowledgeTaxonomyEntry, ...]:
    return _TAXONOMY
