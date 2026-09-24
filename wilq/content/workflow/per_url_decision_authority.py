"""Stable semantic currentness and append-only authority observations per URL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.current_page_identity_v3 import CurrentPageIdentityV3Response
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.schemas.content import ContentFreshnessAssessment

_HEX64 = r"^[0-9a-f]{64}$"
PerUrlContentKind = Literal["editorial", "service", "landing_or_hub"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentPerUrlPolicyFact(_FrozenModel):
    """One approved page policy fact; raw source text stays in its source authority."""

    source_fact_id: str = Field(min_length=1, max_length=240)
    semantic_digest: str = Field(pattern=_HEX64)
    requirement_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_canonical_bindings(self) -> Self:
        if self.requirement_ids != tuple(sorted(set(self.requirement_ids))):
            raise ValueError("Per-URL policy fact requirement IDs must be sorted and unique.")
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))) or any(
            not item.strip() for item in self.evidence_ids
        ):
            raise ValueError("Per-URL policy fact evidence IDs must be sorted and unique.")
        return self


class ContentPerUrlDecisionPolicyFacts(_FrozenModel):
    """Exact, page-bound policy inputs with freshness and evidence kept separate."""

    schema_version: Literal["wilq_per_url_decision_policy_facts_v1"] = (
        "wilq_per_url_decision_policy_facts_v1"
    )
    current_work_item_id: str = Field(min_length=1, max_length=240)
    public_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    policy_id: str = Field(min_length=1, max_length=160)
    policy_version: str = Field(min_length=1, max_length=160)
    content_kind: PerUrlContentKind
    service_card_id: str | None = Field(default=None, max_length=240)
    regulatory_profile_id: str | None = Field(default=None, max_length=160)
    regulatory_profile_version: str | None = Field(default=None, max_length=160)
    source_facts: tuple[ContentPerUrlPolicyFact, ...] = ()
    requirement_ids: tuple[str, ...] = ()
    cta_policy_digest: str | None = Field(default=None, pattern=_HEX64)
    freshness_assessment: ContentFreshnessAssessment
    freshness_connector_ids: tuple[str, ...] = Field(min_length=1)
    freshness_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_policy_scope(self) -> Self:
        if not content_is_safe_public_url(self.public_url):
            raise ValueError("Per-URL policy requires a safe public URL.")
        if content_normalized_path(self.public_url) != self.canonical_path:
            raise ValueError("Per-URL policy URL/path identity does not match.")
        if (
            self.freshness_assessment.checked_at.tzinfo is None
            or self.freshness_assessment.checked_at.utcoffset() is None
        ):
            raise ValueError("Per-URL freshness assessment time must be timezone-aware.")
        if (self.regulatory_profile_id is None) != (
            self.regulatory_profile_version is None
        ):
            raise ValueError("Per-URL regulatory profile identity must be complete.")
        if self.content_kind == "service" and not self.service_card_id:
            raise ValueError("Service policy requires its exact service card.")
        if self.content_kind != "service" and self.service_card_id is not None:
            raise ValueError("Only service policy may carry a service card.")
        fact_ids = tuple(fact.source_fact_id for fact in self.source_facts)
        if fact_ids != tuple(sorted(set(fact_ids))):
            raise ValueError("Per-URL policy facts must be sorted and unique.")
        if self.requirement_ids != tuple(sorted(set(self.requirement_ids))) or any(
            not item.strip() for item in self.requirement_ids
        ):
            raise ValueError("Per-URL requirement IDs must be sorted and unique.")
        fact_requirements = {
            requirement_id
            for fact in self.source_facts
            for requirement_id in fact.requirement_ids
        }
        if not set(self.requirement_ids).issubset(fact_requirements):
            raise ValueError("Per-URL policy requirements lack exact fact lineage.")
        if self.freshness_evidence_ids != tuple(sorted(set(self.freshness_evidence_ids))) or any(
            not item.strip() for item in self.freshness_evidence_ids
        ):
            raise ValueError("Per-URL freshness evidence IDs must be sorted and unique.")
        if self.freshness_connector_ids != tuple(sorted(set(self.freshness_connector_ids))) or any(
            not item.strip() for item in self.freshness_connector_ids
        ):
            raise ValueError("Per-URL freshness connector IDs must be sorted and unique.")
        return self

    def semantic_payload(self) -> dict[str, object]:
        """Exclude rotating evidence and read times from the page-policy identity."""

        return {
            "schema_version": self.schema_version,
            "current_work_item_id": self.current_work_item_id,
            "public_url": self.public_url,
            "canonical_path": self.canonical_path,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "content_kind": self.content_kind,
            "service_card_id": self.service_card_id,
            "regulatory_profile_id": self.regulatory_profile_id,
            "regulatory_profile_version": self.regulatory_profile_version,
            "source_facts": [
                {
                    "source_fact_id": fact.source_fact_id,
                    "semantic_digest": fact.semantic_digest,
                    "requirement_ids": list(fact.requirement_ids),
                }
                for fact in self.source_facts
            ],
            "requirement_ids": list(self.requirement_ids),
            "cta_policy_digest": self.cta_policy_digest,
        }

    @property
    def semantic_digest(self) -> str:
        return canonical_json_digest(self.semantic_payload())

    @property
    def evidence_digest(self) -> str:
        return canonical_json_digest(
            {
                "schema_version": "wilq_per_url_decision_policy_evidence_v1",
                "semantic_digest": self.semantic_digest,
                "source_fact_evidence_ids": [
                    {
                        "source_fact_id": fact.source_fact_id,
                        "evidence_ids": list(fact.evidence_ids),
                    }
                    for fact in self.source_facts
                ],
                "freshness": _policy_freshness_evidence_payload(self),
                "freshness_evidence_ids": list(self.freshness_evidence_ids),
            }
        )


class ContentPerUrlDecisionAuthorityBlocked(ValueError):
    """One exact input or freshness gate prevents an authority observation."""

    def __init__(
        self,
        code: str,
        owner: str,
        evidence_ids: tuple[str, ...],
        safe_next_step: str,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.owner = owner
        self.evidence_ids = evidence_ids
        self.safe_next_step = safe_next_step


class ContentPerUrlDecisionObservation(_FrozenModel):
    """Append-only observation; source_wave_id is provenance, never identity."""

    schema_version: Literal["wilq_per_url_decision_observation_v1"] = (
        "wilq_per_url_decision_observation_v1"
    )
    observation_id: str = Field(min_length=1, max_length=240)
    observation_digest: str = Field(pattern=_HEX64)
    semantic_row_digest: str = Field(pattern=_HEX64)
    evidence_digest: str = Field(pattern=_HEX64)
    source_wave_id: str | None = Field(default=None, max_length=240)
    page_identity: CurrentPageIdentityV3Response
    policy_facts: ContentPerUrlDecisionPolicyFacts
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_aware_observation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Per-URL observation time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_exact_self_authenticating_observation(self) -> Self:
        identity = self.page_identity
        policy = self.policy_facts
        if identity.status != "exact_current":
            raise ValueError("Per-URL authority requires exact current page identity.")
        if _policy_freshness_blocker(policy, self.observed_at) is not None:
            raise ValueError("Per-URL authority requires fresh page policy evidence.")
        if (
            policy.current_work_item_id != identity.work_item_id
            or policy.public_url != identity.page_url
            or policy.canonical_path != identity.canonical_path
        ):
            raise ValueError("Per-URL policy facts do not match the exact page identity.")
        if self.semantic_row_digest != _semantic_row_digest(identity, policy):
            raise ValueError("Per-URL semantic row digest does not match its exact inputs.")
        if self.evidence_digest != _observation_evidence_digest(identity, policy):
            raise ValueError("Per-URL evidence digest does not match its current inputs.")
        digest = per_url_decision_observation_digest(self)
        if self.observation_digest != digest or self.observation_id != (
            f"content_per_url_decision_observation_{digest[:24]}"
        ):
            raise ValueError("Per-URL observation ID/digest does not match.")
        return self


class ContentPerUrlCurrentnessProjection(_FrozenModel):
    """Compare a stored row with one separately refreshed exact per-URL observation."""

    status: Literal["current", "superseded", "blocked"]
    canonical_path: str = Field(min_length=1, max_length=2048)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    observation_id: str = Field(min_length=1, max_length=240)
    semantic_row_digest: str = Field(pattern=_HEX64)
    current_observation_id: str | None = Field(default=None, max_length=240)
    current_semantic_row_digest: str | None = Field(default=None, pattern=_HEX64)
    blocker_code: str | None = None
    blocker_owner: Literal["WILQ content workflow"] | None = None
    safe_next_step: str

    @model_validator(mode="after")
    def require_projection_state(self) -> Self:
        if self.status == "blocked":
            if (
                self.current_observation_id is not None
                or self.current_semantic_row_digest is not None
                or self.blocker_code is None
                or self.blocker_owner != "WILQ content workflow"
            ):
                raise ValueError("Blocked per-URL currentness requires one typed blocker.")
            return self
        if (
            self.current_observation_id is None
            or self.current_semantic_row_digest is None
            or self.blocker_code is not None
            or self.blocker_owner is not None
        ):
            raise ValueError("Current per-URL authority projection is incomplete.")
        expected_status = (
            "current"
            if self.semantic_row_digest == self.current_semantic_row_digest
            else "superseded"
        )
        if self.status != expected_status:
            raise ValueError("Per-URL authority status does not match semantic currentness.")
        return self


def build_content_per_url_decision_observation(
    page_identity: CurrentPageIdentityV3Response,
    policy_facts: ContentPerUrlDecisionPolicyFacts,
    *,
    observed_at: datetime,
    source_wave_id: str | None = None,
) -> ContentPerUrlDecisionObservation:
    """Build one stable semantic row key with separately bound read evidence."""

    if page_identity.status != "exact_current":
        raise ContentPerUrlDecisionAuthorityBlocked(
            page_identity.blocker_code or "current_page_identity_blocked",
            page_identity.blocker_owner or "WILQ content workflow",
            tuple(
                sorted(
                    set(page_identity.current_evidence_ids)
                    | set(page_identity.catalog_evidence_ids)
                )
            ),
            page_identity.safe_next_step,
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Per-URL observation time must be timezone-aware.")
    observed_at = observed_at.astimezone(UTC)
    freshness_blocker = _policy_freshness_blocker(policy_facts, observed_at)
    if freshness_blocker is not None:
        raise ContentPerUrlDecisionAuthorityBlocked(
            freshness_blocker[0],
            "WILQ content workflow",
            policy_facts.freshness_evidence_ids,
            freshness_blocker[1],
        )
    semantic_digest = _semantic_row_digest(page_identity, policy_facts)
    evidence_digest = _observation_evidence_digest(page_identity, policy_facts)
    provisional = ContentPerUrlDecisionObservation.model_construct(
        schema_version="wilq_per_url_decision_observation_v1",
        observation_id="",
        observation_digest="0" * 64,
        semantic_row_digest=semantic_digest,
        evidence_digest=evidence_digest,
        source_wave_id=source_wave_id,
        page_identity=page_identity,
        policy_facts=policy_facts,
        observed_at=observed_at,
    )
    digest = per_url_decision_observation_digest(provisional)
    return ContentPerUrlDecisionObservation.model_validate(
        provisional.model_dump(mode="json")
        | {
            "observation_id": f"content_per_url_decision_observation_{digest[:24]}",
            "observation_digest": digest,
        }
    )


def per_url_decision_observation_digest(
    value: ContentPerUrlDecisionObservation | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("observation_id", None)
    payload.pop("observation_digest", None)
    return canonical_json_digest(payload)


def project_content_per_url_currentness(
    observation: ContentPerUrlDecisionObservation,
    current_observation: ContentPerUrlDecisionObservation | None,
) -> ContentPerUrlCurrentnessProjection:
    """Use fresh current inputs, never a batch-level decision-set digest."""

    if current_observation is None:
        return ContentPerUrlCurrentnessProjection(
            status="blocked",
            canonical_path=observation.policy_facts.canonical_path,
            current_work_item_id=observation.policy_facts.current_work_item_id,
            observation_id=observation.observation_id,
            semantic_row_digest=observation.semantic_row_digest,
            blocker_code="per_url_current_material_unavailable",
            blocker_owner="WILQ content workflow",
            safe_next_step="Odczytaj ponownie świeży semantic row dokładnego URL-a.",
        )
    same_exact_url_scope = (
        current_observation.policy_facts.canonical_path
        == observation.policy_facts.canonical_path
        or current_observation.policy_facts.current_work_item_id
        == observation.policy_facts.current_work_item_id
    )
    if not same_exact_url_scope:
        raise ValueError("Per-URL currentness projection crossed unrelated URL rows.")
    same_semantic_row = (
        observation.semantic_row_digest == current_observation.semantic_row_digest
    )
    return ContentPerUrlCurrentnessProjection(
        status="current" if same_semantic_row else "superseded",
        canonical_path=observation.policy_facts.canonical_path,
        current_work_item_id=observation.policy_facts.current_work_item_id,
        observation_id=observation.observation_id,
        semantic_row_digest=observation.semantic_row_digest,
        current_observation_id=current_observation.observation_id,
        current_semantic_row_digest=current_observation.semantic_row_digest,
        safe_next_step=(
            "Użyj aktualnego semantic row tego URL-a."
            if same_semantic_row
            else "Przygotuj nową decyzję dla zmienionego semantic row tego URL-a."
        ),
    )


def _policy_freshness_blocker(
    policy_facts: ContentPerUrlDecisionPolicyFacts,
    observed_at: datetime,
) -> tuple[str, str] | None:
    assessment = policy_facts.freshness_assessment
    checked_at = assessment.checked_at
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        return (
            "per_url_freshness_assessment_invalid",
            "Odczytaj ponownie freshness wymaganych źródeł.",
        )
    checked_at = checked_at.astimezone(UTC)
    if checked_at > observed_at:
        return (
            "per_url_freshness_assessment_from_future",
            "Odczytaj ponownie freshness wymaganych źródeł.",
        )
    if assessment.stale_after_hours <= 0 or (
        observed_at - checked_at > timedelta(hours=assessment.stale_after_hours)
    ):
        return "per_url_freshness_assessment_expired", "Odśwież freshness wymaganych źródeł URL-a."
    required = set(policy_facts.freshness_connector_ids)
    if not required.issubset(assessment.connector_covered_windows):
        return (
            "per_url_required_connector_window_missing",
            "Odczytaj freshness każdego wymaganego źródła.",
        )
    blocked = (
        set(assessment.missing_connector_ids)
        | set(assessment.blocked_connector_ids)
        | set(assessment.stale_connector_ids)
    )
    if required & blocked:
        return "per_url_required_connector_freshness_blocked", "Odśwież wymagane źródła URL-a."
    return None


def per_url_decision_freshness_blocker(
    policy_facts: ContentPerUrlDecisionPolicyFacts,
    checked_at: datetime,
) -> tuple[str, str] | None:
    """Check the stored freshness assessment against the authority read time."""

    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        return (
            "per_url_freshness_check_time_invalid",
            "Odczytaj ponownie freshness wymaganych źródeł.",
        )
    return _policy_freshness_blocker(policy_facts, checked_at.astimezone(UTC))


def _policy_freshness_evidence_payload(
    policy_facts: ContentPerUrlDecisionPolicyFacts,
) -> dict[str, object]:
    assessment = policy_facts.freshness_assessment
    connectors: dict[str, object] = {}
    for connector_id in policy_facts.freshness_connector_ids:
        window = assessment.connector_covered_windows.get(connector_id)
        if window is None:
            continue
        settlement = assessment.connector_settlement_states.get(connector_id)
        quality = assessment.connector_quality_states.get(connector_id)
        connectors[connector_id] = {
            "window": window.model_dump(mode="json"),
            "refresh_run_id": assessment.connector_refresh_run_ids.get(connector_id),
            "settlement_state": None if settlement is None else str(settlement),
            "quality_state": None if quality is None else str(quality),
        }
    return {
        "checked_at": assessment.checked_at.astimezone(UTC).isoformat(),
        "stale_after_hours": assessment.stale_after_hours,
        "required_connectors": connectors,
    }


def _semantic_row_digest(
    identity: CurrentPageIdentityV3Response,
    policy_facts: ContentPerUrlDecisionPolicyFacts,
) -> str:
    return canonical_json_digest(
        {
            "schema_version": "wilq_per_url_semantic_row_v1",
            "canonical_path": identity.canonical_path,
            "public_url": identity.page_url,
            "current_work_item_id": identity.work_item_id,
            "material_meaning_digest": identity.material_meaning_digest,
            "policy_facts_digest": policy_facts.semantic_digest,
        }
    )


def _observation_evidence_digest(
    identity: CurrentPageIdentityV3Response,
    policy_facts: ContentPerUrlDecisionPolicyFacts,
) -> str:
    return canonical_json_digest(
        {
            "schema_version": "wilq_per_url_decision_evidence_v1",
            "semantic_row_digest": _semantic_row_digest(identity, policy_facts),
            "page_identity_digest": identity.identity_digest,
            "page_evidence_digest": identity.evidence_digest,
            "page_source_status": identity.source_status,
            "page_current_evidence_ids": list(identity.current_evidence_ids),
            "page_catalog_evidence_ids": list(identity.catalog_evidence_ids),
            "policy_evidence_digest": policy_facts.evidence_digest,
        }
    )


__all__ = [
    "ContentPerUrlCurrentnessProjection",
    "ContentPerUrlDecisionAuthorityBlocked",
    "ContentPerUrlDecisionObservation",
    "ContentPerUrlDecisionPolicyFacts",
    "ContentPerUrlPolicyFact",
    "build_content_per_url_decision_observation",
    "per_url_decision_freshness_blocker",
    "per_url_decision_observation_digest",
    "project_content_per_url_currentness",
]
