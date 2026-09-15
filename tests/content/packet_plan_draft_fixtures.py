from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tests.content.test_research_packet import legacy_exact_source_pack_fixture
from tests.content.test_source_pack_binding import _setup_store
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.research_packet import (
    ContentResearchPacketRecordResult,
    reconcile_content_research_packet,
)
from wilq.content.workflow.research_packet_preparation_receipt import (
    ContentResearchPacketPreparationReceipt,
    ContentResearchPacketPreparationReceiptRecordResult,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    content_source_pack_binding_digest,
    content_source_pack_binding_logical_id,
    evidence_ids_digest,
)


@dataclass
class PacketPreparationCase:
    store: Any
    identity: Any
    source_pack: ContentSourcePackBinding
    planning_input: ContentPlanningInput
    snapshot: Any


class PacketPreparationStore:
    def __init__(self, identity: Any, source_pack: ContentSourcePackBinding) -> None:
        self.identity = identity
        self.source_pack = source_pack
        self.classification = SimpleNamespace(
            run_id=identity.classification_run_id,
            run_digest=identity.classification_run_digest,
            decision_set_digest=identity.classification_decision_set_digest,
            row=SimpleNamespace(source_packet_row_digest=identity.classification_source_row_digest),
        )
        self.authority = SimpleNamespace(
            receipt_id=source_pack.source_fact_authority_receipt_id,
            receipt_digest=source_pack.source_fact_authority_receipt_digest,
        )
        self.packets: dict[str, Any] = {}
        self.preparation_receipts: dict[str, ContentResearchPacketPreparationReceipt] = {}

    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[ContentSourcePackBinding]:
        return (
            [self.source_pack]
            if current_work_item_id in {None, self.identity.current_work_item_id}
            else []
        )

    def load_content_source_pack_binding(self, binding_id: str) -> ContentSourcePackBinding | None:
        return self.source_pack if binding_id == self.source_pack.binding_id else None

    def load_content_delivery_identity(self, binding_id: str) -> Any:
        return self.identity if binding_id == self.identity.binding_id else None

    def load_production_classification_for_work_item(self, work_item_id: str) -> Any:
        return self.classification if work_item_id == self.identity.current_work_item_id else None

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> Any:
        del source_fact_ids
        return self.authority if (
            identity_binding_id == self.identity.binding_id
            and current_work_item_id == self.identity.current_work_item_id
        ) else None

    def record_content_research_packet(self, command: Any) -> ContentResearchPacketRecordResult:
        receipt = self.preparation_receipts.get(command.preparation_receipt_id)
        packet = reconcile_content_research_packet(
            command,
            self.identity,
            self.source_pack,
            preparation_receipt=receipt,
        )
        prior = self.packets.get(packet.packet_id)
        if prior is not None:
            return ContentResearchPacketRecordResult(status="idempotent", packet=prior)
        self.packets[packet.packet_id] = packet
        return ContentResearchPacketRecordResult(status="created", packet=packet)

    def _record_content_research_packet_preparation_receipt(
        self, receipt: ContentResearchPacketPreparationReceipt
    ) -> ContentResearchPacketPreparationReceiptRecordResult:
        existing = self.preparation_receipts.get(receipt.receipt_id)
        if existing is not None:
            return ContentResearchPacketPreparationReceiptRecordResult(
                status=(
                    "idempotent"
                    if existing.receipt_digest == receipt.receipt_digest
                    else "conflict"
                ),
                receipt=existing,
            )
        self.preparation_receipts[receipt.receipt_id] = receipt
        return ContentResearchPacketPreparationReceiptRecordResult(
            status="created", receipt=receipt
        )

    def _load_content_research_packet_preparation_receipt(
        self, receipt_id: str
    ) -> ContentResearchPacketPreparationReceipt | None:
        return self.preparation_receipts.get(receipt_id)

    def load_content_research_packet(self, packet_id: str) -> Any:
        return self.packets.get(packet_id)


def build_packet_preparation_case(tmp_path: Path) -> PacketPreparationCase:
    base_store, identity = _setup_store(tmp_path)
    legacy_pack = legacy_exact_source_pack_fixture(base_store, identity)
    source_pack = _build_authority_source_pack(legacy_pack)
    store = PacketPreparationStore(identity, source_pack)
    brief = ContentSalesBrief.model_construct(
        id="sales_brief_packet_prepare",
        work_item_id=identity.current_work_item_id,
        evidence_ids=["ev_brief_packet"],
        cta_destination="/kontakt/",
    )
    return PacketPreparationCase(
        store=store,
        identity=identity,
        source_pack=source_pack,
        planning_input=_build_planning_input(identity),
        snapshot=_build_snapshot(identity, brief),
    )


