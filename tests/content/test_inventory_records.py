from __future__ import annotations

from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory


def _record(**overrides: object) -> ContentInventoryRecord:
    payload: dict[str, object] = {
        "id": "inventory_bdo",
        "url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "content_status": "published",
        "source_connectors": ["wordpress_ekologus"],
        "evidence_ids": ["ev_wp_bdo"],
        "title": "BDO dla firm",
        "topic_tags": ["bdo"],
    }
    payload.update(overrides)
    return ContentInventoryRecord(**payload)


def test_inventory_preserves_existing_public_content_first() -> None:
    resolution = resolve_content_inventory([_record()], duplicate_risk="clear")

    assert resolution.status == "resolved"
    assert resolution.recommended_mode == "preserve"
    assert resolution.similar_existing_urls == ["https://ekologus.pl/bdo/"]
    assert resolution.source_connectors == ["wordpress_ekologus"]
    assert resolution.evidence_ids == ["ev_wp_bdo"]
    assert "preserve-first" in resolution.next_step


def test_inventory_blocks_record_without_final_canonical() -> None:
    resolution = resolve_content_inventory(
        [_record(final_canonical_url=None, intended_final_url=None)],
        duplicate_risk="clear",
    )

    assert resolution.status == "blocked"
    assert resolution.recommended_mode == "block"
    assert [blocker.code for blocker in resolution.blockers] == ["missing_final_canonical"]
    assert "final canonical URL" in resolution.blockers[0].reason


def test_inventory_blocks_dev_preview_as_final_canonical() -> None:
    resolution = resolve_content_inventory(
        [_record(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/")],
        duplicate_risk="clear",
    )

    assert resolution.status == "blocked"
    assert resolution.recommended_mode == "block"
    assert [blocker.code for blocker in resolution.blockers] == ["invalid_final_canonical"]
    assert "dev URL nie może być finalnym adresem SEO" in resolution.blockers[0].reason


def test_inventory_blocks_create_when_duplicate_risk_is_unknown() -> None:
    resolution = resolve_content_inventory([], duplicate_risk="unknown")

    assert resolution.status == "blocked"
    assert resolution.recommended_mode == "block"
    assert [blocker.code for blocker in resolution.blockers] == ["duplicate_risk_unresolved"]


def test_inventory_allows_create_candidate_after_clear_duplicate_check() -> None:
    resolution = resolve_content_inventory([], duplicate_risk="clear")

    assert resolution.status == "review_required"
    assert resolution.recommended_mode == "create_after_review"
    assert resolution.blockers == []
    assert "po review i preflight" in resolution.next_step


def test_inventory_deduplicates_records_by_public_canonical() -> None:
    resolution = resolve_content_inventory(
        [
            _record(id="inventory_bdo_primary"),
            _record(id="inventory_bdo_duplicate", url="https://www.ekologus.pl/bdo/"),
        ],
        duplicate_risk="clear",
    )

    assert len(resolution.records) == 1
    assert resolution.similar_existing_urls == ["https://ekologus.pl/bdo/"]
