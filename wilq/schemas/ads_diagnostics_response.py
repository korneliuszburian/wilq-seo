"""Readiness-enriched public Ads diagnostics response."""

from __future__ import annotations

from pydantic import model_validator

from .ads import AdsDiagnosticsResponse as AdsDiagnosticsResponseBase
from .core import DiagnosticDataReadiness
from .diagnostic_readiness import build_diagnostic_data_readiness


class AdsDiagnosticsResponse(AdsDiagnosticsResponseBase):
    data_readiness: DiagnosticDataReadiness | None = None

    @model_validator(mode="after")
    def build_data_readiness(self) -> AdsDiagnosticsResponse:
        if self.data_readiness is None:
            facts = [fact for section in self.sections for fact in section.metric_facts]
            self.data_readiness = build_diagnostic_data_readiness(
                connector=self.connector,
                latest_refresh=self.latest_refresh,
                factual_metrics=facts[:12] if self.live_data_available else [],
                factual_metric_count=len(facts) if self.live_data_available else 0,
                evidence_ids=self.evidence_ids,
                partial=bool(
                    self.latest_refresh and self.latest_refresh.quality_state.value == "partial"
                ),
                stale=self.connector.freshness.state == "stale",
                partial_coverage_label=(
                    "Pokazane metryki obejmują tylko potwierdzony zakres odczytu Google Ads."
                ),
            )
        return self
