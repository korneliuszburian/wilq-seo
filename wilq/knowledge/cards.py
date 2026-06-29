from __future__ import annotations

from wilq.schemas import KnowledgeCard

CARD_TYPES = (
    "service_card",
    "content_card",
    "keyword_cluster_card",
    "campaign_card",
    "voice_rule",
    "ads_pattern_card",
    "negative_keyword_pattern_card",
    "competitor_card",
    "local_visibility_card",
    "social_pattern_card",
)


def seed_cards() -> list[KnowledgeCard]:
    return [
        KnowledgeCard(
            id="card_goal_001_rules",
            card_type="voice_rule",
            title="Bez zmyślonych metryk",
            summary=(
                "Rekomendacje marketingowe muszą opierać się na dowodach "
                "i źródłach danych z WILQ API."
            ),
            source_type="repo_goal",
            source_id="docs/goals/001-goal.md",
            source_url_or_path="docs/goals/001-goal.md",
            confidence=1.0,
            source_lineage=["docs/goals/001-goal.md"],
        )
    ]
