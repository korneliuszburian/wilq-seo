from __future__ import annotations


def test_section_repair_deadline_contract_is_bounded() -> None:
    try:
        from wilq.content.drafts.section_repair_runtime_contract import (
            DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS,
            section_repair_timeout_seconds,
        )
    except ImportError:
        DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS = None
        section_repair_timeout_seconds = None

    assert DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS == 900.0
    assert section_repair_timeout_seconds is not None
    assert section_repair_timeout_seconds() > 120.0
