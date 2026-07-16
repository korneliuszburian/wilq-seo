from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LocalAuditTrustLevel = Literal["local_unverified"]


@dataclass(frozen=True, slots=True)
class LocalAuditIdentity:
    principal_id: str
    workspace_id: str
    trust_level: LocalAuditTrustLevel


LOCAL_PILOT_AUDIT_IDENTITY = LocalAuditIdentity(
    principal_id="local_operator",
    workspace_id="ekologus_local_pilot",
    trust_level="local_unverified",
)
