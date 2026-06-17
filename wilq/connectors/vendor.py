from __future__ import annotations

from dataclasses import dataclass, field

from wilq.schemas import ConnectorRefreshStatus

MetricSummaryValue = float | int | str


@dataclass(frozen=True)
class VendorMetricFact:
    name: str
    value: MetricSummaryValue
    dimensions: dict[str, str] = field(default_factory=dict)
    period: str = "connector_refresh"
    unit: str | None = None


@dataclass(frozen=True)
class VendorReadResult:
    status: ConnectorRefreshStatus
    summary: str
    external_call_attempted: bool = False
    vendor_data_collected: bool = False
    metric_summary: dict[str, MetricSummaryValue] = field(default_factory=dict)
    metric_facts: list[VendorMetricFact] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
