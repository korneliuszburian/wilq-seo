from __future__ import annotations

import json

import pytest

import wilq.content.regulatory.source_fact_proposals as proposals_module
import wilq.content.regulatory.source_selection as selection_module
from tests.content.test_regulatory_source_fact_proposals import (
    _Client,
    _html_source,
    _ready_output,
    _stores,
)
from wilq.content.regulatory.policy import (
    ContentRegulatorySourceExcludedRange,
    regulatory_source_candidates,
)
from wilq.content.regulatory.source_fact_proposals import (
    generate_source_fact_proposal,
    read_source_fact_proposal,
)


def test_operat_late_provisions_reach_structured_turn_without_future_clauses(
    tmp_path, monkeypatch
) -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    late_provisions = "\n".join(
        [
            "Art. 408. Operat składa się w formie określonej przepisami.",
            "5. Aktualny ustęp 5. pozostaje w mocy.",
            "<8. Przyszły przepis obowiązuje od 2027 r..>",
            "Art. 409. Operat wodnoprawny zawiera część opisową i graficzną.",
            "6. Aktualny ustęp 6. pozostaje w mocy.",
            "Dodany ust. 5a w art. 407 poz. 1156).",
            "7. Aktualny ustęp 7. pozostaje w mocy.",
            "Operat wodnoprawny pozwolenie obowiązek.",
            "Art. 410. Poza zakresem.",
        ]
    )
    extracted = ("RAW-PREFIX " * 70_000) + late_provisions

    class _PdfResult:
        returncode = 0
        stdout = extracted.encode()

    extractor = tmp_path / "pdftotext"
    extractor.touch(mode=0o700)
    monkeypatch.setattr(proposals_module, "_PDFTOTEXT_BINARY", extractor)
    monkeypatch.setattr(proposals_module.subprocess, "run", lambda *args, **kwargs: _PdfResult())
    client = _Client(
        {
            **_ready_output(candidate),
            "source_terms": ["Operat", "wodnoprawny", "pozwolenie"],
        }
    )

    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=client,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: (b"%PDF-bounded-body", "application/pdf"),
    )

    assert result.status == "ready", result.reason
    assert result.proposal is not None
    context = client.requests[0].untrusted_context
    assert "Art. 408." in context
    assert "Art. 409." in context
    assert "Aktualny ustęp 5." in context
    assert "Aktualny ustęp 6." in context
    assert "Aktualny ustęp 7." in context
    assert "2027 r." not in context
    assert "Dodany ust. 5a w" not in context
    assert "RAW-PREFIX" not in context
    assert "RAW-PREFIX" not in proposal_store.path.read_bytes().decode(errors="ignore")
    application_context = json.loads(client.requests[0].application_context)
    assert application_context["as_of"] == "2026-09-20"
    assert application_context["selector"]["kind"] == "provision_range"


def test_heading_set_selects_required_headings_but_blocks_missing_anchor() -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_wody_polskie_2026_r1"
    )
    assert candidate.selector is not None
    source = "\n".join(
        [
            "2. Operat wodnoprawny",
            "Do wniosku dołącz operat wodnoprawny",
            "Jeśli wnioskodawcą są Wody Polskie to wniosek składa się "
            "do Ministerstwa Infrastruktury",
        ]
    )

    assert selection_module.select_bounded_source_text(candidate, source) == source.strip()

    missing = candidate.model_copy(
        update={
            "selector": candidate.selector.model_copy(
                update={"required_anchors": ["brakujący anchor"]}
            )
        }
    )
    with pytest.raises(selection_module.RegulatorySourceSelectionError, match="missing_anchor"):
        selection_module.select_bounded_source_text(missing, source)


