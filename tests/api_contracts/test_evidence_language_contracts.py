from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.env import clear_google_service_env
from wilq.evidence.registry import connector_evidence_id, list_evidence_by_ids


def test_connector_evidence_summary_uses_operator_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "connector_evidence.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "connector_evidence.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "123456789")

    evidence = list_evidence_by_ids([connector_evidence_id("google_merchant_center")])

    assert len(evidence) == 1
    assert evidence[0].summary.startswith("Merchant Center:")
    assert "brak dostępu" in evidence[0].summary or "dostęp skonfigurowany" in evidence[0].summary
    assert "Connector " not in evidence[0].summary
    assert "credential names" not in evidence[0].summary
