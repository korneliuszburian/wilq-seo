"""Read-only exact packet preview from the receiptless official source pack."""

from __future__ import annotations

from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
)
from wilq.content.planning.generation_readiness import planning_generation_blockers
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_pack_v3 import (
    SourcePackV3Fact,
    SourcePackV3Preview,
)

_HEX64 = r"^[0-9a-f]{64}$"
PacketBlockerOwner = Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"]


class ResearchPacketV3Blocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    owner: PacketBlockerOwner
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)


class ResearchPacketV3PlanningContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str | None = None


class ResearchPacketV3InternalLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_url: str = Field(min_length=1)
    anchor_hint: str = Field(min_length=1)
    source_connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("target_url")
    @classmethod
    def require_safe_target(cls, value: str) -> str:
        if not content_is_safe_public_url(value):
            raise ValueError("Packet link requires a safe Ekologus URL.")
        return value


class ResearchPacketV3LegalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_fact_ids: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ResearchPacketV3Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["research_packet_v3_preview"] = "research_packet_v3_preview"
    status: Literal["ready", "blocked"]
    work_item_id: str = Field(min_length=1)
    preview_id: str | None = None
    preview_hash: str | None = Field(default=None, pattern=_HEX64)
    source_pack_id: str | None = None
    source_pack_hash: str | None = Field(default=None, pattern=_HEX64)
    page_url: str | None = None
    canonical_path: str | None = None
    identity_digest: str | None = Field(default=None, pattern=_HEX64)
    material_meaning_digest: str | None = Field(default=None, pattern=_HEX64)
    per_url_delivery_identity_action_id: str | None = Field(default=None, min_length=1)
    planning_input_digest: str | None = Field(default=None, pattern=_HEX64)
    content_kind: Literal["service", "editorial"] | None = None
    service_card_id: str | None = None
    demand_evidence_status: Literal["available", "missing"] | None = None
    selected_facts: tuple[SourcePackV3Fact, ...] = ()
    planning_context: ResearchPacketV3PlanningContext | None = None
    cta_direction: str | None = None
    minimum_cta_blocks: int | None = Field(default=None, ge=1, le=4)
    required_cta_patterns: tuple[str, ...] = ()
    internal_links: tuple[ResearchPacketV3InternalLink, ...] = ()
    regulatory_profile_id: str | None = None
    regulatory_profile_version: str | None = None
    legal_requirements: tuple[ResearchPacketV3LegalRequirement, ...] = ()
    verification_evidence_ids: tuple[str, ...] = ()
    verification_evidence_digest: str | None = Field(default=None, pattern=_HEX64)
    blocker: ResearchPacketV3Blocker | None = None
    generation_allowed: Literal[False] = False
    packet_write_allowed: Literal[False] = False

    @field_validator("page_url")
    @classmethod
    def require_safe_page_url_when_present(cls, value: str | None) -> str | None:
        if value is not None and not content_is_safe_public_url(value):
            raise ValueError("Research packet page URL must be a safe public Ekologus URL.")
        return value

    @field_validator("canonical_path")
    @classmethod
    def require_canonical_path_when_present(cls, value: str | None) -> str | None:
        if value is not None and (
            not value
            or value != value.strip()
            or not value.startswith("/")
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
            or "?" in value
            or "#" in value
        ):
            raise ValueError("Research packet canonical path is invalid.")
        return value

    @model_validator(mode="after")
    def require_exact_preview_or_blocker(self) -> Self:
        if self.status == "blocked":
            if self.blocker is None or self.preview_id or self.preview_hash or self.selected_facts:
                raise ValueError("Blocked research packet cannot expose an artifact.")
            return self
        if (self.page_url is None) != (self.canonical_path is None):
            raise ValueError("Research packet page identity must be complete when present.")
        if self.content_kind == "service" and not self.service_card_id:
            raise ValueError("Service research packet requires its exact service card ID.")
        if self.content_kind == "editorial" and self.service_card_id is not None:
            raise ValueError("Editorial research packet cannot carry a service card ID.")
        if self.content_kind is None and self.service_card_id is not None:
            raise ValueError("Historical packet subject cannot carry an unversioned service card.")
        if (
            self.blocker is not None
            or not self.preview_id
            or not self.preview_hash
            or not self.source_pack_id
            or not self.source_pack_hash
            or not self.identity_digest
            or not self.material_meaning_digest
            or not self.planning_input_digest
            or self.demand_evidence_status is None
            or not self.selected_facts
            or self.planning_context is None
            or not self.cta_direction
            or not self.minimum_cta_blocks
            or not self.internal_links
            or not self.regulatory_profile_id
            or not self.regulatory_profile_version
            or not self.legal_requirements
            or not self.verification_evidence_ids
            or not self.verification_evidence_digest
            or self.preview_hash != canonical_json_digest(self.semantic_payload())
            or self.preview_id != f"content_research_packet_v3_{self.preview_hash[:24]}"
            or self.source_pack_id != f"source_pack_v3_{self.source_pack_hash}"
        ):
            raise ValueError("Ready research packet requires exact source, context and hash.")
        if self.demand_evidence_status == "missing" and self.planning_context.search_intent:
            raise ValueError("Missing demand cannot carry a search-intent recommendation.")
        return self

    def has_exact_page_identity(self) -> bool:
        """Old v3 snapshots predate page identity; new review never accepts them."""

        return (
            self.page_url is not None
            and self.canonical_path is not None
            and content_is_safe_public_url(self.page_url)
            and content_normalized_path(self.page_url) == self.canonical_path
        )

    def has_current_per_url_identity(self) -> bool:
        """Only M2a-bound previews can enter the new v3 ActionObject review."""
        return self.per_url_delivery_identity_action_id is not None

    def semantic_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "contract": self.contract_version,
            "work_item_id": self.work_item_id,
            "source_pack_id": self.source_pack_id,
            "source_pack_hash": self.source_pack_hash,
            "identity_digest": self.identity_digest,
            "material_meaning_digest": self.material_meaning_digest,
            "demand_evidence_status": self.demand_evidence_status,
            "selected_facts": [item.model_dump(mode="json") for item in self.selected_facts],
            "planning_context": None if self.planning_context is None
            else self.planning_context.model_dump(mode="json"),
            "cta_direction": self.cta_direction,
            "minimum_cta_blocks": self.minimum_cta_blocks,
            "required_cta_patterns": list(self.required_cta_patterns),
            "internal_links": [
                {"target_url": item.target_url, "anchor_hint": item.anchor_hint}
                for item in self.internal_links
            ],
            "regulatory_profile_id": self.regulatory_profile_id,
            "regulatory_profile_version": self.regulatory_profile_version,
            "legal_requirements": [
                item.model_dump(mode="json") for item in self.legal_requirements
            ],
        }
        # v3 records created before exact page identity remain immutable historical reads.
        if self.page_url is not None and self.canonical_path is not None:
            payload["page_url"] = self.page_url
            payload["canonical_path"] = self.canonical_path
        # Historical v3 records predate exact generation subject binding.
        if self.content_kind is not None:
            payload["content_kind"] = self.content_kind
            payload["service_card_id"] = self.service_card_id
        if self.per_url_delivery_identity_action_id is not None:
            payload["per_url_delivery_identity_action_id"] = (
                self.per_url_delivery_identity_action_id
            )
        return payload


