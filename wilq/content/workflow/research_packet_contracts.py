"""Typed immutable contracts for content research packets."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal, Self
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.content_kind import ContentKind
from wilq.content.workflow.decisions.production import canonical_json_digest

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_~.%-]*$")
_GENERIC_LONG_TOKEN = re.compile(r"^[A-Za-z0-9_-]{32,}$")
_SAFE_TOKEN_PREFIXES = (
    "action_",
    "ad_",
    "audit_",
    "campaign_",
    "card_",
    "classification_",
    "connector_",
    "content_",
    "draft_",
    "ekologus_",
    "ev_",
    "fact_",
    "identity_",
    "job_",
    "knowledge_",
    "page_",
    "packet_",
    "post_",
    "proposal_",
    "refresh_",
    "research_",
    "review_",
    "run_",
    "service_",
    "source_",
    "workflow_",
    "work_",
    "wp_",
)
_SECRET_LIKE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|gho_[A-Za-z0-9_]{20,}|ya29\.[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)
_MAX_FRESHNESS_AGE = timedelta(days=30)

RESEARCH_PACKET_SCHEMA_VERSION: Literal["wilq_content_research_packet_v1"] = (
    "wilq_content_research_packet_v1"
)

ResearchPacketStatus = Literal["exact_current", "blocked"]
ResearchPacketCurrentStatus = Literal["current", "blocked", "legacy"]
ResearchPacketBlockerSeam = Literal[
    "preparation_receipt",
    "source_pack_binding",
    "identity_binding",
    "work_item_identity",
    "content_kind",
    "source_facts",
    "evidence",
    "freshness",
    "intent",
    "audience",
    "canonical_owner",
    "cta",
    "internal_links",
    "legal_requirements",
]
ResearchPacketBlockerReason = Literal[
    "preparation_receipt_missing",
    "preparation_receipt_mismatch",
    "preparation_receipt_conflict",
    "source_pack_binding_missing",
    "source_pack_binding_digest_mismatch",
    "source_pack_identity_mismatch",
    "source_pack_binding_blocked",
    "identity_binding_missing",
    "identity_binding_digest_mismatch",
    "identity_binding_blocked",
    "context_receipt_missing",
    "context_receipt_mismatch",
    "packet_conflict",
    "work_item_mismatch",
    "disposition_not_keep",
    "content_kind_ambiguous",
    "intent_missing",
    "query_cluster_missing",
    "audience_missing",
    "buyer_problem_missing",
    "buyer_trigger_missing",
    "canonical_owner_missing",
    "source_facts_missing",
    "source_fact_not_bound",
    "source_fact_not_registered",
    "source_fact_not_approved",
    "source_fact_registry_stale",
    "evidence_missing",
    "evidence_not_bound",
    "freshness_missing",
    "freshness_stale",
    "legal_requirements_missing",
    "cta_destination_missing",
    "cta_destination_invalid",
    "internal_links_missing",
    "internal_link_not_verified",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _safe_text(value: str, label: str, *, allow_blank: bool = True) -> str:
    normalized = value.strip()
    if not allow_blank and not normalized:
        raise ValueError(f"{label} must be non-blank.")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError(f"{label} must not contain control characters.")
    if _SECRET_LIKE.search(normalized) or _is_restricted_long_token(normalized):
        raise ValueError(f"{label} must not resemble a credential identifier.")
    return normalized


def _safe_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if (
        any(not item for item in normalized)
        or any(not re.fullmatch(_SAFE_IDENTIFIER, item) for item in normalized)
        or any(_is_restricted_long_token(item) for item in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


def _is_restricted_long_token(value: str) -> bool:
    return bool(
        _SECRET_LIKE.search(value)
        or (
            _GENERIC_LONG_TOKEN.fullmatch(value)
            and not value.casefold().startswith(_SAFE_TOKEN_PREFIXES)
        )
    )


class ContentResearchPacketContextReceipt(_FrozenModel):
    """Server-derived lineage for the semantic inputs of one packet."""

    schema_version: Literal["wilq_content_research_packet_context_v1"] = (
        "wilq_content_research_packet_context_v1"
    )
    classification_run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    source_fact_authority_receipt_id: str | None = Field(
        default=None, max_length=240, pattern=_SAFE_IDENTIFIER
    )
    source_fact_authority_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    source_fact_authority_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    source_fact_authority_provenance_digest: str | None = Field(default=None, pattern=_HEX64)
    service_card_id: str | None = Field(default=None, max_length=240, pattern=_SAFE_IDENTIFIER)
    service_semantic_digest: str = Field(pattern=_HEX64)
    brief_semantic_digest: str = Field(pattern=_HEX64)
    demand_evidence_digest: str = Field(pattern=_HEX64)
    verified_links_digest: str = Field(pattern=_HEX64)
    regulatory_coverage_digest: str = Field(pattern=_HEX64)
    freshness_digest: str = Field(pattern=_HEX64)
    cta_destination: str = Field(default="", max_length=2048)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    source_pack_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    source_fact_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    demand_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    measurement_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    verified_link_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    cta_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    regulatory_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    planning_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)

    @field_validator(
        "classification_run_digest",
        "classification_source_row_digest",
        "identity_binding_digest",
        "source_fact_authority_receipt_digest",
        "source_fact_authority_snapshot_digest",
        "source_fact_authority_provenance_digest",
        "service_semantic_digest",
        "brief_semantic_digest",
        "demand_evidence_digest",
        "verified_links_digest",
        "regulatory_coverage_digest",
        "freshness_digest",
    )
    @classmethod
    def require_nonzero_context_digests(cls, value: str | None) -> str | None:
        if value is not None and value == "0" * 64:
            raise ValueError("Research packet context digest must not be zero.")
        return value

    @field_validator(
        "evidence_ids",
        "source_pack_evidence_ids",
        "source_fact_evidence_ids",
        "demand_evidence_ids",
        "measurement_evidence_ids",
        "verified_link_evidence_ids",
        "cta_evidence_ids",
        "regulatory_evidence_ids",
        "planning_evidence_ids",
    )
    @classmethod
    def require_sorted_context_evidence(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _safe_ids(value, "Research packet context evidence IDs") if value else value

    @field_validator("cta_destination")
    @classmethod
    def require_safe_context_cta_destination(cls, value: str) -> str:
        normalized = _safe_text(value, "Research packet context CTA destination")
        if normalized and not _is_safe_path(normalized):
            raise ValueError("Research packet context CTA destination must be a safe path.")
        return normalized


class ContentResearchPacketFreshness(_FrozenModel):
    """Freshness receipt for one source fact, with no source payload."""

    source_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    checked_at: datetime
    status: Literal["fresh", "stale", "unknown"]

    @field_validator("source_id")
    @classmethod
    def reject_secret_like_source_id(cls, value: str) -> str:
        return _safe_text(value, "Freshness source ID", allow_blank=False)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Freshness evidence IDs") if value else value

    @field_validator("checked_at")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Freshness checked_at must be timezone-aware.")
        return value.astimezone(UTC)


class ContentResearchPacketInternalLink(_FrozenModel):
    """An internal destination; absolute external URLs never enter the packet."""

    destination_path: str = Field(min_length=1, max_length=2048)
    anchor_text: str = Field(min_length=1, max_length=240)
    relation: Literal["supporting", "next_step", "source"]
    verification: Literal["exact_verified", "planned", "blocked"]

    @field_validator("destination_path")
    @classmethod
    def require_safe_destination(cls, value: str) -> str:
        normalized = value.strip()
        if not _is_safe_path(normalized):
            raise ValueError("Internal link destination must be a safe absolute path.")
        return normalized

    @field_validator("anchor_text")
    @classmethod
    def require_safe_anchor(cls, value: str) -> str:
        return _safe_text(value, "Internal link anchor", allow_blank=False)


class ContentResearchPacketBlocker(_FrozenModel):
    seam: ResearchPacketBlockerSeam
    reason: ResearchPacketBlockerReason
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    next_step_pl: str = Field(min_length=1, max_length=600)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_blocker_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Research packet blocker evidence IDs") if value else value

    @field_validator("next_step_pl")
    @classmethod
    def require_safe_next_step(cls, value: str) -> str:
        return _safe_text(value, "Research packet blocker next step", allow_blank=False)


class ContentResearchPacketCommand(_FrozenModel):
    """Caller input for one packet; source payloads are intentionally not fields."""

    source_pack_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_pack_binding_digest: str = Field(pattern=_HEX64)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    preparation_receipt_id: str | None = Field(
        default=None, max_length=280, pattern=_SAFE_IDENTIFIER
    )
    preparation_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    content_kind: ContentKind
    intent: str = Field(default="", max_length=600)
    query_cluster: tuple[str, ...] = Field(default=(), max_length=128)
    canonical_owner: str = Field(default="", max_length=600)
    target_audience: str = Field(default="", max_length=600)
    buyer_problem: str = Field(default="", max_length=1000)
    buyer_trigger: str = Field(default="", max_length=1000)
    approved_source_fact_ids: tuple[str, ...] = Field(default=(), max_length=256)
    blocked_claims: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    freshness: tuple[ContentResearchPacketFreshness, ...] = Field(default=(), max_length=256)
    legal_source_requirements: tuple[str, ...] = Field(default=(), max_length=256)
    cta_destination: str = Field(default="", max_length=2048)
    internal_links: tuple[ContentResearchPacketInternalLink, ...] = Field(
        default=(), max_length=128
    )
    context_receipt: ContentResearchPacketContextReceipt | None = None
    recorded_by: str = Field(min_length=1, max_length=160, pattern=_SAFE_IDENTIFIER)
    recorded_at: datetime

    @field_validator(
        "source_pack_binding_id",
        "identity_binding_id",
        "current_work_item_id",
        "recorded_by",
    )
    @classmethod
    def reject_credential_like_identifiers(cls, value: str, info: object) -> str:
        field_name = str(getattr(info, "field_name", "identifier"))
        return _safe_text(value, field_name, allow_blank=False)

    @field_validator(
        "intent",
        "canonical_owner",
        "target_audience",
        "buyer_problem",
        "buyer_trigger",
        "cta_destination",
    )
    @classmethod
    def normalize_compact_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "packet text")
        return _safe_text(value, str(field_name))

    @field_validator("query_cluster", "approved_source_fact_ids", "blocked_claims", "evidence_ids")
    @classmethod
    def normalize_id_or_claim_lists(
        cls, value: tuple[str, ...], info: object
    ) -> tuple[str, ...]:
        field_name = str(getattr(info, "field_name", "packet values"))
        if field_name == "query_cluster":
            normalized = tuple(_safe_text(item, field_name, allow_blank=False) for item in value)
            if len(normalized) != len(set(normalized)) or normalized != tuple(sorted(normalized)):
                raise ValueError(f"{field_name} must be sorted, unique and non-blank.")
            return normalized
        if field_name in {"approved_source_fact_ids", "evidence_ids"}:
            return _safe_ids(value, field_name) if value else value
        return tuple(_safe_text(item, field_name, allow_blank=False) for item in value)

    @field_validator("legal_source_requirements")
    @classmethod
    def normalize_legal_requirements(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _safe_text(item, "Legal/source requirement", allow_blank=False) for item in value
        )

    @field_validator("recorded_at")
    @classmethod
    def require_aware_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Research packet recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("cta_destination")
    @classmethod
    def require_safe_cta_destination(cls, value: str) -> str:
        if value and not _is_safe_path(value):
            raise ValueError("CTA destination must be a safe absolute path.")
        return value

    @field_validator("source_pack_binding_digest", "identity_binding_digest")
    @classmethod
    def require_nonzero_binding_digest(cls, value: str) -> str:
        if value == "0" * 64:
            raise ValueError("Research packet binding digest must not be zero.")
        return value

    @model_validator(mode="after")
    def require_preparation_receipt_pair(self) -> Self:
        if (self.preparation_receipt_id is None) != (
            self.preparation_receipt_digest is None
        ):
            raise ValueError("Preparation receipt ID and digest must be supplied together.")
        return self


class ContentResearchPacket(_FrozenModel):
    """Immutable exact-bound packet safe to persist and expose through the API."""

    schema_version: Literal["wilq_content_research_packet_v1"] = RESEARCH_PACKET_SCHEMA_VERSION
    packet_id: str = Field(min_length=1, max_length=280)
    packet_digest: str = Field(pattern=_HEX64)
    status: ResearchPacketStatus
    source_pack_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_pack_binding_digest: str = Field(pattern=_HEX64)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    preparation_receipt_id: str | None = Field(
        default=None, max_length=280, pattern=_SAFE_IDENTIFIER
    )
    preparation_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    classification_source_row_digest: str = ""
    canonical_path: str = ""
    public_url: str = ""
    final_disposition: Literal["keep", "noindex", "redirect", "remove"] = "keep"
    content_kind: ContentKind
    intent: str = ""
    query_cluster: tuple[str, ...] = Field(default=(), max_length=128)
    canonical_owner: str = ""
    target_audience: str = ""
    buyer_problem: str = ""
    buyer_trigger: str = ""
    approved_source_fact_ids: tuple[str, ...] = Field(default=(), max_length=256)
    blocked_claims: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    source_fact_registry_digest: str = ""
    source_facts_digest: str = Field(pattern=_HEX64)
    evidence_ids_digest: str = Field(pattern=_HEX64)
    freshness: tuple[ContentResearchPacketFreshness, ...] = Field(default=(), max_length=256)
    legal_source_requirements: tuple[str, ...] = Field(default=(), max_length=256)
    cta_destination: str = ""
    internal_links: tuple[ContentResearchPacketInternalLink, ...] = Field(
        default=(), max_length=128
    )
    context_receipt: ContentResearchPacketContextReceipt | None = None
    input_digest: str = Field(pattern=_HEX64)
    blocker: ContentResearchPacketBlocker | None = None
    recorded_by: str = Field(min_length=1, max_length=160, pattern=_SAFE_IDENTIFIER)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Research packet recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("cta_destination")
    @classmethod
    def require_safe_cta_destination(cls, value: str) -> str:
        if value and not _is_safe_path(value):
            raise ValueError("CTA destination must be a safe absolute path.")
        return value

    @model_validator(mode="after")
    def require_exact_packet_identity(self) -> Self:
        blocked = self.status == "blocked"
        if blocked != (self.blocker is not None):
            raise ValueError("Blocked research packet state must carry exactly one blocker.")
        if self.source_facts_digest != source_ids_digest(self.approved_source_fact_ids):
            raise ValueError("Research packet source facts digest does not match IDs.")
        if self.evidence_ids_digest != source_ids_digest(self.evidence_ids):
            raise ValueError("Research packet evidence digest does not match IDs.")
        if self.context_receipt is not None and not blocked:
            context = self.context_receipt
            if (
                context.identity_binding_id != self.identity_binding_id
                or context.identity_binding_digest != self.identity_binding_digest
                or context.classification_source_row_digest
                != self.classification_source_row_digest
                or context.cta_destination != self.cta_destination
            ):
                raise ValueError("Research packet context receipt does not match its packet.")
        if (self.preparation_receipt_id is None) != (
            self.preparation_receipt_digest is None
        ):
            raise ValueError("Preparation receipt ID and digest must be supplied together.")
        expected = research_packet_digest(self)
        logical_id = research_packet_logical_id(self)
        if (
            self.packet_digest != expected
            or self.packet_id != f"content_research_packet_{logical_id[:24]}"
        ):
            raise ValueError("Research packet ID/digest does not match its payload.")
        if not blocked:
            if self.preparation_receipt_id is None or self.preparation_receipt_digest is None:
                raise ValueError("Exact research packets require a preparation receipt.")
            if self.final_disposition != "keep":
                raise ValueError("Only keep URLs may have an exact research packet.")
            _require_exact_semantic_fields(self)
            if not self.classification_source_row_digest or not self.source_fact_registry_digest:
                raise ValueError("Exact packet requires classification and registry digests.")
        return self


class ContentResearchPacketRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict", "blocked"]
    packet: ContentResearchPacket


class ContentResearchPacketCurrentProjection(_FrozenModel):
    """Read-only current-state assessment for one immutable packet record."""

    status: ResearchPacketCurrentStatus
    packet_id: str = Field(min_length=1, max_length=280)
    packet_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    current_source_pack_binding_id: str | None = Field(default=None, max_length=240)
    current_source_pack_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    current_identity_binding_id: str | None = Field(default=None, max_length=240)
    current_identity_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    blocker: ContentResearchPacketBlocker | None = None
    revalidated_at: datetime

    @field_validator("revalidated_at")
    @classmethod
    def require_aware_revalidation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Research packet revalidation time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_projection_blocker_shape(self) -> Self:
        if self.status == "current" and self.blocker is not None:
            raise ValueError("Current research packet projection cannot carry a blocker.")
        if self.status in {"blocked", "legacy"} and self.blocker is None:
            raise ValueError("Blocked or legacy research packet projection requires a blocker.")
        return self


class ContentResearchPacketReadResult(_FrozenModel):
    status: Literal["found"] = "found"
    packet: ContentResearchPacket
    current: ContentResearchPacketCurrentProjection


def source_ids_digest(values: tuple[str, ...]) -> str:
    return canonical_json_digest({"values": values})


def research_packet_input_digest(command: ContentResearchPacketCommand) -> str:
    payload = command.model_dump(
        mode="json",
        exclude={
            "preparation_receipt_id",
            "preparation_receipt_digest",
            "recorded_by",
            "recorded_at",
        },
    )
    return canonical_json_digest(payload)


def research_packet_logical_id(value: ContentResearchPacket | dict[str, object]) -> str:
    payload = _payload(value)
    return canonical_json_digest(
        {
            "source_pack_binding_id": payload["source_pack_binding_id"],
            "source_pack_binding_digest": payload["source_pack_binding_digest"],
            "identity_binding_id": payload["identity_binding_id"],
            "identity_binding_digest": payload["identity_binding_digest"],
            "current_work_item_id": payload["current_work_item_id"],
            "input_digest": payload["input_digest"],
        }
    )


def research_packet_digest(value: ContentResearchPacket | dict[str, object]) -> str:
    payload = _payload(value)
    for name in ("packet_id", "packet_digest", "recorded_by", "recorded_at"):
        payload.pop(name, None)
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_exact_semantic_fields(packet: ContentResearchPacket) -> None:
    if (
        not packet.canonical_path
        or not packet.public_url
        or not packet.classification_source_row_digest
    ):
        raise ValueError("Exact packet requires canonical identity and classification digest.")
    if not re.fullmatch(_HEX64, packet.classification_source_row_digest):
        raise ValueError("Exact packet classification digest must be SHA-256.")
    if not re.fullmatch(_HEX64, packet.source_fact_registry_digest):
        raise ValueError("Exact packet registry digest must be SHA-256.")
    if content_normalized_path(packet.public_url) != packet.canonical_path:
        raise ValueError("Exact packet canonical path must match its public URL.")
    if packet.canonical_owner != packet.canonical_path:
        raise ValueError("Exact packet canonical owner must match its canonical path.")
    if not packet.intent or not packet.query_cluster or not packet.target_audience:
        raise ValueError("Exact packet requires intent, query cluster and target audience.")
    if not packet.buyer_problem or not packet.buyer_trigger or not packet.canonical_owner:
        raise ValueError("Exact packet requires buyer problem, trigger and canonical owner.")
    if not packet.approved_source_fact_ids or not packet.evidence_ids or not packet.freshness:
        raise ValueError("Exact packet requires source facts, evidence and freshness.")
    if (
        not packet.legal_source_requirements
        or not packet.cta_destination
        or not packet.internal_links
    ):
        raise ValueError("Exact packet requires legal requirements, CTA and internal links.")
    if not _is_safe_path(packet.cta_destination) or any(
        link.verification != "exact_verified" for link in packet.internal_links
    ):
        raise ValueError("Exact packet CTA and internal links must be verified safe paths.")


def _is_safe_path(value: str) -> bool:
    """Accept one local path and reject protocol-relative/encoded traversal."""

    normalized = value.strip()
    if not _SAFE_PATH.fullmatch(normalized) or normalized.startswith("//"):
        return False
    decoded = normalized
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if (
        "%" in decoded
        or _SECRET_LIKE.search(decoded)
        or not _SAFE_PATH.fullmatch(decoded)
        or decoded.startswith("//")
    ):
        return False
    return not any(part in {".", ".."} for part in decoded.split("/"))


def _payload(value: ContentResearchPacket | dict[str, object]) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return dict(value)


__all__ = [
    "ContentResearchPacket",
    "ContentResearchPacketBlocker",
    "ContentResearchPacketCommand",
    "ContentResearchPacketContextReceipt",
    "ContentResearchPacketCurrentProjection",
    "ContentResearchPacketFreshness",
    "ContentResearchPacketInternalLink",
    "ContentResearchPacketReadResult",
    "ContentResearchPacketRecordResult",
    "RESEARCH_PACKET_SCHEMA_VERSION",
    "ResearchPacketBlockerReason",
    "ResearchPacketCurrentStatus",
    "ResearchPacketBlockerSeam",
    "ResearchPacketStatus",
    "research_packet_digest",
    "research_packet_input_digest",
    "research_packet_logical_id",
    "source_ids_digest",
]
