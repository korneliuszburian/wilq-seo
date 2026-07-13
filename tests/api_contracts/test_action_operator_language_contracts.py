from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from wilq.actions.service import _operator_audit_summary_text


def test_legacy_raw_audit_summary_is_not_rewritten_with_string_labels() -> None:
    summary = (
        "Blokady: payload_apply_allowed_false, wordpress_write_not_requested, "
        "blocked_claim:ranking guarantee. Sprawdzone: "
        "candidate:content_brief_gsc_bdo, source_type:gsc_query_page."
    )

    cleaned = _operator_audit_summary_text(summary)

    assert cleaned == (
        "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    )
    assert "payload_apply_allowed_false" not in cleaned
    assert "candidate:" not in cleaned
    assert "blocked_claim:" not in cleaned


def test_operator_audit_summary_hides_raw_audit_identifiers() -> None:
    summary = (
        "Potwierdzenie podglądu zapisane. "
        "Audyt podglądu: audit_act_review_merchant_feed_issues_preview_123abc. "
        "Notatka: Operator potwierdza podgląd. Ten krok nie zapisuje zmian.. "
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )

    cleaned = _operator_audit_summary_text(summary)

    assert "Potwierdzenie podglądu zapisane" in cleaned
    assert "Notatka: Operator potwierdza podgląd" in cleaned
    assert "Audyt podglądu" not in cleaned
    assert "audit_" not in cleaned
    assert ".." not in cleaned
    assert (
        "Ten krok nie zapisuje zmian. Ten krok nie zapisuje zmian w zewnętrznych systemach."
        not in cleaned
    )


def test_action_recommended_reasons_do_not_expose_route_slugs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")

    assert response.status_code == 200
    actions = response.json()
    visible_copy = "\n".join(str(action.get("recommended_reason") or "") for action in actions)
    for route_slug in (
        "/merchant",
        "/content-workflow",
        "/ads-doctor",
        "/ga4",
        "/ads-doctor/demand-gen",
        "/localo",
        "/social-publisher",
    ):
        assert route_slug not in visible_copy
    for stale_term in ("evidence", "source connector", "blocked claims"):
        assert stale_term not in visible_copy
    assert "W widoku Merchant" in visible_copy
    assert "W widoku Treści" in visible_copy
    assert "W widoku GA4" in visible_copy