def build_research_packet_v3_preview(
    work_item_id: str,
    *,
    source_pack: SourcePackV3Preview,
    planning_result: ContentPlanningInputBuildResult,
) -> ResearchPacketV3Preview:
    """Build one reviewable packet; source and demand gaps stay explicit."""

    if source_pack.status == "blocked":
        blocker = source_pack.blocker
        if blocker is None:
            return _blocked(
                work_item_id, "source_pack_blocked", (), "Odczytaj bieżący source pack."
        )
        next_step = (
            "Zatwierdź per-URL identity dokładnej strony w wybranym workspace, "
            "a potem ponów pakiet."
            if blocker.code == "per_url_delivery_identity_required"
            else blocker.safe_next_step
        )
        return _blocked(work_item_id, blocker.code, blocker.evidence_ids,
                        next_step, blocker.owner)
    try:
        source_pack = SourcePackV3Preview.model_validate_json(
            source_pack.model_dump_json(), strict=True
        )
    except (ValidationError, ValueError, AttributeError):
        return _blocked(work_item_id, "source_pack_invalid", (),
                        "Odczytaj ponownie dokładny pakiet oficjalnych źródeł.")
    source_evidence = tuple(source_pack.verification_evidence_ids)
    if source_pack.work_item_id != work_item_id or not source_pack.source_pack_hash:
        return _blocked(work_item_id, "source_pack_identity_mismatch", source_evidence,
                        "Odtwórz pakiet źródeł dla dokładnej strony.")
    planning = planning_result.planning_input
    if planning is None or planning.work_item_id != work_item_id:
        return _blocked(work_item_id, "planning_input_missing_or_changed", source_evidence,
                        "Odtwórz bieżący typed planning input tej strony.")
    if (
        planning.final_canonical_url != source_pack.page_url
        or planning.regulatory_coverage.canonical_path != source_pack.canonical_path
    ):
        return _blocked(work_item_id, "planning_page_identity_mismatch", source_evidence,
                        "Odtwórz plan dla dokładnego bieżącego adresu i profilu prawnego.")
    if planning.content_kind == "service" and (
        planning.confirmed_service_card_id is None
        or source_pack.service_binding is None
        or source_pack.service_binding.card_id != planning.confirmed_service_card_id
        or source_pack.service_binding.binding_url != source_pack.page_url
    ):
        return _blocked(work_item_id, "planning_service_binding_mismatch", source_evidence,
                        "Potwierdź dokładną kartę usługi przypisaną do adresu strony.")
    policy_blocker = _planning_policy_blocker(planning, planning_result)
    if policy_blocker is not None:
        return _blocked(work_item_id, policy_blocker, source_evidence,
                        "Odśwież albo usuń nieświeże dane planu przed review pakietu.")
    legal = _legal_requirements(source_pack, planning)
    if isinstance(legal, str):
        return _blocked(work_item_id, legal, source_evidence,
                        "Powiąż wymagania z dokładnymi oficjalnymi faktami pakietu.")
    links = tuple(
        ResearchPacketV3InternalLink(
            target_url=item.target_url,
            anchor_hint=item.anchor_hint,
            evidence_ids=tuple(sorted(set(item.evidence_ids))),
        )
        for item in planning.internal_link_candidates
        if item.source_connector == "wordpress_ekologus"
        and item.evidence_ids
        and set(item.evidence_ids).issubset(planning.evidence_ids)
    )
    if not links:
        return _blocked(work_item_id, "internal_links_missing_or_ambiguous", source_evidence,
                        "Dostarcz zweryfikowane linki wewnętrzne dla tej strony.")
    return _ready(work_item_id, source_pack, planning, links, legal)


