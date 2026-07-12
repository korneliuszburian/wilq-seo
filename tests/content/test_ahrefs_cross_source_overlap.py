from __future__ import annotations

from wilq.content.planning.ahrefs_overlap import (
    AhrefsCrossSourceMatcher,
    assess_ahrefs_cross_source_overlap,
)
from wilq.schemas import MetricFact


def _fact(
    *,
    source_connector: str,
    evidence_id: str,
    **dimensions: str,
) -> MetricFact:
    return MetricFact(
        name="content_signal",
        value=1,
        period="test",
        source_connector=source_connector,
        evidence_id=evidence_id,
        dimensions=dimensions,
    )


def test_weak_keyword_overlap_remains_manual_not_exact() -> None:
    overlap = assess_ahrefs_cross_source_overlap(
        keyword="mieszalnik IBC",
        referenced_public_url=None,
        gsc_facts=[
            _fact(
                source_connector="google_search_console",
                evidence_id="ev_gsc_kontener_ibc",
                query="kontener IBC odpady",
                page="https://www.ekologus.pl/kontener-ibc/",
            )
        ],
        wordpress_facts=[
            _fact(
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_lejek_ibc",
                title="Lejek do kontenerów IBC",
                content_url="https://www.ekologus.pl/lejek-do-kontenerow-ibc/",
            )
        ],
    )

    assert overlap.gsc.strength == "weak"
    assert overlap.gsc.source_connectors == ("google_search_console",)
    assert overlap.gsc.evidence_ids == ("ev_gsc_kontener_ibc",)
    assert overlap.wordpress.strength == "weak"
    assert overlap.wordpress.source_connectors == ("wordpress_ekologus",)
    assert overlap.wordpress.evidence_ids == ("ev_wp_lejek_ibc",)
    assert overlap.has_exact_match is False


def test_exact_phrase_and_public_url_lineage_are_confirmed() -> None:
    overlap = assess_ahrefs_cross_source_overlap(
        keyword="bdo odpady",
        referenced_public_url="https://www.ekologus.pl/bdo/",
        gsc_facts=[
            _fact(
                source_connector="google_search_console",
                evidence_id="ev_gsc_bdo_odpady",
                query="bdo odpady",
                page="https://www.ekologus.pl/bdo/",
            )
        ],
        wordpress_facts=[
            _fact(
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_bdo_odpady",
                title="Obsługa BDO odpady dla firm",
                content_url="https://ekologus.pl/bdo/",
            )
        ],
    )

    assert overlap.gsc.strength == "exact"
    assert overlap.gsc.matching_labels == ("bdo odpady",)
    assert overlap.wordpress.strength == "exact"
    assert overlap.wordpress.matching_labels == ("https://ekologus.pl/bdo/",)
    assert overlap.has_exact_match is True


def test_wordpress_title_or_h1_is_typed_exact_inventory_metadata() -> None:
    overlap = assess_ahrefs_cross_source_overlap(
        keyword="zielony ład",
        referenced_public_url=None,
        gsc_facts=[],
        wordpress_facts=[
            _fact(
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_zielony_lad",
                title_or_h1="Europejski Zielony Ład — co to takiego?",
                content_url="https://www.ekologus.pl/europejski-zielony-lad/",
            )
        ],
    )

    assert overlap.wordpress.strength == "exact"
    assert overlap.wordpress.evidence_ids == ("ev_wp_zielony_lad",)


def test_dev_workspace_url_cannot_become_wordpress_confirmation() -> None:
    overlap = assess_ahrefs_cross_source_overlap(
        keyword="bdo odpady",
        referenced_public_url="https://ekologus.dev.proudsite.pl/bdo/",
        gsc_facts=[],
        wordpress_facts=[
            _fact(
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_dev_bdo",
                title="BDO odpady",
                content_url="https://ekologus.dev.proudsite.pl/bdo/",
            )
        ],
    )

    assert overlap.wordpress.strength == "missing"
    assert overlap.wordpress.source_connectors == ()
    assert overlap.wordpress.evidence_ids == ()
    assert overlap.has_exact_match is False


def test_compiled_matcher_preserves_exact_phrase_and_public_url_lineage() -> None:
    matcher = AhrefsCrossSourceMatcher.from_metric_facts(
        gsc_facts=[
            _fact(
                source_connector="google_search_console",
                evidence_id="ev_gsc_bdo_odpady",
                query="bdo odpady",
                page="https://www.ekologus.pl/bdo/",
            )
        ],
        wordpress_facts=[
            _fact(
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_bdo_odpady",
                title="Obsługa BDO odpady dla firm",
                content_url="https://ekologus.pl/bdo/",
            )
        ],
    )

    overlap = matcher.assess(
        keyword="bdo odpady",
        referenced_public_url="https://www.ekologus.pl/bdo/",
    )

    assert overlap.gsc.strength == "exact"
    assert overlap.gsc.matching_labels == ("bdo odpady",)
    assert overlap.wordpress.strength == "exact"
    assert overlap.wordpress.matching_labels == ("https://ekologus.pl/bdo/",)
    assert overlap.has_exact_match is True
