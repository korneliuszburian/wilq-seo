"""Domain-ownership guard for human-recorded Ads execution/observation."""

from __future__ import annotations

from pathlib import Path

from wilq.actions import ads_external_execution as domain

ROUTER_SOURCE = Path(__file__).resolve().parents[2] / "apps/api/wilq_api/routers/actions.py"


def test_domain_owns_ads_external_execution() -> None:
    assert callable(domain.acknowledge_external_ads_execution)
    assert callable(domain.record_external_ads_observation)
    assert issubclass(domain.AdsExternalAuditViolation, Exception)


def test_router_delegates_instead_of_building_audit_events() -> None:
    source = ROUTER_SOURCE.read_text(encoding="utf-8")
    assert "ads_external_execution.acknowledge_external_ads_execution(" in source
    assert "ads_external_execution.record_external_ads_observation(" in source
    assert "ads_external_execution_acknowledged" not in source
    assert "ads_external_observation_recorded" not in source