def _planning_policy_blocker(
    planning: ContentPlanningInput,
    result: ContentPlanningInputBuildResult,
) -> str | None:
    blockers = planning_generation_blockers(result.blockers)
    for blocker in blockers:
        if blocker.code != "stale_planning_sources":
            return blocker.code
    assessments = {item.source: item.status for item in planning.source_assessments}
    stale = {source for source, status in assessments.items() if status == "stale"}
    has_stale_gsc = any(item.code == "stale_planning_sources" for item in blockers)
    demand = planning.query_portfolio
    if has_stale_gsc and (
        stale != {"gsc"}
        or assessments.get("wordpress") != "used"
        or (planning.content_kind == "service" and assessments.get("service_profile") != "used")
        or demand.status != "missing"
        or demand.gsc_query_rows
        or demand.ads_term_rows
        or demand.keyword_planner_rows
        or demand.evidence_ids
        or any(item.source_connector == "google_search_console" for item in planning.source_facts)
        or any(item.status == "available" for item in planning.metric_comparisons)
    ):
        return "stale_gsc_data_in_packet"
    if demand.status == "missing" and (
        demand.gsc_query_rows or demand.ads_term_rows or demand.keyword_planner_rows
        or demand.evidence_ids
    ):
        return "demand_evidence_inconsistent"
    if demand.status == "available" and (
        assessments.get("gsc") != "used"
        or not demand.gsc_query_rows
        or any(row.freshness != "fresh" for row in demand.gsc_query_rows)
    ):
        return "demand_evidence_not_fresh"
    return None


