from __future__ import annotations

import sqlite3
import time
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_initial_draft as initial_draft_router
import apps.api.wilq_api.routers.content_refresh_preparation_authority as refresh_authority_router
from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers import content_snapshot as content_snapshot_router
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content import dynamic_planning_test_support as planning_support
from tests.content.initial_draft_authority_fakes import _rebuild_run, exact_public_bdo_run
from tests.content.packet_plan_draft_fixtures import (
    PacketPreparationCase,
    PacketPreparationStore,
)
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.content.drafts import initial_draft_queue as initial_draft_queue_module
from wilq.content.planning import generation_input as generation_input_module
from wilq.content.planning import (
    planning_generation_queue,
    proposal_packet_binding,
    route_packet_binding,
)
from wilq.content.planning import proposal_read as proposal_read_module
from wilq.content.planning.dynamic_input import (
    bind_research_packet_to_planning_input,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal import with_explicit_content_service_selection
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow import refresh_preparation_resolution as refresh_resolution_module
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityBinding,
    content_delivery_identity_digest,
    content_delivery_identity_logical_id,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.refresh_preparation_models import RefreshPreparationUnclassified
from wilq.content.workflow.research_packet_preparation import prepare_content_research_packet
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    content_source_pack_binding_digest,
    content_source_pack_binding_logical_id,
    content_source_pack_context_digest,
)
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore


class InlinePlanningExecutor:
    def submit(self, function: Any, /, *args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)


class PlanningMechanicsRefreshAuthority:
    """Keep invalid-subject/stale probes on their named planning seams."""

    def __init__(self, authority: Any, packet_store: DynamicPacketStore) -> None:
        self._authority = authority
        self._packet_store = packet_store

    def resolve_planning(self, work_item_id: str, request: Any) -> Any:
        approved = {
            "ekologus_service_bdo_reporting",
            "ekologus_service_environmental_consulting_outsourcing",
        }
        if request.content_kind == "service" and request.service_card_id not in approved:
            return RefreshPreparationUnclassified(work_item_id)
        if request.refresh_preparation_authorization_id is None:
            current = self._packet_store._bound_planning_inputs.get(work_item_id)
            if current is not None and request.expected_planning_input_digest != (
                current.planning_input_digest
            ):
                return RefreshPreparationUnclassified(work_item_id)
        return self._authority.resolve_planning(work_item_id, request)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._authority, name)


