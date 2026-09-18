"""Leaf contracts and digest primitives for exact evidence acquisition."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import (
    content_is_safe_public_url,
    content_normalized_path,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    canonical_json_digest,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.security.redaction import SECRET_VALUE_RE

if TYPE_CHECKING:
    from wilq.content.workflow.authoring_inventory_receipt import (
        ContentAuthoringInventoryReceipt,
    )

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SECRET_FIELD_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key)\s*[:=]\s*\S+"
)
_WORDPRESS_CONNECTOR_ID = "wordpress_ekologus"
_MAX_EXCERPT_CHARS = 2400
_EXCERPT_DERIVATION: Literal["normalized_sanitized_text_prefix_v1"] = (
    "normalized_sanitized_text_prefix_v1"
)


class EvidenceObservationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_type: Literal["current_page_observation"] = "current_page_observation"
    quality_tier: Literal["exact_page_observation"] = "exact_page_observation"
    source_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    source_snapshot_digest: str = Field(pattern=_HEX64)
    body_digest: str = Field(pattern=_HEX64)
    excerpt_digest: str = Field(pattern=_HEX64)
    collected_at: datetime
    read_at: datetime
    freshness_date: str = Field(min_length=1, max_length=64)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    source_connectors: tuple[str, ...] = Field(min_length=1, max_length=64)
    extraction_region: str = Field(min_length=1, max_length=240)
    sanitized_excerpt: str = Field(min_length=1, max_length=_MAX_EXCERPT_CHARS)
    excerpt_derivation: Literal["normalized_sanitized_text_prefix_v1"] = _EXCERPT_DERIVATION
    redaction_status: Literal["sanitized"] = "sanitized"
    verification_status: Literal["observed_not_verified"] = "observed_not_verified"
    raw_content_retained: Literal[False] = False

    @field_validator("collected_at", "read_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Current-page receipt timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_exact_safe_receipt(self) -> EvidenceObservationReceipt:
        if self.source_type != "current_page_observation":
            raise ValueError("Current-page receipt source type is fixed.")
        if self.quality_tier != "exact_page_observation":
            raise ValueError("Current-page receipt quality tier is fixed.")
        if self.redaction_status != "sanitized" or self.raw_content_retained is not False:
            raise ValueError("Current-page receipt must be sanitized and raw-free.")
        if not content_is_safe_public_url(self.source_url):
            raise ValueError("Current-page receipt requires a safe public URL.")
        if content_normalized_path(self.source_url) != self.canonical_path:
            raise ValueError("Current-page receipt URL/path mismatch.")
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Current-page receipt evidence IDs must be sorted and unique.")
        if any(not value.strip() for value in self.evidence_ids):
            raise ValueError("Current-page receipt evidence IDs cannot be blank.")
        if self.source_connectors != (_WORDPRESS_CONNECTOR_ID,):
            raise ValueError("Current-page receipt connector is server-owned.")
        if self.excerpt_derivation != _EXCERPT_DERIVATION:
            raise ValueError("Current-page excerpt derivation is fixed.")
        if _sanitized_text(self.sanitized_excerpt) != self.sanitized_excerpt:
            raise ValueError("Current-page excerpt must be normalized and sanitized.")
        if sha256(self.sanitized_excerpt.encode("utf-8")).hexdigest() != self.excerpt_digest:
            raise ValueError("Current-page excerpt digest does not match its excerpt.")
        expected_snapshot_digest = canonical_json_digest(
            _snapshot_digest_payload(
                source_url=self.source_url,
                canonical_path=self.canonical_path,
                body_digest=self.body_digest,
                excerpt_digest=self.excerpt_digest,
                extraction_region=self.extraction_region,
                read_at=self.read_at,
            )
        )
        if self.source_snapshot_digest != expected_snapshot_digest:
            raise ValueError("Current-page snapshot digest does not match its receipt.")
        expected_evidence_id = f"ev_content_current_page_{expected_snapshot_digest[:24]}"
        expected_observation_id = (
            f"content_current_page_observation_{expected_snapshot_digest[:24]}"
        )
        if self.evidence_ids != (expected_evidence_id,):
            raise ValueError("Current-page evidence ID does not match its receipt.")
        if self.observation_id != expected_observation_id:
            raise ValueError("Current-page observation ID does not match its receipt.")
        if self.collected_at != self.read_at:
            raise ValueError("Current-page receipt collected_at must equal read_at.")
        if self.freshness_date != self.read_at.date().isoformat():
            raise ValueError("Current-page receipt freshness date must match read_at.")
        return self


def _sanitized_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.strip().split())
    normalized = _SECRET_FIELD_RE.sub("[redacted]", normalized)
    return SECRET_VALUE_RE.sub("[redacted]", normalized)


def _snapshot_digest_payload(
    *,
    source_url: str,
    canonical_path: str,
    body_digest: str,
    excerpt_digest: str,
    extraction_region: str,
    read_at: datetime,
) -> dict[str, str]:
    return {
        "body_digest": body_digest,
        "canonical_path": canonical_path,
        "connector": _WORDPRESS_CONNECTOR_ID,
        "excerpt_derivation": _EXCERPT_DERIVATION,
        "excerpt_digest": excerpt_digest,
        "extraction_region": extraction_region,
        "quality_tier": "exact_page_observation",
        "read_at": read_at.isoformat(),
        "redaction_status": "sanitized",
        "source_url": source_url,
    }


class EvidenceAcquisitionIdentitySubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_kind: Literal["identity_binding"] = "identity_binding"
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)


class EvidenceAcquisitionAuthoringInventorySubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_kind: Literal["authoring_inventory_receipt"] = "authoring_inventory_receipt"
    authoring_inventory_receipt_id: str = Field(
        min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER
    )


EvidenceAcquisitionSubject = Annotated[
    EvidenceAcquisitionIdentitySubject | EvidenceAcquisitionAuthoringInventorySubject,
    Field(discriminator="subject_kind"),
]


class EvidenceAcquisitionStartCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: EvidenceAcquisitionSubject
    research_question: str = Field(min_length=5, max_length=1000)
    attempt: int = Field(default=0, ge=0, le=1000)
    source_intent: Literal[
        "current_page",
        "historical_page",
        "official_primary",
        "reviewed_ekologus",
        "credible_external",
    ] = "current_page"


class EvidenceAcquisitionRunBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class EvidenceAcquisitionRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_evidence_acquisition_run"] = (
        "content_evidence_acquisition_run"
    )
    contract_version: Literal["content_evidence_acquisition_run_v2"] = (
        "content_evidence_acquisition_run_v2"
    )
    run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    run_digest: str = Field(pattern=_HEX64)
    request_digest: str = Field(pattern=_HEX64)
    attempt: int = Field(ge=0, le=1000)
    status: Literal["blocked", "ready_for_researcher"]
    run_status: Literal["proposal_only"] = "proposal_only"
    subject_kind: Literal["identity_binding", "authoring_inventory_receipt"] = (
        "identity_binding"
    )
    identity_binding_id: str | None = None
    identity_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    authoring_inventory_receipt_id: str | None = None
    authoring_inventory_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    authoring_catalog_context_digest: str | None = Field(default=None, pattern=_HEX64)
    subject_public_url: str | None = None
    subject_canonical_path: str | None = None
    subject_evidence_ids: tuple[str, ...] = ()
    production_authority: Literal[False] = False
    disposition_status: Literal["unknown"] = "unknown"
    source_authority_status: Literal["unknown"] = "unknown"
    generation_allowed: Literal[False] = False
    current_work_item_id: str | None = None
    canonical_path: str | None = None
    public_url: str | None = None
    classification_run_id: str | None = None
    classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    classification_source_row_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_evidence_ids: tuple[str, ...] = ()
    research_question_safe: str = Field(min_length=5, max_length=1000)
    question_digest: str = Field(pattern=_HEX64)
    source_intent: str = Field(min_length=1)
    observation: EvidenceObservationReceipt | None = None
    proposed_facts: tuple[()] = ()
    vendor_read_status: Literal["not_attempted", "completed", "blocked"] = "not_attempted"
    researcher_executor_status: Literal["missing"] = "missing"
    blockers: tuple[EvidenceAcquisitionRunBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_state(self) -> Self:
        if self.subject_kind == "identity_binding":
            if not self.identity_binding_id:
                raise ValueError("Identity acquisition runs require identity_binding_id.")
            if (
                self.authoring_inventory_receipt_id is not None
                or self.authoring_inventory_receipt_digest is not None
                or self.authoring_catalog_context_digest is not None
            ):
                raise ValueError(
                    "Identity acquisition runs cannot carry authoring receipt lineage."
                )
            if self.status == "ready_for_researcher" and not all(
                (
                    self.identity_binding_digest,
                    self.current_work_item_id,
                    self.canonical_path,
                    self.public_url,
                    self.classification_run_id,
                    self.classification_run_digest,
                    self.classification_source_row_digest,
                    self.inventory_evidence_ids,
                )
            ):
                raise ValueError(
                    "Ready identity acquisition runs require exact identity and "
                    "classification fields."
                )
        else:
            if (
                self.identity_binding_id is not None
                or self.identity_binding_digest is not None
                or self.classification_run_id is not None
                or self.classification_run_digest is not None
                or self.classification_source_row_digest is not None
            ):
                raise ValueError(
                    "Authoring receipt acquisition runs cannot carry identity or "
                    "classification authority."
                )
            if self.status == "ready_for_researcher" and (
                not self.authoring_inventory_receipt_id
                or not self.authoring_inventory_receipt_digest
                or not self.subject_public_url
                or not self.subject_canonical_path
                or not self.subject_evidence_ids
                or not self.current_work_item_id
                or not self.canonical_path
                or not self.public_url
                or not self.inventory_evidence_ids
            ):
                raise ValueError(
                    "Ready authoring receipt acquisition runs require exact current subject fields."
                )
            if self.status == "ready_for_researcher" and self.source_intent != "current_page":
                raise ValueError(
                    "Authoring receipt acquisition runs support current_page only."
                )
        if self.production_authority or self.generation_allowed:
            raise ValueError("Acquisition runs cannot authorize production or generation.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked acquisition run requires typed blockers.")
        if self.status == "ready_for_researcher" and self.observation is None:
            raise ValueError("Researcher-ready run requires an exact observation.")
        expected = _run_digest(self)
        if (
            self.run_digest != expected
            or self.run_id != f"content_evidence_acquisition_{expected[:24]}"
        ):
            raise ValueError("Evidence acquisition run ID/digest does not match payload.")
        return self


class EvidenceAcquisitionCurrentProjection(BaseModel):
    """Current server assessment over one immutable persisted acquisition run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_evidence_acquisition_current_projection"] = (
        "content_evidence_acquisition_current_projection"
    )
    contract_version: Literal["content_evidence_acquisition_current_projection_v1"] = (
        "content_evidence_acquisition_current_projection_v1"
    )
    recorded_run: EvidenceAcquisitionRun
    run_id: str
    run_digest: str
    request_digest: str
    attempt: int
    recorded_status: Literal["blocked", "ready_for_researcher"]
    assessed_at: datetime
    freshness: Literal["fresh", "stale", "not_applicable"]
    current_status: Literal["blocked", "ready_for_researcher"]
    current_blockers: tuple[EvidenceAcquisitionRunBlocker, ...] = ()
    current_safe_next_step: str

    @model_validator(mode="after")
    def require_recorded_status(self) -> Self:
        if self.recorded_status != self.recorded_run.status:
            raise ValueError("Projection recorded status must match persisted run.")
        if (
            self.run_id != self.recorded_run.run_id
            or self.run_digest != self.recorded_run.run_digest
            or self.request_digest != self.recorded_run.request_digest
            or self.attempt != self.recorded_run.attempt
        ):
            raise ValueError("Projection identity must match persisted run.")
        if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
            raise ValueError("Projection assessment time must be timezone-aware.")
        if self.current_status == "blocked" and not self.current_blockers:
            raise ValueError("Blocked current projection requires typed blockers.")
        return self

    @property
    def status(self) -> Literal["blocked", "ready_for_researcher"]:
        return self.current_status

    @property
    def blockers(self) -> tuple[EvidenceAcquisitionRunBlocker, ...]:
        return self.current_blockers

    @property
    def safe_next_step(self) -> str:
        return self.current_safe_next_step

    def __getattr__(self, name: str) -> Any:
        recorded = self.__dict__.get("recorded_run")
        if recorded is not None:
            try:
                return getattr(recorded, name)
            except AttributeError:
                pass
        raise AttributeError(name)



