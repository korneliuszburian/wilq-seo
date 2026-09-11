from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel

from wilq.schemas.core import utc_now

STOP_TELEMETRY_CONTRACT_VERSION: Literal[1] = 1
DEFAULT_STOP_TELEMETRY_RETENTION_DAYS = 30
DEFAULT_STOP_TELEMETRY_PURGE_BATCH_SIZE = 500
DEFAULT_STOP_TELEMETRY_HIGH_WATERMARK = 100_000

_STOP_TELEMETRY_RETENTION_DAYS_ENV = "WILQ_STOP_TELEMETRY_RETENTION_DAYS"
_STOP_TELEMETRY_PURGE_BATCH_SIZE_ENV = "WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE"
_STOP_TELEMETRY_HIGH_WATERMARK_ENV = "WILQ_STOP_TELEMETRY_HIGH_WATERMARK"
_SQLITE_MAX_INTEGER = (1 << 63) - 1


class StopTelemetryConfigurationError(ValueError):
    """Raised when bounded Stop telemetry policy cannot be constructed."""


class StopTelemetryPolicy(BaseModel):
    retention_days: int
    purge_batch_size: int
    high_watermark: int


class StopTelemetryEvent(BaseModel):
    event_id: str
    received_at: datetime
    event_type: Literal["stop"] = "stop"
    contract_version: Literal[1] = STOP_TELEMETRY_CONTRACT_VERSION


class StopTelemetryReceipt(BaseModel):
    status: Literal["accepted", "healthy", "high_watermark", "unavailable"] = (
        "accepted"
    )
    cutoff: datetime | None
    purged_count: int
    count: int | None


class StopTelemetryIntakeAccepted(StopTelemetryEvent):
    lifecycle: StopTelemetryReceipt


StopTelemetryUnavailableCode = Literal[
    "stop_telemetry_high_watermark",
    "stop_telemetry_storage_unavailable",
    "stop_telemetry_configuration_invalid",
]


class StopTelemetryUnavailable(BaseModel):
    type: Literal["stop_telemetry_unavailable"] = "stop_telemetry_unavailable"
    code: StopTelemetryUnavailableCode
    lifecycle: StopTelemetryReceipt


class StopTelemetryHighWatermarkError(RuntimeError):
    def __init__(self, receipt: StopTelemetryReceipt) -> None:
        super().__init__("Stop telemetry reached its configured high-watermark")
        self.receipt = receipt


class StopTelemetryStorageUnavailable(RuntimeError):
    """Sanitized failure exposed by a Stop telemetry storage adapter."""


class StopTelemetryStore(Protocol):
    def intake_stop_telemetry_event(
        self,
        event: StopTelemetryEvent,
        *,
        cutoff: datetime,
        purge_batch_size: int,
        high_watermark: int,
    ) -> StopTelemetryReceipt: ...

    def stop_telemetry_health(
        self,
        *,
        cutoff: datetime,
        high_watermark: int,
    ) -> StopTelemetryReceipt: ...


def stop_telemetry_policy() -> StopTelemetryPolicy:
    return StopTelemetryPolicy(
        retention_days=_positive_environment_integer(
            _STOP_TELEMETRY_RETENTION_DAYS_ENV,
            DEFAULT_STOP_TELEMETRY_RETENTION_DAYS,
        ),
        purge_batch_size=_positive_environment_integer(
            _STOP_TELEMETRY_PURGE_BATCH_SIZE_ENV,
            DEFAULT_STOP_TELEMETRY_PURGE_BATCH_SIZE,
        ),
        high_watermark=_positive_environment_integer(
            _STOP_TELEMETRY_HIGH_WATERMARK_ENV,
            DEFAULT_STOP_TELEMETRY_HIGH_WATERMARK,
        ),
    )


def new_stop_telemetry_intake(
    policy: StopTelemetryPolicy,
) -> tuple[StopTelemetryEvent, datetime]:
    received_at = utc_now()
    return new_stop_telemetry_event(received_at=received_at), _retention_cutoff(
        received_at,
        policy,
    )


def stop_telemetry_cutoff(policy: StopTelemetryPolicy) -> datetime:
    return _retention_cutoff(utc_now(), policy)


