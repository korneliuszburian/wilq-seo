from __future__ import annotations

from datetime import UTC, datetime

from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.schemas import MetricFact


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