IdentityLoader = Callable[[str], ContentDeliveryIdentityBinding | None]
ClassificationLoader = Callable[
    [str], ContentProductionClassificationProjection | None
]
CurrentPageSnapshotReader = Callable[..., EvidenceObservationReceipt]
ServerClock = Callable[[], datetime]


class EvidenceAcquisitionStore(Protocol):
    """Store port for server-owned acquisition and exact subject reads."""

    def get_evidence_acquisition_run_by_request_digest(
        self, request_digest: str
    ) -> EvidenceAcquisitionRun | None: ...

    def get_evidence_acquisition_run(self, run_id: str) -> EvidenceAcquisitionRun | None: ...

    def save_evidence_acquisition_run(
        self, run: EvidenceAcquisitionRun
    ) -> EvidenceAcquisitionRun: ...

    def load_content_authoring_inventory_receipt(
        self, receipt_id: str
    ) -> ContentAuthoringInventoryReceipt | None: ...


def _question_digest(question_safe: str) -> str:
    return sha256(question_safe.encode("utf-8")).hexdigest()


def _request_digest(
    command: EvidenceAcquisitionStartCommand,
    *,
    question_safe: str,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    receipt: Any | None = None,
    catalog_context_digest: str | None = None,
    receipt_freshness: Literal["fresh", "stale"] | None = None,
) -> str:
    subject = command.subject
    payload: dict[str, Any] = {
        "identity_binding_digest": None if identity is None else identity.binding_digest,
        "classification_run_id": None if classification is None else classification.run_id,
        "classification_run_digest": (
            None if classification is None else classification.run_digest
        ),
        "classification_source_row_digest": (
            None if classification is None else classification.row.source_packet_row_digest
        ),
        "question_digest": _question_digest(question_safe),
        "attempt": command.attempt,
        "source_intent": command.source_intent,
    }
    if isinstance(subject, EvidenceAcquisitionIdentitySubject):
        payload["identity_binding_id"] = subject.identity_binding_id
    else:
        payload["subject"] = subject.model_dump(mode="json")
        payload["authoring_inventory_receipt_digest"] = (
            None if receipt is None else receipt.receipt_digest
        )
        payload["authoring_catalog_context_digest"] = catalog_context_digest
        payload["authoring_receipt_freshness"] = receipt_freshness
    return canonical_json_digest(payload)