def intake_stop_telemetry(
    store: StopTelemetryStore,
) -> StopTelemetryIntakeAccepted | StopTelemetryUnavailable:
    try:
        policy = stop_telemetry_policy()
        event, cutoff = new_stop_telemetry_intake(policy)
    except StopTelemetryConfigurationError:
        return _stop_telemetry_unavailable(
            code="stop_telemetry_configuration_invalid",
            cutoff=None,
        )
    try:
        lifecycle = store.intake_stop_telemetry_event(
            event,
            cutoff=cutoff,
            purge_batch_size=policy.purge_batch_size,
            high_watermark=policy.high_watermark,
        )
    except StopTelemetryHighWatermarkError as exc:
        return StopTelemetryUnavailable(
            code="stop_telemetry_high_watermark",
            lifecycle=exc.receipt,
        )
    except StopTelemetryStorageUnavailable:
        return _stop_telemetry_unavailable(
            code="stop_telemetry_storage_unavailable",
            cutoff=cutoff,
        )
    return StopTelemetryIntakeAccepted(
        event_id=event.event_id,
        received_at=event.received_at,
        event_type=event.event_type,
        contract_version=event.contract_version,
        lifecycle=lifecycle,
    )


def read_stop_telemetry_health(
    store: StopTelemetryStore,
) -> StopTelemetryReceipt | StopTelemetryUnavailable:
    try:
        policy = stop_telemetry_policy()
        cutoff = stop_telemetry_cutoff(policy)
    except StopTelemetryConfigurationError:
        return _stop_telemetry_unavailable(
            code="stop_telemetry_configuration_invalid",
            cutoff=None,
        )
    try:
        return store.stop_telemetry_health(
            cutoff=cutoff,
            high_watermark=policy.high_watermark,
        )
    except StopTelemetryHighWatermarkError as exc:
        return StopTelemetryUnavailable(
            code="stop_telemetry_high_watermark",
            lifecycle=exc.receipt,
        )
    except StopTelemetryStorageUnavailable:
        return _stop_telemetry_unavailable(
            code="stop_telemetry_storage_unavailable",
            cutoff=cutoff,
        )


def new_stop_telemetry_event(
    *,
    received_at: datetime | None = None,
) -> StopTelemetryEvent:
    return StopTelemetryEvent(
        event_id=f"codex_stop_event_{uuid4().hex}",
        received_at=received_at or utc_now(),
    )


def _retention_cutoff(
    received_at: datetime,
    policy: StopTelemetryPolicy,
) -> datetime:
    try:
        return received_at - timedelta(days=policy.retention_days)
    except OverflowError as exc:
        raise StopTelemetryConfigurationError(
            f"{_STOP_TELEMETRY_RETENTION_DAYS_ENV} is outside the supported range"
        ) from exc


def _stop_telemetry_unavailable(
    *,
    code: StopTelemetryUnavailableCode,
    cutoff: datetime | None,
) -> StopTelemetryUnavailable:
    return StopTelemetryUnavailable(
        code=code,
        lifecycle=StopTelemetryReceipt(
            status="unavailable",
            cutoff=cutoff,
            purged_count=0,
            count=None,
        ),
    )


def _positive_environment_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise StopTelemetryConfigurationError(
            f"{name} must be a positive integer"
        ) from exc
    if value <= 0 or value > _SQLITE_MAX_INTEGER:
        raise StopTelemetryConfigurationError(
            f"{name} must be a positive 64-bit integer"
        )
    return value


__all__ = [
    "DEFAULT_STOP_TELEMETRY_HIGH_WATERMARK",
    "DEFAULT_STOP_TELEMETRY_PURGE_BATCH_SIZE",
    "DEFAULT_STOP_TELEMETRY_RETENTION_DAYS",
    "STOP_TELEMETRY_CONTRACT_VERSION",
    "StopTelemetryConfigurationError",
    "StopTelemetryEvent",
    "StopTelemetryHighWatermarkError",
    "StopTelemetryIntakeAccepted",
    "StopTelemetryPolicy",
    "StopTelemetryReceipt",
    "StopTelemetryStorageUnavailable",
    "StopTelemetryStore",
    "StopTelemetryUnavailable",
    "StopTelemetryUnavailableCode",
    "intake_stop_telemetry",
    "new_stop_telemetry_event",
    "new_stop_telemetry_intake",
    "read_stop_telemetry_health",
    "stop_telemetry_cutoff",
    "stop_telemetry_policy",
]
