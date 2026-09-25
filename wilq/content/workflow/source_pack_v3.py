"""Read-only source pack from exact page identity and approved official facts."""

from __future__ import annotations

from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage, regulatory_content_coverage
from wilq.content.workflow.current_page_identity_v3 import CurrentPageIdentityV3Response
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_contracts import _sanitized_text
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionObservation,
)
from wilq.content.workflow.per_url_delivery_identity_authority import (
    PerUrlDeliveryIdentityProjection,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.content.workflow.source_fact_candidate_v3 import (
    CandidateV3BlockerCode,
    ContentSourceFactCandidateV3Projection,
)
from wilq.security.redaction import redact_mapping

_HEX64 = r"^[0-9a-f]{64}$"
SourcePackV3BlockerCode = CandidateV3BlockerCode | Literal[
    "page_identity_blocked",
    "source_fact_candidates_blocked",
    "source_fact_identity_changed",
    "approved_official_fact_missing",
    "selected_source_fact_changed",
    "selected_source_fact_not_commit_safe",
    "selected_source_fact_connector_invalid",
    "selected_source_fact_redaction_required",
    "official_regulatory_profile_missing",
    "legal_requirements_incomplete",
    "legal_requirement_lineage_mismatch",
    "official_fact_not_current",
    "per_url_delivery_identity_required",
    "per_url_delivery_identity_not_found",
    "per_url_delivery_identity_not_applied",
    "per_url_delivery_identity_not_current",
    "per_url_delivery_identity_subject_mismatch",
    "per_url_delivery_identity_page_changed",
    "per_url_delivery_identity_observation_missing",
]


class SourcePackV3Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_fact_id: str = Field(min_length=1)
    fact_digest: str = Field(pattern=_HEX64)
    text: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    freshness_date: str = Field(min_length=1)
    source_type: Literal["legal_update"] = "legal_update"
    official_source: Literal[True] = True
    privacy_class: Literal["commit_safe"] = "commit_safe"
    source_connectors: tuple[Literal["official_regulatory_review"], ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    regulatory_requirement_ids: tuple[str, ...] = Field(min_length=1)


class SourcePackV3Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str = Field(min_length=1)
    source_fact_ids: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class SourcePackV3Blocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: SourcePackV3BlockerCode
    owner: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class SourcePackV3PerUrlIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    binding_id: str = Field(min_length=1)
    binding_digest: str = Field(pattern=_HEX64)
    semantic_row_digest: str = Field(pattern=_HEX64)
    observation_id: str = Field(min_length=1)
    disposition_receipt_id: str = Field(min_length=1)
    disposition_receipt_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    current_work_item_id: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    canonical_path: str = Field(min_length=1)
    material_meaning_digest: str = Field(pattern=_HEX64)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Per-URL source-pack identity evidence must be sorted and unique.")
        return value

    @model_validator(mode="after")
    def require_exact_page(self) -> Self:
        if (
            not content_is_safe_public_url(self.page_url)
            or content_normalized_path(self.page_url) != self.canonical_path
        ):
            raise ValueError("Per-URL source-pack identity URL/path does not match.")
        return self


class SourcePackV3Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["source_pack_v3"] = "source_pack_v3"
    status: Literal["ready", "blocked"]
    work_item_id: str = Field(min_length=1)
    source_pack_id: str | None = None
    source_pack_hash: str | None = Field(default=None, pattern=_HEX64)
    page_url: str | None = None
    canonical_path: str | None = None
    identity_id: str | None = None
    identity_digest: str | None = Field(default=None, pattern=_HEX64)
    material_meaning_digest: str | None = Field(default=None, pattern=_HEX64)
    per_url_identity: SourcePackV3PerUrlIdentity | None = None
    registry_digest: str | None = Field(default=None, pattern=_HEX64)
    regulatory_profile_id: str | None = None
    regulatory_profile_version: str | None = None
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None
    facts: tuple[SourcePackV3Fact, ...] = ()
    requirements: tuple[SourcePackV3Requirement, ...] = ()
    verification_evidence_ids: tuple[str, ...] = ()
    verification_evidence_digest: str | None = Field(default=None, pattern=_HEX64)
    blocker: SourcePackV3Blocker | None = None
    generation_allowed: Literal[False] = False
    packet_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_pack_or_blocker(self) -> Self:
        if self.status == "blocked":
            if (
                self.blocker is None
                or self.source_pack_id
                or self.source_pack_hash
                or self.facts
                or self.per_url_identity is not None
            ):
                raise ValueError("Blocked source pack cannot expose an artifact.")
            return self
        if (
            self.blocker is not None
            or not self.source_pack_id
            or not self.source_pack_hash
            or not self.page_url
            or not self.canonical_path
            or not self.identity_id
            or not self.identity_digest
            or not self.material_meaning_digest
            or self.per_url_identity is None
            or self.per_url_identity.current_work_item_id != self.work_item_id
            or self.per_url_identity.page_url != self.page_url
            or self.per_url_identity.canonical_path != self.canonical_path
            or self.per_url_identity.material_meaning_digest
            != self.material_meaning_digest
            or not self.registry_digest
            or not self.regulatory_profile_id
            or not self.regulatory_profile_version
            or self.service_binding is None
            or self.service_binding.status != "exact_bound"
            or not self.facts
            or not self.requirements
            or not self.verification_evidence_ids
            or not self.verification_evidence_digest
            or self.source_pack_hash != canonical_json_digest(self.semantic_payload())
            or self.source_pack_id != f"source_pack_v3_{self.source_pack_hash}"
        ):
            raise ValueError("Ready source pack requires exact identity, facts and hash.")
        return self

    def semantic_payload(self) -> dict[str, object]:
        return {
            "contract": self.contract_version,
            "work_item_id": self.work_item_id,
            "page_url": self.page_url,
            "canonical_path": self.canonical_path,
            "identity_id": self.identity_id,
            "identity_digest": self.identity_digest,
            "material_meaning_digest": self.material_meaning_digest,
            "per_url_identity": (
                None
                if self.per_url_identity is None
                else self.per_url_identity.model_dump(mode="json")
            ),
            "regulatory_profile_id": self.regulatory_profile_id,
            "regulatory_profile_version": self.regulatory_profile_version,
            "service_binding": (
                None if self.service_binding is None
                else self.service_binding.model_dump(mode="json")
            ),
            "facts": [item.model_dump(mode="json") for item in self.facts],
            "requirements": [item.model_dump(mode="json") for item in self.requirements],
        }


def resolve_source_pack_v3_per_url_identity(
    work_item_id: str,
    identity: CurrentPageIdentityV3Response,
    *,
    action_id: str | None,
    authority: PerUrlDeliveryIdentityProjection | None,
    observation: ContentPerUrlDecisionObservation | None,
) -> tuple[SourcePackV3PerUrlIdentity | None, SourcePackV3Blocker | None]:
    evidence_ids = tuple(
        sorted(set(identity.current_evidence_ids + identity.catalog_evidence_ids))
    )
    if identity.status != "exact_current":
        return None, _per_url_identity_blocker(
            identity.blocker_code or "page_identity_blocked",
            identity.blocker_owner or "WILQ content workflow",
            evidence_ids,
            identity.safe_next_step,
        )
    if action_id is None:
        return None, _per_url_identity_blocker(
            "per_url_delivery_identity_required",
            "WILQ content workflow",
            evidence_ids,
            "Podaj action ID zatwierdzonego per-URL delivery identity dla tej strony.",
        )
    authority_blocker = _per_url_identity_authority_blocker(
        authority, action_id, evidence_ids
    )
    if authority_blocker is not None:
        return None, authority_blocker
    assert authority is not None and authority.binding is not None
    binding = authority.binding
    page_blocker = _per_url_identity_page_blocker(
        work_item_id, identity, binding, observation, evidence_ids
    )
    if page_blocker is not None:
        return None, page_blocker
    assert observation is not None
    observed_identity = observation.page_identity
    if (
        observed_identity.material_meaning_digest is None
        or observed_identity.material_meaning_digest != identity.material_meaning_digest
    ):
        return None, _per_url_identity_blocker(
            "per_url_delivery_identity_page_changed",
            "WILQ content workflow",
            evidence_ids,
            "Odczytaj i zatwierdź per-URL identity dla aktualnego materiału tej strony.",
        )
    snapshot = binding.snapshot
    return (
        SourcePackV3PerUrlIdentity(
            action_id=binding.action_id,
            binding_id=binding.binding_id,
            binding_digest=binding.binding_digest,
            semantic_row_digest=snapshot.semantic_row_digest,
            observation_id=snapshot.observation_id,
            disposition_receipt_id=snapshot.disposition_receipt_id,
            disposition_receipt_digest=snapshot.disposition_receipt_digest,
            evidence_ids=snapshot.evidence_ids,
            current_work_item_id=snapshot.current_work_item_id,
            page_url=snapshot.public_url,
            canonical_path=snapshot.canonical_path,
            material_meaning_digest=observed_identity.material_meaning_digest,
        ),
        None,
    )


def _per_url_identity_authority_blocker(
    authority: PerUrlDeliveryIdentityProjection | None,
    action_id: str,
    evidence_ids: tuple[str, ...],
) -> SourcePackV3Blocker | None:
    if authority is None or authority.status == "missing":
        return _per_url_identity_blocker(
            "per_url_delivery_identity_not_found",
            "WILQ content workflow",
            evidence_ids,
            "Odczytaj lub zatwierdź per-URL delivery identity dla tej strony.",
        )
    if authority.status == "preview_ready":
        return _per_url_identity_blocker(
            "per_url_delivery_identity_not_applied",
            "Wilku",
            evidence_ids,
            "Zakończ review i apply dokładnego per-URL delivery identity ActionObject.",
        )
    if authority.status == "blocked":
        blocker = authority.blockers[0] if authority.blockers else None
        return _per_url_identity_blocker(
            "per_url_delivery_identity_not_current",
            "WILQ content workflow" if blocker is None else blocker.owner,
            evidence_ids if blocker is None else blocker.evidence_ids,
            "Odczytaj bieżące per-URL delivery identity."
            if blocker is None
            else blocker.safe_next_step,
        )
    if (
        authority.binding is None
        or authority.action is None
        or authority.binding.action_id != action_id
        or authority.action.id != action_id
    ):
        return _per_url_identity_blocker(
            "per_url_delivery_identity_not_current",
            "WILQ content workflow",
            evidence_ids,
            "Odczytaj per-URL identity dla dokładnego action ID.",
        )
    return None


def _per_url_identity_page_blocker(
    work_item_id: str,
    identity: CurrentPageIdentityV3Response,
    binding: Any,
    observation: ContentPerUrlDecisionObservation | None,
    evidence_ids: tuple[str, ...],
) -> SourcePackV3Blocker | None:
    snapshot = binding.snapshot
    if snapshot.current_work_item_id != work_item_id:
        return _per_url_identity_blocker(
            "per_url_delivery_identity_subject_mismatch",
            "WILQ content workflow",
            evidence_ids,
            "Użyj per-URL identity należącego do tego work itemu.",
        )
    if (
        observation is None
        or observation.observation_id != snapshot.observation_id
        or observation.semantic_row_digest != snapshot.semantic_row_digest
    ):
        return _per_url_identity_blocker(
            "per_url_delivery_identity_observation_missing",
            "WILQ content workflow",
            evidence_ids,
            "Odczytaj ponownie świeży per-URL semantic row tej strony.",
        )
    observed_identity = observation.page_identity
    if (
        snapshot.canonical_path != identity.canonical_path
        or snapshot.public_url != identity.page_url
        or observed_identity.work_item_id != identity.work_item_id
        or observed_identity.page_url != identity.page_url
        or observed_identity.canonical_path != identity.canonical_path
        or observed_identity.material_meaning_digest != identity.material_meaning_digest
    ):
        return _per_url_identity_blocker(
            "per_url_delivery_identity_page_changed",
            "WILQ content workflow",
            evidence_ids,
            "Odczytaj i zatwierdź per-URL identity dla aktualnego materiału tej strony.",
        )
    return None


def _per_url_identity_blocker(
    code: SourcePackV3BlockerCode,
    owner: str,
    evidence_ids: tuple[str, ...],
    safe_next_step: str,
) -> SourcePackV3Blocker:
    return SourcePackV3Blocker(
        code=code,
        owner=owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=safe_next_step,
    )


def build_source_pack_v3_preview(
    work_item_id: str,
    *,
    identity: CurrentPageIdentityV3Response,
    candidates: ContentSourceFactCandidateV3Projection,
    facts: tuple[ContentSourceFact, ...],
    per_url_identity: SourcePackV3PerUrlIdentity,
) -> SourcePackV3Preview:
    """Build only from current approved official facts; this performs no write."""

    evidence = tuple(sorted(set(
        identity.current_evidence_ids + identity.catalog_evidence_ids
        + candidates.registry_evidence_ids
    )))
    if identity.status != "exact_current":
        return _blocked(work_item_id, identity.blocker_code or "page_identity_blocked",
                        identity.blocker_owner or "WILQ content workflow",
                        evidence, identity.safe_next_step)
    if candidates.status != "eligible":
        return _blocked(work_item_id,
                        candidates.blocker_code or "source_fact_candidates_blocked",
                        candidates.blocker_owner or "WILQ content workflow",
                        tuple(sorted(set(evidence + candidates.blocker_evidence_ids))),
                        candidates.safe_next_step)
    if (
        candidates.work_item_id != work_item_id
        or candidates.identity_digest != identity.identity_digest
        or candidates.evidence_digest != identity.evidence_digest
        or candidates.page_url != identity.page_url
        or candidates.canonical_path != identity.canonical_path
        or candidates.material_meaning_digest != identity.material_meaning_digest
    ):
        return _blocked(work_item_id, "source_fact_identity_changed", "WILQ content workflow",
                        evidence, "Odczytaj ponownie tożsamość strony i kandydatów źródeł.")
    if (
        per_url_identity.current_work_item_id != work_item_id
        or per_url_identity.current_work_item_id != identity.work_item_id
        or per_url_identity.page_url != identity.page_url
        or per_url_identity.canonical_path != identity.canonical_path
        or per_url_identity.material_meaning_digest != identity.material_meaning_digest
    ):
        return _blocked(
            work_item_id,
            "per_url_delivery_identity_page_changed",
            "WILQ content workflow",
            evidence,
            "Odczytaj i zatwierdź per-URL identity dla aktualnego materiału tej strony.",
        )
    sources, blocker = _current_approved_source_facts(
        work_item_id, candidates, facts, evidence
    )
    if blocker is not None:
        return blocker
    assert identity.canonical_path is not None
    binding = candidates.service_binding
    coverage = regulatory_content_coverage(
        service_card_id=None if binding is None else binding.card_id,
        canonical_path=identity.canonical_path,
        source_facts=tuple(sources),
    )
    if coverage.applicability_status != "required" or not coverage.profile_id:
        return _blocked(work_item_id, "official_regulatory_profile_missing",
                        "WILQ content workflow", evidence,
                        "Zarejestruj dokładny profil prawny dla tej strony.")
    if not coverage.complete:
        return _blocked(work_item_id, "legal_requirements_incomplete", "Wilku",
                        tuple(sorted(set(evidence + tuple(coverage.evidence_ids)))),
                        "Zatwierdź oficjalne źródło dla każdego brakującego wymagania.")
    source_by_id = {source.source_id: source for source in sources}
    if (
        not set(coverage.source_fact_ids).issubset(source_by_id)
        or any(
            not row.source_fact_ids
            or not set(row.source_fact_ids).issubset(source_by_id)
            or set(row.evidence_ids) != {
                evidence_id
                for fact_id in row.source_fact_ids
                for evidence_id in source_by_id[fact_id].evidence_ids
            }
            for row in coverage.requirement_coverage
        )
    ):
        return _blocked(work_item_id, "legal_requirement_lineage_mismatch",
                        "WILQ content workflow", evidence,
                        "Odtwórz powiązanie wymagań z dokładnie wybranymi źródłami.")
    current_ids = set(coverage.source_fact_ids)
    current_sources = tuple(source for source in sources if source.source_id in current_ids)
    if not current_sources:
        return _blocked(work_item_id, "official_fact_not_current", "WILQ content workflow",
                        evidence, "Odśwież zatwierdzone oficjalne fakty tej strony.")
    return _ready(
        work_item_id,
        identity,
        candidates,
        current_sources,
        coverage,
        per_url_identity,
    )


def _current_approved_source_facts(
    work_item_id: str,
    candidates: ContentSourceFactCandidateV3Projection,
    facts: tuple[ContentSourceFact, ...],
    evidence: tuple[str, ...],
) -> tuple[tuple[ContentSourceFact, ...], SourcePackV3Preview | None]:
    by_id = {fact.source_id: fact for fact in facts}
    legal = [item for item in candidates.candidates if item.source_type == "legal_update"]
    if not legal:
        return (), _blocked(
            work_item_id,
            "approved_official_fact_missing",
            "Wilku",
            evidence,
            "Zarejestruj i zatwierdź dokładne oficjalne fakty dla tej strony.",
        )
    sources: list[ContentSourceFact] = []
    for candidate in legal:
        source = by_id.get(candidate.source_fact_id)
        blocker = _source_blocker(work_item_id, candidate.fact_digest, source, evidence)
        if blocker is not None:
            return (), blocker
        assert source is not None
        sources.append(source)
    return tuple(sources), None


def _source_blocker(
    work_item_id: str, expected_digest: str, source: ContentSourceFact | None,
    evidence: tuple[str, ...],
) -> SourcePackV3Preview | None:
    if source is None or canonical_json_digest(source.model_dump(mode="json")) != expected_digest \
            or source.review_status != "approved" or not source.official_source:
        return _blocked(work_item_id, "selected_source_fact_changed", "WILQ content workflow",
                        evidence, "Odczytaj ponownie zatwierdzony oficjalny fakt.")
    if source.privacy_class != "commit_safe":
        return _blocked(work_item_id, "selected_source_fact_not_commit_safe",
                        "WILQ content workflow", evidence,
                        "Zatwierdź zredagowany wariant factu do pakietu.")
    if tuple(sorted(set(source.source_connectors))) != ("official_regulatory_review",):
        return _blocked(work_item_id, "selected_source_fact_connector_invalid",
                        "WILQ content workflow", evidence,
                        "Powiąż fakt z audytowanym odczytem oficjalnego źródła.")
    safe = redact_mapping({"text": source.extracted_fact, "url": source.source_url_or_path})
    if (
        safe.get("text") != source.extracted_fact
        or safe.get("url") != source.source_url_or_path
        or _sanitized_text(source.extracted_fact) != source.extracted_fact
    ):
        return _blocked(work_item_id, "selected_source_fact_redaction_required",
                        "WILQ content workflow", evidence,
                        "Zatwierdź bezpieczny tekst i adres oficjalnego źródła.")
    return None


def _ready(
    work_item_id: str,
    identity: CurrentPageIdentityV3Response,
    candidates: ContentSourceFactCandidateV3Projection,
    sources: tuple[ContentSourceFact, ...],
    coverage: ContentRegulatoryCoverage,
    per_url_identity: SourcePackV3PerUrlIdentity,
) -> SourcePackV3Preview:
    candidate_by_id = {item.source_fact_id: item for item in candidates.candidates}
    packet_facts = tuple(
        SourcePackV3Fact(
            source_fact_id=source.source_id,
            fact_digest=candidate_by_id[source.source_id].fact_digest,
            text=source.extracted_fact,
            source_reference=source.source_url_or_path,
            freshness_date=source.freshness_date,
            source_connectors=("official_regulatory_review",),
            evidence_ids=tuple(sorted(set(source.evidence_ids))),
            regulatory_requirement_ids=tuple(sorted(set(source.regulatory_requirement_ids))),
        )
        for source in sorted(sources, key=lambda item: item.source_id)
    )
    requirements = tuple(
        SourcePackV3Requirement(
            requirement_id=row.requirement_id,
            source_fact_ids=tuple(sorted(set(row.source_fact_ids))),
            evidence_ids=tuple(sorted(set(row.evidence_ids))),
        )
        for row in sorted(coverage.requirement_coverage, key=lambda item: item.requirement_id)
    )
    binding_evidence = (
        () if candidates.service_binding is None
        else candidates.service_binding.card_evidence_ids
    )
    verification_ids = tuple(sorted(set(
        identity.current_evidence_ids + identity.catalog_evidence_ids
        + candidates.registry_evidence_ids + tuple(coverage.evidence_ids)
        + binding_evidence
        + per_url_identity.evidence_ids
    )))
    fields: dict[str, object] = {
        "status": "ready",
        "work_item_id": work_item_id,
        "page_url": identity.page_url,
        "canonical_path": identity.canonical_path,
        "identity_id": identity.identity_id,
        "identity_digest": identity.identity_digest,
        "material_meaning_digest": identity.material_meaning_digest,
        "per_url_identity": per_url_identity,
        "registry_digest": candidates.registry_digest,
        "regulatory_profile_id": coverage.profile_id,
        "regulatory_profile_version": coverage.profile_version,
        "service_binding": candidates.service_binding,
        "facts": packet_facts,
        "requirements": requirements,
        "verification_evidence_ids": verification_ids,
        "verification_evidence_digest": identity.evidence_digest,
    }
    semantic = SourcePackV3Preview.model_construct(**cast(dict[str, Any], fields))
    digest = canonical_json_digest(semantic.semantic_payload())
    return SourcePackV3Preview.model_validate(
        fields | {"source_pack_id": f"source_pack_v3_{digest}", "source_pack_hash": digest}
    )


def _blocked(
    work_item_id: str, code: SourcePackV3BlockerCode, owner: str,
    evidence: tuple[str, ...], step: str,
) -> SourcePackV3Preview:
    return SourcePackV3Preview(
        status="blocked",
        work_item_id=work_item_id,
        blocker=SourcePackV3Blocker(
            code=code,
            owner=owner,
            evidence_ids=tuple(sorted(set(evidence))),
            safe_next_step=step,
        ),
    )