class DynamicPacketStore:
    """Delegate ordinary reads while serving exact packet/auth fixtures."""

    def __init__(
        self,
        base: ContentWorkflowStore,
        cases: tuple[PacketPreparationCase, ...],
        classification_run: Any,
    ) -> None:
        self._base = base
        self._cases_by_work_item = {
            case.identity.current_work_item_id: case for case in cases
        }
        self._cases_by_binding = {case.source_pack.binding_id: case for case in cases}
        self._cases_by_packet: dict[str, PacketPreparationCase] = {}
        self._bound_planning_inputs: dict[str, Any] = {}
        self._baseline_planning_input_digests: dict[str, str] = {}
        self._classification_run = classification_run
        self._refresh_authorizations: dict[str, Any] = {}

    def _case_for_work_item(self, work_item_id: str) -> PacketPreparationCase:
        try:
            return self._cases_by_work_item[work_item_id]
        except KeyError as exc:
            raise AssertionError(f"No exact packet fixture for {work_item_id}") from exc

    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[ContentSourcePackBinding]:
        if current_work_item_id is None:
            return [case.source_pack for case in self._cases_by_work_item.values()]
        case = self._cases_by_work_item.get(current_work_item_id)
        return [] if case is None else [case.source_pack]

    def load_content_source_pack_binding(self, binding_id: str) -> ContentSourcePackBinding | None:
        case = self._cases_by_binding.get(binding_id)
        return None if case is None else case.source_pack

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None:
        case = next(
            (
                candidate
                for candidate in self._cases_by_work_item.values()
                if candidate.identity.binding_id == binding_id
            ),
            None,
        )
        return None if case is None else case.identity

    def load_production_classification_for_work_item(self, work_item_id: str) -> Any:
        return self._case_for_work_item(work_item_id).store.classification

    def load_latest_production_classification(self) -> Any:
        return self._classification_run

    def load_refresh_preparation_authorization(self, authorization_id: str) -> Any:
        return self._refresh_authorizations.get(authorization_id)

    def find_refresh_preparation_authorization(self, **context: str | None) -> Any:
        for authorization in self._refresh_authorizations.values():
            if all(getattr(authorization, key) == value for key, value in context.items()):
                return authorization
        return None

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> Any:
        return self._case_for_work_item(
            current_work_item_id
        ).store.load_content_source_fact_authority_receipt_for_identity(
            identity_binding_id,
            current_work_item_id,
            source_fact_ids,
        )

    def record_content_research_packet(self, command: Any) -> Any:
        case = self._case_for_work_item(command.current_work_item_id)
        result = case.store.record_content_research_packet(command)
        self._cases_by_packet[result.packet.packet_id] = case
        return result

    def _record_content_research_packet_preparation_receipt(self, receipt: Any) -> Any:
        return self._case_for_work_item(
            receipt.current_work_item_id
        ).store._record_content_research_packet_preparation_receipt(receipt)

    def _load_content_research_packet_preparation_receipt(self, receipt_id: str) -> Any:
        for case in self._cases_by_work_item.values():
            receipt = case.store._load_content_research_packet_preparation_receipt(receipt_id)
            if receipt is not None:
                return receipt
        return None

    def load_content_research_packet(self, packet_id: str) -> Any:
        case = self._cases_by_packet.get(packet_id)
        if case is not None:
            return case.store.load_content_research_packet(packet_id)
        for candidate in self._cases_by_work_item.values():
            packet = candidate.store.load_content_research_packet(packet_id)
            if packet is not None:
                self._cases_by_packet[packet_id] = candidate
                return packet
        return None

    def latest_packet_for_work_item(self, work_item_id: str) -> Any:
        case = self._case_for_work_item(work_item_id)
        if not case.store.packets:
            return None
        return max(
            case.store.packets.values(),
            key=lambda packet: (packet.recorded_at, packet.packet_id),
        )

    def list_research_fact_promotion_receipts(self) -> list[Any]:
        return []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


