from __future__ import annotations

from types import SimpleNamespace

import wilq.content.workflow.entry as entry_module


def _candidate(
    *,
    index: int,
    impressions: int | None = None,
    clicks: int | None = None,
    comparison_status: str = "not_available",
    comparison_periods: list[str] | None = None,
    title: str | None = None,
    reason: str | None = None,
    recommended_mode: str = "refresh",
    recommended_mode_label: str = "odśwież istniejącą treść",
    blockers: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        work_item_id=f"content_work_item_{index}",
        title=f"Strona {index}" if title is None else title,
        source_public_url=f"https://www.ekologus.pl/strona-{index}/",
        final_canonical_url=None,
        recommended_mode=recommended_mode,
        recommended_mode_label=recommended_mode_label,
        blockers=[] if blockers is None else blockers,
        reason=f"Powód {index} pochodzi z danych strony." if reason is None else reason,
        page_inventory=SimpleNamespace(
            title_or_h1=f"Publiczna strona {index}" if title is None else title
        ),
        search_metrics=SimpleNamespace(
            impressions=impressions,
            clicks=clicks,
            primary_query="operat wodnoprawny" if index == 1 else None,
            comparison_status=comparison_status,
            comparison_periods=[] if comparison_periods is None else comparison_periods,
        ),
    )


def test_recommendation_marks_an_unblocked_refresh_as_work_to_do_now() -> None:
    recommendation = entry_module._recommendation(_candidate(index=1))

    assert recommendation.decision_mode == "refresh"
    assert recommendation.decision_label == "odśwież istniejącą treść"
    assert recommendation.decision_action == "do_it_now"
    assert recommendation.blockers == []


def test_recommendation_projects_a_blocked_decision_and_its_blocker() -> None:
    recommendation = entry_module._recommendation(
        _candidate(
            index=1,
            recommended_mode="block",
            recommended_mode_label="wstrzymaj pracę",
            blockers=[
                SimpleNamespace(
                    code="missing_evidence",
                    label="aktualnych danych GSC",
                )
            ],
        )
    )

    assert recommendation.decision_action == "wait_or_block"
    assert recommendation.blockers[0].code == "missing_evidence"
    assert recommendation.blockers[0].label == "aktualnych danych GSC"


def test_gsc_facts_show_the_latest_available_comparison_period_only() -> None:
    facts_with_period = entry_module._facts(
        _candidate(
            index=2,
            impressions=120,
            clicks=8,
            comparison_status="available",
            comparison_periods=[
                "2026-06-01/2026-06-30",
                "2026-07-01/2026-07-31",
            ],
        )
    )
    facts_without_period = entry_module._facts(
        _candidate(index=2, impressions=120, comparison_status="available")
    )

    assert [fact.period_label for fact in facts_with_period] == [
        "od 2026-07-01 do 2026-07-31",
        "od 2026-07-01 do 2026-07-31",
    ]
    assert facts_without_period[0].period_label == ""


def test_entry_limits_recommendations_and_does_not_read_inventory_without_search(
    monkeypatch,
) -> None:
    candidates = [
        _candidate(
            index=index,
            impressions=100 if index == 1 else None,
            recommended_mode="block" if index == 2 else "refresh",
            recommended_mode_label=(
                "wstrzymaj — najpierw sprawdź"
                if index == 2
                else "odśwież istniejącą treść"
            ),
            blockers=(
                [
                    SimpleNamespace(
                        code="missing_evidence",
                        label="aktualnych danych GSC",
                    )
                ]
                if index == 2
                else None
            ),
        )
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
    assert response.recommendations[0].title == "Publiczna strona 1"
    assert response.recommendations[0].reason == "Powód 1 pochodzi z danych strony."
    assert response.recommendations[0].facts[-1] == entry_module.ContentWorkflowEntryFact(
        label="Główne zapytanie",
        value="operat wodnoprawny",
    )
    assert response.recommendations[1].decision_action == "wait_or_block"
    assert response.recommendations[1].blockers[0].label == "aktualnych danych GSC"
    assert response.recommendations[1].title == "Publiczna strona 2"
    assert response.recommendations[1].facts == [
        entry_module.ContentWorkflowEntryFact(
            label="Dane strony",
            value="Dane zapytań nie zostały wczytane.",
        )
    ]


def test_entry_keeps_a_page_title_and_reason_or_omits_the_recommendation(monkeypatch) -> None:
    candidates = [
        _candidate(index=1, title="", reason="Powód widoczny dla marketera."),
        _candidate(index=2, reason="   "),
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

    assert [(item.work_item_id, item.title, item.reason) for item in response.recommendations] == [
        ("content_work_item_1", "Strona 1", "Powód widoczny dla marketera."),
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
