"""Resolve the exact planning context used by advisory content reviews.

The planning and draft seams persist a planning-input digest after binding an
immutable research packet.  A review must therefore rebuild the ordinary
planning input first, bind the persisted packet, and only then compare the
digest and current authority.  Keeping that work behind one domain interface
prevents semantic and independent review from quietly growing two different
revalidation ladders.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    bind_research_packet_to_planning_input,
    build_content_planning_input,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketBlocker,
    ContentResearchPacketCurrentProjection,
)
from wilq.content.workflow.research_packet_current import revalidate_content_research_packet
from wilq.content.workflow.research_packet_preparation import ResearchPacketPreparationStore


@dataclass(frozen=True, slots=True)
class ContentReviewBindingBlocker:
    """A transport-neutral blocker returned before an advisory review turn."""

    code: str
    label: str
    reason: str
    next_step: str
    source_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContentReviewInputs:
    """The exact review inputs, including the packet projection when present."""

    revision: ContentDraftRevision
    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal
    packet: ContentResearchPacket | None = None
    current_packet: ContentResearchPacketCurrentProjection | None = None


@dataclass(frozen=True, slots=True)
class ContentReviewClaimToken:
    """Immutable scalar authority expected by the same-DB claim transaction."""

    work_item_id: str
    revision_id: str
    revision_digest: str
    planning_digest: str | None
    planning_input_digest: str | None
    proposal_id: str | None
    packet_id: str
    packet_digest: str
    current_packet_status: str | None
    current_source_pack_binding_id: str | None
    current_source_pack_binding_digest: str | None
    current_identity_binding_id: str | None
    current_identity_binding_digest: str | None
    source_pack_binding_id: str
    source_pack_binding_digest: str
    identity_binding_id: str
    identity_binding_digest: str
    classification_run_id: str | None
    classification_run_digest: str | None
    classification_source_row_digest: str | None
    source_fact_receipt_id: str | None
    source_fact_receipt_digest: str | None
    source_fact_snapshot_digest: str | None
    source_fact_provenance_digest: str | None
    source_fact_registry_digest: str
    source_facts_digest: str


@dataclass(frozen=True, slots=True)
class ContentReviewInputResolution:
    """One successful review context or one typed blocker."""

    inputs: ContentReviewInputs | None = None
    blocker: ContentReviewBindingBlocker | None = None

    def __post_init__(self) -> None:
        if (self.inputs is None) == (self.blocker is None):
            raise ValueError("Review input resolution requires exactly one outcome.")


ReviewSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def same_content_review_inputs(
    first: Any,
    second: Any,
) -> bool:
    """Compare the complete immutable identity used by both review writers."""

    return (
        first.revision.revision_id == second.revision.revision_id
        and first.revision.content_digest == second.revision.content_digest
        and first.revision.planning_digest == second.revision.planning_digest
        and first.revision.planning_input_digest == second.revision.planning_input_digest
        and first.revision.research_packet_id == second.revision.research_packet_id
        and first.revision.research_packet_digest == second.revision.research_packet_digest
        and first.proposal.proposal_id == second.proposal.proposal_id
        and first.proposal.planning_digest == second.proposal.planning_digest
        and first.proposal.planning_input_digest == second.proposal.planning_input_digest
        and first.proposal.research_packet_id == second.proposal.research_packet_id
        and first.proposal.research_packet_digest == second.proposal.research_packet_digest
        and (
            None
            if getattr(first, "packet", None) is None
            else first.packet.packet_id
        )
        == (
            None
            if getattr(second, "packet", None) is None
            else second.packet.packet_id
        )
        and (
            None
            if getattr(first, "packet", None) is None
            else first.packet.packet_digest
        )
        == (
            None
            if getattr(second, "packet", None) is None
            else second.packet.packet_digest
        )
        and _current_packet_projection(first) == _current_packet_projection(second)
    )


def _current_packet_projection(inputs: Any) -> tuple[Any, ...] | None:
    current = getattr(inputs, "current_packet", None)
    if current is None:
        return None
    return (
        getattr(current, "status", None),
        getattr(current, "packet_id", None),
        getattr(current, "packet_digest", None),
        getattr(current, "current_work_item_id", None),
        getattr(current, "current_source_pack_binding_id", None),
        getattr(current, "current_source_pack_binding_digest", None),
        getattr(current, "current_identity_binding_id", None),
        getattr(current, "current_identity_binding_digest", None),
        _projection_value(getattr(current, "blocker", None)),
    )


def _projection_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return _projection_value(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _projection_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_projection_value(item) for item in value)
    if hasattr(value, "__dict__"):
        return _projection_value(vars(value))
    return repr(value)


def content_review_revision_is_packet_bound(
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal | None = None,
) -> bool:
    values = (
        getattr(revision, "research_packet_id", None),
        getattr(revision, "research_packet_digest", None),
        None if proposal is None else getattr(proposal, "research_packet_id", None),
        None if proposal is None else getattr(proposal, "research_packet_digest", None),
    )
    return any(value is not None for value in values)


def content_review_inputs_match_revision(
    expected: ContentDraftRevision,
    actual: ContentReviewInputs,
) -> bool:
    revision_fields = (
        "work_item_id",
        "revision_id",
        "content_digest",
        "planning_digest",
        "planning_input_digest",
        "research_packet_id",
        "research_packet_digest",
    )
    if any(
        getattr(expected, field, None) != getattr(actual.revision, field, None)
        for field in revision_fields
    ):
        return False
    proposal = actual.proposal
    if (
        proposal.work_item_id != expected.work_item_id
        or proposal.planning_digest != expected.planning_digest
        or proposal.planning_input_digest != expected.planning_input_digest
        or proposal.research_packet_id != expected.research_packet_id
        or proposal.research_packet_digest != expected.research_packet_digest
    ):
        return False
    packet_bound = content_review_revision_is_packet_bound(expected, proposal)
    if not packet_bound:
        return actual.packet is None and actual.current_packet is None
    if actual.packet is None or actual.current_packet is None:
        return False
    expected_packet_id = getattr(expected, "research_packet_id", None)
    expected_packet_digest = getattr(expected, "research_packet_digest", None)
    if expected_packet_id is None:
        expected_packet_id = proposal.research_packet_id
        expected_packet_digest = proposal.research_packet_digest
    if (
        actual.packet.packet_id != expected_packet_id
        or actual.packet.packet_digest != expected_packet_digest
        or actual.current_packet.status != "current"
        or actual.current_packet.packet_id != expected_packet_id
        or actual.current_packet.packet_digest != expected_packet_digest
        or actual.current_packet.current_work_item_id != expected.work_item_id
    ):
        return False
    planning_input = actual.planning_input
    return (
        planning_input.work_item_id == expected.work_item_id
        and planning_input.planning_input_digest == expected.planning_input_digest
        and planning_input.research_packet_id == expected.research_packet_id
        and planning_input.research_packet_digest == expected.research_packet_digest
    )


def claim_token_for_review_inputs(
    inputs: ContentReviewInputs,
) -> ContentReviewClaimToken | None:
    packet = inputs.packet
    packet_bound = content_review_revision_is_packet_bound(inputs.revision, inputs.proposal)
    if packet is None:
        if packet_bound:
            raise ValueError("Packet-bound review inputs require an exact packet.")
        return None
    context = packet.context_receipt
    current = inputs.current_packet
    if not packet_bound or current is None:
        raise ValueError("Packet-bound review inputs require current packet projection.")
    return ContentReviewClaimToken(
        work_item_id=inputs.revision.work_item_id,
        revision_id=inputs.revision.revision_id,
        revision_digest=inputs.revision.content_digest,
        planning_digest=inputs.revision.planning_digest,
        planning_input_digest=inputs.revision.planning_input_digest,
        proposal_id=inputs.proposal.proposal_id,
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
        current_packet_status=None if current is None else current.status,
        current_source_pack_binding_id=(
            None if current is None else current.current_source_pack_binding_id
        ),
        current_source_pack_binding_digest=(
            None if current is None else current.current_source_pack_binding_digest
        ),
        current_identity_binding_id=(
            None if current is None else current.current_identity_binding_id
        ),
        current_identity_binding_digest=(
            None if current is None else current.current_identity_binding_digest
        ),
        source_pack_binding_id=packet.source_pack_binding_id,
        source_pack_binding_digest=packet.source_pack_binding_digest,
        identity_binding_id=packet.identity_binding_id,
        identity_binding_digest=packet.identity_binding_digest,
        classification_run_id=None if context is None else context.classification_run_id,
        classification_run_digest=(
            None if context is None else context.classification_run_digest
        ),
        classification_source_row_digest=(
            None if context is None else context.classification_source_row_digest
        ),
        source_fact_receipt_id=(
            None if context is None else context.source_fact_authority_receipt_id
        ),
        source_fact_receipt_digest=(
            None if context is None else context.source_fact_authority_receipt_digest
        ),
        source_fact_snapshot_digest=(
            None if context is None else context.source_fact_authority_snapshot_digest
        ),
        source_fact_provenance_digest=(
            None if context is None else context.source_fact_authority_provenance_digest
        ),
        source_fact_registry_digest=packet.source_fact_registry_digest,
        source_facts_digest=packet.source_facts_digest,
    )




def content_review_snapshot_packet_pair(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> tuple[str | None, str | None]:
    revision = snapshot.revision_workspace.latest_revision
    planning = getattr(snapshot, "planning_workspace", None)
    proposal = None if planning is None else getattr(planning, "proposal", None)
    revision_pair = (
        None if revision is None else getattr(revision, "research_packet_id", None),
        None if revision is None else getattr(revision, "research_packet_digest", None),
    )
    proposal_pair = (
        None if proposal is None else getattr(proposal, "research_packet_id", None),
        None if proposal is None else getattr(proposal, "research_packet_digest", None),
    )
    return revision_pair if any(value is not None for value in revision_pair) else proposal_pair


def content_review_snapshot_is_packet_bound(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> bool:
    revision = snapshot.revision_workspace.latest_revision
    planning = getattr(snapshot, "planning_workspace", None)
    proposal = None if planning is None else getattr(planning, "proposal", None)
    return any(
        getattr(item, field, None) is not None
        for item in (revision, proposal)
        if item is not None
        for field in ("research_packet_id", "research_packet_digest")
    )


def resolve_content_review_inputs(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    workflow_store: ResearchPacketPreparationStore,
    snapshot_loader: ReviewSnapshotLoader | None = None,
    planning_input_builder: Callable[..., Any] | None = None,
) -> ContentReviewInputResolution:
    """Load and validate the exact persisted proposal, packet and current state.

    ``snapshot`` is the API-owned projection containing the persisted planning
    proposal.  A loader is supplied by queued/public routes for the second
    check, so that the same interface can re-read the latest revision before a
    review is persisted.  No model or review-store side effect occurs here.
    """

    current_snapshot = snapshot
    if snapshot_loader is not None:
        try:
            current_snapshot = snapshot_loader(snapshot.preflight.item.id)
        except Exception:
            return _blocked(
                "stale_content_context",
                "Zmienił się kontekst treści",
                "Nie można odczytać bieżącego snapshotu przed advisory review.",
                "Odśwież workspace i uruchom review dla bieżącej wersji.",
            )

    revision_and_proposal = _load_revision_and_proposal(
        snapshot=current_snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
    )
    if isinstance(revision_and_proposal, ContentReviewInputResolution):
        return revision_and_proposal
    revision, proposal = revision_and_proposal
    if (
        revision.planning_digest != proposal.planning_digest
        or revision.planning_input_digest != proposal.planning_input_digest
    ):
        return _blocked(
            "planning_digest_mismatch",
            "Plan nie odpowiada dokładnej wersji",
            "Zapisany proposal i revision nie mają wspólnego planning digestu oraz tożsamości.",
            "Wygeneruj nową wersję z dokładnego planu.",
        )

    packet_pair = _packet_pair(revision, proposal)
    if packet_pair is None:
        if revision.research_packet_id is not None or proposal.research_packet_id is not None:
            return _blocked(
                "research_packet_conflict",
                "Research packet nie jest aktualny",
                "Revision i persisted proposal nie mają kompletnego packet bindingu.",
                "Odśwież exact packet i wygeneruj nową wersję planu.",
            )
    else:
        packet_id, packet_digest = packet_pair
        packet = workflow_store.load_content_research_packet(packet_id)
        if packet is None:
            return _blocked(
                "research_packet_missing",
                "Brakuje exact research packetu",
                "Persisted revision wskazuje packet, którego WILQ nie może odczytać.",
                "Odczytaj bieżący research packet i utwórz nową wersję planu.",
            )
        if (
            packet.packet_digest != packet_digest
            or packet.current_work_item_id != revision.work_item_id
            or packet.packet_id != packet_id
        ):
            return _blocked(
                "research_packet_conflict",
                "Research packet nie odpowiada dokładnej wersji",
                "Packet ID, digest albo work item nie zgadza się z persisted revision.",
                "Odśwież exact packet i wygeneruj nową wersję planu.",
                source_codes=(packet.packet_id, packet.packet_digest),
            )
        return _resolve_packet_bound(
            snapshot=current_snapshot,
            revision=revision,
            proposal=proposal,
            packet=packet,
            workflow_store=workflow_store,
            planning_input_builder=planning_input_builder,
        )

    return _resolve_unbound(
        snapshot=current_snapshot,
        revision=revision,
        proposal=proposal,
        planning_input_builder=planning_input_builder,
    )


def _load_revision_and_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
) -> tuple[ContentDraftRevision, ContentPlanningProposal] | ContentReviewInputResolution:
    revision = snapshot.revision_workspace.latest_revision
    if revision is None:
        return _blocked(
            "missing_revision",
            "Brakuje pełnej wersji do review",
            "Review wymaga zapisanej exact revision.",
            "Najpierw wygeneruj pełny dokument.",
        )
    if revision.revision_id != revision_id or revision.content_digest != expected_revision_digest:
        return _blocked(
            "stale_revision",
            "Wybrana wersja nie jest aktualna",
            "Revision ID albo digest zmienił się przed review.",
            "Odśwież workspace i uruchom review bieżącej wersji.",
        )
    if revision.schema_version != "wilq_content_draft_revision_v2":
        return _blocked(
            "legacy_revision",
            "Starsza wersja nie zawiera całej strony",
            "Review wymaga rewizji v2 z page assets, FAQ i CTA.",
            "Utwórz pełny dokument v2 przed review.",
        )
    if not snapshot.revision_workspace.context_current:
        return _blocked(
            "stale_content_context",
            "Zmienił się kontekst treści",
            "Plan, inventory, usługa, wiedza albo metryki nie odpowiadają rewizji.",
            "Zrebasuj dokument na aktualny planning input.",
        )
    planning = snapshot.planning_workspace
    proposal = None if planning is None else getattr(planning, "proposal", None)
    if proposal is None:
        return _blocked(
            "missing_planning_input",
            "Brakuje aktualnego wejścia strategicznego",
            "Review musi porównać rewizję z dokładnym zapisanym planem.",
            "Odśwież albo wygeneruj aktualny plan przed review.",
        )
    return revision, proposal


def _resolve_packet_bound(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal,
    packet: ContentResearchPacket,
    workflow_store: ResearchPacketPreparationStore,
    planning_input_builder: Callable[..., Any] | None,
) -> ContentReviewInputResolution:
    revision_work_item_id = getattr(revision, "work_item_id", None)
    revision_content_kind = getattr(revision, "content_kind", None)
    revision_service_card_id = getattr(revision, "service_card_id", None)
    if (
        getattr(proposal, "work_item_id", revision_work_item_id) != revision_work_item_id
        or getattr(proposal, "content_kind", revision_content_kind) != revision_content_kind
        or getattr(proposal, "service_card_id", revision_service_card_id)
        != revision_service_card_id
    ):
        return _blocked(
            "planning_digest_mismatch",
            "Plan nie odpowiada dokładnej wersji",
            "Persisted proposal i packet-bound revision nie mają wspólnej tożsamości.",
            "Wygeneruj nową wersję z dokładnego planu.",
        )
    if packet.status != "exact_current":
        return _packet_blocked(packet.blocker, packet)
    base = _build_base_input(snapshot, proposal, planning_input_builder)
    if isinstance(base, ContentReviewInputResolution):
        return base
    try:
        planning_input = bind_research_packet_to_planning_input(base, packet)
    except (TypeError, ValueError):
        return _blocked(
            "research_packet_conflict",
            "Research packet nie odpowiada dokładnej wersji",
            "Nie można związać packetu z planning input tego persisted proposal.",
            "Odśwież exact packet i wygeneruj nową wersję planu.",
        )
    if (
        planning_input.planning_input_digest != revision.planning_input_digest
        or planning_input.planning_input_digest != proposal.planning_input_digest
        or planning_input.research_packet_id != packet.packet_id
        or planning_input.research_packet_digest != packet.packet_digest
    ):
        return _blocked(
            "planning_digest_mismatch",
            "Planning input nie odpowiada packet-bound wersji",
            "Ponownie zbudowany planning input ma inny digest niż persisted "
            "proposal albo revision.",
            "Wygeneruj nową wersję z bieżącego packetu.",
            source_codes=(packet.packet_id, packet.packet_digest),
        )
    try:
        current = revalidate_content_research_packet(
            store=workflow_store,
            packet=packet,
            snapshot_loader=lambda _work_item_id: snapshot,
        )
    except Exception:
        return _blocked(
            "research_packet_blocked",
            "Research packet nie jest aktualny",
            "Nie można odtworzyć bieżącego source pack, classification, identity "
            "albo context receipt.",
            "Odśwież source pack i research packet przed review.",
        )
    if current.status != "current":
        return _packet_blocked(current.blocker, packet)
    if (
        current.packet_id != packet.packet_id
        or current.packet_digest != packet.packet_digest
        or current.current_work_item_id != revision.work_item_id
    ):
        return _blocked(
            "research_packet_conflict",
            "Bieżąca projekcja packetu nie jest exact",
            "Current packet projection nie wiąże się z persisted revision.",
            "Odśwież workspace i uruchom review dla nowego packetu.",
        )
    return ContentReviewInputResolution(
        inputs=ContentReviewInputs(
            revision=revision,
            planning_input=planning_input,
            proposal=proposal,
            packet=packet,
            current_packet=current,
        )
    )


def _resolve_unbound(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal,
    planning_input_builder: Callable[..., Any] | None,
) -> ContentReviewInputResolution:
    base = _build_base_input(snapshot, proposal, planning_input_builder)
    if isinstance(base, ContentReviewInputResolution):
        return base
    if (
        base.planning_input_digest != revision.planning_input_digest
        or base.planning_input_digest != proposal.planning_input_digest
    ):
        return _blocked(
            "planning_digest_mismatch",
            "Planning input nie odpowiada dokładnej wersji",
            "Ponownie zbudowany planning input ma inny digest niż persisted "
            "proposal albo revision.",
            "Zrebasuj dokument na aktualny planning input.",
        )
    return ContentReviewInputResolution(
        inputs=ContentReviewInputs(
            revision=revision,
            planning_input=base,
            proposal=proposal,
        )
    )


def _build_base_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
    planning_input_builder: Callable[..., Any] | None,
) -> ContentPlanningInput | ContentReviewInputResolution:
    try:
        builder = planning_input_builder or build_content_planning_input
        result = builder(
            snapshot,
            service_card_id=proposal.service_card_id,
        )
    except Exception:
        return _blocked(
            "missing_planning_input",
            "Brakuje aktualnego wejścia strategicznego",
            "Nie można odtworzyć planning input z bieżącego snapshotu.",
            "Odśwież albo wygeneruj aktualny plan przed review.",
        )
    if result.planning_input is None or result.blockers:
        blocker = result.blockers[0] if result.blockers else None
        return _blocked(
            "missing_planning_input" if blocker is None else str(blocker.code),
            "Brakuje aktualnego wejścia strategicznego"
            if blocker is None
            else blocker.label,
            "Planning input ma typed blocker przed review."
            if blocker is None
            else blocker.reason,
            "Odśwież albo wygeneruj aktualny plan przed review."
            if blocker is None
            else blocker.next_step,
            source_codes=() if blocker is None else (str(blocker.code),),
        )
    return result.planning_input


def _packet_pair(
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal,
) -> tuple[str, str] | None:
    revision_pair = (
        getattr(revision, "research_packet_id", None),
        getattr(revision, "research_packet_digest", None),
    )
    proposal_pair = (
        getattr(proposal, "research_packet_id", None),
        getattr(proposal, "research_packet_digest", None),
    )
    if revision_pair != proposal_pair:
        return None
    if revision_pair[0] is None or revision_pair[1] is None:
        return None
    return revision_pair[0], revision_pair[1]


def _packet_blocked(
    blocker: ContentResearchPacketBlocker | None,
    packet: ContentResearchPacket,
) -> ContentReviewInputResolution:
    reason = "research_packet_blocked"
    next_step = "Odśwież source pack i research packet przed review."
    source_codes: tuple[str, ...] = (packet.packet_id, packet.packet_digest)
    if blocker is not None:
        reason = {
            "source_pack_binding_missing": "research_packet_missing",
            "packet_conflict": "research_packet_conflict",
        }.get(blocker.reason, "research_packet_blocked")
        next_step = blocker.next_step_pl
        source_codes = tuple(dict.fromkeys([blocker.reason, *blocker.evidence_ids]))
    return _blocked(
        reason,
        "Research packet nie jest aktualny",
        next_step,
        next_step,
        source_codes=source_codes,
    )


def _blocked(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: tuple[str, ...] = (),
) -> ContentReviewInputResolution:
    return ContentReviewInputResolution(
        blocker=ContentReviewBindingBlocker(
            code=code,
            label=label,
            reason=reason,
            next_step=next_step,
            source_codes=tuple(dict.fromkeys(source_codes)),
        )
    )


__all__ = [
    "ContentReviewBindingBlocker",
    "ContentReviewClaimToken",
    "ContentReviewInputResolution",
    "ContentReviewInputs",
    "ReviewSnapshotLoader",
    "claim_token_for_review_inputs",
    "content_review_inputs_match_revision",
    "content_review_revision_is_packet_bound",
    "content_review_snapshot_is_packet_bound",
    "content_review_snapshot_packet_pair",
    "resolve_content_review_inputs",
    "same_content_review_inputs",
]
