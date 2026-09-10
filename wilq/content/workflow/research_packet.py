"""Immutable, redacted per-URL research packets for content production."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal, Self
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.content_kind import ContentKind
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    source_fact_registry_digest,
)

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_~.%-]*$")
_SECRET_LIKE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|gho_[A-Za-z0-9_]{20,}|ya29\.[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)
_MAX_FRESHNESS_AGE = timedelta(days=30)

RESEARCH_PACKET_SCHEMA_VERSION: Literal["wilq_content_research_packet_v1"] = (
    "wilq_content_research_packet_v1"
)

ResearchPacketStatus = Literal["exact_current", "blocked"]
ResearchPacketBlockerSeam = Literal[
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
    "source_pack_binding_missing",
    "source_pack_binding_digest_mismatch",
    "source_pack_identity_mismatch",
    "source_pack_binding_blocked",
    "identity_binding_missing",
    "identity_binding_digest_mismatch",
    "identity_binding_blocked",
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
    if _SECRET_LIKE.search(normalized):
        raise ValueError(f"{label} must not resemble a credential identifier.")
    return normalized


def _safe_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if (
        any(not item for item in normalized)
        or any(not re.fullmatch(_SAFE_IDENTIFIER, item) for item in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


class ContentResearchPacketFreshness(_FrozenModel):
    """Freshness receipt for one source fact, with no source payload."""

    source_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    checked_at: datetime
    status: Literal["fresh", "stale", "unknown"]

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

    @field_validator("source_pack_binding_digest", "identity_binding_digest")
    @classmethod
    def require_nonzero_binding_digest(cls, value: str) -> str:
        if value == "0" * 64:
            raise ValueError("Research packet binding digest must not be zero.")
        return value


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

    @model_validator(mode="after")
    def require_exact_packet_identity(self) -> Self:
        blocked = self.status == "blocked"
        if blocked != (self.blocker is not None):
            raise ValueError("Blocked research packet state must carry exactly one blocker.")
        if self.source_facts_digest != source_ids_digest(self.approved_source_fact_ids):
            raise ValueError("Research packet source facts digest does not match IDs.")
        if self.evidence_ids_digest != source_ids_digest(self.evidence_ids):
            raise ValueError("Research packet evidence digest does not match IDs.")
        expected = research_packet_digest(self)
        logical_id = research_packet_logical_id(self)
        if (
            self.packet_digest != expected
            or self.packet_id != f"content_research_packet_{logical_id[:24]}"
        ):
            raise ValueError("Research packet ID/digest does not match its payload.")
        if not blocked:
            if self.final_disposition != "keep":
                raise ValueError("Only keep URLs may have an exact research packet.")
            _require_exact_semantic_fields(self)
            if not self.classification_source_row_digest or not self.source_fact_registry_digest:
                raise ValueError("Exact packet requires classification and registry digests.")
        return self


class ContentResearchPacketRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    packet: ContentResearchPacket


class ContentResearchPacketReadResult(_FrozenModel):
    status: Literal["found"] = "found"
    packet: ContentResearchPacket


def source_ids_digest(values: tuple[str, ...]) -> str:
    return canonical_json_digest({"values": values})


def research_packet_input_digest(command: ContentResearchPacketCommand) -> str:
    payload = command.model_dump(mode="json", exclude={"recorded_by", "recorded_at"})
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


def reconcile_content_research_packet(
    command: ContentResearchPacketCommand,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    *,
    now: datetime | None = None,
) -> ContentResearchPacket:
    accepted = ContentResearchPacketCommand.model_validate_json(
        command.model_dump_json(), strict=True
    )
    timestamp = now or accepted.recorded_at
    blocker = _research_packet_blocker(accepted, identity, source_pack, timestamp)
    status: ResearchPacketStatus = "blocked" if blocker else "exact_current"
    identity_fields = _identity_fields(identity)
    registry_digest = ""
    if source_pack is not None:
        registry_digest = source_pack.source_fact_registry_receipt.registry_digest
    payload: dict[str, object] = {
        "schema_version": RESEARCH_PACKET_SCHEMA_VERSION,
        "status": status,
        "source_pack_binding_id": accepted.source_pack_binding_id,
        "source_pack_binding_digest": accepted.source_pack_binding_digest,
        "identity_binding_id": accepted.identity_binding_id,
        "identity_binding_digest": accepted.identity_binding_digest,
        "current_work_item_id": accepted.current_work_item_id,
        **identity_fields,
        "content_kind": accepted.content_kind,
        "intent": accepted.intent,
        "query_cluster": accepted.query_cluster,
        "canonical_owner": accepted.canonical_owner,
        "target_audience": accepted.target_audience,
        "buyer_problem": accepted.buyer_problem,
        "buyer_trigger": accepted.buyer_trigger,
        "approved_source_fact_ids": accepted.approved_source_fact_ids,
        "blocked_claims": accepted.blocked_claims,
        "evidence_ids": accepted.evidence_ids,
        "source_fact_registry_digest": registry_digest,
        "source_facts_digest": source_ids_digest(accepted.approved_source_fact_ids),
        "evidence_ids_digest": source_ids_digest(accepted.evidence_ids),
        "freshness": tuple(item.model_dump(mode="json") for item in accepted.freshness),
        "legal_source_requirements": accepted.legal_source_requirements,
        "cta_destination": accepted.cta_destination,
        "internal_links": tuple(
            item.model_dump(mode="json") for item in accepted.internal_links
        ),
        "input_digest": research_packet_input_digest(accepted),
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
        "recorded_by": accepted.recorded_by,
        "recorded_at": accepted.recorded_at.isoformat(),
    }
    digest = research_packet_digest(payload)
    logical_id = research_packet_logical_id(payload)
    return ContentResearchPacket.model_validate(
        {
            "packet_id": f"content_research_packet_{logical_id[:24]}",
            "packet_digest": digest,
            **payload,
        }
    )


def _identity_fields(identity: ContentDeliveryIdentityBinding | None) -> dict[str, object]:
    if identity is None:
        return {
            "classification_source_row_digest": "",
            "canonical_path": "",
            "public_url": "",
            "final_disposition": "keep",
        }
    return {
        "classification_source_row_digest": identity.classification_source_row_digest,
        "canonical_path": identity.canonical_path,
        "public_url": identity.public_url,
        "final_disposition": identity.final_disposition,
    }


def _research_packet_blocker(
    command: ContentResearchPacketCommand,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    now: datetime,
) -> ContentResearchPacketBlocker | None:
    evidence = command.evidence_ids
    if source_pack is None:
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            evidence,
            "Najpierw zapisz exact source-pack binding dla tego identity bindingu.",
        )
    if (
        source_pack.binding_id != command.source_pack_binding_id
        or source_pack.binding_digest != command.source_pack_binding_digest
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_digest_mismatch",
            evidence,
            "Użyj ID i digestu z tego same persisted source-pack bindingu.",
        )
    if (
        source_pack.identity_binding_id != command.identity_binding_id
        or source_pack.identity_binding_digest != command.identity_binding_digest
        or source_pack.current_work_item_id != command.current_work_item_id
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_identity_mismatch",
            source_pack.evidence_ids,
            "Użyj source-pack bindingu należącego do tego samego identity i work itemu.",
        )
    if source_pack.status == "blocked":
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            source_pack.evidence_ids,
            "Usuń typed blocker source-pack bindingu i odśwież packet.",
        )
    if identity is None:
        return _blocker(
            "identity_binding",
            "identity_binding_missing",
            source_pack.evidence_ids,
            "Najpierw zapisz exact delivery identity binding.",
        )
    if (
        identity.binding_id != command.identity_binding_id
        or identity.binding_digest != command.identity_binding_digest
    ):
        return _blocker(
            "identity_binding",
            "identity_binding_digest_mismatch",
            source_pack.evidence_ids,
            "Użyj ID i digestu z tego same persisted identity bindingu.",
        )
    if identity.status == "blocked":
        return _blocker(
            "identity_binding",
            "identity_binding_blocked",
            identity.inventory_evidence_ids,
            "Usuń typed blocker identity bindingu i odśwież packet.",
        )
    if identity.current_work_item_id != command.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            identity.inventory_evidence_ids,
            "Wskaż current work item z exact identity bindingu.",
        )
    if identity.final_disposition != "keep":
        return _blocker(
            "work_item_identity",
            "disposition_not_keep",
            identity.inventory_evidence_ids,
            "Packet produkcyjny twórz wyłącznie dla URL-a z decyzją keep.",
        )
    return (
        _semantic_blocker(command, source_pack, identity, now)
        or _source_fact_blocker(command, source_pack)
        or _evidence_blocker(command, source_pack)
        or _freshness_blocker(command, source_pack, now)
    )


def _semantic_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    now: datetime,
) -> ContentResearchPacketBlocker | None:
    del source_pack, identity, now
    checks: tuple[
        tuple[ResearchPacketBlockerSeam, ResearchPacketBlockerReason, bool, str], ...
    ] = (
        (
            "content_kind",
            "content_kind_ambiguous",
            command.content_kind not in {"service", "editorial", "landing_or_hub"},
            "Ustal exact content kind z inventory i nie używaj ambiguous.",
        ),
        (
            "intent",
            "intent_missing",
            not command.intent,
            "Uzupełnij exact intent dla tego URL-a.",
        ),
        (
            "intent",
            "query_cluster_missing",
            not command.query_cluster,
            "Uzupełnij exact query cluster z aktualnego evidence.",
        ),
        (
            "audience",
            "audience_missing",
            not command.target_audience,
            "Uzupełnij exact target audience.",
        ),
        (
            "audience",
            "buyer_problem_missing",
            not command.buyer_problem,
            "Uzupełnij problem kupującego.",
        ),
        (
            "audience",
            "buyer_trigger_missing",
            not command.buyer_trigger,
            "Uzupełnij trigger/problem moment.",
        ),
        (
            "canonical_owner",
            "canonical_owner_missing",
            not command.canonical_owner,
            "Ustal canonical owner bez fuzzy joinu.",
        ),
        (
            "legal_requirements",
            "legal_requirements_missing",
            not command.legal_source_requirements,
            "Zapisz wymagania źródłowe albo jawne none_identified.",
        ),
        (
            "cta",
            "cta_destination_missing",
            not command.cta_destination,
            "Ustal jedną bezpieczną destynację CTA.",
        ),
    )
    for seam, reason, failed, next_step in checks:
        if failed:
            return _blocker(seam, reason, (), next_step)
    if not _is_safe_path(command.cta_destination):
        return _blocker(
            "cta",
            "cta_destination_invalid",
            (),
            "Użyj wyłącznie bezpiecznej ścieżki CTA na stronie Ekologus.",
        )
    if not command.internal_links:
        return _blocker(
            "internal_links",
            "internal_links_missing",
            (),
            "Dodaj co najmniej jeden exact internal link albo zablokuj packet.",
        )
    if any(link.verification != "exact_verified" for link in command.internal_links):
        return _blocker(
            "internal_links",
            "internal_link_not_verified",
            (),
            "Potwierdź exact destination każdego internal linku.",
        )
    return None


def _source_fact_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
) -> ContentResearchPacketBlocker | None:
    if not command.approved_source_fact_ids:
        return _blocker(
            "source_facts",
            "source_facts_missing",
            source_pack.evidence_ids,
            "Wskaż approved source-fact IDs.",
        )
    if not set(command.approved_source_fact_ids).issubset(set(source_pack.source_fact_ids)):
        return _blocker(
            "source_facts",
            "source_fact_not_bound",
            source_pack.evidence_ids,
            "Użyj wyłącznie fact IDs z exact source-pack whitelisty.",
        )
    facts = {fact.source_id: fact for fact in ekologus_source_facts()}
    if set(command.approved_source_fact_ids) - set(facts):
        return _blocker(
            "source_facts",
            "source_fact_not_registered",
            source_pack.evidence_ids,
            "Odśwież current source-fact registry.",
        )
    if any(
        facts[item].review_status != "approved"
        for item in command.approved_source_fact_ids
    ):
        return _blocker(
            "source_facts",
            "source_fact_not_approved",
            source_pack.evidence_ids,
            "Użyj tylko source facts ze statusem approved.",
        )
    required_blocked_claims = {
        claim
        for item in command.approved_source_fact_ids
        for claim in facts[item].blocked_claims
    }
    if not required_blocked_claims.issubset(set(command.blocked_claims)):
        return _blocker(
            "source_facts",
            "source_fact_not_approved",
            source_pack.evidence_ids,
            "Przenieś wszystkie blocked claims z fact registry do packetu.",
        )
    current_digest = source_fact_registry_digest(ekologus_source_facts())
    if source_pack.source_fact_registry_receipt.registry_digest != current_digest:
        return _blocker(
            "source_facts",
            "source_fact_registry_stale",
            source_pack.evidence_ids,
            "Odśwież source-pack binding względem aktualnego registry.",
        )
    return None


def _evidence_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
) -> ContentResearchPacketBlocker | None:
    if not command.evidence_ids:
        return _blocker(
            "evidence", "evidence_missing", (), "Wskaż evidence IDs z exact source packa."
        )
    allowed = set(source_pack.evidence_ids) | set(
        source_pack.source_fact_registry_receipt.evidence_ids
    )
    if not set(command.evidence_ids).issubset(allowed):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            source_pack.evidence_ids,
            "Usuń evidence spoza source-pack whitelisty.",
        )
    return None


def _freshness_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
    now: datetime,
) -> ContentResearchPacketBlocker | None:
    del source_pack
    if not command.freshness:
        return _blocker(
            "freshness",
            "freshness_missing",
            command.evidence_ids,
            "Dodaj freshness receipt dla każdego source factu.",
        )
    facts = set(command.approved_source_fact_ids)
    freshness_by_source = {item.source_id: item for item in command.freshness}
    if set(freshness_by_source) != facts:
        return _blocker(
            "freshness",
            "freshness_missing",
            command.evidence_ids,
            "Zwiąż freshness dokładnie z każdym approved source factem.",
        )
    for item in command.freshness:
        if not item.evidence_ids:
            return _blocker(
                "freshness",
                "evidence_missing",
                command.evidence_ids,
                "Każdy freshness receipt musi wskazywać evidence ID.",
            )
        if (
            item.status != "fresh"
            or item.checked_at > now
            or now - item.checked_at > _MAX_FRESHNESS_AGE
        ):
            return _blocker(
                "freshness",
                "freshness_stale",
                item.evidence_ids,
                "Odśwież stale/unknown source evidence przed packetem.",
            )
        if not set(item.evidence_ids).issubset(set(command.evidence_ids)):
            return _blocker(
                "freshness",
                "evidence_not_bound",
                item.evidence_ids,
                "Zwiąż freshness tylko z evidence packetu.",
            )
    return None


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
        raise ValueError("Exact packet canonical path does not match public URL.")
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


def _blocker(
    seam: ResearchPacketBlockerSeam,
    reason: ResearchPacketBlockerReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentResearchPacketBlocker:
    return ContentResearchPacketBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids)))[:256],
        next_step_pl=next_step,
    )


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
    "ContentResearchPacketFreshness",
    "ContentResearchPacketInternalLink",
    "ContentResearchPacketReadResult",
    "ContentResearchPacketRecordResult",
    "RESEARCH_PACKET_SCHEMA_VERSION",
    "reconcile_content_research_packet",
    "research_packet_digest",
    "research_packet_input_digest",
    "research_packet_logical_id",
    "source_ids_digest",
]
