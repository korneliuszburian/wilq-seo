from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from wilq.schemas.core import utc_now

STOP_TELEMETRY_CONTRACT_VERSION: Literal[1] = 1


class StopTelemetryEvent(BaseModel):
    event_id: str
    received_at: datetime
    event_type: Literal["stop"] = "stop"
    contract_version: Literal[1] = STOP_TELEMETRY_CONTRACT_VERSION


def new_stop_telemetry_event() -> StopTelemetryEvent:
    return StopTelemetryEvent(
        event_id=f"codex_stop_event_{uuid4().hex}",
        received_at=utc_now(),
    )


__all__ = [
    "STOP_TELEMETRY_CONTRACT_VERSION",
    "StopTelemetryEvent",
    "new_stop_telemetry_event",
]
