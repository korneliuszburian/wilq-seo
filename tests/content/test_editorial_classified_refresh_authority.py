from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.refresh_preparation_editorial as refresh_editorial
import wilq.content.workflow.refresh_preparation_operations as refresh_operations
import wilq.content.workflow.refresh_preparation_resolution as refresh_resolution
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningSourceAssessment,
)
from wilq.content.planning.input_summary import ContentPlanningInputSummary
from wilq.content.workflow.content_kind_receipt import (
    ContentKindReceipt,
    ContentKindReceiptRecordResult,
)
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.refresh_preparation import (
    ContentRefreshPreparationAuthority,
    RefreshPreparationRuntimeAuthorized,
    RefreshPreparationRuntimeBlocked,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationRecordResult,
    ContentRefreshPreparationAuthorizationRequest,
)
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

PUBLIC_URL = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
WORK_ITEM_ID = inventory_work_item_id(PUBLIC_URL)
RUN_DIGEST = "a" * 64
DECISION_DIGEST = "b" * 64
ROW_DIGEST = "c" * 64
INPUT_DIGEST = "d" * 64


@dataclass
class _Store:
    authorizations: dict[str, ContentRefreshPreparationAuthorization] = field(default_factory=dict)
    receipts: dict[str, ContentKindReceipt] = field(default_factory=dict)

    def load_latest_production_classification(self) -> object:
        row = SimpleNamespace(
            current_work_item_id=WORK_ITEM_ID,
            decision="refresh",
            canonical_path="/analiza-pozwolen-zintegrowanych",
            public_url=PUBLIC_URL,
            source_packet_row_digest=ROW_DIGEST,
            blockers=(),
            next_step_pl="Odśwież exact inventory.",
        )
        return SimpleNamespace(
            run_id="content_production_classification_editorial",
            run_digest=RUN_DIGEST,
            input=SimpleNamespace(decision_set_digest=DECISION_DIGEST),
            freshness=SimpleNamespace(requires_refresh=False, connector_ids=()),
            for_work_item=lambda work_item_id: row if work_item_id == WORK_ITEM_ID else None,
        )

    def record_content_kind_receipt(
        self, receipt: ContentKindReceipt
    ) -> ContentKindReceiptRecordResult:
        existing = self.receipts.get(receipt.receipt_id)
        if existing is None:
            self.receipts[receipt.receipt_id] = receipt
            return ContentKindReceiptRecordResult(status="created", receipt=receipt)
        return ContentKindReceiptRecordResult(
            status="idempotent" if existing == receipt else "conflict",
            receipt=existing,
        )

    def load_content_kind_receipt(self, receipt_id: str) -> ContentKindReceipt | None:
        return self.receipts.get(receipt_id)

    def record_refresh_preparation_authorization(
        self,
        authorization: ContentRefreshPreparationAuthorization,
    ) -> ContentRefreshPreparationAuthorizationRecordResult:
        existing = self.authorizations.get(authorization.authorization_id)
        if existing is None:
            self.authorizations[authorization.authorization_id] = authorization
            return ContentRefreshPreparationAuthorizationRecordResult(
                status="created", authorization=authorization
            )
        return ContentRefreshPreparationAuthorizationRecordResult(
            status="idempotent" if existing == authorization else "conflict",
            authorization=existing,
        )

    def load_refresh_preparation_authorization(
        self, authorization_id: str
    ) -> ContentRefreshPreparationAuthorization | None:
        return self.authorizations.get(authorization_id)

    def find_refresh_preparation_authorization(self, **context: str | None):
        return next(
            (
                authorization
                for authorization in self.authorizations.values()
                if all(getattr(authorization, key) == value for key, value in context.items())
            ),
            None,
        )


@dataclass
class _ProposalStore:
    def latest(self, _work_item_id: str) -> None:
        return None


def test_exact_editorial_work_item_reaches_public_refresh_preparation_without_service(
    monkeypatch,
) -> None:
    store = _Store()
    calls: list[str | None] = []
    authority = _authority(monkeypatch, store=store, calls=calls)
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    app.include_router(router)
    client = TestClient(app)

    ready = client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation",
        params={"content_kind": "editorial"},
    )
    body = ready.json()
    request = ContentRefreshPreparationAuthorizationRequest(
        expected_production_classification_run_digest=body["classification"][
            "classification_run_digest"
        ],
        expected_production_classification_decision_set_digest=body["classification"][
            "decision_set_digest"
        ],
        expected_production_classification_source_packet_row_digest=body["classification"][
            "source_packet_row_digest"
        ],
        expected_planning_input_digest=body["planning_input_digest"],
        content_kind="editorial",
        service_card_id=None,
        authorized_by="wilku",
    )
    authorized = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json=request.model_dump(mode="json"),
    )
    authorization = authorized.json()["authorization"]
    resolution = authority.resolve_planning(
        WORK_ITEM_ID,
        ContentPlanningProposalRequest(
            content_kind="editorial",
            service_card_id=None,
            expected_planning_input_digest=INPUT_DIGEST,
            requested_by="wilku",
            refresh_preparation_authorization_id=authorization["authorization_id"],
            expected_refresh_preparation_authorization_digest=authorization["authorization_digest"],
        ),
    )

    assert ready.status_code == 200
    assert body["status"] == "ready_to_authorize"
    assert body["content_kind"] == "editorial"
    assert body["service_candidate"] is None
    assert authorized.status_code == 201
    assert authorized.json()["authorization"]["content_kind"] == "editorial"
    assert authorized.json()["authorization"]["service_card_id"] is None
    assert len(store.receipts) == 1
    assert isinstance(resolution, RefreshPreparationRuntimeAuthorized)
    assert resolution.service_candidate is None
    assert calls and set(calls) == {None}