def _build_authority_source_pack(
    legacy_pack: ContentSourcePackBinding,
) -> ContentSourcePackBinding:
    authority_id = "content_source_fact_authority_current"
    payload = legacy_pack.model_dump(mode="json")
    payload.update(
        {
            "source_fact_authority_receipt_id": authority_id,
            "source_fact_authority_receipt_digest": "c" * 64,
            "source_fact_authority_snapshot_digest": "d" * 64,
        }
    )
    payload["evidence_ids"] = sorted(
        {
            *payload["evidence_ids"],
            *(
                evidence_id
                for fact in ekologus_source_facts()
                if fact.source_id in payload["source_fact_ids"]
                for evidence_id in fact.evidence_ids
            ),
        }
    )
    payload["evidence_ids_digest"] = evidence_ids_digest(tuple(payload["evidence_ids"]))
    payload.pop("binding_id", None)
    payload.pop("binding_digest", None)
    digest = content_source_pack_binding_digest(payload)
    binding_id = (
        "content_source_pack_binding_"
        f"{content_source_pack_binding_logical_id(payload)[:24]}"
    )
    return ContentSourcePackBinding.model_validate(
        {"binding_id": binding_id, "binding_digest": digest, **payload}
    )


def _build_planning_input(identity: Any) -> ContentPlanningInput:
    demand = ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[
            ContentSearchDemandRow(
                source_kind="gsc_query",
                source_connector="google_search_console",
                term="bdo dla firm",
                page=identity.public_url,
                section_mapping_status="page_only",
                period="2026-09",
                freshness="fresh",
                evidence_ids=[identity.inventory_evidence_ids[0]],
            )
        ],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Sprawdź popyt.",
    )
    return ContentPlanningInput.model_construct(
        planning_input_digest="a" * 64,
        work_item_id=identity.current_work_item_id,
        content_kind="service",
        confirmed_service_card_id="ekologus_service_bdo_reporting",
        service_label="Raportowanie BDO",
        target_reader="Przedsiębiorca",
        buyer_problem="Niepewność obowiązków.",
        buyer_trigger="Zbliżający się termin.",
        search_intent="bdo dla firm",
        source_facts=[],
        source_assessments=[],
        query_portfolio=demand,
        regulatory_coverage=ContentRegulatoryCoverage(),
        inventory=SimpleNamespace(),
        internal_link_candidates=[
            ContentPlanningInternalLinkCandidate(
                target_url="https://www.ekologus.pl/kontakt/",
                anchor_hint="Kontakt",
                evidence_ids=[identity.inventory_evidence_ids[0]],
            )
        ],
        evidence_ids=[identity.inventory_evidence_ids[0]],
    )


def _build_snapshot(identity: Any, brief: ContentSalesBrief) -> Any:
    return SimpleNamespace(
        sales_brief=SimpleNamespace(sales_brief_result=SimpleNamespace(brief=brief)),
        service_profile_context=ContentWorkItemServiceProfileContext.not_evaluated(),
        freshness_assessment={"state": "fresh"},
        preflight=SimpleNamespace(item=SimpleNamespace(evidence_ids=[identity.inventory_evidence_ids[0]])),
    )


def snapshot_without_cta(case: PacketPreparationCase) -> Any:
    return SimpleNamespace(
        sales_brief=SimpleNamespace(
            sales_brief_result=SimpleNamespace(
                brief=ContentSalesBrief.model_construct(
                    id="sales_brief_packet_prepare_missing_cta",
                    work_item_id=case.identity.current_work_item_id,
                    evidence_ids=["ev_brief_packet"],
                    cta_destination="",
                )
            )
        ),
        service_profile_context=ContentWorkItemServiceProfileContext.not_evaluated(),
        freshness_assessment={"state": "fresh"},
        preflight=SimpleNamespace(
            item=SimpleNamespace(evidence_ids=[case.identity.inventory_evidence_ids[0]])
        ),
    )


__all__ = [
    "PacketPreparationCase",
    "PacketPreparationStore",
    "build_packet_preparation_case",
    "snapshot_without_cta",
]
