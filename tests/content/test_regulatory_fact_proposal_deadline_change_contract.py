from __future__ import annotations


def test_regulatory_fact_proposal_deadline_contract_is_bounded(monkeypatch) -> None:
    try:
        from wilq.content.regulatory.runtime_contract import (
            DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS,
            regulatory_fact_proposal_timeout_seconds,
        )
    except ImportError:
        DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS = None
        regulatory_fact_proposal_timeout_seconds = None

    monkeypatch.delenv("WILQ_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS", raising=False)
    assert DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS == 900.0
    assert regulatory_fact_proposal_timeout_seconds is not None
    assert regulatory_fact_proposal_timeout_seconds() > 120.0
