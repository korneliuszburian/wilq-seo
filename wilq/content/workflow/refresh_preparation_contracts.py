"""Typed, redacted authorization contracts for classified refresh preparation.

The production-classification receipt deliberately keeps its source packet outside
WILQ.  This module stores only the exact, stable identifiers required to bind a
manual refresh authorization to the current classified row and rebuilt planning
input.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY, LocalAuditTrustLevel
from wilq.content.planning.input_summary import ContentPlanningInputSummary

_HEX64 = r"^[0-9a-f]{64}$"
_NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, strict=True)]

ContentRefreshPreparationBlockerCode = Literal[
    "production_classification_missing",
    "production_classification_item_missing",
    "refresh_preparation_alias_not_current",
    "refresh_preparation_decision_not_refresh",
    "stale_production_classification",
    "refresh_preparation_service_required",
    "refresh_preparation_service_unavailable",
    "refresh_preparation_service_not_approved",
    "refresh_preparation_service_sources_missing",
    "refresh_preparation_input_blocked",
    "refresh_preparation_authorization_missing",
    "refresh_preparation_authorization_foreign",
    "refresh_preparation_authorization_digest_mismatch",
    "refresh_preparation_authorization_service_mismatch",
    "refresh_preparation_authorization_input_mismatch",
    "refresh_preparation_authorization_stale",
    "refresh_preparation_proposal_binding_mismatch",
    "refresh_preparation_acknowledgement_mismatch",
    "refresh_preparation_authorization_conflict",
]
_SAFE_LOCAL_OPERATOR_RE = re.compile(r"^[\w .-]+$", re.UNICODE)
_UNSAFE_LOCAL_OPERATOR_RE = re.compile(
    r"(?:basic|bearer|token|password|secret|credential|api[_ -]?key)",
    re.IGNORECASE,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContentRefreshPreparationBlocker(_StrictModel):
    code: ContentRefreshPreparationBlockerCode
    label: _NonBlank
    reason: _NonBlank
    next_step: _NonBlank
    source_codes: list[str] = Field(default_factory=list)


class ContentRefreshPreparationClassificationBinding(_StrictModel):
    """The smallest classification receipt that a refresh authorization needs."""

    classification_run_id: _NonBlank
    classification_run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    source_packet_row_digest: str = Field(pattern=_HEX64)
    current_work_item_id: _NonBlank
    canonical_path: _NonBlank
    public_url: _NonBlank
    classification_blocker_codes: list[str] = Field(default_factory=list)

    @field_validator("classification_blocker_codes")
    @classmethod
    def require_unique_blocker_codes(cls, value: list[str]) -> list[str]:
        normalized = [code.strip() for code in value]
        if any(not code for code in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("Classification blocker codes must be unique non-blank values.")
        return sorted(normalized)


class ContentRefreshPreparationServiceCandidate(_StrictModel):
    """One explicitly selected service candidate and its safe lineage identifiers."""

    service_card_id: _NonBlank
    service_label: _NonBlank
    lifecycle_status: _NonBlank
    matched_terms: list[str] = Field(min_length=1)
    match_reasons: list[str] = Field(min_length=1)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)

    @field_validator(
        "matched_terms",
        "match_reasons",
        "source_fact_ids",
        "source_material_ids",
        "evidence_ids",
        "source_connectors",
    )
    @classmethod
    def require_visible_members(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("Refresh preparation identifiers must be non-blank.")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def require_approved_source_lineage(self) -> ContentRefreshPreparationServiceCandidate:
        if self.lifecycle_status != "approved_current":
            raise ValueError("Refresh preparation requires an approved-current service candidate.")
        if not self.evidence_ids or not self.source_connectors:
            raise ValueError("Refresh preparation requires exact service source lineage.")
        if not self.source_fact_ids and not self.source_material_ids:
            raise ValueError("Refresh preparation requires a reviewed source fact or material.")
        return self


class ContentRefreshPreparationBinding(_StrictModel):
    """Full immutable receipt carried by generated plans and draft revisions."""

    authorization_id: _NonBlank
    authorization_digest: str = Field(pattern=_HEX64)
    classification_run_id: _NonBlank
    classification_run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    source_packet_row_digest: str = Field(pattern=_HEX64)
    current_work_item_id: _NonBlank
    canonical_path: _NonBlank
    public_url: _NonBlank
    service_card_id: _NonBlank
    planning_input_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def require_deterministic_id(self) -> ContentRefreshPreparationBinding:
        expected = f"content_refresh_preparation_authorization_{self.authorization_digest[:24]}"
        if self.authorization_id != expected:
            raise ValueError("Refresh preparation authorization ID does not match its digest.")
        return self


class ContentRefreshPreparationAuthorizationRequest(_StrictModel):
    expected_production_classification_run_digest: str = Field(pattern=_HEX64)
    expected_production_classification_decision_set_digest: str = Field(pattern=_HEX64)
    expected_production_classification_source_packet_row_digest: str = Field(pattern=_HEX64)
    expected_planning_input_digest: str = Field(pattern=_HEX64)
    service_card_id: _NonBlank
    authorized_by: str = Field(min_length=1, max_length=160)
    acknowledged_classification_blocker_codes: list[str] = Field(default_factory=list)

    @field_validator("acknowledged_classification_blocker_codes")
    @classmethod
    def require_exact_acknowledgement_set(cls, value: list[str]) -> list[str]:
        normalized = [code.strip() for code in value]
        if any(not code for code in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("Acknowledged classification blocker codes must be a unique set.")
        return sorted(normalized)

    @field_validator("authorized_by")
    @classmethod
    def require_safe_local_operator_identity(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
            or not _SAFE_LOCAL_OPERATOR_RE.fullmatch(normalized)
            or _UNSAFE_LOCAL_OPERATOR_RE.search(normalized)
        ):
            raise ValueError(
                "Refresh authorization requires a safe visible local operator identity."
            )
        return normalized


class ContentRefreshPreparationAuthorization(_StrictModel):
    schema_version: Literal["wilq_content_refresh_preparation_authorization_v1"] = (
        "wilq_content_refresh_preparation_authorization_v1"
    )
    authorization_id: _NonBlank
    authorization_digest: str = Field(pattern=_HEX64)
    work_item_id: _NonBlank
    classification_run_id: _NonBlank
    classification_run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    source_packet_row_digest: str = Field(pattern=_HEX64)
    canonical_path: _NonBlank
    public_url: _NonBlank
    planning_input_digest: str = Field(pattern=_HEX64)
    service_card_id: _NonBlank
    acknowledged_classification_blocker_codes: list[str] = Field(default_factory=list)
    authorized_by: str = Field(min_length=1, max_length=160)
    principal_id: Literal["local_operator"] = "local_operator"
    workspace_id: Literal["ekologus_local_pilot"] = "ekologus_local_pilot"
    trust_level: LocalAuditTrustLevel = LOCAL_PILOT_AUDIT_IDENTITY.trust_level
    authorized_at: datetime

    @field_validator("acknowledged_classification_blocker_codes")
    @classmethod
    def require_unique_acknowledgements(cls, value: list[str]) -> list[str]:
        normalized = [code.strip() for code in value]
        if any(not code for code in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("Authorization acknowledgement codes must be unique and non-blank.")
        return sorted(normalized)

    @field_validator("authorized_at")
    @classmethod
    def require_aware_authorized_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Refresh preparation authorization time must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("authorized_by")
    @classmethod
    def require_safe_authorized_by(cls, value: str) -> str:
        return ContentRefreshPreparationAuthorizationRequest.require_safe_local_operator_identity(
            value
        )

    @model_validator(mode="after")
    def require_exact_digest_and_identity(self) -> ContentRefreshPreparationAuthorization:
        digest = content_refresh_preparation_authorization_digest(
            work_item_id=self.work_item_id,
            classification_run_id=self.classification_run_id,
            classification_run_digest=self.classification_run_digest,
            decision_set_digest=self.decision_set_digest,
            source_packet_row_digest=self.source_packet_row_digest,
            canonical_path=self.canonical_path,
            public_url=self.public_url,
            planning_input_digest=self.planning_input_digest,
            service_card_id=self.service_card_id,
            acknowledged_classification_blocker_codes=self.acknowledged_classification_blocker_codes,
            authorized_by=self.authorized_by,
        )
        if self.authorization_digest != digest:
            raise ValueError("Refresh preparation authorization digest does not match its receipt.")
        expected_id = f"content_refresh_preparation_authorization_{digest[:24]}"
        if self.authorization_id != expected_id:
            raise ValueError("Refresh preparation authorization ID does not match its receipt.")
        return self

    @property
    def binding(self) -> ContentRefreshPreparationBinding:
        return ContentRefreshPreparationBinding(
            authorization_id=self.authorization_id,
            authorization_digest=self.authorization_digest,
            classification_run_id=self.classification_run_id,
            classification_run_digest=self.classification_run_digest,
            decision_set_digest=self.decision_set_digest,
            source_packet_row_digest=self.source_packet_row_digest,
            current_work_item_id=self.work_item_id,
            canonical_path=self.canonical_path,
            public_url=self.public_url,
            service_card_id=self.service_card_id,
            planning_input_digest=self.planning_input_digest,
        )


ContentRefreshPreparationAuthorizationRecordStatus = Literal["created", "idempotent", "conflict"]


class ContentRefreshPreparationAuthorizationRecordResult(_StrictModel):
    status: ContentRefreshPreparationAuthorizationRecordStatus
    authorization: ContentRefreshPreparationAuthorization


class ContentRefreshPreparationSelectionRequired(_StrictModel):
    status: Literal["selection_required"]
    work_item_id: _NonBlank
    classification: ContentRefreshPreparationClassificationBinding
    service_candidates: list[ContentRefreshPreparationServiceCandidate] = Field(
        default_factory=list
    )
    blockers: list[ContentRefreshPreparationBlocker] = Field(default_factory=list)
    safe_next_step: _NonBlank


class ContentRefreshPreparationBlocked(_StrictModel):
    status: Literal["blocked"]
    work_item_id: _NonBlank
    classification: ContentRefreshPreparationClassificationBinding | None = None
    service_candidate: ContentRefreshPreparationServiceCandidate | None = None
    planning_input_digest: str | None = Field(default=None, pattern=_HEX64)
    input_summary: ContentPlanningInputSummary | None = None
    blockers: list[ContentRefreshPreparationBlocker] = Field(min_length=1)
    safe_next_step: _NonBlank


class ContentRefreshPreparationStale(_StrictModel):
    status: Literal["stale"]
    work_item_id: _NonBlank
    classification: ContentRefreshPreparationClassificationBinding
    blockers: list[ContentRefreshPreparationBlocker] = Field(min_length=1)
    safe_next_step: _NonBlank


class _ContentRefreshPreparationReadyBase(_StrictModel):
    work_item_id: _NonBlank
    classification: ContentRefreshPreparationClassificationBinding
    service_candidate: ContentRefreshPreparationServiceCandidate
    planning_input_digest: str = Field(pattern=_HEX64)
    input_summary: ContentPlanningInputSummary
    blockers: list[ContentRefreshPreparationBlocker] = Field(default_factory=list)
    safe_next_step: _NonBlank


class ContentRefreshPreparationReadyToAuthorize(_ContentRefreshPreparationReadyBase):
    status: Literal["ready_to_authorize"]


class ContentRefreshPreparationAuthorized(_ContentRefreshPreparationReadyBase):
    status: Literal["authorized"]
    authorization: ContentRefreshPreparationAuthorization

    @model_validator(mode="after")
    def require_exact_authorization_binding(self) -> ContentRefreshPreparationAuthorized:
        authorization = self.authorization
        if (
            authorization.work_item_id != self.work_item_id
            or authorization.classification_run_id != self.classification.classification_run_id
            or authorization.classification_run_digest
            != self.classification.classification_run_digest
            or authorization.decision_set_digest != self.classification.decision_set_digest
            or authorization.source_packet_row_digest
            != self.classification.source_packet_row_digest
            or authorization.canonical_path != self.classification.canonical_path
            or authorization.public_url != self.classification.public_url
            or authorization.planning_input_digest != self.planning_input_digest
            or authorization.service_card_id != self.service_candidate.service_card_id
        ):
            raise ValueError("Refresh preparation authorization does not match the ready context.")
        return self


ContentRefreshPreparationPreview = Annotated[
    ContentRefreshPreparationSelectionRequired
    | ContentRefreshPreparationBlocked
    | ContentRefreshPreparationStale
    | ContentRefreshPreparationReadyToAuthorize
    | ContentRefreshPreparationAuthorized,
    Field(discriminator="status"),
]


class _ContentRefreshPreparationAuthorizationResponse(_StrictModel):
    safe_next_step: _NonBlank


class ContentRefreshPreparationAuthorizationCreatedResponse(
    _ContentRefreshPreparationAuthorizationResponse
):
    status: Literal["created"]
    authorization: ContentRefreshPreparationAuthorization
    blockers: list[ContentRefreshPreparationBlocker] = Field(default_factory=list, max_length=0)


class ContentRefreshPreparationAuthorizationIdempotentResponse(
    _ContentRefreshPreparationAuthorizationResponse
):
    status: Literal["idempotent"]
    authorization: ContentRefreshPreparationAuthorization
    blockers: list[ContentRefreshPreparationBlocker] = Field(default_factory=list, max_length=0)


class ContentRefreshPreparationAuthorizationConflictResponse(
    _ContentRefreshPreparationAuthorizationResponse
):
    status: Literal["conflict"]
    authorization: None = None
    blockers: list[ContentRefreshPreparationBlocker] = Field(min_length=1)


ContentRefreshPreparationAuthorizationResponse = Annotated[
    ContentRefreshPreparationAuthorizationCreatedResponse
    | ContentRefreshPreparationAuthorizationIdempotentResponse
    | ContentRefreshPreparationAuthorizationConflictResponse,
    Field(discriminator="status"),
]


class ContentRefreshPreparationGuardError(ValueError):
    """Transport a typed refresh-authority failure through persistence guards."""

    def __init__(self, blocker: ContentRefreshPreparationBlocker) -> None:
        self.blocker = blocker
        super().__init__(blocker.code)


def content_refresh_preparation_authorization_digest(
    *,
    work_item_id: str,
    classification_run_id: str,
    classification_run_digest: str,
    decision_set_digest: str,
    source_packet_row_digest: str,
    canonical_path: str,
    public_url: str,
    planning_input_digest: str,
    service_card_id: str,
    acknowledged_classification_blocker_codes: list[str],
    authorized_by: str,
) -> str:
    payload = {
        "work_item_id": work_item_id,
        "classification_run_id": classification_run_id,
        "classification_run_digest": classification_run_digest,
        "decision_set_digest": decision_set_digest,
        "source_packet_row_digest": source_packet_row_digest,
        "canonical_path": canonical_path,
        "public_url": public_url,
        "planning_input_digest": planning_input_digest,
        "service_card_id": service_card_id,
        "acknowledged_classification_blocker_codes": sorted(
            acknowledged_classification_blocker_codes
        ),
        "authorized_by": authorized_by,
    }
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def build_content_refresh_preparation_authorization(
    *,
    work_item_id: str,
    classification: ContentRefreshPreparationClassificationBinding,
    planning_input_digest: str,
    service_card_id: str,
    acknowledged_classification_blocker_codes: list[str],
    authorized_by: str,
    authorized_at: datetime,
) -> ContentRefreshPreparationAuthorization:
    digest = content_refresh_preparation_authorization_digest(
        work_item_id=work_item_id,
        classification_run_id=classification.classification_run_id,
        classification_run_digest=classification.classification_run_digest,
        decision_set_digest=classification.decision_set_digest,
        source_packet_row_digest=classification.source_packet_row_digest,
        canonical_path=classification.canonical_path,
        public_url=classification.public_url,
        planning_input_digest=planning_input_digest,
        service_card_id=service_card_id,
        acknowledged_classification_blocker_codes=acknowledged_classification_blocker_codes,
        authorized_by=authorized_by,
    )
    return ContentRefreshPreparationAuthorization(
        authorization_id=f"content_refresh_preparation_authorization_{digest[:24]}",
        authorization_digest=digest,
        work_item_id=work_item_id,
        classification_run_id=classification.classification_run_id,
        classification_run_digest=classification.classification_run_digest,
        decision_set_digest=classification.decision_set_digest,
        source_packet_row_digest=classification.source_packet_row_digest,
        canonical_path=classification.canonical_path,
        public_url=classification.public_url,
        planning_input_digest=planning_input_digest,
        service_card_id=service_card_id,
        acknowledged_classification_blocker_codes=acknowledged_classification_blocker_codes,
        authorized_by=authorized_by,
        authorized_at=authorized_at,
    )


def refresh_preparation_binding_matches_content_identity(
    binding: ContentRefreshPreparationBinding,
    *,
    work_item_id: str,
    service_card_id: str | None,
    planning_input_digest: str | None,
    final_canonical_url: str | None,
) -> bool:
    if (
        service_card_id is None
        or planning_input_digest is None
        or final_canonical_url is None
        or binding.current_work_item_id != work_item_id
        or binding.service_card_id != service_card_id
        or binding.planning_input_digest != planning_input_digest
        or binding.public_url != final_canonical_url
    ):
        return False
    parsed = urlsplit(final_canonical_url)
    canonical_path = parsed.path.rstrip("/") or "/"
    return binding.canonical_path == canonical_path


__all__ = [
    "ContentRefreshPreparationAuthorization",
    "ContentRefreshPreparationAuthorizationConflictResponse",
    "ContentRefreshPreparationAuthorizationCreatedResponse",
    "ContentRefreshPreparationAuthorizationIdempotentResponse",
    "ContentRefreshPreparationAuthorizationRecordResult",
    "ContentRefreshPreparationAuthorizationRequest",
    "ContentRefreshPreparationAuthorizationResponse",
    "ContentRefreshPreparationAuthorized",
    "ContentRefreshPreparationBinding",
    "ContentRefreshPreparationBlocked",
    "ContentRefreshPreparationBlocker",
    "ContentRefreshPreparationBlockerCode",
    "ContentRefreshPreparationClassificationBinding",
    "ContentRefreshPreparationGuardError",
    "ContentRefreshPreparationPreview",
    "ContentRefreshPreparationReadyToAuthorize",
    "ContentRefreshPreparationSelectionRequired",
    "ContentRefreshPreparationServiceCandidate",
    "ContentRefreshPreparationStale",
    "build_content_refresh_preparation_authorization",
    "content_refresh_preparation_authorization_digest",
    "refresh_preparation_binding_matches_content_identity",
]
