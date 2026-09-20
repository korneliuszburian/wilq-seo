"""Parent-safe observer for the bounded regulatory source selection contract.

The module under test is new, so this file must stay import-safe against the
parent commit: every check that depends on the new surface first guards the
lookup and then asserts, so the parent fails in the call phase with a real
assertion instead of a collection error.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from wilq.content.regulatory.policy import (
    ContentRegulatorySourceCandidate,
    regulatory_source_candidates,
)


def _operat_candidate() -> ContentRegulatorySourceCandidate | None:
    return next(
        (
            item
            for item in regulatory_source_candidates()
            if item.candidate_id == "operat_prawo_wodne_2025_960_r1"
        ),
        None,
    )


def _selector_module() -> tuple[Any, Any]:
    try:
        from wilq.content.regulatory.source_selection import (
            RegulatorySourceSelectionError,
            select_bounded_source_text,
        )
    except ImportError:  # pragma: no cover - parent tree predates the module
        return None, None
    return select_bounded_source_text, RegulatorySourceSelectionError


def _operat_source() -> str:
    return "\n".join(
        [
            "Art. 389. zakres pozwolenia",
            "Art. 390. wyjątki",
            "Art. 397. właściwy organ",
            "Art. 399. wniosek i operat",
            "Art. 400. okres obowiązywania",
            "Art. 407. zawartość operatu",
            "Art. 408. forma operatu",
            "<4a) przyszła jednostka 2027 r.;>",
            "Art. 409. część opisowa i graficzna",
            "<5a. przyszła jednostka 2027 r.>",
            "<8. przyszła jednostka 2027 r.>",
            "Dodany pkt 4a w art. 407 poz. 1156).",
            "Dodany ust. 5a w art. 407 poz. 1156).",
        ]
    )


def test_operat_source_selector_is_bounded_and_fail_closed() -> None:
    candidate = _operat_candidate()
    assert candidate is not None, "Operat candidate must exist in the source registry"
    selector = getattr(candidate, "selector", None)
    assert selector is not None, "Operat candidate must carry a bounded selector"
    assert getattr(candidate, "as_of", None) == date(2026, 9, 20)

    select_bounded_source_text, selection_error = _selector_module()
    assert select_bounded_source_text is not None, "bounded selector module must exist"
    assert selection_error is not None

    selected = select_bounded_source_text(candidate, _operat_source())
    assert "Art. 389." in selected
    assert "Art. 409." in selected
    assert "2027" not in selected
    assert "Dodany" not in selected
    assert "<" not in selected
    assert ">" not in selected

    missing = candidate.model_copy(
        update={
            "selector": selector.model_copy(update={"required_anchors": ["Art. 999."]})
        }
    )
    try:
        select_bounded_source_text(missing, _operat_source())
    except selection_error as error:
        assert error.code in {"missing_anchor", "required_anchor_removed"}
    else:
        raise AssertionError("a missing required anchor must fail closed")
