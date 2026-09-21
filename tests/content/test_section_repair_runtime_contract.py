from __future__ import annotations

from wilq.content.drafts.section_repair_runtime_contract import (
    DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS,
    section_repair_timeout_seconds,
)


def test_section_repair_runtime_contract_uses_bounded_floor(monkeypatch) -> None:
    monkeypatch.delenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", raising=False)
    assert DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS == 900.0
    assert section_repair_timeout_seconds() == 900.0

    monkeypatch.setenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", "123")
    assert section_repair_timeout_seconds() == 123.0

    monkeypatch.setenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", "1")
    assert section_repair_timeout_seconds() == 5.0

    monkeypatch.setenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", "not-a-number")
    assert section_repair_timeout_seconds() == 900.0

    for non_finite in ("inf", "nan"):
        monkeypatch.setenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", non_finite)
        assert section_repair_timeout_seconds() == 900.0
