"""Exact, append-only source-fact authority for a current v2 KEEP receipt."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.regulatory.policy import regulatory_content_coverage
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityBlockerCode,
    CurrentPageIdentityBlockerOwner,
    CurrentPageIdentityV2Response,
    resolve_current_page_identity_v2,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.content.workflow.source_fact_candidate_v2 import (
    ContentSourceFactCandidateV2,
    ContentSourceFactCandidateV2BlockerCode,
    ContentSourceFactCandidateV2Projection,
    build_content_source_fact_candidates_v2_projection,
)
from wilq.content.workflow.source_pack_binding import SOURCE_FACT_REGISTRY_ID
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)

SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE = "content_source_fact_authority_v2"
SOURCE_FACT_AUTHORITY_V2_MUTATION_ADAPTER = "source_fact_authority_store"
SOURCE_FACT_AUTHORITY_V2_PREVIEW_CONTRACT = "content_source_fact_authority_snapshot_v2"
_HEX64 = r"^[0-9a-f]{64}$"
SOURCE_FACT_AUTHORITY_V2_BLOCKER_OWNER: CurrentPageIdentityBlockerOwner = "WILQ content workflow"
ContentSourceFactAuthorityV2BlockerCode = (
    CurrentPageIdentityBlockerCode
    | ContentSourceFactCandidateV2BlockerCode
    | Literal[
        "current_keep_changed",
        "selected_source_fact_not_current_approved",
        "regulatory_source_policy_not_current",
        "source_fact_freshness_invalid",
        "source_fact_authority_receipt_mismatch",
        "source_fact_authority_unavailable",
    ]
)


class SourceFactAuthorityV2Blocked(ValueError):
    def __init__(
        self,
        code: ContentSourceFactAuthorityV2BlockerCode,
        safe_next_step: str,
        evidence_ids: tuple[str, ...] = (),
        owner: CurrentPageIdentityBlockerOwner = SOURCE_FACT_AUTHORITY_V2_BLOCKER_OWNER,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.owner = owner
        self.evidence_ids = tuple(sorted(set(evidence_ids)))
        self.safe_next_step = safe_next_step


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentSourceFactAuthorityV2Snapshot(_FrozenModel):
    schema_version: Literal["wilq_content_source_fact_authority_snapshot_v2"] = (
        "wilq_content_source_fact_authority_snapshot_v2"
    )
    keep_receipt_id: str = Field(min_length=1, max_length=240)
    keep_receipt_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    page_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    material_meaning_digest: str = Field(pattern=_HEX64)
    original_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    apply_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    current_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    registry_id: str = Field(min_length=1, max_length=240)
    registry_digest: str = Field(pattern=_HEX64)
    registry_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    selected_facts: tuple[ContentSourceFactCandidateV2, ...] = Field(min_length=1, max_length=256)
    service_binding: ContentSourceFactAuthorityServiceBinding
    context_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        for name in (
            "original_evidence_ids",
            "apply_evidence_ids",
            "current_evidence_ids",
            "registry_evidence_ids",
        ):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))) or any(not value.strip() for value in values):
                raise ValueError(f"{name} must be sorted, unique and non-blank.")
        ids = tuple(fact.source_fact_id for fact in self.selected_facts)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("Selected source fact IDs must be sorted and unique.")
        if any(
            fact.review_status != "approved" or not fact.evidence_ids
            for fact in self.selected_facts
        ):
            raise ValueError("Selected source facts must be approved and evidence-bound.")
        if any(
            fact.deterministic_origin == "exact_service_card_binding"
            for fact in self.selected_facts
        ) and (
            self.service_binding.status != "exact_bound"
            or self.service_binding.card_id is None
            or self.service_binding.card_status != "approved_current"
            or not self.service_binding.card_evidence_ids
            or not self.service_binding.card_source_connectors
            or self.service_binding.card_freshness is None
        ):
            raise ValueError("Card-scoped facts require exact approved card provenance.")
        if self.registry_id != SOURCE_FACT_REGISTRY_ID:
            raise ValueError("Source fact registry ID is not canonical.")
        if self.service_binding.status != "exact_bound":
            raise ValueError("Source fact authority requires an exact service/page binding.")
        if self.context_digest != source_fact_authority_v2_snapshot_digest(self):
            raise ValueError("Source fact authority v2 snapshot digest does not match.")
        return self


class ContentSourceFactAuthorityV2Proposal(_FrozenModel):
    schema_version: Literal["wilq_content_source_fact_authority_proposal_v2"] = (
        "wilq_content_source_fact_authority_proposal_v2"
    )
    action_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    attempt: int = Field(default=0, ge=0, le=1000, strict=True)
    snapshot: ContentSourceFactAuthorityV2Snapshot

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        expected = source_fact_authority_v2_proposal_digest(self.snapshot, self.attempt)
        if (
            self.proposal_digest != expected
            or self.action_id != f"content_source_fact_authority_v2_{expected}"
        ):
            raise ValueError("Source fact authority v2 proposal identity does not match.")
        return self


class ContentSourceFactAuthorityV2Receipt(_FrozenModel):
    schema_version: Literal["wilq_content_source_fact_authority_receipt_v2"] = (
        "wilq_content_source_fact_authority_receipt_v2"
    )
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: ContentSourceFactAuthorityV2Snapshot
    verification_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    verification_registry_digest: str = Field(pattern=_HEX64)
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)
    recorded_at: datetime

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        if self.verification_evidence_ids != tuple(sorted(set(self.verification_evidence_ids))):
            raise ValueError("Verification evidence IDs must be sorted and unique.")
        expected = source_fact_authority_v2_receipt_digest(self)
        if (
            self.receipt_digest != expected
            or self.receipt_id != f"content_source_fact_authority_v2_receipt_{expected}"
        ):
            raise ValueError("Source fact authority v2 receipt digest does not match.")
        return self


class ContentSourceFactAuthorityV2PreviewCommand(_FrozenModel):
    work_item_id: str = Field(min_length=1, max_length=240)
    expected_keep_receipt_id: str = Field(min_length=1, max_length=240)
    expected_keep_receipt_digest: str = Field(pattern=_HEX64)
    expected_material_meaning_digest: str = Field(pattern=_HEX64)
    source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    attempt: int = Field(default=0, ge=0, le=1000, strict=True)

    @model_validator(mode="after")
    def validate_ids(self) -> Self:
        if self.source_fact_ids != tuple(sorted(set(self.source_fact_ids))):
            raise ValueError("Source fact IDs must be sorted and unique.")
        return self


def source_fact_authority_v2_snapshot_digest(
    value: ContentSourceFactAuthorityV2Snapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def source_fact_authority_v2_proposal_digest(
    snapshot: ContentSourceFactAuthorityV2Snapshot, attempt: int
) -> str:
    payload = snapshot.model_dump(mode="json")
    for rotating_key in (
        "context_digest",
        "current_evidence_ids",
        "registry_digest",
        "registry_evidence_ids",
    ):
        payload.pop(rotating_key)
    return canonical_json_digest({"semantic_snapshot": payload, "attempt": attempt})


def source_fact_authority_v2_receipt_digest(
    value: ContentSourceFactAuthorityV2Receipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def source_fact_authority_v2_projection(
    *,
    identity: CurrentPageIdentityV2Response,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
) -> ContentSourceFactCandidateV2Projection:
    return build_content_source_fact_candidates_v2_projection(
        identity=identity,
        facts=tuple(ekologus_source_facts()) if facts is None else facts,
        cards=tuple(ekologus_content_knowledge_cards()) if cards is None else cards,
    )


def prepare_source_fact_authority_v2(
    command: ContentSourceFactAuthorityV2PreviewCommand,
    *,
    identity: CurrentPageIdentityV2Response,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
) -> ContentSourceFactAuthorityV2Proposal:
    current_facts = tuple(ekologus_source_facts()) if facts is None else facts
    current_cards = tuple(ekologus_content_knowledge_cards()) if cards is None else cards
    projection = source_fact_authority_v2_projection(
        identity=identity, facts=current_facts, cards=current_cards
    )
    if identity.status != "exact_current":
        raise SourceFactAuthorityV2Blocked(
            identity.blocker_code or "missing_approved_keep_receipt",
            identity.safe_next_step or "Odczytaj ponownie bieżący KEEP.",
            tuple(identity.current_evidence_ids),
            identity.blocker_owner or SOURCE_FACT_AUTHORITY_V2_BLOCKER_OWNER,
        )
    if projection.status != "eligible":
        raise SourceFactAuthorityV2Blocked(
            projection.blocker_code or "approved_source_fact_candidate_missing",
            projection.safe_next_step,
            tuple(projection.blocker_evidence_ids),
            projection.blocker_owner or SOURCE_FACT_AUTHORITY_V2_BLOCKER_OWNER,
        )
    assert projection.service_binding is not None
    if (
        identity.work_item_id != command.work_item_id
        or identity.receipt_id != command.expected_keep_receipt_id
        or identity.receipt_digest != command.expected_keep_receipt_digest
        or identity.material_meaning_digest != command.expected_material_meaning_digest
    ):
        raise SourceFactAuthorityV2Blocked(
            "current_keep_changed",
            "Odczytaj najnowszy KEEP i bieżący materiał, a potem przygotuj nowy preview.",
            tuple(identity.current_evidence_ids),
        )
    by_id = {candidate.source_fact_id: candidate for candidate in projection.candidates}
    if any(source_id not in by_id for source_id in command.source_fact_ids):
        raise SourceFactAuthorityV2Blocked(
            "selected_source_fact_not_current_approved",
            "Odczytaj aktualnych kandydatów i wybierz wyłącznie zatwierdzone fakty.",
            tuple(
                sorted(
                    set(identity.current_evidence_ids)
                    | {
                        evidence
                        for candidate in projection.candidates
                        for evidence in candidate.evidence_ids
                    }
                )
            ),
        )
    selected = tuple(by_id[source_id] for source_id in command.source_fact_ids)
    _validate_selected_freshness_dates(selected)
    _validate_regulatory_facts(
        selected, projection.canonical_path, projection.service_binding.card_id, current_facts
    )
    provisional = {
        "schema_version": "wilq_content_source_fact_authority_snapshot_v2",
        "keep_receipt_id": identity.receipt_id,
        "keep_receipt_digest": identity.receipt_digest,
        "work_item_id": identity.work_item_id,
        "page_url": identity.page_url,
        "canonical_path": identity.canonical_path,
        "material_meaning_digest": identity.material_meaning_digest,
        "original_evidence_ids": identity.original_evidence_ids,
        "apply_evidence_ids": identity.apply_evidence_ids,
        "current_evidence_ids": identity.current_evidence_ids,
        "registry_id": projection.registry_id,
        "registry_digest": projection.registry_digest,
        "registry_evidence_ids": projection.registry_evidence_ids,
        "selected_facts": tuple(fact.model_dump(mode="json") for fact in selected),
        "service_binding": projection.service_binding.model_dump(mode="json"),
        "context_digest": "0" * 64,
    }
    snapshot = ContentSourceFactAuthorityV2Snapshot.model_validate(
        provisional | {"context_digest": source_fact_authority_v2_snapshot_digest(provisional)}
    )
    digest = source_fact_authority_v2_proposal_digest(snapshot, command.attempt)
    return ContentSourceFactAuthorityV2Proposal(
        action_id=f"content_source_fact_authority_v2_{digest}",
        proposal_digest=digest,
        attempt=command.attempt,
        snapshot=snapshot,
    )


def source_fact_authority_v2_action(
    proposal: ContentSourceFactAuthorityV2Proposal,
) -> ActionObject:
    snapshot = proposal.snapshot
    return ActionObject(
        id=proposal.action_id,
        title="Zatwierdź exact źródła faktów dla bieżącej strony",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=sorted(
            set(
                snapshot.original_evidence_ids
                + snapshot.apply_evidence_ids
                + snapshot.current_evidence_ids
                + snapshot.registry_evidence_ids
                + tuple(
                    evidence for fact in snapshot.selected_facts for evidence in fact.evidence_ids
                )
                + snapshot.service_binding.card_evidence_ids
            )
        ),
        human_diagnosis="To jest wybór zatwierdzonych źródeł dla exact bieżącego KEEP.",
        recommended_reason="Sprawdź dokładne dowody, kartę usługi i aktualność źródeł.",
        payload={
            "action_type": SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "source_fact_authority_v2": proposal.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": proposal.action_id,
                    "operation_type": "record_source_fact_authority_v2_receipt",
                    "work_item_id": snapshot.work_item_id,
                    "page_url": snapshot.page_url,
                    "source_fact_ids": [fact.source_fact_id for fact in snapshot.selected_facts],
                    "source_fact_freshness": [
                        {
                            "source_fact_id": fact.source_fact_id,
                            "freshness_date": fact.freshness_date,
                        }
                        for fact in snapshot.selected_facts
                    ],
                    "apply_allowed": True,
                    "generation_allowed": False,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_allowed": False,
        },
        validation_status="not_validated",
        created_by="system_core_source_fact_authority_v2",
    )


def validate_source_fact_authority_v2_payload(payload: dict[str, Any]) -> list[str]:
    if payload.get("action_type") != SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE:
        return ["Source fact authority v2 action type is invalid."]
    if payload.get("local_authority_only") is not True:
        return ["Source fact authority v2 must remain local-only."]
    try:
        ContentSourceFactAuthorityV2Proposal.model_validate_json(
            json.dumps(payload.get("source_fact_authority_v2", {}), sort_keys=True), strict=True
        )
    except (TypeError, ValueError):
        return ["Source fact authority v2 proposal is invalid."]
    return []


def execute_source_fact_authority_v2(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_source_fact_authority_v2_proposal(action.id)
    if proposal is None:
        return None, ["Source fact authority v2 proposal is missing."]
    from wilq.content.workflow.current_page_evidence import read_current_page_evidence_current

    identity = resolve_current_page_identity_v2(
        proposal.snapshot.work_item_id,
        store=store,
        evidence=read_current_page_evidence_current(proposal.snapshot.work_item_id),
    )
    try:
        command = ContentSourceFactAuthorityV2PreviewCommand(
            work_item_id=proposal.snapshot.work_item_id,
            expected_keep_receipt_id=proposal.snapshot.keep_receipt_id,
            expected_keep_receipt_digest=proposal.snapshot.keep_receipt_digest,
            expected_material_meaning_digest=proposal.snapshot.material_meaning_digest,
            source_fact_ids=tuple(fact.source_fact_id for fact in proposal.snapshot.selected_facts),
            attempt=proposal.attempt,
        )
        expected_proposal = prepare_source_fact_authority_v2(command, identity=identity)
    except Exception:
        return None, [
            "Current page, KEEP receipt, registry, card, or selected facts changed before apply."
        ]
    if expected_proposal.proposal_digest != proposal.proposal_digest:
        return None, ["Selected facts, KEEP receipt, or page material changed before apply."]
    expected_action = source_fact_authority_v2_action(proposal)
    if action.payload != expected_action.payload:
        return None, ["Source fact authority v2 ActionObject payload changed before apply."]
    from wilq.actions.action_chain import revision_bound_action_chain

    payload_digest = canonical_json_digest(action.payload)
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=_confirmation_actor(audit_events, action.id),
        binding_from_event=_v2_audit_binding,
        expected_binding=(proposal.snapshot.context_digest, payload_digest),
    )
    if chain is None:
        return None, [blockers[0].reason]
    preview, review, confirmation, impact = chain
    provisional = {
        "schema_version": "wilq_content_source_fact_authority_receipt_v2",
        "receipt_id": "",
        "receipt_digest": "0" * 64,
        "action_id": action.id,
        "action_payload_digest": payload_digest,
        "snapshot": proposal.snapshot.model_dump(mode="json"),
        "verification_evidence_ids": tuple(identity.current_evidence_ids),
        "verification_registry_digest": expected_proposal.snapshot.registry_digest,
        "preview_audit_id": preview.id,
        "review_audit_id": review.id,
        "confirmation_audit_id": confirmation.id,
        "impact_audit_id": impact.id,
        "reviewed_by": review.actor,
        "confirmed_by": confirmation.actor,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    digest = source_fact_authority_v2_receipt_digest(provisional)
    receipt = ContentSourceFactAuthorityV2Receipt.model_validate(
        provisional
        | {
            "receipt_id": f"content_source_fact_authority_v2_receipt_{digest}",
            "receipt_digest": digest,
        }
    )
    status, stored = store.record_source_fact_authority_v2_receipt(receipt)
    if status == "conflict":
        return None, ["Source fact authority v2 receipt conflicts with its stored proposal."]
    return {
        "receipt_id": stored.receipt_id,
        "status": status,
        "generation_allowed": False,
        "external_write_attempted": False,
        "mutation_adapter": SOURCE_FACT_AUTHORITY_V2_MUTATION_ADAPTER,
    }, []


def _validate_regulatory_facts(
    selected: tuple[ContentSourceFactCandidateV2, ...],
    canonical_path: str | None,
    service_card_id: str | None,
    facts: tuple[ContentSourceFact, ...],
) -> None:
    legal_ids = {fact.source_fact_id for fact in selected if fact.source_type == "legal_update"}
    if not legal_ids:
        return
    try:
        coverage = regulatory_content_coverage(
            service_card_id=service_card_id,
            canonical_path=canonical_path,
            source_facts=facts,
        )
    except ValueError as error:
        raise SourceFactAuthorityV2Blocked(
            "regulatory_source_policy_not_current",
            "Sprawdź bieżący profil prawny, jego wersję, źródło i dowody przed wyborem faktu.",
            tuple(
                sorted(
                    {
                        evidence
                        for fact in selected
                        if fact.source_fact_id in legal_ids
                        for evidence in fact.evidence_ids
                    }
                )
            ),
        ) from error
    if not legal_ids.issubset(set(coverage.source_fact_ids)):
        raise SourceFactAuthorityV2Blocked(
            "regulatory_source_policy_not_current",
            "Sprawdź bieżący profil prawny, jego wersję, źródło i dowody przed wyborem faktu.",
            tuple(
                sorted(
                    {
                        evidence
                        for fact in selected
                        if fact.source_fact_id in legal_ids
                        for evidence in fact.evidence_ids
                    }
                )
            ),
        )


def _validate_selected_freshness_dates(
    selected: tuple[ContentSourceFactCandidateV2, ...],
) -> None:
    today = datetime.now(UTC).date()
    invalid: list[ContentSourceFactCandidateV2] = []
    for fact in selected:
        try:
            observed = date.fromisoformat(fact.freshness_date)
        except ValueError:
            invalid.append(fact)
            continue
        if observed > today:
            invalid.append(fact)
    if invalid:
        raise SourceFactAuthorityV2Blocked(
            "source_fact_freshness_invalid",
            "Uzupełnij zatwierdzony fact źródłowy z prawidłową datą obserwacji.",
            tuple(sorted({evidence for fact in invalid for evidence in fact.evidence_ids})),
        )


def _v2_audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("source_fact_authority_v2_snapshot_digest")
    payload = event.details.get("source_fact_authority_v2_action_payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _confirmation_actor(events: list[AuditEvent], action_id: str) -> str:
    events = sorted(
        (
            event
            for event in events
            if event.action_id == action_id and event.event_type == "action_apply_confirmed"
        ),
        key=lambda event: (event.created_at, event.id),
    )
    return events[-1].actor if events else ""


__all__ = [
    "SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE",
    "SOURCE_FACT_AUTHORITY_V2_MUTATION_ADAPTER",
    "SOURCE_FACT_AUTHORITY_V2_PREVIEW_CONTRACT",
    "SOURCE_FACT_AUTHORITY_V2_BLOCKER_OWNER",
    "ContentSourceFactAuthorityV2BlockerCode",
    "ContentSourceFactAuthorityV2PreviewCommand",
    "ContentSourceFactAuthorityV2Proposal",
    "ContentSourceFactAuthorityV2Receipt",
    "ContentSourceFactAuthorityV2Snapshot",
    "SourceFactAuthorityV2Blocked",
    "execute_source_fact_authority_v2",
    "prepare_source_fact_authority_v2",
    "source_fact_authority_v2_action",
    "source_fact_authority_v2_projection",
    "source_fact_authority_v2_snapshot_digest",
    "validate_source_fact_authority_v2_payload",
]
