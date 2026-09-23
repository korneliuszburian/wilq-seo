"""Read-only, self-authenticating preview derived from exact current inputs."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_pack_v2 import (
    SourcePackV2Blocker,
    SourcePackV2Fact,
    SourcePackV2Preview,
)


class ResearchPacketV2PreviewBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    owner: Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"]
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class ResearchPacketV2PlanningContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)


class ResearchPacketV2LegalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_fact_ids: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ResearchPacketV2Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ready", "blocked"]
    work_item_id: str = Field(min_length=1)
    preview_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_pack_id: str | None = None
    source_pack_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    keep_receipt_id: str | None = None
    keep_receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    material_meaning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authority_receipt_id: str | None = None
    authority_receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    planning_input_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    selected_facts: tuple[SourcePackV2Fact, ...] = ()
    planning_context: ResearchPacketV2PlanningContext | None = None
    cta_direction: str | None = None
    minimum_cta_blocks: int | None = Field(default=None, ge=1, le=4)
    required_cta_patterns: tuple[str, ...] = ()
    internal_links: tuple[ContentPlanningInternalLinkCandidate, ...] = ()
    regulatory_profile_id: str | None = None
    regulatory_profile_version: str | None = None
    legal_requirements: tuple[ResearchPacketV2LegalRequirement, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    blocker: ResearchPacketV2PreviewBlocker | None = None
    generation_allowed: Literal[False] = False
    packet_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_preview(self) -> Self:
        if self.status == "blocked":
            if (
                self.blocker is None
                or self.preview_hash is not None
                or self.source_pack_id is not None
                or self.source_pack_hash is not None
                or self.keep_receipt_id is not None
                or self.keep_receipt_digest is not None
                or self.material_meaning_digest is not None
                or self.authority_receipt_id is not None
                or self.authority_receipt_digest is not None
                or self.planning_input_digest is not None
                or self.selected_facts
                or self.planning_context is not None
                or self.cta_direction is not None
                or self.minimum_cta_blocks is not None
                or self.required_cta_patterns
                or self.internal_links
                or self.regulatory_profile_id is not None
                or self.regulatory_profile_version is not None
                or self.legal_requirements
                or self.evidence_ids
            ):
                raise ValueError("Blocked preview cannot expose an artifact.")
            return self
        if (
            self.blocker is not None
            or self.preview_hash is None
            or self.source_pack_id is None
            or self.source_pack_hash is None
            or self.keep_receipt_id is None
            or self.keep_receipt_digest is None
            or self.material_meaning_digest is None
            or self.authority_receipt_id is None
            or self.authority_receipt_digest is None
            or self.planning_input_digest is None
            or not self.selected_facts
            or self.planning_context is None
        ):
            raise ValueError("Ready preview requires exact source and planning inputs.")
        if self.source_pack_id != f"source_pack_v2_{self.source_pack_hash}":
            raise ValueError("Research packet preview source pack ID/hash mismatch.")
        if (self.regulatory_profile_id is None) != (self.regulatory_profile_version is None):
            raise ValueError("Regulatory profile ID and version must be paired.")
        if self.legal_requirements and self.regulatory_profile_id is None:
            raise ValueError("Legal requirements require their exact regulatory profile.")
        if self.preview_hash != canonical_json_digest(self.semantic_payload()):
            raise ValueError("Research packet preview hash does not match its exact payload.")
        return self

    def semantic_payload(self) -> dict[str, object]:
        return {
            "work_item_id": self.work_item_id,
            "source_pack_id": self.source_pack_id,
            "source_pack_hash": self.source_pack_hash,
            "keep_receipt_id": self.keep_receipt_id,
            "keep_receipt_digest": self.keep_receipt_digest,
            "material_meaning_digest": self.material_meaning_digest,
            "authority_receipt_id": self.authority_receipt_id,
            "authority_receipt_digest": self.authority_receipt_digest,
            "planning_input_digest": self.planning_input_digest,
            "selected_facts": [fact.model_dump(mode="json") for fact in self.selected_facts],
            "planning_context": None
            if self.planning_context is None
            else self.planning_context.model_dump(mode="json"),
            "cta_direction": self.cta_direction,
            "minimum_cta_blocks": self.minimum_cta_blocks,
            "required_cta_patterns": list(self.required_cta_patterns),
            "internal_links": [link.model_dump(mode="json") for link in self.internal_links],
            "regulatory_profile_id": self.regulatory_profile_id,
            "regulatory_profile_version": self.regulatory_profile_version,
            "legal_requirements": [
                item.model_dump(mode="json") for item in self.legal_requirements
            ],
            "evidence_ids": list(self.evidence_ids),
        }


def build_research_packet_v2_preview(
    work_item_id: str,
    *,
    source_pack: SourcePackV2Preview,
    planning_input: ContentPlanningInput | None,
    planning_blocker: SourcePackV2Blocker | None = None,
) -> ResearchPacketV2Preview:
    if source_pack.status == "blocked":
        source_blocker = source_pack.blocker
        if source_blocker is None:
            return _block(work_item_id, "source_pack_blocked", (), "Odczytaj bieżący source pack.")
        return ResearchPacketV2Preview(
            status="blocked",
            work_item_id=work_item_id,
            blocker=_copy_blocker(source_blocker),
        )
    try:
        source_pack = SourcePackV2Preview.model_validate_json(
            source_pack.model_dump_json(), strict=True
        )
    except (ValidationError, ValueError, AttributeError):
        return _block(
            work_item_id,
            "source_pack_invalid",
            (),
            "Odczytaj ponownie dokładny zatwierdzony source pack v2.",
        )
    source_evidence = set(source_pack.verification_evidence_ids)
    if source_pack.work_item_id != work_item_id or not source_pack.source_pack_hash:
        return _block(
            work_item_id,
            "source_pack_identity_mismatch",
            source_evidence,
            "Odczytaj ponownie bieżący exact source pack.",
        )
    if planning_blocker is not None:
        return ResearchPacketV2Preview(
            status="blocked",
            work_item_id=work_item_id,
            blocker=_copy_blocker(planning_blocker),
        )
    if planning_input is None:
        return ResearchPacketV2Preview(
            status="blocked",
            work_item_id=work_item_id,
            blocker=_blocker(
                "planning_input_missing",
                source_evidence,
                "Odśwież bieżący typed planning input przed przygotowaniem packetu.",
            ),
        )
    if planning_input.work_item_id != work_item_id:
        return _block(
            work_item_id,
            "planning_input_identity_mismatch",
            source_evidence | set(planning_input.evidence_ids),
            "Odtwórz planning input dla bieżącego work itemu.",
        )
    candidate_links = tuple(
        candidate
        for candidate in planning_input.internal_link_candidates
        if candidate.evidence_ids
        and set(candidate.evidence_ids).issubset(set(planning_input.evidence_ids))
    )
    if not candidate_links:
        return _block(
            work_item_id,
            "internal_links_missing_or_ambiguous",
            source_evidence | set(planning_input.evidence_ids),
            "Dostarcz zweryfikowane internal-link candidates w bieżącym planning input.",
        )
    legal = _legal_requirements_or_blocker(
        work_item_id, source_pack, planning_input, source_evidence
    )
    if isinstance(legal, ResearchPacketV2Preview):
        return legal
    return _ready_preview(work_item_id, source_pack, planning_input, candidate_links, legal)


def _legal_requirements_or_blocker(
    work_item_id: str,
    source_pack: SourcePackV2Preview,
    planning_input: ContentPlanningInput,
    source_evidence: set[str],
) -> tuple[ResearchPacketV2LegalRequirement, ...] | ResearchPacketV2Preview:
    coverage = planning_input.regulatory_coverage
    if coverage.applicability_status == "review_required":
        return _block(
            work_item_id,
            "legal_requirements_ambiguous",
            source_evidence | set(coverage.evidence_ids),
            "Uzupełnij typed regulatory coverage i exact oficjalne źródła.",
        )
    if coverage.applicability_status == "required" and not coverage.complete:
        return _block(
            work_item_id,
            "legal_requirements_incomplete",
            source_evidence | set(coverage.evidence_ids),
            "Uzupełnij typed regulatory coverage dla wszystkich wymagań.",
        )
    selected_fact_ids = {fact.source_fact_id for fact in source_pack.facts}
    coverage_by_id = {row.requirement_id: row for row in coverage.requirement_coverage}
    legal_requirements: list[ResearchPacketV2LegalRequirement] = []
    for requirement in coverage.requirements:
        row = coverage_by_id.get(requirement.id)
        if (
            row is None
            or not row.source_fact_ids
            or not row.evidence_ids
            or not set(row.source_fact_ids).issubset(selected_fact_ids)
        ):
            return _block(
                work_item_id,
                "legal_requirement_outside_reviewed_pack",
                source_evidence | set(coverage.evidence_ids),
                "Zatwierdź w source pack dokładne oficjalne fakty dla każdego wymagania.",
            )
        selected_evidence = {
            evidence_id
            for fact in source_pack.facts
            if fact.source_fact_id in row.source_fact_ids
            for evidence_id in fact.evidence_ids
        }
        if set(row.evidence_ids) != selected_evidence:
            return _block(
                work_item_id,
                "legal_requirement_evidence_unbound",
                source_evidence | set(row.evidence_ids),
                "Powiąż wymaganie z evidence wybranych oficjalnych faktów w source pack.",
            )
        legal_requirements.append(
            ResearchPacketV2LegalRequirement(
                requirement_id=requirement.id,
                label=requirement.label,
                source_fact_ids=tuple(sorted(set(row.source_fact_ids))),
                evidence_ids=tuple(sorted(set(row.evidence_ids))),
            )
        )
    return tuple(legal_requirements)


def _ready_preview(
    work_item_id: str,
    source_pack: SourcePackV2Preview,
    planning_input: ContentPlanningInput,
    internal_links: tuple[ContentPlanningInternalLinkCandidate, ...],
    legal_requirements: tuple[ResearchPacketV2LegalRequirement, ...],
) -> ResearchPacketV2Preview:
    if not source_pack.facts:
        return _block(
            work_item_id, "source_pack_facts_missing", (), "Odśwież bieżący exact source pack."
        )
    planning_context = ResearchPacketV2PlanningContext(
        target_reader=planning_input.target_reader,
        buyer_problem=planning_input.buyer_problem,
        buyer_trigger=planning_input.buyer_trigger,
        search_intent=planning_input.search_intent,
    )
    coverage = planning_input.regulatory_coverage
    evidence = tuple(
        sorted(
            set(source_pack.verification_evidence_ids)
            | set(planning_input.evidence_ids)
            | set(coverage.evidence_ids)
            | {evidence_id for fact in source_pack.facts for evidence_id in fact.evidence_ids}
            | {evidence_id for row in legal_requirements for evidence_id in row.evidence_ids}
        )
    )
    fields: dict[str, Any] = {
        "status": "ready",
        "work_item_id": work_item_id,
        "source_pack_id": source_pack.source_pack_id,
        "source_pack_hash": source_pack.source_pack_hash,
        "keep_receipt_id": source_pack.keep_receipt_id,
        "keep_receipt_digest": source_pack.keep_receipt_digest,
        "material_meaning_digest": source_pack.material_meaning_digest,
        "authority_receipt_id": source_pack.authority_receipt_id,
        "authority_receipt_digest": source_pack.authority_receipt_digest,
        "planning_input_digest": planning_input.planning_input_digest,
        "selected_facts": source_pack.facts,
        "planning_context": planning_context,
        "cta_direction": planning_input.baseline_cta_direction,
        "minimum_cta_blocks": planning_input.minimum_cta_blocks,
        "required_cta_patterns": tuple(planning_input.required_cta_patterns),
        "internal_links": internal_links,
        "regulatory_profile_id": coverage.profile_id,
        "regulatory_profile_version": coverage.profile_version,
        "legal_requirements": legal_requirements,
        "evidence_ids": evidence,
    }
    semantic = ResearchPacketV2Preview.model_construct(**fields)
    return ResearchPacketV2Preview.model_validate(
        fields | {"preview_hash": canonical_json_digest(semantic.semantic_payload())}
    )


def _copy_blocker(blocker: SourcePackV2Blocker) -> ResearchPacketV2PreviewBlocker:
    owner = (
        blocker.owner
        if blocker.owner in {"WILQ content workflow", "WILQ WordPress connector", "Wilku"}
        else "WILQ content workflow"
    )
    return ResearchPacketV2PreviewBlocker(
        code=blocker.code,
        owner=owner,
        evidence_ids=tuple(sorted(set(blocker.evidence_ids))),
        safe_next_step=blocker.safe_next_step,
    )


def _block(
    work_item_id: str,
    code: str,
    evidence_ids: set[str] | tuple[str, ...],
    next_step: str,
) -> ResearchPacketV2Preview:
    return ResearchPacketV2Preview(
        status="blocked",
        work_item_id=work_item_id,
        blocker=_blocker(code, evidence_ids, next_step),
    )


def _blocker(
    code: str,
    evidence_ids: set[str] | tuple[str, ...],
    next_step: str,
) -> ResearchPacketV2PreviewBlocker:
    return ResearchPacketV2PreviewBlocker(
        code=code,
        owner="WILQ content workflow",
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )


__all__ = ["ResearchPacketV2Preview", "build_research_packet_v2_preview"]
