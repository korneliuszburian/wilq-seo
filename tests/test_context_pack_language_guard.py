from __future__ import annotations

from scripts.context_pack_language_guard import (
    FORBIDDEN_VALUE_TERMS,
    _walk_string_values,
)


def test_context_pack_guard_tracks_action_and_url_jargon() -> None:
    required_terms = {
        "ActionObject",
        "Dry-run",
        "dry-run",
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "preview_url",
        "target site",
        "mapping-review",
        "blockers",
    }

    assert required_terms.issubset(set(FORBIDDEN_VALUE_TERMS))


def test_context_pack_guard_scans_nested_string_values() -> None:
    payload = {
        "context": {
            "decision": [
                {"visible": "ActionObject payload should never reach skill context"}
            ]
        }
    }

    hits = [
        (path, term)
        for path, value in _walk_string_values(payload)
        for term in FORBIDDEN_VALUE_TERMS
        if term in value
    ]

    assert ("$.context.decision[0].visible", "ActionObject") in hits
    assert ("$.context.decision[0].visible", "payload") in hits