def _legal_requirements(
    source_pack: SourcePackV3Preview,
    planning: ContentPlanningInput,
) -> tuple[ResearchPacketV3LegalRequirement, ...] | str:
    coverage = planning.regulatory_coverage
    if (
        coverage.applicability_status != "required"
        or not coverage.complete
        or coverage.profile_id != source_pack.regulatory_profile_id
        or coverage.profile_version != source_pack.regulatory_profile_version
    ):
        return "legal_requirements_incomplete_or_changed"
    pack_by_id = {item.requirement_id: item for item in source_pack.requirements}
    planning_by_id = {item.requirement_id: item for item in coverage.requirement_coverage}
    if set(pack_by_id) != {item.id for item in coverage.requirements}:
        return "legal_requirements_outside_pack"
    labels = {item.id: item.label for item in coverage.requirements}
    bound: list[ResearchPacketV3LegalRequirement] = []
    for requirement_id, packet_row in sorted(pack_by_id.items()):
        current_row = planning_by_id.get(requirement_id)
        if (
            current_row is None
            or set(current_row.source_fact_ids) != set(packet_row.source_fact_ids)
            or set(current_row.evidence_ids) != set(packet_row.evidence_ids)
        ):
            return "legal_requirement_evidence_unbound"
        bound.append(ResearchPacketV3LegalRequirement(
            requirement_id=requirement_id,
            label=labels[requirement_id],
            source_fact_ids=packet_row.source_fact_ids,
            evidence_ids=packet_row.evidence_ids,
        ))
    return tuple(bound)


def _ready(
    work_item_id: str,
    source_pack: SourcePackV3Preview,
    planning: ContentPlanningInput,
    links: tuple[ResearchPacketV3InternalLink, ...],
    legal: tuple[ResearchPacketV3LegalRequirement, ...],
) -> ResearchPacketV3Preview:
    demand_status = planning.query_portfolio.status
    assert demand_status in {"missing", "available"}
    context = ResearchPacketV3PlanningContext(
        target_reader=planning.target_reader,
        buyer_problem=planning.buyer_problem,
        buyer_trigger=planning.buyer_trigger,
        search_intent=planning.search_intent if demand_status == "available" else None,
    )
    evidence_ids = tuple(sorted(set(
        source_pack.verification_evidence_ids
        + tuple(evidence for link in links for evidence in link.evidence_ids)
        + tuple(evidence for row in legal for evidence in row.evidence_ids)
    )))
    fields: dict[str, object] = {
        "status": "ready",
        "work_item_id": work_item_id,
        "source_pack_id": source_pack.source_pack_id,
        "source_pack_hash": source_pack.source_pack_hash,
        "page_url": source_pack.page_url,
        "canonical_path": source_pack.canonical_path,
        "identity_digest": source_pack.identity_digest,
        "material_meaning_digest": source_pack.material_meaning_digest,
        "per_url_delivery_identity_action_id": (
            None
            if source_pack.per_url_identity is None
            else source_pack.per_url_identity.action_id
        ),
        "planning_input_digest": planning.planning_input_digest,
        "content_kind": planning.content_kind,
        "service_card_id": planning.confirmed_service_card_id,
        "demand_evidence_status": demand_status,
        "selected_facts": source_pack.facts,
        "planning_context": context,
        "cta_direction": planning.baseline_cta_direction,
        "minimum_cta_blocks": planning.minimum_cta_blocks,
        "required_cta_patterns": tuple(planning.required_cta_patterns),
        "internal_links": links,
        "regulatory_profile_id": source_pack.regulatory_profile_id,
        "regulatory_profile_version": source_pack.regulatory_profile_version,
        "legal_requirements": legal,
        "verification_evidence_ids": evidence_ids,
        "verification_evidence_digest": canonical_json_digest({
            "source_pack_evidence_digest": source_pack.verification_evidence_digest,
            "evidence_ids": evidence_ids,
        }),
    }
    provisional = ResearchPacketV3Preview.model_construct(**cast(dict[str, Any], fields))
    digest = canonical_json_digest(provisional.semantic_payload())
    return ResearchPacketV3Preview.model_validate(fields | {
        "preview_id": f"content_research_packet_v3_{digest[:24]}",
        "preview_hash": digest,
    })


def _blocked(
    work_item_id: str,
    code: str,
    evidence_ids: tuple[str, ...],
    next_step: str,
    owner: str = "WILQ content workflow",
) -> ResearchPacketV3Preview:
    allowed_owner: PacketBlockerOwner = (
        "WILQ WordPress connector" if owner == "WILQ WordPress connector"
        else "Wilku" if owner == "Wilku" else "WILQ content workflow"
    )
    return ResearchPacketV3Preview(
        status="blocked",
        work_item_id=work_item_id,
        blocker=ResearchPacketV3Blocker(
            code=code,
            owner=allowed_owner,
            evidence_ids=tuple(sorted(set(evidence_ids))),
            safe_next_step=next_step,
        ),
    )
