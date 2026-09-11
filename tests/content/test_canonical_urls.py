from __future__ import annotations

from wilq.content.canonical.urls import (
    content_authoring_path_matches_public_url,
    content_decision_has_public_final_canonical,
    content_decision_url_semantics,
    content_is_safe_authoring_url,
    content_normalized_path,
    content_normalized_url,
    content_url_host,
)
from wilq.schemas import ContentDecisionItem


def test_content_url_semantics_keep_dev_preview_out_of_final_canonical() -> None:
    semantics = content_decision_url_semantics(
        source_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        wordpress_content_url="https://ekologus.dev.proudsite.pl/bdo/",
    )

    assert semantics == {
        "source_public_url": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        "preview_url": None,
        "intended_final_url": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        "final_canonical_url": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
    }


def test_content_url_semantics_accept_public_wordpress_canonical() -> None:
    semantics = content_decision_url_semantics(
        source_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        wordpress_content_url="https://ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
    )

    assert semantics["intended_final_url"] == (
        "https://ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    assert semantics["final_canonical_url"] == (
        "https://ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )


def test_content_decision_public_final_canonical_uses_public_hosts() -> None:
    decision = ContentDecisionItem(
        id="content_decision_bdo",
        title="BDO",
        decision_type="refresh_or_merge",
        status="ready",
        reason="Istniejąca treść wymaga odświeżenia.",
        rationale="Publiczny canonical jest na domenie Ekologus.",
        next_step="Sprawdź plan odświeżenia.",
        source_public_url="https://www.ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        evidence_ids=["ev_content_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
    )

    assert content_decision_has_public_final_canonical(decision)


def test_content_url_normalization_helpers() -> None:
    assert content_url_host("https://WWW.EKOLOGUS.PL/bdo/") == "www.ekologus.pl"
    assert content_normalized_path("https://www.ekologus.pl/bdo/") == "/bdo"
    assert content_normalized_url("HTTPS://WWW.EKOLOGUS.PL/bdo/") == (
        "https://www.ekologus.pl/bdo"
    )


def test_authoring_rest_path_match_requires_one_safe_exact_dev_origin() -> None:
    public_url = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
    valid = "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych"

    assert content_is_safe_authoring_url(valid)
    assert content_authoring_path_matches_public_url(public_url, valid)
    for invalid in (
        "http://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
        "https://user@ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
        "https://ekologus.dev.proudsite.pl:443/analiza-pozwolen-zintegrowanych/",
        "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/?x=1",
        "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/#fragment",
        "https://other.example/analiza-pozwolen-zintegrowanych/",
    ):
        assert not content_is_safe_authoring_url(invalid)
        assert not content_authoring_path_matches_public_url(public_url, invalid)
