from __future__ import annotations

from types import SimpleNamespace

from wilq.briefing.ahrefs_diagnostics import _apply_exact_wordpress_cross_checks


def test_exact_wordpress_url_cross_check_promotes_gap_without_phrase_fallback() -> None:
    record = SimpleNamespace(
        keyword="audyt środowiskowy",
        source_url="https://competitor.example/audyt/",
        mapping_status="unbound",
        referenced_public_url=None,
        evidence_ids=["ev_ahrefs"],
    )
    candidate = SimpleNamespace(
        keyword="audyt środowiskowy",
        source_url="https://competitor.example/audyt/",
        wordpress_cross_check=SimpleNamespace(strength="exact", evidence_ids=["ev_wp"]),
        wordpress_overlap_urls=["https://www.ekologus.pl/audyt-srodowiskowy/"],
    )

    result = _apply_exact_wordpress_cross_checks([record], [candidate])

    assert result[0].mapping_status == "exact"
    assert result[0].referenced_public_url == "https://www.ekologus.pl/audyt-srodowiskowy/"
    assert result[0].evidence_ids == ["ev_ahrefs", "ev_wp"]
