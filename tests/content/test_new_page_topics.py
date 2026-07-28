from types import SimpleNamespace

import pytest

from wilq.content.workflow.new_page import ContentNewPageBriefInput, build_new_page_brief
from wilq.content.workflow.new_page_topics import (
    build_new_page_topic_recommendations,
    resolve_new_page_topic_candidate,
)


def test_topic_recommendation_requires_exact_demand_and_no_existing_page() -> None:
    recommendations = build_new_page_topic_recommendations(_diagnostics())

    assert recommendations.status == "ready"
    assert len(recommendations.candidates) == 1
    candidate = recommendations.candidates[0]
    assert candidate.title == "Operat wodnoprawny"
    assert candidate.source_connectors == ["ahrefs", "google_search_console"]
    assert resolve_new_page_topic_candidate(
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        recommendations=recommendations,
    ) == candidate


def test_topic_with_existing_wordpress_match_is_not_offered_as_new_page() -> None:
    recommendations = build_new_page_topic_recommendations(
        _diagnostics(wordpress_strength="exact")
    )

    assert recommendations.status == "no_qualified_topics"
    assert recommendations.candidates == []


def test_source_backed_brief_requires_current_exact_topic_identity() -> None:
    candidate = build_new_page_topic_recommendations(_diagnostics()).candidates[0]
    input = ContentNewPageBriefInput(
        title=candidate.title,
        purpose="Pomóc inwestorowi zrozumieć wymagania operatu.",
        service="Obsługa środowiskowa",
        audience="Inwestor realizujący przedsięwzięcie",
        search_intent="operat wodnoprawny wymagania",
        proposed_ia_location="Usługi → Gospodarka wodna",
        topic_candidate_id=candidate.candidate_id,
        topic_candidate_digest=candidate.candidate_digest,
    )

    brief = build_new_page_brief(input, topic_candidate=candidate)

    assert brief.topic_evidence_ids == ["ev_ahrefs", "ev_gsc"]
    with pytest.raises(ValueError, match="Wybrany temat zmienił się"):
        build_new_page_brief(
            input.model_copy(update={"title": "Inny temat"}), topic_candidate=candidate
        )


def _diagnostics(wordpress_strength: str = "missing") -> object:
    candidate = SimpleNamespace(
        topic="Operat wodnoprawny",
        keyword="Operat wodnoprawny",
        gap_type="content_gap",
        relevance_status="relevant",
        relevance_score=42,
        gsc_cross_check=SimpleNamespace(strength="exact"),
        wordpress_cross_check=SimpleNamespace(strength=wordpress_strength),
        source_connectors=["ahrefs", "google_search_console"],
        evidence_ids=["ev_ahrefs", "ev_gsc"],
        mapping_key="ahrefs-gap-v1|content_gap|operat",
    )
    return SimpleNamespace(
        gap_read_contract=SimpleNamespace(
            status="ready",
            source_connectors=["ahrefs", "google_search_console", "wordpress_ekologus"],
            evidence_ids=["ev_ahrefs", "ev_gsc", "ev_wp"],
            cross_check_candidates=[candidate],
        )
    )
