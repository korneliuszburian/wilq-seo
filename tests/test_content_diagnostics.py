from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import sleep

import wilq.briefing.content_diagnostics as content_diagnostics_module
from wilq.briefing.content_diagnostics import (
    _rank_content_decisions_for_diagnostics,
    build_content_diagnostics,
)
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    MetricFact,
    TacticalQueueResponse,
)


def test_content_diagnostics_cache_reuses_one_build_for_initial_request_flow(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_CONTENT_DIAGNOSTICS_CACHE_SECONDS", "15")
    content_diagnostics_module.clear_content_diagnostics_cache()


def test_content_diagnostics_default_cache_survives_startup_waterfall(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_CONTENT_DIAGNOSTICS_CACHE_SECONDS", raising=False)
    content_diagnostics_module.clear_content_diagnostics_cache()


    now = 100.0
    calls = 0
    sentinel = ContentDiagnosticsResponse.model_construct()

    def fake_build() -> ContentDiagnosticsResponse:
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(content_diagnostics_module, "monotonic", lambda: now)
    monkeypatch.setattr(content_diagnostics_module, "build_content_diagnostics", fake_build)

    first = content_diagnostics_module.build_content_diagnostics_cached()
    now += 30.0
    second = content_diagnostics_module.build_content_diagnostics_cached()

    assert first is sentinel
    assert second is sentinel
    assert calls == 1
    content_diagnostics_module.clear_content_diagnostics_cache()
    calls = 0
    sentinel = ContentDiagnosticsResponse.model_construct()

    def fake_build() -> ContentDiagnosticsResponse:
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(content_diagnostics_module, "build_content_diagnostics", fake_build)

    first = content_diagnostics_module.build_content_diagnostics_cached()
    second = content_diagnostics_module.build_content_diagnostics_cached()

    assert first is sentinel
    assert second is sentinel
    assert calls == 1
    content_diagnostics_module.clear_content_diagnostics_cache()


def test_content_diagnostics_cache_invalidates_when_refresh_identity_changes(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_CONTENT_DIAGNOSTICS_CACHE_SECONDS", "60")
    content_diagnostics_module.clear_content_diagnostics_cache()
    refresh_identity = ("refresh-a",)
    calls = 0
    first = ContentDiagnosticsResponse.model_construct()
    second = ContentDiagnosticsResponse.model_construct()

    monkeypatch.setattr(
        content_diagnostics_module,
        "_content_diagnostics_refresh_identity",
        lambda: (("google_search_console", *refresh_identity, ()),),
    )

    def fake_build() -> ContentDiagnosticsResponse:
        nonlocal calls
        calls += 1
        return first if calls == 1 else second

    monkeypatch.setattr(content_diagnostics_module, "build_content_diagnostics", fake_build)
    assert content_diagnostics_module.build_content_diagnostics_cached() is first
    assert content_diagnostics_module.build_content_diagnostics_cached() is first
    assert calls == 1

    refresh_identity = ("refresh-b",)
    assert content_diagnostics_module.build_content_diagnostics_cached() is second
    assert calls == 2
    content_diagnostics_module.clear_content_diagnostics_cache()


def test_content_diagnostics_cache_serializes_concurrent_cold_builds(monkeypatch) -> None:
    calls: list[str] = []
    sentinel = ContentDiagnosticsResponse.model_construct()

    monkeypatch.setattr(
        content_diagnostics_module,
        "_content_diagnostics_cache_seconds",
        lambda: 60.0,
    )
    monkeypatch.setattr(content_diagnostics_module, "monotonic", lambda: 0.0)

    def fake_build() -> ContentDiagnosticsResponse:
        calls.append("build")
        sleep(0.05)
        return sentinel

    monkeypatch.setattr(content_diagnostics_module, "build_content_diagnostics", fake_build)
    content_diagnostics_module.clear_content_diagnostics_cache()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: content_diagnostics_module.build_content_diagnostics_cached(),
                [1, 2],
            )
        )

    assert results == [sentinel, sentinel]
    assert calls == ["build"]
    content_diagnostics_module.clear_content_diagnostics_cache()


def test_content_diagnostics_uses_latest_metric_evidence_by_identity() -> None:
    old_at = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
    new_at = datetime(2026, 6, 29, 8, 0, tzinfo=UTC)
    page = "https://www.ekologus.pl/"
    query = "ekologus"

    diagnostics = build_content_diagnostics(
        tactical_items=[],
        actions=[],
        metric_facts=[
            _gsc_fact("clicks", 1, query, page, "ev_old_gsc", old_at),
            _gsc_fact("clicks", 7, query, page, "ev_new_gsc", new_at),
            _wordpress_fact(page, "ev_old_wp", old_at),
            _wordpress_fact(page, "ev_new_wp", new_at),
        ],
    )

    all_section_evidence = {
        evidence_id for section in diagnostics.sections for evidence_id in section.evidence_ids
    }

    assert "ev_new_gsc" in diagnostics.evidence_ids
    assert "ev_new_wp" in diagnostics.evidence_ids
    assert "ev_old_gsc" not in diagnostics.evidence_ids
    assert "ev_old_wp" not in diagnostics.evidence_ids
    assert "ev_new_gsc" in all_section_evidence
    assert "ev_new_wp" in all_section_evidence
    assert "ev_old_gsc" not in all_section_evidence
    assert "ev_old_wp" not in all_section_evidence


def test_content_diagnostics_keeps_all_ranked_evidenced_pages_in_workflow_queue(
    monkeypatch,
) -> None:
    collected_at = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
    bdo_page = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    pages = [bdo_page, *[f"https://www.ekologus.pl/usluga-{index}/" for index in range(6)]]
    facts: list[MetricFact] = []
    for index, page in enumerate(pages):
        query = "bdo co to jest" if page == bdo_page else f"usługa {index}"
        impressions = 1000 if page == bdo_page else 10 + index
        evidence_suffix = "bdo" if page == bdo_page else str(index)
        facts.extend(
            [
                _gsc_fact(
                    "impressions",
                    impressions,
                    query,
                    page,
                    f"ev_gsc_{evidence_suffix}",
                    collected_at,
                ),
                _gsc_fact(
                    "clicks",
                    1,
                    query,
                    page,
                    f"ev_gsc_{evidence_suffix}",
                    collected_at,
                ),
                _wordpress_fact(page, f"ev_wp_{evidence_suffix}", collected_at),
            ]
        )
    monkeypatch.setattr(
        content_diagnostics_module,
        "build_tactical_queue",
        lambda **_: TacticalQueueResponse.model_construct(items=[]),
    )

    diagnostics = build_content_diagnostics(actions=[], metric_facts=facts)

    assert any(decision.page == bdo_page for decision in diagnostics.decision_queue)
    assert len(diagnostics.decision_queue) == len(pages)
    assert {decision.page for decision in diagnostics.decision_queue} == set(pages)


def test_content_diagnostics_ranking_prefers_fresh_primary_over_stale_ahrefs() -> None:
    gsc_decision = ContentDecisionItem(
        id="content_decision_gsc_refresh",
        title="GSC refresh",
        decision_type="refresh_or_merge",
        status="ready",
        priority=23,
        total_impressions=700,
        query_count=2,
        reason="GSC i WordPress mają świeży sygnał.",
        rationale="Primary content evidence is current.",
        next_step="Przygotuj plan odświeżenia.",
        evidence_ids=["ev_refresh_gsc"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
    )
    ahrefs_decision = ContentDecisionItem(
        id="content_decision_ahrefs_gap_records_review",
        title="Ahrefs gaps",
        decision_type="review_ahrefs_gap_records",
        status="ready",
        priority=18,
        total_impressions=None,
        query_count=4,
        reason="Ahrefs ma luki do sprawdzenia.",
        rationale="Secondary gap evidence needs review.",
        next_step="Zweryfikuj luki z GSC i WordPress.",
        evidence_ids=["ev_refresh_ahrefs"],
        source_connectors=["ahrefs"],
    )

    ranked = _rank_content_decisions_for_diagnostics(
        [ahrefs_decision, gsc_decision],
        {
            "google_search_console": "fresh",
            "wordpress_ekologus": "fresh",
            "ahrefs": "stale",
        },
    )

    assert ranked == [gsc_decision, ahrefs_decision]


def test_content_diagnostics_ranking_keeps_fresh_ahrefs_priority() -> None:
    gsc_decision = ContentDecisionItem(
        id="content_decision_gsc_refresh",
        title="GSC refresh",
        decision_type="refresh_or_merge",
        status="ready",
        priority=23,
        total_impressions=700,
        query_count=2,
        reason="GSC i WordPress mają świeży sygnał.",
        rationale="Primary content evidence is current.",
        next_step="Przygotuj plan odświeżenia.",
        evidence_ids=["ev_refresh_gsc"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
    )
    ahrefs_decision = ContentDecisionItem(
        id="content_decision_ahrefs_gap_records_review",
        title="Ahrefs gaps",
        decision_type="review_ahrefs_gap_records",
        status="ready",
        priority=18,
        total_impressions=None,
        query_count=4,
        reason="Ahrefs ma luki do sprawdzenia.",
        rationale="Secondary gap evidence needs review.",
        next_step="Zweryfikuj luki z GSC i WordPress.",
        evidence_ids=["ev_refresh_ahrefs"],
        source_connectors=["ahrefs"],
    )

    ranked = _rank_content_decisions_for_diagnostics(
        [gsc_decision, ahrefs_decision],
        {
            "google_search_console": "fresh",
            "wordpress_ekologus": "fresh",
            "ahrefs": "fresh",
        },
    )

    assert ranked == [ahrefs_decision, gsc_decision]


def _gsc_fact(
    name: str,
    value: float | int,
    query: str,
    page: str,
    evidence_id: str,
    collected_at: datetime,
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="2026-06-29",
        source_connector="google_search_console",
        evidence_id=evidence_id,
        dimensions={"query": query, "page": page},
        collected_at=collected_at,
    )


def _wordpress_fact(page: str, evidence_id: str, collected_at: datetime) -> MetricFact:
    return MetricFact(
        name="content_object_seen",
        value=1,
        period="snapshot",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        dimensions={
            "content_url": page,
            "content_type": "page",
            "status": "publish",
            "inventory_source": "public_sitemap",
        },
        collected_at=collected_at,
    )
