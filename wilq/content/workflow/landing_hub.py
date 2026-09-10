"""Exact authorization receipt for landing/hub content kinds."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Self
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    canonical_json_digest,
)
from wilq.security.redaction import redact_mapping

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_~.%-]*$")
_FREE_TEXT_SECRET_VALUE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z0-9+/=_-]{20,}(?![A-Za-z0-9])"
)
_SAFE_OPERATOR = re.compile(r"^[\w .-]+$", re.UNICODE)
_UNSAFE_OPERATOR = re.compile(
    r"(?:basic|bearer|token|password|secret|credential|api[_ -]?key)",
    re.IGNORECASE,
)

LANDING_HUB_AUTHORIZATION_SCHEMA: Literal[
    "wilq_content_landing_hub_authorization_v1"
] = "wilq_content_landing_hub_authorization_v1"

LandingHubAuthorizationBlockerReason = Literal[
    "classification_missing",
    "classification_stale",
    "classification_work_item_mismatch",
    "classification_identity_mismatch",
    "classification_decision_blocked",
    "classification_decision_unsupported",
    "content_kind_mismatch",
    "inventory_missing",
    "inventory_untrusted",
    "canonical_identity_mismatch",
    "intent_missing",
    "source_facts_missing",
    "source_fact_not_registered",
    "source_fact_not_approved",
    "source_fact_registry_stale",
    "evidence_missing",
    "evidence_not_bound",
    "blocked_claims_missing",
    "cta_missing",
    "cta_invalid",
    "duplicate_gate_missing",
    "authorization_digest_mismatch",
    "authorization_conflict",
    "authorization_stale",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _safe_text(value: str, label: str, *, allow_blank: bool = False) -> str:
    normalized = value.strip()
    if not allow_blank and not normalized:
        raise ValueError(f"{label} must be non-blank.")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError(f"{label} must not contain control characters.")
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


def _is_safe_path(value: str) -> bool:
    normalized = value.strip()
    if not _SAFE_PATH.fullmatch(normalized) or normalized.startswith("//"):
        return False
    decoded = normalized
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if "%" in decoded or not _SAFE_PATH.fullmatch(decoded) or decoded.startswith("//"):
        return False
    return not any(part in {".", ".."} for part in decoded.split("/"))


class ContentLandingHubAuthorizationBlocker(_FrozenModel):
    seam: Literal[
        "classification",
        "inventory",
        "content_kind",
        "source_facts",
        "evidence",
        "cta",
        "duplicate_gate",
        "authorization",
    ]
    reason: LandingHubAuthorizationBlockerReason
    next_step_pl: str = Field(min_length=1, max_length=600)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)

    @field_validator("next_step_pl")
    @classmethod
    def normalize_next_step(cls, value: str) -> str:
        return _safe_text(value, "Landing/hub blocker next step")

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Landing/hub blocker evidence IDs") if value else value


class ContentLandingHubAuthorizationRequest(_FrozenModel):
    """Caller-owned compact landing brief; no page body or raw source is accepted."""

    expected_classification_run_id: str = Field(
        min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER
    )
    expected_classification_run_digest: str = Field(pattern=_HEX64)
    expected_decision_set_digest: str = Field(pattern=_HEX64)
    expected_source_packet_row_digest: str = Field(pattern=_HEX64)
    intent: str = Field(default="", max_length=600)
    approved_source_fact_ids: tuple[str, ...] = Field(default=(), max_length=256)
    blocked_claims: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    cta_destinations: tuple[str, ...] = Field(default=(), max_length=8)
    duplicate_gate: Literal["checked", "risk_found", "missing"] = "missing"
    duplicate_gate_evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    duplicate_gate_digest: str = Field(
        default="", max_length=64, pattern=r"^(?:|[0-9a-f]{64})$"
    )
    authorized_by: str = Field(min_length=1, max_length=160)

    @field_validator("intent")
    @classmethod
    def normalize_intent(cls, value: str) -> str:
        return _safe_text(value, "Landing/hub intent", allow_blank=True)

    @field_validator("approved_source_fact_ids", "evidence_ids")
    @classmethod
    def normalize_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Landing/hub source IDs") if value else value

    @field_validator("blocked_claims")
    @classmethod
    def normalize_claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_safe_text(item, "Landing/hub blocked claim") for item in value)
        if any(len(item) > 600 for item in normalized):
            raise ValueError("Landing/hub blocked claims must be at most 600 characters.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Landing/hub blocked claims must be unique.")
        return tuple(sorted(normalized))

    @field_validator("duplicate_gate_evidence_ids")
    @classmethod
    def normalize_duplicate_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Landing/hub duplicate evidence IDs") if value else value

    @field_validator("cta_destinations")
    @classmethod
    def normalize_ctas(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(len(item) > 2048 or not _is_safe_path(item) for item in normalized):
            raise ValueError("Landing/hub CTA destinations must be safe local paths.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Landing/hub CTA destinations must be unique.")
        return normalized

    @field_validator("authorized_by")
    @classmethod
    def normalize_authorized_by(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or not _SAFE_OPERATOR.fullmatch(normalized)
            or _UNSAFE_OPERATOR.search(normalized)
            or _FREE_TEXT_SECRET_VALUE.fullmatch(normalized)
        ):
            raise ValueError("Landing/hub authorization requires a safe operator identity.")
        return normalized


class ContentLandingHubAuthorization(_FrozenModel):
    """Immutable receipt authorizing only one exact landing/hub identity."""

    schema_version: Literal["wilq_content_landing_hub_authorization_v1"] = (
        LANDING_HUB_AUTHORIZATION_SCHEMA
    )
    authorization_id: str = Field(min_length=1, max_length=280)
    authorization_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    classification_run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    classification_run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    source_packet_row_digest: str = Field(pattern=_HEX64)
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    content_kind: Literal["landing_or_hub"] = "landing_or_hub"
    wordpress_content_type: str = Field(min_length=1, max_length=80)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    inventory_evidence_digest: str = Field(pattern=_HEX64)
    intent: str = Field(min_length=1, max_length=600)
    approved_source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    blocked_claims: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    source_fact_registry_digest: str = Field(pattern=_HEX64)
    cta_destinations: tuple[str, ...] = Field(min_length=1, max_length=8)
    duplicate_gate: Literal["checked"] = "checked"
    duplicate_gate_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    duplicate_gate_digest: str = Field(pattern=_HEX64)
    input_digest: str = Field(pattern=_HEX64)
    authorized_by: str = Field(min_length=1, max_length=160)
    authorized_at: datetime

    @field_validator("authorized_at")
    @classmethod
    def require_aware_authorized_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Landing/hub authorization time must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("inventory_evidence_ids", "approved_source_fact_ids", "evidence_ids")
    @classmethod
    def require_sorted_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _safe_ids(value, "Landing/hub authorization IDs")

    @field_validator("blocked_claims")
    @classmethod
    def require_canonical_claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(item) > 600 for item in value):
            raise ValueError("Landing/hub authorization blocked claims are too long.")
        if len(value) != len(set(value)):
            raise ValueError("Landing/hub authorization blocked claims must be unique.")
        return tuple(sorted(value))

    @field_validator("cta_destinations")
    @classmethod
    def require_safe_ctas(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if (
            any(len(item) > 2048 or not _is_safe_path(item) for item in normalized)
            or len(normalized) != len(set(normalized))
        ):
            raise ValueError("Landing/hub authorization CTA destinations are unsafe or duplicate.")
        return normalized

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        if self.inventory_evidence_digest != inventory_evidence_digest(self.inventory_evidence_ids):
            raise ValueError("Landing/hub inventory evidence digest does not match IDs.")
        if (
            not set(self.duplicate_gate_evidence_ids).issubset(set(self.evidence_ids))
            or self.duplicate_gate_digest
            != duplicate_gate_receipt_digest(self.intent, self.duplicate_gate_evidence_ids)
        ):
            raise ValueError("Landing/hub duplicate gate receipt does not match evidence.")
        digest = landing_hub_authorization_digest(self)
        if self.authorization_digest != digest:
            raise ValueError("Landing/hub authorization digest does not match its receipt.")
        if self.authorization_id != f"content_landing_hub_authorization_{digest[:24]}":
            raise ValueError("Landing/hub authorization ID does not match its digest.")
        if not _is_safe_path(self.canonical_path):
            raise ValueError("Landing/hub canonical path must be safe.")
        return self


class ContentLandingHubAuthorizationRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    authorization: ContentLandingHubAuthorization


class ContentLandingHubAuthorizationPreview(_FrozenModel):
    status: Literal["ready_to_authorize", "authorized", "blocked"]
    work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    authorization: ContentLandingHubAuthorization | None = None
    classification_run_id: str | None = None
    classification_run_digest: str | None = None
    canonical_path: str | None = None
    public_url: str | None = None
    blockers: tuple[ContentLandingHubAuthorizationBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_preview_state(self) -> Self:
        if self.status == "authorized" and self.authorization is None:
            raise ValueError("Authorized landing/hub preview requires its receipt.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked landing/hub preview requires a blocker.")
        if self.status == "ready_to_authorize" and self.authorization is not None:
            raise ValueError("Ready landing/hub preview cannot carry an authorization.")
        return self


def inventory_evidence_digest(evidence_ids: tuple[str, ...]) -> str:
    return canonical_json_digest({"inventory_evidence_ids": evidence_ids})


def landing_hub_input_digest(
    *,
    work_item_id: str,
    classification_run_id: str,
    classification_run_digest: str,
    decision_set_digest: str,
    source_packet_row_digest: str,
    canonical_path: str,
    public_url: str,
    inventory_evidence_ids: tuple[str, ...],
    intent: str,
    approved_source_fact_ids: tuple[str, ...],
    blocked_claims: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    source_fact_registry_digest: str,
    cta_destinations: tuple[str, ...],
    duplicate_gate: Literal["checked"],
    duplicate_gate_evidence_ids: tuple[str, ...],
    duplicate_gate_digest: str,
) -> str:
    return canonical_json_digest(
        {
            "work_item_id": work_item_id,
            "classification_run_id": classification_run_id,
            "classification_run_digest": classification_run_digest,
            "decision_set_digest": decision_set_digest,
            "source_packet_row_digest": source_packet_row_digest,
            "canonical_path": canonical_path,
            "public_url": public_url,
            "inventory_evidence_ids": inventory_evidence_ids,
            "intent": intent,
            "approved_source_fact_ids": approved_source_fact_ids,
            "blocked_claims": blocked_claims,
            "evidence_ids": evidence_ids,
            "source_fact_registry_digest": source_fact_registry_digest,
            "cta_destinations": cta_destinations,
            "duplicate_gate": duplicate_gate,
            "duplicate_gate_evidence_ids": duplicate_gate_evidence_ids,
            "duplicate_gate_digest": duplicate_gate_digest,
        }
    )


def landing_hub_authorization_digest(
    value: ContentLandingHubAuthorization | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for name in ("authorization_id", "authorization_digest", "authorized_at"):
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


def build_landing_hub_authorization(
    *,
    work_item_id: str,
    classification: ContentProductionClassificationRun,
    row: ContentProductionClassificationRow,
    inventory_binding: ContentKindInventoryBinding,
    request: ContentLandingHubAuthorizationRequest,
    authorized_at: datetime,
) -> ContentLandingHubAuthorization:
    request = redacted_landing_hub_request(request)
    blocker = landing_hub_authorization_blocker(
        work_item_id=work_item_id,
        classification=classification,
        row=row,
        inventory_binding=inventory_binding,
        request=request,
    )
    if blocker is not None:
        raise ValueError(blocker.reason)
    registry_digest = canonical_source_fact_registry_digest()
    input_digest = landing_hub_input_digest(
        work_item_id=work_item_id,
        classification_run_id=classification.run_id,
        classification_run_digest=classification.run_digest,
        decision_set_digest=classification.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        canonical_path=inventory_binding.canonical_path,
        public_url=inventory_binding.public_url,
        inventory_evidence_ids=tuple(sorted(inventory_binding.inventory_evidence_ids)),
        intent=request.intent,
        approved_source_fact_ids=request.approved_source_fact_ids,
        blocked_claims=request.blocked_claims,
        evidence_ids=request.evidence_ids,
        source_fact_registry_digest=registry_digest,
        cta_destinations=request.cta_destinations,
        duplicate_gate="checked",
        duplicate_gate_evidence_ids=request.duplicate_gate_evidence_ids,
        duplicate_gate_digest=request.duplicate_gate_digest,
    )
    payload: dict[str, object] = {
        "schema_version": LANDING_HUB_AUTHORIZATION_SCHEMA,
        "work_item_id": work_item_id,
        "classification_run_id": classification.run_id,
        "classification_run_digest": classification.run_digest,
        "decision_set_digest": classification.input.decision_set_digest,
        "source_packet_row_digest": row.source_packet_row_digest,
        "canonical_path": inventory_binding.canonical_path,
        "public_url": inventory_binding.public_url,
        "content_kind": "landing_or_hub",
        "wordpress_content_type": inventory_binding.wordpress_content_type,
        "inventory_evidence_ids": tuple(sorted(inventory_binding.inventory_evidence_ids)),
        "inventory_evidence_digest": inventory_evidence_digest(
            tuple(sorted(inventory_binding.inventory_evidence_ids))
        ),
        "intent": request.intent,
        "approved_source_fact_ids": request.approved_source_fact_ids,
        "blocked_claims": request.blocked_claims,
        "evidence_ids": request.evidence_ids,
        "source_fact_registry_digest": registry_digest,
        "cta_destinations": request.cta_destinations,
        "duplicate_gate": "checked",
        "duplicate_gate_evidence_ids": request.duplicate_gate_evidence_ids,
        "duplicate_gate_digest": request.duplicate_gate_digest,
        "input_digest": input_digest,
        "authorized_by": request.authorized_by,
        "authorized_at": authorized_at.astimezone(UTC).isoformat(),
    }
    digest = landing_hub_authorization_digest(payload)
    return ContentLandingHubAuthorization.model_validate(
        {
            "authorization_id": f"content_landing_hub_authorization_{digest[:24]}",
            "authorization_digest": digest,
            **payload,
        }
    )


def landing_hub_authorization_blocker(
    *,
    work_item_id: str,
    classification: ContentProductionClassificationRun | None,
    row: ContentProductionClassificationRow | None,
    inventory_binding: ContentKindInventoryBinding | None,
    request: ContentLandingHubAuthorizationRequest | None = None,
) -> ContentLandingHubAuthorizationBlocker | None:
    evidence = () if inventory_binding is None else inventory_binding.inventory_evidence_ids
    if classification is None or row is None:
        return _blocker(
            "classification",
            "classification_missing",
            evidence,
            "Najpierw zapisz bieżącą klasyfikację URL-a.",
        )
    if request is not None and (
        request.expected_classification_run_id != classification.run_id
        or request.expected_classification_run_digest != classification.run_digest
        or request.expected_decision_set_digest != classification.input.decision_set_digest
        or request.expected_source_packet_row_digest != row.source_packet_row_digest
    ):
        return _blocker(
            "classification",
            "classification_identity_mismatch",
            evidence,
            "Odśwież landing/hub preview i użyj wszystkich aktualnych digestów klasyfikacji.",
        )
    if row.current_work_item_id != work_item_id:
        return _blocker(
            "classification",
            "classification_work_item_mismatch",
            evidence,
            "Użyj exact current work itemu z klasyfikacji.",
        )
    if str(row.decision) == "blocked" or any(
        blocker.blocks_initial_generation is True for blocker in row.blockers
    ):
        return _blocker(
            "classification",
            "classification_decision_blocked",
            evidence,
            "Usuń blokady klasyfikacji i dopiero potem autoryzuj landing/hub.",
        )
    if row.decision not in {"refresh", "write"}:
        return _blocker(
            "classification",
            "classification_decision_unsupported",
            evidence,
            "Landing/hub wymaga bieżącej decyzji refresh albo write.",
        )
    if classification.freshness.requires_refresh:
        return _blocker(
            "classification",
            "classification_stale",
            evidence,
            "Odśwież źródła i klasyfikację przed autoryzacją landing/hub.",
        )
    if inventory_binding is None:
        return _blocker(
            "inventory",
            "inventory_missing",
            (),
            "Odczytaj exact WordPress inventory dla landing/hub.",
        )
    if not inventory_binding.trusted:
        return _blocker(
            "inventory",
            "inventory_untrusted",
            evidence,
            "Potwierdź bieżące WordPress evidence dla tego landing/hub.",
        )
    if (
        inventory_binding.work_item_id != work_item_id
        or inventory_binding.canonical_path != row.canonical_path
        or inventory_binding.public_url != row.public_url
    ):
        return _blocker(
            "classification",
            "canonical_identity_mismatch",
            evidence,
            "Zwiąż inventory, klasyfikację i URL bez fuzzy joinu.",
        )
    if inventory_binding.content_kind != "landing_or_hub":
        return _blocker(
            "content_kind",
            "content_kind_mismatch",
            evidence,
            "Ten URL nie jest landing_or_hub; nie używaj ścieżki landing/hub.",
        )
    if request is None:
        return None
    return _landing_hub_request_blocker(request, inventory_binding, evidence)


def _landing_hub_request_blocker(
    request: ContentLandingHubAuthorizationRequest,
    inventory_binding: ContentKindInventoryBinding,
    evidence: tuple[str, ...],
) -> ContentLandingHubAuthorizationBlocker | None:
    facts = {fact.source_id: fact for fact in ekologus_source_facts()}
    if not request.intent:
        return _blocker(
            "content_kind", "intent_missing", evidence, "Uzupełnij exact intent landing/hub."
        )
    if not request.approved_source_fact_ids:
        return _blocker(
            "source_facts",
            "source_facts_missing",
            evidence,
            "Wskaż approved source facts dla landing/hub.",
        )
    if set(request.approved_source_fact_ids) - set(facts):
        return _blocker(
            "source_facts", "source_fact_not_registered", evidence, "Odśwież source-fact registry."
        )
    if any(facts[item].review_status != "approved" for item in request.approved_source_fact_ids):
        return _blocker(
            "source_facts",
            "source_fact_not_approved",
            evidence,
            "Użyj wyłącznie approved source facts.",
        )
    required_claims = {
        claim for item in request.approved_source_fact_ids for claim in facts[item].blocked_claims
    }
    if not required_claims.issubset(set(request.blocked_claims)):
        return _blocker(
            "source_facts",
            "blocked_claims_missing",
            evidence,
            "Przenieś blocked claims z registry do authorization.",
        )
    if not request.evidence_ids:
        return _blocker(
            "evidence",
            "evidence_missing",
            evidence,
            "Wskaż evidence IDs z inventory i source facts.",
        )
    allowed_evidence = set(inventory_binding.inventory_evidence_ids) | {
        evidence_id
        for item in request.approved_source_fact_ids
        for evidence_id in facts[item].evidence_ids
    }
    if set(request.evidence_ids) - allowed_evidence:
        return _blocker(
            "evidence",
            "evidence_not_bound",
            evidence,
            "Usuń evidence spoza exact landing/hub contextu.",
        )
    if not request.cta_destinations:
        return _blocker(
            "cta", "cta_missing", evidence, "Ustal co najmniej jedną bezpieczną destynację CTA."
        )
    if any(not _is_safe_path(item) for item in request.cta_destinations):
        return _blocker(
            "cta", "cta_invalid", evidence, "Użyj wyłącznie lokalnych, bezpiecznych ścieżek CTA."
        )
    if request.duplicate_gate != "checked":
        return _blocker(
            "duplicate_gate",
            "duplicate_gate_missing",
            evidence,
            "Zamknij duplicate/intent gate przed autoryzacją landing/hub.",
        )
    if (
        not request.duplicate_gate_evidence_ids
        or not set(request.duplicate_gate_evidence_ids).issubset(set(request.evidence_ids))
        or request.duplicate_gate_digest
        != duplicate_gate_receipt_digest(
            request.intent,
            request.duplicate_gate_evidence_ids,
        )
    ):
        return _blocker(
            "duplicate_gate",
            "duplicate_gate_missing",
            evidence,
            "Dołącz evidence i digest exact duplicate/intent checku.",
        )
    return None


def duplicate_gate_receipt_digest(intent: str, evidence_ids: tuple[str, ...]) -> str:
    return canonical_json_digest(
        {"gate": "duplicate_intent", "intent": intent, "evidence_ids": evidence_ids}
    )


def redacted_landing_hub_request(
    request: ContentLandingHubAuthorizationRequest,
) -> ContentLandingHubAuthorizationRequest:
    payload = redact_mapping(request.model_dump(mode="json"))
    payload["intent"] = redact_landing_hub_free_text(str(payload["intent"]))
    payload["blocked_claims"] = [
        redact_landing_hub_free_text(str(claim)) for claim in payload["blocked_claims"]
    ]
    return ContentLandingHubAuthorizationRequest.model_validate_json(
        json.dumps(payload, ensure_ascii=False), strict=True
    )


def redact_landing_hub_free_text(value: str) -> str:
    return _FREE_TEXT_SECRET_VALUE.sub(_redact_free_text_token, value)


def _redact_free_text_token(match: re.Match[str]) -> str:
    token = match.group(0)
    if len(token) >= 32 or any(char.isdigit() or char in "+/=_-" for char in token):
        return "[REDACTED]"
    if len(token) >= 20 and all(char.casefold() in "abcdef0123456789" for char in token):
        return "[REDACTED]"
    return token


def canonical_source_fact_registry_digest() -> str:
    facts = ekologus_source_facts()
    return canonical_json_digest(
        {
            "registry_id": "ekologus_source_fact_registry",
            "fact_count": len(facts),
            "facts": [fact.model_dump(mode="json") for fact in facts],
        }
    )


def _blocker(
    seam: Literal[
        "classification",
        "inventory",
        "content_kind",
        "source_facts",
        "evidence",
        "cta",
        "duplicate_gate",
        "authorization",
    ],
    reason: LandingHubAuthorizationBlockerReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentLandingHubAuthorizationBlocker:
    return ContentLandingHubAuthorizationBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids)))[:256],
        next_step_pl=next_step,
    )


__all__ = [
    "ContentLandingHubAuthorization",
    "ContentLandingHubAuthorizationBlocker",
    "ContentLandingHubAuthorizationPreview",
    "ContentLandingHubAuthorizationRecordResult",
    "ContentLandingHubAuthorizationRequest",
    "LANDING_HUB_AUTHORIZATION_SCHEMA",
    "build_landing_hub_authorization",
    "canonical_source_fact_registry_digest",
    "inventory_evidence_digest",
    "landing_hub_authorization_blocker",
    "landing_hub_authorization_digest",
    "landing_hub_input_digest",
    "redact_landing_hub_free_text",
    "redacted_landing_hub_request",
]
