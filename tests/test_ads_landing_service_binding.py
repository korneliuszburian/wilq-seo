from __future__ import annotations

from types import SimpleNamespace

from wilq.briefing import ads_landing_service_binding as binding


def test_resolves_landing_hash_to_inventory_and_review_required_service(monkeypatch) -> None:
    landing_url = "https://www.ekologus.pl/szkolenie/gospodarka-odpadami/"
    item = SimpleNamespace(
        url=landing_url,
        work_item_id="content_work_item_training",
        path="/szkolenie/gospodarka-odpadami/",
        title="Gospodarka odpadami",
        section_count=3,
        content_summary="Szkolenie z gospodarki odpadami.",
        content_word_count=200,
        acf_section_count=None,
        evidence_id="ev_wp_training",
        source_connector="wordpress_ekologus",
    )
    candidate = SimpleNamespace(
        service_card_id="ekologus_service_environmental_compliance_audit",
        service_label="Audyt zgodności środowiskowej",
        lifecycle_status="source_backed_review_required",
    )
    monkeypatch.setattr(
        binding,
        "build_content_inventory_catalog",
        lambda: SimpleNamespace(items=[item]),
    )
    monkeypatch.setattr(
        binding,
        "build_content_work_item_service_profile_context",
        lambda _item: SimpleNamespace(
            service_status="source_backed_review_required",
            service_candidates=[candidate],
            reason="Karta usługi wymaga review.",
            safe_next_step="Zatwierdź kartę usługi.",
        ),
    )
    binding.resolve_ads_landing_service_binding.cache_clear()

    result = binding.resolve_ads_landing_service_binding(binding._url_identity_hash(landing_url))

    assert result is not None
    assert result.status == "review_required"
    assert result.inventory_work_item_id == "content_work_item_training"
    assert result.service_candidate_ids == ["ekologus_service_environmental_compliance_audit"]
    assert result.service_lifecycle_statuses == ["source_backed_review_required"]


def test_bdo_hash_stays_unbound_when_inventory_has_no_matching_page(monkeypatch) -> None:
    monkeypatch.setattr(
        binding,
        "build_content_inventory_catalog",
        lambda: SimpleNamespace(items=[]),
    )
    binding.resolve_ads_landing_service_binding.cache_clear()

    result = binding.resolve_ads_landing_service_binding(
        binding._url_identity_hash(
            "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
        )
    )

    assert result is not None
    assert result.status == "unbound"
    assert result.inventory_work_item_id is None