def test_editorial_runtime_fails_closed_when_persisted_receipt_is_missing_foreign_or_mismatched(
    monkeypatch,
) -> None:
    for mutation in ("missing", "foreign", "mismatched"):
        store = _Store()
        authority = _authority(monkeypatch, store=store, calls=[])
        preview = authority.preview(
            WORK_ITEM_ID,
            service_card_id=None,
        )
        request = _authorization_request(preview)
        created = authority.authorize(WORK_ITEM_ID, request)
        authorization = created.authorization
        assert authorization is not None
        receipt_id = next(iter(store.receipts))
        if mutation == "missing":
            store.receipts.clear()
        elif mutation == "foreign":
            store.receipts[receipt_id] = store.receipts[receipt_id].model_copy(
                update={"work_item_id": "content_work_item_foreign"}
            )
        else:
            store.receipts[receipt_id] = store.receipts[receipt_id].model_copy(
                update={"inventory_evidence_digest": "e" * 64}
            )

        resolution = authority.resolve_planning(
            WORK_ITEM_ID,
            ContentPlanningProposalRequest(
                content_kind="editorial",
                service_card_id=None,
                expected_planning_input_digest=INPUT_DIGEST,
                requested_by="wilku",
                refresh_preparation_authorization_id=authorization.authorization_id,
                expected_refresh_preparation_authorization_digest=authorization.authorization_digest,
            ),
        )

        assert isinstance(resolution, RefreshPreparationRuntimeBlocked)
        assert resolution.blocker.code == "refresh_preparation_authorization_stale"


def _authority(
    monkeypatch,
    *,
    store: _Store,
    calls: list[str | None],
) -> ContentRefreshPreparationAuthority:
    planning_input = SimpleNamespace(
        work_item_id=WORK_ITEM_ID,
        planning_input_digest=INPUT_DIGEST,
        content_kind="editorial",
        confirmed_service_card_id=None,
        final_canonical_url=PUBLIC_URL,
    )
    result = SimpleNamespace(planning_input=planning_input, blockers=[])
    monkeypatch.setattr(
        refresh_resolution,
        "build_content_planning_input",
        lambda *_args, **_kwargs: result,
    )
    monkeypatch.setattr(
        refresh_resolution,
        "planning_generation_blockers",
        lambda blockers: blockers,
    )
    for module in (refresh_resolution, refresh_operations, refresh_editorial):
        monkeypatch.setattr(module, "content_planning_input_summary", lambda _input: _summary())
    return ContentRefreshPreparationAuthority(
        store=store,
        snapshot_loader=lambda _work_item_id, service_card_id: (
            calls.append(service_card_id) or SimpleNamespace()
        ),
        proposal_store=_ProposalStore(),  # type: ignore[arg-type]
        content_kind_inventory_loader=lambda work_item_id: (
            _inventory_binding() if work_item_id == WORK_ITEM_ID else None
        ),
    )


def _inventory_binding() -> ContentKindInventoryBinding:
    return ContentKindInventoryBinding(
        work_item_id=WORK_ITEM_ID,
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url=PUBLIC_URL,
        wordpress_content_type="posts",
        content_kind="editorial",
        inventory_evidence_ids=("ev_current_public", "ev_current_rest"),
        trusted=True,
    )


def _authorization_request(preview) -> ContentRefreshPreparationAuthorizationRequest:
    return ContentRefreshPreparationAuthorizationRequest(
        expected_production_classification_run_digest=preview.classification.classification_run_digest,
        expected_production_classification_decision_set_digest=preview.classification.decision_set_digest,
        expected_production_classification_source_packet_row_digest=(
            preview.classification.source_packet_row_digest
        ),
        expected_planning_input_digest=preview.planning_input_digest,
        content_kind="editorial",
        service_card_id=None,
        authorized_by="wilku",
    )


def _summary() -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        goal="refresh_existing",
        final_canonical_url=PUBLIC_URL,
        content_kind="editorial",
        service_label=None,
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="available",
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Poza zakresem falsyfikatora.",
            )
            for source in sorted(PLANNING_SOURCE_NAMES)
        ],
        source_fact_count=0,
        source_fact_ids=[],
        source_material_ids=[],
        evidence_id_count=2,
        knowledge_card_count=0,
    )