def test_all_operat_candidates_select_without_false_future_marker_block() -> None:
    sources = {
        "operat_prawo_wodne_scope_r1": "\n".join(
            [
                "Art. 389. Zakres pozwolenia.",
                "Art. 390. Wyjątki.",
                "Art. 397. Poza zakresem.",
            ]
        ),
        "operat_prawo_wodne_application_r1": "\n".join(
            [
                "Art. 407. Wymagania wniosku i operatu.",
                "<5a. Przyszła jednostka 2027 r..>",
                "Art. 408. Forma operatu.",
            ]
        ),
        "operat_prawo_wodne_contents_r1": "\n".join(
            [
                "Art. 408. Forma operatu.",
                "<8. Przyszła jednostka 2027 r..>",
                "Art. 409. Część opisowa i graficzna.",
                "Dodany ust. 5a w art. 407 poz. 1156).",
                "Art. 410. Poza zakresem.",
            ]
        ),
        "operat_prawo_wodne_validity_r1": "\n".join(
            [
                "Art. 400. Okres obowiązywania.",
                "Art. 401. Poza zakresem.",
            ]
        ),
        "operat_prawo_wodne_authority_r1": "\n".join(
            [
                "Art. 397. Właściwy organ.",
                "Art. 398. Poza zakresem.",
            ]
        ),
        "operat_kpa_2025_1691_r1": "\n".join(
            [
                "Art. 35. Termin załatwienia sprawy.",
                "Art. 36. Zawiadomienie o zwłoce.",
                "Art. 37. Ponaglenie.",
                "Art. 38. Poza zakresem.",
            ]
        ),
        "operat_wody_polskie_2026_r1": (
            "2. Operat wodnoprawny\n"
            "Do wniosku dołącz operat wodnoprawny\n"
            "Jeśli wnioskodawcą są Wody Polskie to wniosek składa się "
            "do Ministerstwa Infrastruktury"
        ),
        "operat_oplaty_2026_2025_717_r1": (
            "Tabela: opłaty za wydanie pozwolenia wodnoprawnego w 2026 r."
        ),
    }

    candidates = tuple(
        candidate
        for candidate in regulatory_source_candidates()
        if candidate.candidate_id in sources
    )

    assert len(candidates) == 8
    assert {candidate.candidate_id for candidate in candidates} == set(sources)
    for candidate in candidates:
        source = sources[candidate.candidate_id]
        selected = selection_module.select_bounded_source_text(candidate, source)
        assert selected
        for forbidden in ("<", ">", "2027", "Dodany"):
            if forbidden in source:
                assert forbidden not in selected
    # The candidates that own excluded future units must actually carry markers,
    # otherwise the removal assertions above would be vacuous.
    assert "2027" in sources["operat_prawo_wodne_application_r1"]
    assert "2027" in sources["operat_prawo_wodne_contents_r1"]
    assert "Dodany" in sources["operat_prawo_wodne_contents_r1"]


def test_residual_forbidden_anchor_blocks_future_marker_left_after_exclusion() -> None:
    original = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )
    assert original.selector is not None
    candidate = original.model_copy(
        update={
            "selector": original.selector.model_copy(
                update={
                    "excluded_ranges": [
                        ContentRegulatorySourceExcludedRange(
                            start_anchor="REMOVE_ME",
                            end_anchor="REMOVED",
                        )
                    ],
                    "residual_forbidden_anchors": ["<", ">", "2027", "Dodany"],
                }
            )
        }
    )
    source = "\n".join(
        [
            "Art. 408. Forma.",
            "Art. 409. Część opisowa.",
            "REMOVE_ME",
            "REMOVED",
            "< przyszła jednostka 2027 r. >",
            "Art. 410. Poza zakresem.",
        ]
    )

    with pytest.raises(selection_module.RegulatorySourceSelectionError) as error:
        selection_module.select_bounded_source_text(candidate, source)

    assert error.value.code == "future_marker_present"


def test_excluded_ranges_remove_only_exact_future_units_and_amendment_notes() -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )
    source = "\n".join(
        [
            "Art. 408. forma operatu",
            "5. Aktualny ustęp 5.",
            "<8. przyszła jednostka 2027 r.>",
            "Art. 409. część opisowa i graficzna",
            "6. Aktualny ustęp 6.",
            "Dodany ust. 5a w art. 407 poz. 1156).",
            "7. Aktualny ustęp 7.",
            "Art. 410. poza zakresem",
        ]
    )

    selected = selection_module.select_bounded_source_text(candidate, source)

    for value in ("przyszła jednostka", "Dodany ust. 5a w"):
        assert value not in selected
    for value in (
        "Aktualny ustęp 5.",
        "Aktualny ustęp 6.",
        "Aktualny ustęp 7.",
    ):
        assert value in selected


