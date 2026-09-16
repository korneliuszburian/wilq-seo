"""Server-owned preparation and current validation for content research packets."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.source_pack_projection import (
    project_selected_source_pack_facts,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketBlocker,
    ContentResearchPacketCommand,
    ContentResearchPacketRecordResult,
    ResearchPacketBlockerReason,
    ResearchPacketBlockerSeam,
    reconcile_content_research_packet,
)
from wilq.content.workflow.research_packet_derivation import (
    build_server_owned_research_packet_command,
)
from wilq.content.workflow.research_packet_preparation_receipt import (
    ContentResearchPacketPreparationReceipt,
    ContentResearchPacketPreparationReceiptRecordResult,
    build_research_packet_preparation_receipt,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    content_source_pack_context_digest,
    source_fact_registry_digest,
)
from wilq.schemas.core import utc_now


class ResearchPacketPreparationStore(Protocol):
    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[ContentSourcePackBinding]: ...

    def load_content_source_pack_binding(
        self, binding_id: str
    ) -> ContentSourcePackBinding | None: ...

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None: ...

    def load_production_classification_for_work_item(self, work_item_id: str) -> Any: ...

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> Any: ...

    def record_content_research_packet(
        self, command: ContentResearchPacketCommand
    ) -> ContentResearchPacketRecordResult: ...

    def _record_content_research_packet_preparation_receipt(
        self, receipt: ContentResearchPacketPreparationReceipt
    ) -> ContentResearchPacketPreparationReceiptRecordResult: ...

    def _load_content_research_packet_preparation_receipt(
        self, receipt_id: str
    ) -> ContentResearchPacketPreparationReceipt | None: ...

    def load_content_research_packet(self, packet_id: str) -> ContentResearchPacket | None: ...


class ContentResearchPacketPreparationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["created", "idempotent", "blocked", "conflict"]
    packet: ContentResearchPacket | None = None
    blocker: ContentResearchPacketBlocker | None = None

    @classmethod
    def blocked_result(
        cls, blocker: ContentResearchPacketBlocker, *, packet: ContentResearchPacket | None = None
    ) -> ContentResearchPacketPreparationResult:
        return cls(status="blocked", packet=packet, blocker=blocker)


def prepare_content_research_packet(
    *,
    store: ResearchPacketPreparationStore,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    source_pack_binding_id: str | None = None,
    expected_source_pack_binding_digest: str | None = None,
    now: datetime | None = None,
) -> ContentResearchPacketPreparationResult:
    """Derive and persist one packet without accepting caller semantic fields."""

    timestamp = (now or utc_now()).astimezone(UTC)
    source_pack = _select_source_pack(
        store,
        work_item_id=planning_input.work_item_id,
        binding_id=source_pack_binding_id,
        expected_digest=expected_source_pack_binding_digest,
    )
    if isinstance(source_pack, ContentResearchPacketBlocker):
        return ContentResearchPacketPreparationResult.blocked_result(source_pack)
    identity = store.load_content_delivery_identity(source_pack.identity_binding_id)
    if identity is not None and planning_input.work_item_id != identity.current_work_item_id:
        return ContentResearchPacketPreparationResult.blocked_result(
            _blocker(
                "work_item_identity",
                "work_item_mismatch",
                identity.inventory_evidence_ids,
                "Planning input musi należeć do bieżącego work itemu identity.",
            )
        )
    blocker = _current_source_pack_blocker(store, source_pack, identity)
    if blocker is not None:
        return ContentResearchPacketPreparationResult.blocked_result(blocker)
    if identity is None:
        return ContentResearchPacketPreparationResult.blocked_result(
            _blocker(
                "identity_binding",
                "identity_binding_missing",
                source_pack.evidence_ids,
                "Najpierw zapisz exact delivery identity dla tej paczki źródłowej.",
            )
        )
    projected_input_or_blocker = _project_source_pack_input_or_blocker(
        planning_input=planning_input,
        source_pack=source_pack,
    )
    if isinstance(projected_input_or_blocker, ContentResearchPacketBlocker):
        return ContentResearchPacketPreparationResult.blocked_result(projected_input_or_blocker)
    command_or_blocker = build_server_owned_research_packet_command(
        snapshot=snapshot,
        planning_input=projected_input_or_blocker,
        source_pack=source_pack,
        identity=identity,
        now=timestamp,
    )
    if isinstance(command_or_blocker, ContentResearchPacketBlocker):
        return ContentResearchPacketPreparationResult.blocked_result(command_or_blocker)
    receipt = build_research_packet_preparation_receipt(
        command_or_blocker,
        recorded_at=timestamp,
    )
    receipt_result = store._record_content_research_packet_preparation_receipt(receipt)
    if receipt_result.status == "conflict":
        return ContentResearchPacketPreparationResult.blocked_result(
            _blocker(
                "preparation_receipt",
                "preparation_receipt_conflict",
                command_or_blocker.evidence_ids,
                "Istnieje inny preparation receipt dla tego exact kontekstu; odśwież packet.",
            )
        )
    command = command_or_blocker.model_copy(
        update={
            "preparation_receipt_id": receipt_result.receipt.receipt_id,
            "preparation_receipt_digest": receipt_result.receipt.receipt_digest,
        }
    )
    result = store.record_content_research_packet(command)
    if result.status == "conflict":
        return ContentResearchPacketPreparationResult.blocked_result(
            _blocker(
                "source_pack_binding",
                "packet_conflict",
                result.packet.evidence_ids,
                "Zachowany packet ma inny digest; odśwież exact source-pack i kontekst.",
            ),
            packet=result.packet,
        )
    if result.packet.status != "exact_current":
        return ContentResearchPacketPreparationResult.blocked_result(
            result.packet.blocker
            or _blocker(
                "source_pack_binding",
                "source_pack_binding_blocked",
                result.packet.evidence_ids,
                "Usuń typed blocker packetu i odśwież jego exact kontekst.",
            ),
            packet=result.packet,
        )
    return ContentResearchPacketPreparationResult(
        status=result.status,
        packet=result.packet,
    )


def current_research_packet_blocker(
    *,
    store: ResearchPacketPreparationStore,
    packet: ContentResearchPacket,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
) -> ContentResearchPacketBlocker | None:
    """Compare a persisted packet with a freshly derived, non-persisted packet."""

    if planning_input.work_item_id != packet.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            packet.evidence_ids,
            "Bieżący planning input musi należeć do work itemu packetu.",
        )
    source_pack_or_blocker = _revalidation_source_pack(store, packet)
    if isinstance(source_pack_or_blocker, ContentResearchPacketBlocker):
        return source_pack_or_blocker
    source_pack = source_pack_or_blocker
    identity = store.load_content_delivery_identity(packet.identity_binding_id)
    blocker = _current_source_pack_blocker(store, source_pack, identity)
    if blocker is not None:
        return blocker
    if identity is None:
        return _blocker(
            "identity_binding",
            "identity_binding_missing",
            packet.evidence_ids,
            "Odczytaj bieżący identity binding przed użyciem packetu.",
        )
    projected_input_or_blocker = _project_source_pack_input_or_blocker(
        planning_input=planning_input,
        source_pack=source_pack,
    )
    if isinstance(projected_input_or_blocker, ContentResearchPacketBlocker):
        return projected_input_or_blocker
    projected_input = projected_input_or_blocker
    command = build_server_owned_research_packet_command(
        snapshot=snapshot,
        planning_input=projected_input,
        source_pack=source_pack,
        identity=identity,
        now=utc_now(),
    )
    if isinstance(command, ContentResearchPacketBlocker):
        return command
    if command.context_receipt != packet.context_receipt:
        return _blocker(
            "identity_binding",
            "context_receipt_mismatch",
            packet.evidence_ids,
            "Bieżący server-owned context receipt różni się od packetu; odśwież packet.",
        )
    if packet.preparation_receipt_id is None or packet.preparation_receipt_digest is None:
        return _blocker(
            "preparation_receipt",
            "preparation_receipt_missing",
            packet.evidence_ids,
            "Przygotuj server-owned preparation receipt przed użyciem packetu.",
        )
    command = command.model_copy(
        update={
            "preparation_receipt_id": packet.preparation_receipt_id,
            "preparation_receipt_digest": packet.preparation_receipt_digest,
        }
    )
    expected = reconcile_content_research_packet(
        command,
        identity,
        source_pack,
        preparation_receipt=store._load_content_research_packet_preparation_receipt(
            packet.preparation_receipt_id
        ),
        now=utc_now(),
    )
    if expected.status != "exact_current":
        return expected.blocker or _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            expected.evidence_ids,
            "Odśwież packet po rozwiązaniu bieżącej blokady źródeł.",
        )
    if expected.packet_id != packet.packet_id or expected.packet_digest != packet.packet_digest:
        return _blocker(
            "source_pack_binding",
            "packet_conflict",
            tuple(sorted(set(packet.evidence_ids) | set(expected.evidence_ids))),
            "Kontekst packetu zmienił się; wygeneruj nowy plan z bieżącego packetu.",
        )
    return None


def _project_source_pack_input_or_blocker(
    *,
    planning_input: ContentPlanningInput,
    source_pack: ContentSourcePackBinding,
) -> ContentPlanningInput | ContentResearchPacketBlocker:
    try:
        return project_selected_source_pack_facts(
            planning_input,
            source_pack.source_fact_ids,
            ekologus_source_facts(),
        )
    except ValueError:
        return _blocker(
            "source_facts",
            "source_fact_not_registered",
            source_pack.evidence_ids,
            "Odśwież source-fact registry i source-pack względem bieżących faktów.",
        )


def _revalidation_source_pack(
    store: ResearchPacketPreparationStore,
    packet: ContentResearchPacket,
) -> ContentSourcePackBinding | ContentResearchPacketBlocker:
    if packet.status != "exact_current":
        return packet.blocker or _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            packet.evidence_ids,
            "Usuń blocker packetu i przygotuj nowy exact input.",
        )
    if packet.context_receipt is None:
        return _blocker(
            "identity_binding",
            "context_receipt_missing",
            packet.evidence_ids,
            "Przygotuj exact typed context receipt przed generowaniem.",
        )
    latest_pack = latest_source_pack_for_work_item(store, packet.current_work_item_id)
    if latest_pack is None:
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            packet.evidence_ids,
            "Odczytaj najnowszy source-pack binding; historyczny packet nie wystarcza.",
        )
    if latest_pack.status != "exact_current":
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            latest_pack.evidence_ids,
            "Usuń blocker najnowszego source-packu przed użyciem packetu.",
        )
    if (
        latest_pack.binding_id != packet.source_pack_binding_id
        or latest_pack.binding_digest != packet.source_pack_binding_digest
    ):
        return _blocker(
            "source_pack_binding",
            "packet_conflict",
            tuple(sorted(set(packet.evidence_ids) | set(latest_pack.evidence_ids))),
            "Wygeneruj nowy packet z najnowszego source-pack bindingu.",
        )
    source_pack = store.load_content_source_pack_binding(packet.source_pack_binding_id)
    if source_pack is None:
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            packet.evidence_ids,
            "Odczytaj bieżący source-pack binding; historyczny packet nie wystarcza.",
        )
    return source_pack


def latest_source_pack_for_work_item(
    store: ResearchPacketPreparationStore,
    work_item_id: str,
) -> ContentSourcePackBinding | None:
    packs = store.list_content_source_pack_bindings(current_work_item_id=work_item_id)
    return max(packs, key=lambda item: (item.recorded_at, item.binding_id)) if packs else None


# Keep the old internal name for existing callers while the public shared seam
# owns the single newest-receipt policy.
_latest_source_pack_for_work_item = latest_source_pack_for_work_item


def _select_source_pack(
    store: ResearchPacketPreparationStore,
    *,
    work_item_id: str,
    binding_id: str | None,
    expected_digest: str | None,
) -> ContentSourcePackBinding | ContentResearchPacketBlocker:
    if binding_id is not None:
        pack = store.load_content_source_pack_binding(binding_id)
        if pack is None:
            return _blocker(
                "source_pack_binding",
                "source_pack_binding_missing",
                (),
                "Wskaż istniejący exact source-pack binding dla tego work itemu.",
            )
        if expected_digest is not None and pack.binding_digest != expected_digest:
            return _blocker(
                "source_pack_binding",
                "source_pack_binding_digest_mismatch",
                pack.evidence_ids,
                "Użyj digestu odczytanego z tego samego source-pack bindingu.",
            )
        if pack.current_work_item_id != work_item_id:
            return _blocker(
                "work_item_identity",
                "work_item_mismatch",
                pack.evidence_ids,
                "Wskaż source-pack binding należący do bieżącego work itemu.",
            )
        return pack
    pack = latest_source_pack_for_work_item(store, work_item_id)
    if pack is None:
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            (),
            "Zapisz exact current source-pack binding przed przygotowaniem planu.",
        )
    # The shared selector keeps the newest relevant receipt authoritative,
    # including when that newest receipt is blocked.
    return pack


def _current_source_pack_blocker(
    store: ResearchPacketPreparationStore,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding | None,
) -> ContentResearchPacketBlocker | None:
    if source_pack.status != "exact_current":
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            source_pack.evidence_ids
            if source_pack.blocker is None
            else tuple(source_pack.blocker.evidence_ids),
            "Odśwież source-pack po rozwiązaniu typed blokady.",
        )
    if identity is None:
        return _blocker(
            "identity_binding",
            "identity_binding_missing",
            source_pack.evidence_ids,
            "Odczytaj exact identity binding związany ze source-packiem.",
        )
    if source_pack.current_work_item_id != identity.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            source_pack.evidence_ids,
            "Zwiąż source-pack z bieżącym work itemem identity.",
        )
    if (
        identity.status != "exact_current"
        or identity.binding_id != source_pack.identity_binding_id
        or identity.binding_digest != source_pack.identity_binding_digest
    ):
        return _blocker(
            "identity_binding",
            "identity_binding_blocked",
            identity.inventory_evidence_ids,
            "Odśwież source-pack i identity dla bieżącej klasyfikacji.",
        )
    if identity.final_disposition != "keep":
        return _blocker(
            "work_item_identity",
            "disposition_not_keep",
            identity.inventory_evidence_ids,
            "Packet produkcyjny twórz wyłącznie dla URL-a z decyzją keep.",
        )
    classification = store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    row = None if classification is None else getattr(classification, "row", None)
    if (
        classification is None
        or row is None
        or classification.run_id != identity.classification_run_id
        or classification.run_digest != identity.classification_run_digest
        or getattr(classification, "decision_set_digest", None)
        != identity.classification_decision_set_digest
        or row.source_packet_row_digest != identity.classification_source_row_digest
    ):
        return _blocker(
            "identity_binding",
            "identity_binding_blocked",
            identity.inventory_evidence_ids,
            "Odśwież bieżącą klasyfikację i zwiąż ponownie source-pack.",
        )
    authority = store.load_content_source_fact_authority_receipt_for_identity(
        identity.binding_id,
        identity.current_work_item_id,
        source_pack.source_fact_ids,
    )
    if authority is None or (
        source_pack.source_fact_authority_receipt_id != getattr(authority, "receipt_id", None)
        or source_pack.source_fact_authority_receipt_digest
        != getattr(authority, "receipt_digest", None)
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            source_pack.evidence_ids,
            "Odśwież exact authorized-facts receipt dla bieżącego identity.",
        )
    if source_pack.source_fact_registry_receipt.registry_digest != source_fact_registry_digest():
        return _blocker(
            "source_pack_binding",
            "source_fact_registry_stale",
            source_pack.evidence_ids,
            "Odśwież source-fact registry i utwórz nowy source-pack.",
        )
    attestation = source_pack.fresh_context_attestation
    if (
        attestation.context_digest != content_source_pack_context_digest(identity, attestation)
        or attestation.run_id != identity.classification_run_id
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            source_pack.evidence_ids,
            "Odśwież context attestation dla bieżącej klasyfikacji.",
        )
    return None


def current_source_pack_blocker(
    *,
    store: ResearchPacketPreparationStore,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding | None,
) -> ContentResearchPacketBlocker | None:
    """Revalidate one source-pack receipt for shared read-only consumers."""

    return _current_source_pack_blocker(store, source_pack, identity)


def _blocker(
    seam: ResearchPacketBlockerSeam,
    reason: ResearchPacketBlockerReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentResearchPacketBlocker:
    return ContentResearchPacketBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step_pl=next_step,
    )


__all__ = [
    "ContentResearchPacketPreparationResult",
    "ResearchPacketPreparationStore",
    "build_server_owned_research_packet_command",
    "current_source_pack_blocker",
    "current_research_packet_blocker",
    "latest_source_pack_for_work_item",
    "prepare_content_research_packet",
]