def install_packet_harness(
    monkeypatch: Any,
    *,
    base_store: ContentWorkflowStore,
    base_case: PacketPreparationCase,
    work_items: tuple[tuple[str, str], ...],
) -> DynamicPacketStore:
    classification_run = _build_synthetic_refresh_classification(base_case, work_items)
    cases = tuple(
        _adapt_packet_case(base_case, work_item_id, url, classification_run)
        for work_item_id, url in work_items
    )
    packet_store = DynamicPacketStore(base_store, cases, classification_run)
    _seed_packet_bound_planning_inputs(packet_store)
    _patch_packet_bound_input_builders(monkeypatch, packet_store)
    monkeypatch.setattr(planning_router, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(initial_draft_router, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(initial_draft_queue_module, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(proposal_packet_binding, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(route_packet_binding, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(content_snapshot_router, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(
        planning_generation_queue,
        "_PLANNING_GENERATION_EXECUTOR",
        InlinePlanningExecutor(),
    )
    monkeypatch.setattr(refresh_authority_router, "content_workflow_store", lambda: packet_store)
    monkeypatch.setattr(
        refresh_authority_router,
        "_selected_refresh_snapshot",
        lambda work_item_id, service_card_id: with_explicit_content_service_selection(
            snapshot_for_work_item_or_404(work_item_id), service_card_id
        ),
    )
    canonical_authority_factory = planning_router._canonical_refresh_preparation_authority
    monkeypatch.setattr(
        planning_router,
        "_canonical_refresh_preparation_authority",
        lambda: PlanningMechanicsRefreshAuthority(
            canonical_authority_factory(), packet_store
        ),
    )
    return packet_store


def _seed_packet_bound_planning_inputs(packet_store: DynamicPacketStore) -> None:
    for work_item_id in packet_store._cases_by_work_item:
        snapshot = snapshot_for_work_item_or_404(work_item_id)
        service_card_id = snapshot.service_profile_context.service_card_id
        if service_card_id is None:
            raise AssertionError(f"Missing exact service card for {work_item_id}")
        selected_snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
        result = build_content_planning_input(selected_snapshot, service_card_id=service_card_id)
        planning_input = result.planning_input
        if planning_input is None:
            raise AssertionError(f"Missing planning input for {work_item_id}")
        prepared = prepare_content_research_packet(
            store=packet_store,
            snapshot=selected_snapshot,
            planning_input=planning_input,
        )
        if prepared.packet is None:
            raise AssertionError(
                f"Packet fixture did not prepare for {work_item_id}: {prepared.blocker}"
            )
        packet_store._baseline_planning_input_digests[work_item_id] = (
            planning_input.planning_input_digest
        )
        packet_store._bound_planning_inputs[work_item_id] = bind_research_packet_to_planning_input(
            planning_input, prepared.packet
        )
    packet_store._base.record_production_classification(packet_store._classification_run)
    for work_item_id, case in packet_store._cases_by_work_item.items():
        identity = case.identity
        bound = packet_store._bound_planning_inputs[work_item_id]
        classification = ContentRefreshPreparationClassificationBinding(
            classification_run_id=identity.classification_run_id,
            classification_run_digest=identity.classification_run_digest,
            decision_set_digest=identity.classification_decision_set_digest,
            source_packet_row_digest=identity.classification_source_row_digest,
            current_work_item_id=work_item_id,
            canonical_path=identity.canonical_path,
            public_url=identity.public_url,
        )
        authorization = build_content_refresh_preparation_authorization(
            work_item_id=work_item_id,
            classification=classification,
            planning_input_digest=bound.planning_input_digest,
            service_card_id=bound.confirmed_service_card_id,
            acknowledged_classification_blocker_codes=[],
            authorized_by="wilku",
            authorized_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        packet_store._base.record_refresh_preparation_authorization(authorization)
        packet_store._refresh_authorizations[authorization.authorization_id] = authorization


def _patch_packet_bound_input_builders(monkeypatch: Any, packet_store: DynamicPacketStore) -> None:
    original = build_content_planning_input

    def packet_bound_builder(snapshot: Any, *, service_card_id: str | None) -> Any:
        result = original(snapshot, service_card_id=service_card_id)
        planning_input = result.planning_input
        work_item_id = snapshot.preflight.item.id
        bound = packet_store._bound_planning_inputs.get(work_item_id)
        if (
            planning_input is not None
            and bound is not None
            and planning_input.planning_input_digest
            == packet_store._baseline_planning_input_digests[work_item_id]
        ):
            return result.model_copy(update={"planning_input": bound})
        return result

    monkeypatch.setattr(
        generation_input_module,
        "build_content_planning_input",
        packet_bound_builder,
    )
    monkeypatch.setattr(
        proposal_read_module,
        "build_content_planning_input",
        packet_bound_builder,
    )
    monkeypatch.setattr(
        refresh_resolution_module,
        "build_content_planning_input",
        packet_bound_builder,
    )


def _adapt_packet_case(
    base_case: PacketPreparationCase,
    work_item_id: str,
    public_url: str,
    classification_run: Any,
) -> PacketPreparationCase:
    canonical_path = public_url.removeprefix("https://www.ekologus.pl").rstrip("/") or "/"
    identity_payload = base_case.identity.model_dump(mode="json")
    identity_payload.update(
        {
            "canonical_path": canonical_path,
            "public_url": public_url,
            "current_work_item_id": work_item_id,
        }
    )
    classification_row = classification_run.for_work_item(work_item_id)
    if classification_row is None:
        raise AssertionError(f"Missing synthetic classification row for {work_item_id}")
    identity_payload.update(
        {
            "classification_run_id": classification_run.run_id,
            "classification_run_digest": classification_run.run_digest,
            "classification_decision_set_digest": classification_run.input.decision_set_digest,
            "classification_source_row_digest": classification_row.source_packet_row_digest,
        }
    )
    identity_payload.pop("binding_id", None)
    identity_payload.pop("binding_digest", None)
    identity_digest = content_delivery_identity_digest(identity_payload)
    identity_id = (
        "content_delivery_identity_"
        f"{content_delivery_identity_logical_id(identity_payload)[:24]}"
    )
    identity = ContentDeliveryIdentityBinding.model_validate(
        {"binding_id": identity_id, "binding_digest": identity_digest, **identity_payload}
    )
    source_payload = base_case.source_pack.model_dump(mode="json")
    source_payload.update(
        {
            "identity_binding_id": identity.binding_id,
            "identity_binding_digest": identity.binding_digest,
            "current_work_item_id": work_item_id,
        }
    )
    attestation = base_case.source_pack.fresh_context_attestation
    context_digest = content_source_pack_context_digest(identity, attestation)
    source_payload["fresh_context_attestation"] = attestation.model_copy(
        update={"context_digest": context_digest}
    ).model_dump(mode="json")
    source_payload["fresh_context_digest"] = context_digest
    source_payload.pop("binding_id", None)
    source_payload.pop("binding_digest", None)
    source_digest = content_source_pack_binding_digest(source_payload)
    source_id = (
        "content_source_pack_binding_"
        f"{content_source_pack_binding_logical_id(source_payload)[:24]}"
    )
    source_pack = ContentSourcePackBinding.model_validate(
        {"binding_id": source_id, "binding_digest": source_digest, **source_payload}
    )
    return PacketPreparationCase(
        store=PacketPreparationStore(identity, source_pack),
        identity=identity,
        source_pack=source_pack,
        planning_input=base_case.planning_input,
        snapshot=base_case.snapshot,
    )


def _build_synthetic_refresh_classification(
    base_case: PacketPreparationCase,
    work_items: tuple[tuple[str, str], ...],
) -> Any:
    baseline = exact_public_bdo_run()
    rows = []
    for work_item_id, public_url in work_items:
        rows.append(
            baseline.rows[0].model_copy(
                update={
                    "canonical_path": public_url.removeprefix("https://www.ekologus.pl").rstrip("/"),
                    "public_url": public_url,
                    "decision": "refresh",
                    "generation_allowed": False,
                    "current_work_item_id": work_item_id,
                    "retained_work_item_id": None,
                    "revision_id": None,
                    "revision_digest": None,
                    "revision_approved": False,
                    "revision_complete": False,
                    "retained_binding": None,
                    "verified_actions": (),
                    "verified_drafts": (),
                    "blockers": (),
                    "source_packet_row_digest": base_case.identity.classification_source_row_digest,
                }
            )
        )
    return _rebuild_run(baseline, tuple(sorted(rows, key=lambda row: row.canonical_path)))


def patch_fast_synthetic_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    base = build_content_diagnostics(tactical_items=[], actions=[], metric_facts=[])
    freshness = base.freshness_assessment.model_copy(
        update={
            "state": "fresh",
            "requires_refresh": False,
            "missing_connector_ids": [],
            "blocked_connector_ids": [],
            "stale_connector_ids": [],
            "connector_labels_requiring_refresh": [],
            "summary": "Syntetyczny świeży proof planowania.",
            "next_step": "Można zbudować wejście planu do testu.",
        }
    )

    def diagnostics(_work_item_id: str) -> Any:
        return base.model_copy(
            update={
                "decision_queue": [
                    planning_support._synthetic_planning_decision(url)
                    for url in planning_support._PLANNING_URLS
                ],
                "freshness_assessment": freshness,
            }
        )

    monkeypatch.setattr(content_snapshot_router, "diagnostics_with_exact_gsc_demand", diagnostics)


def generate_plan(
    client: TestClient,
    runtime: Any,
    work_item_id: str,
    *,
    expected_calls: int,
) -> dict[str, Any]:
    snapshot = snapshot_for_work_item_or_404(work_item_id)
    service_card_id = snapshot.service_profile_context.service_card_id
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert before.status_code == 200
    assert before.json()["status"] == "not_generated", before.json()["blockers"]
    input_summary = before.json()["input_summary"]
    assert len(input_summary["source_assessments"]) == 10
    gsc_assessment = next(
        item for item in input_summary["source_assessments"] if item["source"] == "gsc"
    )
    assert gsc_assessment["status"] == "used"
    assert gsc_assessment["landing_match_tiers"]
    assert input_summary["evidence_id_count"] > 0
    assert runtime.calls == expected_calls
    if expected_calls == 0:
        assert not planning_table_exists()
    input_digest = before.json()["planning_input_digest"]
    unknown = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=generation_request("ekologus_service_unknown", input_digest),
    )
    assert unknown.status_code == 422
    assert unknown.json()["blockers"][0]["code"] == "unknown_service_card"
    stale = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=generation_request(service_card_id, "0" * 64),
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "stale"
    assert stale.json().get("planning_input_digest") in {None, input_digest}
    created = post_planning(
        client,
        work_item_id,
        generation_request_for_work_item(work_item_id, service_card_id, input_digest),
    )
    assert created.status_code == 200
    assert created.json()["status"] in {"ready", "idempotent"}, [
        (blocker.get("code"), blocker.get("source_codes"), blocker.get("reason"))
        for blocker in created.json().get("blockers", [])
    ]
    assert created.json()["proposal"]["input_schema_version"] == "wilq_content_planning_input_v7"
    repeated = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=generation_request_for_work_item(work_item_id, service_card_id, input_digest),
    )
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["proposal"]["proposal_id"] == created.json()["proposal"]["proposal_id"]
    ready = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert ready.json()["status"] == "ready"
    assert ready.json()["proposal"] == created.json()["proposal"]
    assert ready.json()["planning_workspace"]["proposal"] == created.json()["proposal"]
    assert ready.json()["planning_workspace"]["scope_current"] is False
    assert ready.json()["input_summary"] == input_summary
    return cast(dict[str, Any], created.json()["proposal"])


def post_planning(client: TestClient, work_item_id: str, request: dict[str, str]) -> Any:
    response = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=request,
    )
    if response.status_code == 200 and response.json().get("status") == "generating":
        for _ in range(200):
            time.sleep(0.05)
            response = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
            if response.json().get("status") != "generating":
                break
    return response


def snapshot(_client: TestClient, work_item_id: str) -> dict[str, Any]:
    return cast(dict[str, Any], snapshot_for_work_item_or_404(work_item_id).model_dump())


def initial_draft_request(proposal: dict[str, Any]) -> dict[str, str]:
    refresh_binding = proposal["refresh_preparation_binding"]
    return {
        "expected_proposal_id": proposal["proposal_id"],
        "expected_planning_digest": proposal["planning_digest"],
        "expected_planning_input_digest": proposal["planning_input_digest"],
        "requested_by": "wilku",
        "research_packet_id": proposal["research_packet_id"],
        "research_packet_digest": proposal["research_packet_digest"],
        "refresh_preparation_authorization_id": refresh_binding["authorization_id"],
        "expected_refresh_preparation_authorization_digest": refresh_binding[
            "authorization_digest"
        ],
    }


def generation_request(service_card_id: str, digest: str) -> dict[str, str]:
    return {
        "service_card_id": service_card_id,
        "expected_planning_input_digest": digest,
        "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
        "requested_by": "wilku",
    }


def generation_request_for_work_item(
    work_item_id: str,
    service_card_id: str,
    digest: str,
    *,
    include_authorization: bool = True,
) -> dict[str, str]:
    request = generation_request(service_card_id, digest)
    packet_store = planning_router.content_workflow_store()
    case = packet_store._cases_by_work_item[work_item_id]
    request.update(
        {
            "source_pack_binding_id": case.source_pack.binding_id,
            "expected_source_pack_binding_digest": case.source_pack.binding_digest,
        }
    )
    packet = packet_store.latest_packet_for_work_item(work_item_id)
    if packet is None:
        raise AssertionError(f"Missing exact packet for {work_item_id}")
    request.update(
        {
            "research_packet_id": packet.packet_id,
            "expected_research_packet_digest": packet.packet_digest,
        }
    )
    if include_authorization:
        authorization = next(
            authorization
            for authorization in packet_store._refresh_authorizations.values()
            if authorization.work_item_id == work_item_id
            and authorization.service_card_id == service_card_id
        )
        request.update(
            {
                "refresh_preparation_authorization_id": authorization.authorization_id,
                "expected_refresh_preparation_authorization_digest": (
                    authorization.authorization_digest
                ),
            }
        )
    return request


def generated_proposal_from(payload: dict[str, Any]) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_validate(payload)


def planning_table_exists() -> bool:
    path = content_planning_proposal_store().path
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_planning_proposals",),
        ).fetchone()
    return row is not None