def test_excluded_range_cannot_recreate_a_removed_required_anchor() -> None:
    original = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )
    assert original.selector is not None
    candidate = original.model_copy(
        update={
            "selector": original.selector.model_copy(
                update={
                    "required_anchors": ["Art. 409."],
                    "excluded_ranges": [
                        ContentRegulatorySourceExcludedRange(
                            start_anchor="EXCLUDED_START",
                            end_anchor="EXCLUDED_END",
                        )
                    ],
                }
            )
        }
    )
    source = "\n".join(
        [
            "Art. 408. Forma.",
            "EXCLUDED_START",
            "Art. 409.",
            "EXCLUDED_END",
            "409.",
            "Art. 410. Poza zakresem.",
        ]
    )

    with pytest.raises(
        selection_module.RegulatorySourceSelectionError,
        match="required_anchor_removed",
    ):
        selection_module.select_bounded_source_text(candidate, source)


def test_heading_set_with_zero_context_keeps_required_anchor() -> None:
    original = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_oplaty_2026_2025_717_r1"
    )
    assert original.selector is not None
    candidate = original.model_copy(
        update={
            "selector": original.selector.model_copy(update={"context_chars": 0})
        }
    )
    anchor = "opłaty za wydanie pozwolenia wodnoprawnego"
    source = f"Wstęp\n{anchor}\nKoniec"

    selected = selection_module.select_bounded_source_text(candidate, source)

    assert anchor in selected


def test_excluded_range_cannot_swallow_required_provision_or_create_proposal(
    tmp_path,
) -> None:
    original = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )
    assert original.selector is not None
    candidate = original.model_copy(
        update={
            "selector": original.selector.model_copy(
                update={"excluded_ranges": [original.selector.excluded_ranges[1]]}
            )
        }
    )
    source = "\n".join(
        [
            "Art. 408. forma",
            "Dodany ust. 5a w art. 407",
            "Art. 409. części opisowa i graficzna",
            "poz. 1156).",
            "Art. 410. poza zakresem",
        ]
    )

    with pytest.raises(
        selection_module.RegulatorySourceSelectionError,
        match="required_anchor_removed",
    ):
        selection_module.select_bounded_source_text(candidate, source)

    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source(source),
        candidates=(candidate,),
    )

    assert result.status == "blocked"
    assert result.proposal is None
    assert proposal_store.latest(candidate.candidate_id) is None


@pytest.mark.parametrize(
    "extracted,expected_error",
    [
        ("Art. 408. tylko początek bez końcowego przepisu.", "missing"),
        (
            "Art. 408. pierwszy\nArt. 408. drugi\nArt. 409. koniec",
            "ambiguous",
        ),
    ],
)
def test_operat_selector_missing_or_ambiguous_anchor_fails_closed(
    tmp_path, monkeypatch, extracted: str, expected_error: str
) -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_contents_r1"
    )

    class _PdfResult:
        returncode = 0
        stdout = extracted.encode()

    extractor = tmp_path / "pdftotext"
    extractor.touch(mode=0o700)
    monkeypatch.setattr(proposals_module, "_PDFTOTEXT_BINARY", extractor)
    monkeypatch.setattr(proposals_module.subprocess, "run", lambda *args, **kwargs: _PdfResult())
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)

    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(_ready_output(candidate)),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: (b"%PDF-selector-fixture", "application/pdf"),
    )

    assert result.status == "blocked"
    assert expected_error in result.reason
    assert result.proposal is None
    assert proposal_store.latest(candidate.candidate_id) is None


def test_operat_selector_scope_drift_invalidates_existing_proposal(tmp_path) -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "operat_prawo_wodne_scope_r1"
    )
    proposal_store, snapshot_store, _review_store, run_store = _stores(tmp_path)
    result = generate_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        client=_Client(
            {
                **_ready_output(candidate),
                "source_terms": ["Operat", "wodnoprawny", "pozwolenie"],
            }
        ),
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        run_store=run_store,
        reader=lambda _: _html_source(
            " ".join(
                [
                    "Art. 389. zakres pozwolenia",
                    "Art. 390. wyjątki",
                    "Art. 397. właściwy organ",
                    "Operat wodnoprawny pozwolenie obowiązek.",
                ]
            ).replace("<", "&lt;")
        ),
    )

    assert result.proposal is not None
    assert candidate.selector is not None
    changed = candidate.model_copy(
        update={
            "selector": candidate.selector.model_copy(
                update={"max_chars": candidate.selector.max_chars - 1}
            )
        }
    )
    restored = read_source_fact_proposal(
        candidate_id=candidate.candidate_id,
        proposal_store=proposal_store,
        snapshot_store=snapshot_store,
        candidates=(changed,),
    )

    assert restored.status == "blocked"
    assert restored.proposal is None
