"""Redaction must preserve the non-secret authoring-profile digest.

The new-page apply audit schema requires ``authoring_profile_digest`` to be a
64-char lowercase-hex value. Redaction replaced it with ``[REDACTED]`` because
the key was not allowlisted, so the audit record failed re-validation and the
public apply route returned 422.
"""

from __future__ import annotations

from wilq.security.redaction import redact_mapping

HEX64 = "b" * 64


def test_authoring_profile_digest_is_preserved_inside_binding() -> None:
    redacted = redact_mapping(
        {
            "new_page_draft_binding": {
                "authoring_profile_digest": HEX64,
                "revision_digest": "a" * 64,
            }
        }
    )["new_page_draft_binding"]

    assert redacted["authoring_profile_digest"] == HEX64
    assert redacted["revision_digest"] == "a" * 64


def test_non_hex_authoring_profile_digest_is_still_redacted() -> None:
    redacted = redact_mapping(
        {"new_page_draft_binding": {"authoring_profile_digest": "not-a-digest"}}
    )["new_page_draft_binding"]

    assert redacted["authoring_profile_digest"] == "[REDACTED]"
