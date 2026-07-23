from __future__ import annotations

from types import SimpleNamespace

import wilq.content.workflow.entry as entry_module


def _candidate(*, index: int, impressions: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        work_item_id=f"content_work_item_{index}",
        title=f"Strona {index}",
        source_public_url=f"https://www.ekologus.pl/strona-{index}/",
        final_canonical_url=None,
        recommended_mode="refresh",
        reason=f"Powód {index} pochodzi z danych strony.",
        search_metrics=SimpleNamespace(
            impressions=impressions,
            clicks=None,
            primary_query="operat wodnoprawny" if index == 1 else None,
        ),
    )


def test_entry_limits_recommendations_and_does_not_read_inventory_without_search(
    monkeypatch,
) -> None:
    candidates = [
        _candidate(index=index, impressions=100 if index == 1 else None)
        for index in range(1, 6)
    ]
    monkeypatch.setattr(entry_module, "build_content_diagnostics_cached", lambda: object())
    monkeypatch.setattr(
        entry_module,
        "build_content_work_item_queue_response",
        lambda _diagnostics: SimpleNamespace(candidates=candidates),
    )
    monkeypatch.setattr(
        entry_module,
        "build_content_inventory_catalog_cached",
        lambda: (_ for _ in ()).throw(AssertionError("inventory must stay unopened")),
    )

    response = entry_module.build_content_workflow_entry()

    assert response.refresh_existing.kind == "refresh_existing"
    assert response.new_page.kind == "new_page"
    assert [item.work_item_id for item in response.recommendations] == [
        "content_work_item_1",
        "content_work_item_2",
        "content_work_item_3",
    ]
    assert response.recommendations[0].facts[0].value == "100"
    assert response.recommendations[0].title == "Operat wodnoprawny"
    assert response.recommendations[1].title == "Strona 2"
    assert response.recommendations[1].facts == [
        entry_module.ContentWorkflowEntryFact(
            label="Dane strony",
            value="Dane zapytań nie zostały wczytane.",
        )
    ]


def test_entry_search_returns_public_material_labels_without_target_claims(monkeypatch) -> None:
    monkeypatch.setattr(entry_module, "build_content_diagnostics_cached", lambda: object())
    monkeypatch.setattr(
        entry_module,
        "build_content_work_item_queue_response",
        lambda _diagnostics: SimpleNamespace(candidates=[]),
    )
    monkeypatch.setattr(
        entry_module,
        "build_content_inventory_catalog_cached",
        lambda: SimpleNamespace(
            items=[
                SimpleNamespace(
                    work_item_id="content_work_item_bdo",
                    title="BDO dla firm",
                    path="/bdo/",
                    url="https://www.ekologus.pl/bdo/",
                    content_summary="Obowiązki BDO dla przedsiębiorców.",
                    material_status="content_and_structure",
                ),
                SimpleNamespace(
                    work_item_id="content_work_item_woda",
                    title="Operat wodnoprawny",
                    path="/operat-wodnoprawny/",
                    url="https://www.ekologus.pl/operat-wodnoprawny/",
                    content_summary=None,
                    material_status="url_only",
                ),
            ]
        ),
    )

    response = entry_module.build_content_workflow_entry(search="bdo")

    assert response.search_query == "bdo"
    assert [(item.work_item_id, item.material_label) for item in response.search_results] == [
        ("content_work_item_bdo", "Materiał strony dostępny")
    ]
    assert "WordPress" not in response.search_results[0].material_label
    assert "target" not in response.search_results[0].material_label.lower()
