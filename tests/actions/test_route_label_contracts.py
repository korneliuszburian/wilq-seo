from __future__ import annotations

from wilq.operator_labels import route_cta_label, route_operator_label


def test_route_label_fallbacks_do_not_expose_raw_paths() -> None:
    unknown_route = "/internal/raw-route"

    assert route_operator_label("/command-center") == "Centrum pracy"
    assert route_cta_label("/command-center") == "Otwórz Centrum pracy"
    assert route_operator_label(unknown_route) == "widok do sprawdzenia"
    assert unknown_route not in route_cta_label(unknown_route)