def _run_digest(run: EvidenceAcquisitionRun | Mapping[str, object]) -> str:
    payload = run.model_dump(mode="json") if isinstance(run, BaseModel) else dict(run)
    if payload.get("authoring_catalog_context_digest") is None:
        payload.pop("authoring_catalog_context_digest", None)
    if payload.get("subject_kind", "identity_binding") == "identity_binding":
        for field_name in (
            "subject_kind",
            "authoring_inventory_receipt_id",
            "authoring_inventory_receipt_digest",
            "authoring_catalog_context_digest",
            "subject_public_url",
            "subject_canonical_path",
            "subject_evidence_ids",
            "production_authority",
            "disposition_status",
            "source_authority_status",
            "generation_allowed",
        ):
            payload.pop(field_name, None)
    payload.pop("run_id", None)
    payload.pop("run_digest", None)
    return canonical_json_digest(_json_value(payload))


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _finalize_run(payload: dict[str, Any]) -> EvidenceAcquisitionRun:
    digest = _run_digest(payload)
    return EvidenceAcquisitionRun.model_validate(
        payload
        | {
            "run_id": f"content_evidence_acquisition_{digest[:24]}",
            "run_digest": digest,
        }
    )


__all__ = [
    "ClassificationLoader",
    "CurrentPageSnapshotReader",
    "EvidenceAcquisitionAuthoringInventorySubject",
    "EvidenceAcquisitionCurrentProjection",
    "EvidenceAcquisitionIdentitySubject",
    "EvidenceAcquisitionRun",
    "EvidenceAcquisitionRunBlocker",
    "EvidenceAcquisitionStartCommand",
    "EvidenceAcquisitionStore",
    "EvidenceAcquisitionSubject",
    "EvidenceObservationReceipt",
    "IdentityLoader",
    "ServerClock",
]
