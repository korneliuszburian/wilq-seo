from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import wilq.content.knowledge.source_facts as source_facts_module
import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.evidence_acquisition_coordinator as acquisition_module
import wilq.content.workflow.evidence_acquisition_snapshot as evidence_snapshot_module
import wilq.content.workflow.research_promotion_authority as promotion_authority
import wilq.content.workflow.research_promotion_candidate as promotion_candidate_module
import wilq.content.workflow.store.store as workflow_store_module
import wilq.evidence.registry as evidence_registry
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_evidence_acquisition as acquisition_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_authoring_inventory_receipt import _catalog as authoring_catalog
from tests.content.test_authoring_inventory_receipt import _item as authoring_item
from tests.content.test_authoring_inventory_receipt import _receipt as authoring_receipt
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.actions import action_catalog
from wilq.actions import service as action_service
from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_coordinator import (
    EvidenceAcquisitionCoordinator,
    EvidenceAcquisitionRun,
    EvidenceAcquisitionStartCommand,
)
from wilq.content.workflow.evidence_acquisition_snapshot import (
    CurrentPageSnapshotReadError,
    EvidenceObservationReceipt,
    WordPressCurrentPageSnapshotAdapter,
)
from wilq.content.workflow.research_promotion_authority import (
    ContentResearchFactPromotionPreviewCommand,
    ContentResearchFactPromotionReceipt,
    prepare_research_fact_promotion_preview,
    promotion_action_payload_digest,
    validate_research_fact_promotion_action_payload,
)
from wilq.content.workflow.research_promotion_candidate import (
    build_research_promotion_candidate_projection,
)
from wilq.content.workflow.research_proposal import (
    EvidenceResearchCoordinator,
    ResearchProposalLegacyUnreadable,
    ResearchProposalReadDiagnostic,
)
from wilq.content.workflow.source_pack_binding import source_fact_registry_digest
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.store.store_schema import (
    ContentWorkflowSchemaMigrationError,
)
from wilq.schemas import AuditEvent
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _identity_subject(binding_id: str) -> dict[str, str]:
    return {"subject_kind": "identity_binding", "identity_binding_id": binding_id}


def _exact_bdo_identity_command():
    return identity_command(retained=True).model_copy(
        update={"retained_work_item_id": None, "retained_usage": None}
    )


def _coordinator(tmp_path: Path) -> tuple[EvidenceAcquisitionCoordinator, object]:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
    )
    return coordinator, identity


def test_start_derives_exact_observation_and_blocks_missing_researcher(tmp_path: Path) -> None:
    coordinator, identity = _coordinator(tmp_path)

    run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Jakie twierdzenia usługowe wymagałyby review?",
        )
    )

    assert run.status == "blocked"
    assert run.blockers[0].code == "current_page_snapshot_unavailable"
    assert run.observation is None
    assert run.vendor_read_status == "not_attempted"
    assert run.production_authority is False
    assert run.generation_allowed is False
    assert run.proposed_facts == ()
    current = coordinator.read(run.run_id)
    assert current is not None
    assert current.recorded_run == run.recorded_run


def test_observation_subject_reuses_exact_authoring_receipt_and_stays_non_authoritative(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    item = authoring_item()
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Aktualny materiał z receipt subject.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("observation subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "observation subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: catalog,
        clock=lambda: read_time,
    )

    command = EvidenceAcquisitionStartCommand(
        subject={
            "subject_kind": "authoring_inventory_receipt",
            "authoring_inventory_receipt_id": receipt.receipt_id,
        },
        research_question="Sprawdź aktualny materiał strony.",
    )
    run = coordinator.start(command)

    assert run.status == "ready_for_researcher", run.blockers
    assert run.subject_kind == "authoring_inventory_receipt"
    assert run.identity_binding_id is None
    assert run.authoring_inventory_receipt_id == receipt.receipt_id
    assert run.authoring_inventory_receipt_digest == receipt.receipt_digest
    assert run.subject_public_url == receipt.public_url
    assert run.subject_canonical_path == receipt.canonical_path
    assert run.subject_evidence_ids == (receipt.evidence_id,)
    assert run.production_authority is False
    assert run.disposition_status == "unknown"
    assert run.source_authority_status == "unknown"
    assert run.generation_allowed is False
    assert run.observation is not None
    assert run.observation.source_url == receipt.public_url
    assert set(run.observation.evidence_ids).isdisjoint({receipt.evidence_id})

    stale_coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("observation subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "observation subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: authoring_catalog(
            authoring_item(section_headings=["Zmieniony zakres"])
        ),
        clock=lambda: read_time,
    )
    stale = stale_coordinator.start(command.model_copy(update={"attempt": 1}))
    assert stale.status == "blocked"
    assert stale.blockers[0].code == "authoring_inventory_receipt_stale"

    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=coordinator.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    assert proposal.status == "ready_for_review"
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=run.recorded_run,
        identity=None,
        classification=None,
        checked_at=read_time,
    )
    assert candidate.status == "blocked"
    assert candidate.policy is None


def test_authoring_subject_blocks_unsupported_intent_before_snapshot_read(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    item = authoring_item()
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    reads: list[str] = []

    def reader(*, source_url: str, canonical_path: str) -> EvidenceObservationReceipt:
        reads.append(source_url)
        raise AssertionError("unsupported intent must not invoke the snapshot reader")

    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=reader,
        catalog_loader=lambda: catalog,
        clock=lambda: datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )

    run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject={
                "subject_kind": "authoring_inventory_receipt",
                "authoring_inventory_receipt_id": receipt.receipt_id,
            },
            research_question="Sprawdź oficjalne źródła.",
            source_intent="official_primary",
        )
    )

    assert run.status == "blocked"
    assert run.blockers[0].code == "researcher_executor_missing"
    assert run.vendor_read_status == "not_attempted"
    assert reads == []


def test_authoring_catalog_drift_cannot_reuse_ready_run(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    item = authoring_item()
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Aktualny materiał.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    command = EvidenceAcquisitionStartCommand(
        subject={
            "subject_kind": "authoring_inventory_receipt",
            "authoring_inventory_receipt_id": receipt.receipt_id,
        },
        research_question="Sprawdź aktualny materiał.",
    )
    first = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: catalog,
        clock=lambda: read_time,
    ).start(command)
    assert first.status == "ready_for_researcher"

    def unexpected_reader(*, source_url: str, canonical_path: str) -> EvidenceObservationReceipt:
        raise AssertionError("catalog drift must block before snapshot read")

    drifted_catalog = authoring_catalog(
        authoring_item(collected_at=item.collected_at + timedelta(hours=1))
    )
    second = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=unexpected_reader,
        catalog_loader=lambda: drifted_catalog,
        clock=lambda: read_time,
    ).start(command)

    assert second.status == "blocked"
    assert second.blockers[0].code == "authoring_inventory_receipt_stale"
    assert second.run_id != first.run_id


@pytest.mark.parametrize(
    ("age", "expected_status"),
    [
        (timedelta(hours=48), "ready_for_researcher"),
        (timedelta(hours=48, seconds=1), "blocked"),
        (timedelta(days=40), "blocked"),
    ],
)
def test_authoring_receipt_freshness_uses_server_clock_boundary(
    tmp_path: Path, age: timedelta, expected_status: str
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    item = authoring_item(collected_at=read_time - age)
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Aktualny materiał.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    run = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: catalog,
        clock=lambda: read_time,
    ).start(
        EvidenceAcquisitionStartCommand(
            subject={
                "subject_kind": "authoring_inventory_receipt",
                "authoring_inventory_receipt_id": receipt.receipt_id,
            },
            research_question="Sprawdź aktualny materiał.",
        )
    )

    assert run.status == expected_status
    if expected_status == "blocked":
        assert run.blockers[0].code == "authoring_inventory_receipt_stale"


def test_run_validator_rejects_recomputed_mixed_subject_payloads(tmp_path: Path) -> None:
    coordinator, identity = _coordinator(tmp_path)
    identity_run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Sprawdź exact źródła.",
        )
    ).recorded_run.model_dump(mode="json")
    identity_run["authoring_inventory_receipt_id"] = "content_authoring_inventory_mixed"
    identity_run["authoring_inventory_receipt_digest"] = "a" * 64
    identity_digest = acquisition_module._run_digest(identity_run)
    identity_run.update(
        run_id=f"content_evidence_acquisition_{identity_digest[:24]}",
        run_digest=identity_digest,
    )
    with pytest.raises(ValidationError, match="cannot carry authoring receipt"):
        EvidenceAcquisitionRun.model_validate(identity_run)

    observation_run = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=ContentWorkflowStore(tmp_path / "observation.sqlite3"),
    ).start(
        EvidenceAcquisitionStartCommand(
            subject={
                "subject_kind": "authoring_inventory_receipt",
                "authoring_inventory_receipt_id": "content_authoring_inventory_missing",
            },
            research_question="Sprawdź exact źródła.",
        )
    ).recorded_run.model_dump(mode="json")
    observation_run["identity_binding_id"] = identity.binding_id
    observation_digest = acquisition_module._run_digest(observation_run)
    observation_run.update(
        run_id=f"content_evidence_acquisition_{observation_digest[:24]}",
        run_digest=observation_digest,
    )
    with pytest.raises(ValidationError, match="cannot carry identity"):
        EvidenceAcquisitionRun.model_validate(observation_run)


def test_observation_subject_forbids_caller_url_and_evidence_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceAcquisitionStartCommand.model_validate(
            {
                "subject": {
                    "subject_kind": "authoring_inventory_receipt",
                    "authoring_inventory_receipt_id": "content_authoring_inventory_receipt",
                    "url": "https://www.ekologus.pl/news/",
                },
                "research_question": "Sprawdź materiał.",
                "evidence_ids": ["forged"],
            }
        )


def test_authoring_ready_projection_rechecks_receipt_freshness_before_research(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    collected_at = datetime(2026, 9, 11, 13, 0, tzinfo=UTC)
    read_time = collected_at + timedelta(hours=47)
    item = authoring_item(collected_at=collected_at)
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Aktualny materiał.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    command = EvidenceAcquisitionStartCommand(
        subject={
            "subject_kind": "authoring_inventory_receipt",
            "authoring_inventory_receipt_id": receipt.receipt_id,
        },
        research_question="Sprawdź aktualny materiał.",
    )
    first = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: catalog,
        clock=lambda: read_time,
    ).start(command)
    assert first.status == "ready_for_researcher"

    assessed_at = read_time + timedelta(hours=2)

    def unexpected_reader(*, source_url: str, canonical_path: str) -> EvidenceObservationReceipt:
        raise AssertionError("current projection must not invoke the snapshot reader")

    current = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=unexpected_reader,
        catalog_loader=lambda: catalog,
        clock=lambda: assessed_at,
    ).read(first.run_id)
    assert current is not None
    assert current.recorded_status == "ready_for_researcher"
    assert current.current_status == "blocked"
    assert current.current_blockers[0].code == "authoring_inventory_receipt_stale"
    assert workflow_store.get_evidence_acquisition_run(first.run_id) == first.recorded_run

    researcher = _FakeResearcher(
        {
            "proposed_claim": "Nie powinno zostać użyte.",
            "scope": "opis",
            "observation_ids": [first.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=EvidenceAcquisitionCoordinator(
            identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
            classification_loader=lambda _work_item_id: pytest.fail(
                "authoring subject must not load classification"
            ),
            store=workflow_store,
            current_page_snapshot_reader=unexpected_reader,
            catalog_loader=lambda: catalog,
            clock=lambda: assessed_at,
        ).read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: assessed_at,
    ).start(first.run_id)
    assert proposal.status == "blocked"
    assert proposal.blockers[0].code == "authoring_inventory_receipt_stale"
    assert researcher.requests == []


def test_authoring_ready_projection_rechecks_catalog_before_research(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    item = authoring_item()
    catalog = authoring_catalog(item)
    receipt = authoring_receipt(item)
    workflow_store.record_content_authoring_inventory_receipt(receipt)
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Aktualny materiał.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    first = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        catalog_loader=lambda: catalog,
        clock=lambda: read_time,
    ).start(
        EvidenceAcquisitionStartCommand(
            subject={
                "subject_kind": "authoring_inventory_receipt",
                "authoring_inventory_receipt_id": receipt.receipt_id,
            },
            research_question="Sprawdź aktualny materiał.",
        )
    )
    assert first.status == "ready_for_researcher"
    drifted_catalog = authoring_catalog(
        authoring_item(collected_at=item.collected_at + timedelta(hours=1))
    )

    def unexpected_reader(*, source_url: str, canonical_path: str) -> EvidenceObservationReceipt:
        raise AssertionError("catalog drift must block before snapshot reader")

    drifted = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: pytest.fail("authoring subject must not load S1"),
        classification_loader=lambda _work_item_id: pytest.fail(
            "authoring subject must not load classification"
        ),
        store=workflow_store,
        current_page_snapshot_reader=unexpected_reader,
        catalog_loader=lambda: drifted_catalog,
        clock=lambda: read_time,
    )
    current = drifted.read(first.run_id)
    assert current is not None
    assert current.recorded_status == "ready_for_researcher"
    assert current.current_status == "blocked"
    assert current.current_blockers[0].code == "authoring_inventory_receipt_stale"

    researcher = _FakeResearcher(
        {
            "proposed_claim": "Nie powinno zostać użyte.",
            "scope": "opis",
            "observation_ids": [first.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=drifted.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(first.run_id)
    assert proposal.status == "blocked"
    assert proposal.blockers[0].code == "authoring_inventory_receipt_stale"
    assert researcher.requests == []


def test_current_page_adapter_issues_new_receipt_for_changed_body(tmp_path: Path) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    bodies = iter(
        (
            "Pierwsza treść; token=sk-DO-NOT-STORE-123456789.",
            "Druga treść po zmianie.",
        )
    )
    read_times = iter(
        (
            datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 13, 12, 1, tzinfo=UTC),
        )
    )

    def read_material(url: str) -> SimpleNamespace:
        body = next(bodies)
        return SimpleNamespace(
            url=url,
            content_text=body,
            extraction_region="wordpress_rest.content",
        )

    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=read_material,
        clock=lambda: next(read_times),
    )
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
    )

    first = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
            attempt=0,
        )
    )
    second = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
            attempt=1,
        )
    )

    assert first.status == second.status == "ready_for_researcher"
    assert first.observation is not None
    assert second.observation is not None
    assert first.observation.body_digest != second.observation.body_digest
    assert first.observation.evidence_ids != second.observation.evidence_ids
    assert first.observation.quality_tier == "exact_page_observation"
    assert set(first.observation.evidence_ids).isdisjoint(identity.inventory_evidence_ids)
    assert "sk-DO-NOT-STORE" not in first.model_dump_json()
    assert first.observation.raw_content_retained is False
    assert first.observation.source_connectors == ("wordpress_ekologus",)


def test_tampered_observation_digest_fails_on_readback(tmp_path: Path) -> None:
    coordinator, identity = _coordinator(tmp_path)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Treść do odczytu.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )
    run = EvidenceAcquisitionCoordinator(
        identity_loader=coordinator._identity_loader,
        classification_loader=coordinator._classification_loader,
        store=coordinator._store,
        current_page_snapshot_reader=adapter.read,
    ).start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
        )
    )
    assert run.observation is not None
    tampered = run.observation.model_dump(mode="json")
    tampered["body_digest"] = "0" * 64
    with pytest.raises(ValidationError):
        EvidenceObservationReceipt.model_validate(tampered)


def test_observed_host_or_path_mismatch_is_blocked(tmp_path: Path) -> None:
    coordinator, identity = _coordinator(tmp_path)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda _url: SimpleNamespace(
            url="https://www.ekologus.pl/inny-adres/",
            content_text="Nie ta strona.",
            extraction_region="rendered_html.main",
        ),
        clock=lambda: datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )
    run = EvidenceAcquisitionCoordinator(
        identity_loader=coordinator._identity_loader,
        classification_loader=coordinator._classification_loader,
        store=coordinator._store,
        current_page_snapshot_reader=adapter.read,
    ).start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
            attempt=1,
        )
    )
    assert run.status == "blocked"
    assert run.blockers[0].code == "current_page_snapshot_lineage_mismatch"


def test_stale_receipt_requires_explicit_new_attempt_and_keeps_old_readable(
    tmp_path: Path,
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    server_time = [read_time]
    bodies = iter(("Pierwsza treść.", "Odświeżona treść."))
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text=next(bodies),
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: server_time[0],
    )
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        clock=lambda: server_time[0],
    )
    command = EvidenceAcquisitionStartCommand(
        subject=_identity_subject(identity.binding_id),
        research_question="Zbadaj aktualną treść.",
        attempt=0,
    )

    first = coordinator.start(command)
    server_time[0] = read_time.replace(day=15, hour=12)
    stale = coordinator.start(command)
    retry = coordinator.start(command.model_copy(update={"attempt": 1}))

    assert first.status == "ready_for_researcher"
    assert stale.status == "blocked"
    assert stale.current_status == "blocked"
    assert stale.recorded_status == "ready_for_researcher"
    assert stale.run_id == first.run_id
    assert stale.blockers[0].code == "current_page_snapshot_stale"
    assert workflow_store.get_evidence_acquisition_run(first.run_id) == first.recorded_run
    assert retry.status == "ready_for_researcher"
    assert retry.attempt == 1
    assert retry.observation is not None
    assert retry.observation.evidence_ids != first.observation.evidence_ids


def test_current_page_evidence_resolves_without_vendor_read_and_assesses_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Bezpieczny, krótki excerpt.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    run = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
    ).start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
        )
    )
    assert run.observation is not None
    monkeypatch.setattr(
        "wilq.content.workflow.store.store.content_workflow_store",
        lambda: workflow_store,
    )
    monkeypatch.setattr(evidence_registry, "utc_now", lambda: read_time)

    evidence = evidence_registry.get_evidence(run.observation.evidence_ids[0])

    assert evidence is not None
    assert evidence.source_url == identity.public_url
    assert evidence.source_connector == "wordpress_ekologus"
    assert evidence.collected_at == read_time
    assert evidence.freshness.state == "fresh"
    assert evidence.summary == "Bezpieczny, krótki excerpt."
    assert "raw" not in evidence.summary.casefold()

    monkeypatch.setattr(
        evidence_registry,
        "utc_now",
        lambda: read_time.replace(day=15, hour=12),
    )
    stale = evidence_registry.get_evidence(run.observation.evidence_ids[0])
    assert stale is not None
    assert stale.freshness.state == "stale"


def test_default_coordinator_wires_snapshot_adapter_and_typed_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    delegate = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Default adapter excerpt.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )

    class FakeAdapter:
        def read(self, *, source_url: str, canonical_path: str):
            return delegate.read(source_url=source_url, canonical_path=canonical_path)

    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: workflow_store)
    monkeypatch.setattr(acquisition_module, "WordPressCurrentPageSnapshotAdapter", FakeAdapter)

    default = acquisition_module.build_default_evidence_acquisition_coordinator()
    completed = default.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
        )
    )

    assert completed.status == "ready_for_researcher"
    assert completed.vendor_read_status == "completed"
    assert completed.production_authority is False
    assert completed.generation_allowed is False
    assert completed.observation is not None
    assert completed.observation.source_url == identity.public_url
    assert set(completed.observation.evidence_ids).isdisjoint(identity.inventory_evidence_ids)

    class BlockedAdapter:
        def read(self, *, source_url: str, canonical_path: str):
            raise CurrentPageSnapshotReadError(
                "current_page_snapshot_unavailable", "fake adapter unavailable"
            )

    monkeypatch.setattr(acquisition_module, "WordPressCurrentPageSnapshotAdapter", BlockedAdapter)
    blocked = acquisition_module.build_default_evidence_acquisition_coordinator().start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
            attempt=1,
        )
    )
    assert blocked.status == "blocked"
    assert blocked.vendor_read_status == "blocked"
    assert blocked.blockers[0].code == "current_page_snapshot_unavailable"


def _ready_acquisition_fixture(tmp_path: Path):
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    read_time = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    adapter = WordPressCurrentPageSnapshotAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Bezpieczny researcher excerpt.",
            extraction_region="wordpress_rest.content",
        ),
        clock=lambda: read_time,
    )
    acquisition = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
        current_page_snapshot_reader=adapter.read,
        clock=lambda: read_time,
    )
    run = acquisition.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Zbadaj aktualną treść.",
        )
    )
    assert run.status == "ready_for_researcher"
    return workflow_store, acquisition, run, read_time


def test_identity_acquisition_revalidates_newer_classification_before_researcher(
    tmp_path: Path,
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    recorded_run = exact_public_bdo_run()
    newer_packet_sha = "a" * 64
    newer_run = production_module._build_run(
        input_receipt=recorded_run.input.model_copy(
            update={"packet_sha256": newer_packet_sha}
        ),
        counts=recorded_run.counts,
        freshness=recorded_run.freshness,
        source_receipts=recorded_run.source_receipts,
        judge_receipt=recorded_run.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": newer_packet_sha}
        ),
        rows=recorded_run.rows,
        audit=recorded_run.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 1, 10, 5, tzinfo=UTC)}
        ),
    )
    workflow_store.record_production_classification(newer_run)

    current = acquisition.read(run.run_id)
    assert current is not None
    assert current.recorded_status == "ready_for_researcher"
    assert current.current_status == "blocked"
    assert current.current_blockers[0].code == "identity_classification_drift"

    repeated = acquisition.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(run.identity_binding_id),
            research_question="Zbadaj aktualną treść.",
        )
    )
    assert repeated.current_status == "blocked"
    assert repeated.current_blockers[0].code == "identity_classification_drift"

    researcher = _FakeResearcher(
        {
            "proposed_claim": "Nie powinno zostać użyte.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    assert proposal.status == "blocked"
    assert proposal.blockers[0].code == "identity_classification_drift"
    assert researcher.requests == []


class _FakeResearcher:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(self.payload),
            turn_id="turn_research_test",
        )


def test_research_proposal_is_server_lineaged_and_review_only(tmp_path: Path) -> None:
    workflow_store, acquisition, run, _read_time = _ready_acquisition_fixture(tmp_path)
    assert run.observation is not None
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "opis bieżącej strony",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": ["Brak niezależnego źródła pierwotnego."],
        }
    )
    coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
    )

    proposal = coordinator.start(run.run_id)

    assert proposal.status == "ready_for_review"
    assert proposal.approved is False
    assert proposal.review_required is True
    assert proposal.acquisition_run_digest == run.recorded_run.run_digest
    assert proposal.observation_id == run.observation.observation_id
    assert proposal.evidence_ids == run.observation.evidence_ids
    assert proposal.source_url == run.observation.source_url
    assert proposal.researcher_run_id == "turn_research_test"
    assert "evidence_ids" not in researcher.requests[0].output_schema["properties"]
    assert "source_url" not in researcher.requests[0].output_schema["properties"]
    assert "Bezpieczny researcher excerpt." in researcher.requests[0].untrusted_context
    assert workflow_store.get_research_proposal(proposal.proposal_id) == proposal.recorded_proposal


def test_ready_research_proposal_projects_stale_on_post_and_get(
    tmp_path: Path,
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    first_researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    first = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=first_researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stale_researcher = _FakeResearcher(
        {
            "proposed_claim": "Nie powinno zostać użyte.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    stale_coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=stale_researcher,
        clock=lambda: read_time.replace(day=15, hour=12),
    )

    stale_post = stale_coordinator.start(run.run_id)
    stale_get = stale_coordinator.read(first.proposal_id)

    assert stale_get is not None
    assert stale_post.proposal_id == first.proposal_id
    assert stale_post.status == stale_get.status == "blocked"
    assert stale_post.current_status == stale_get.current_status == "blocked"
    assert stale_post.recorded_status == stale_get.recorded_status == "ready_for_review"
    assert stale_post.blockers[0].code == stale_get.blockers[0].code
    assert stale_post.blockers[0].code == "current_page_snapshot_stale"
    assert stale_post.recorded_proposal.proposal_id == first.proposal_id
    assert stale_researcher.requests == []


def test_research_promotion_candidate_is_exact_and_exposes_human_choices(
    tmp_path: Path,
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    assert run.observation is not None
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "invented_scope",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    research = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    )
    proposal = research.start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )

    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )

    assert candidate.status == "ready_for_human_decisions"
    assert candidate.proposal_id == proposal.proposal_id
    assert candidate.acquisition_run_digest == stored_run.run_digest
    assert candidate.service_binding.status == "exact_bound"
    assert candidate.policy is not None
    assert candidate.policy.target_card_id == candidate.service_binding.card_id
    assert candidate.proposed_scope_text == "invented_scope"
    scope_choice = next(
        item for item in candidate.required_human_decisions if item.field == "scope"
    )
    confidence_choice = next(
        item for item in candidate.required_human_decisions if item.field == "confidence"
    )
    assert set(scope_choice.allowed_values) == {
        "service",
        "buyer_problem",
        "cta",
        "claim_policy",
        "evidence_requirement",
        "metric_signal",
    }
    assert confidence_choice.minimum == 0.0
    assert confidence_choice.maximum == 1.0


@pytest.mark.parametrize(
    "card_status",
    ["source_backed_review_required", "unreviewed", "stale", "rejected"],
)
def test_research_promotion_candidate_blocks_unapproved_card_lifecycle(
    tmp_path: Path,
    card_status: str,
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    cards = ekologus_content_knowledge_cards()
    target_card_id = next(
        card.id
        for card in cards
        if identity.public_url.rstrip("/") in {url.rstrip("/") for url in card.service_binding_urls}
    )
    changed_cards = tuple(
        card.model_copy(update={"lifecycle_status": card_status})
        if card.id == target_card_id
        else card
        for card in cards
    )

    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        cards=changed_cards,
        checked_at=read_time,
    )

    assert candidate.status == "blocked"
    assert candidate.blockers[0].reason.startswith("service_card_review_required:")
    assert "ev_content_service_profile_source_facts" in candidate.blockers[0].evidence_ids
    assert "zatwierdź exact kartę Service Profile" in candidate.blockers[0].next_step
    assert candidate.safe_next_step == candidate.blockers[0].next_step
    assert candidate.policy is None


def test_research_promotion_candidate_blocks_stale_proposal(tmp_path: Path) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    assert run.observation is not None
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    research = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    )
    proposal = research.start(run.run_id)
    stale = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time.replace(day=15, hour=12),
    ).read(proposal.proposal_id)
    assert stale is not None
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )

    candidate = build_research_promotion_candidate_projection(
        stale,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time.replace(day=15, hour=12),
    )

    assert candidate.status == "blocked"
    assert any(blocker.reason for blocker in candidate.blockers)


def test_public_promotion_candidate_translates_legacy_and_keeps_valid_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )
    test_app = FastAPI()
    test_router = APIRouter()
    acquisition_router.register_content_evidence_acquisition_routes(test_router)
    test_app.include_router(test_router)

    def legacy_reader(_proposal_id: str):
        raise ResearchProposalLegacyUnreadable(
            ResearchProposalReadDiagnostic(
                proposal_id="content_research_proposal_legacy_candidate",
                acquisition_run_id=run.run_id,
                stored_contract_version="content_research_proposal_attempt_v1",
                source_url=run.observation.source_url,
                reason="Stored research proposal does not satisfy the current contract.",
                safe_next_step="Utwórz nową próbę bez reinterpretacji starego digestu.",
            )
        )

    monkeypatch.setattr(
        acquisition_router,
        "build_default_research_promotion_candidate",
        legacy_reader,
    )
    client = TestClient(test_app, raise_server_exceptions=False)
    legacy_response = client.get(
        "/api/content/evidence-acquisition/research/"
        "content_research_proposal_legacy_candidate/promotion-candidate"
    )
    assert legacy_response.status_code == 409, legacy_response.text
    assert legacy_response.json()["detail"]["code"] == (
        "research_proposal_legacy_unreadable"
    )
    assert legacy_response.json()["detail"]["stored_contract_version"] == (
        "content_research_proposal_attempt_v1"
    )
    assert "payload_json" not in legacy_response.text

    monkeypatch.setattr(
        acquisition_router,
        "build_default_research_promotion_candidate",
        lambda _proposal_id: candidate,
    )
    valid_response = client.get(
        f"/api/content/evidence-acquisition/research/{proposal.proposal_id}/"
        "promotion-candidate"
    )
    assert valid_response.status_code == 200, valid_response.text
    assert valid_response.json()["status"] == "ready_for_human_decisions"
    assert valid_response.json()["proposal_id"] == proposal.proposal_id


def test_research_promotion_preview_is_local_non_executable_and_self_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )
    monkeypatch.setattr(
        promotion_authority,
        "build_default_research_promotion_candidate",
        lambda _proposal_id: candidate,
    )

    response = prepare_research_fact_promotion_preview(
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=proposal.proposal_id,
            proposed_scope="service",
            proposed_confidence=0.8,
        )
    )

    assert response.status == "preview_ready"
    assert response.action is not None
    assert response.action.payload["apply_allowed"] is True
    assert response.action.payload["api_mutation_ready"] is True
    assert response.action.payload["local_authority_only"] is True
    assert response.action.payload["runtime_blockers"] == []
    assert response.snapshot is not None
    assert response.snapshot.context_digest
    assert response.action.payload["promotion_snapshot"]["evidence_ids"] == list(
        run.observation.evidence_ids
    )

    for missing_claim in (None, ""):
        monkeypatch.setattr(
            promotion_authority,
            "build_default_research_promotion_candidate",
            lambda _proposal_id, missing_claim=missing_claim: candidate.model_copy(
                update={"proposed_claim": missing_claim}
            ),
        )
        blocked = prepare_research_fact_promotion_preview(
            ContentResearchFactPromotionPreviewCommand(
                proposal_id=proposal.proposal_id,
                proposed_scope="service",
                proposed_confidence=0.8,
            )
        )
        assert blocked.status == "blocked"
        assert blocked.action is None
        assert blocked.blockers[0].startswith("research_claim_missing:")


def test_research_promotion_preview_rejects_forged_choices() -> None:
    with pytest.raises(ValidationError):
        ContentResearchFactPromotionPreviewCommand.model_validate(
            {
                "proposal_id": "content_research_proposal_test",
                "proposed_scope": "freeform",
                "proposed_confidence": 1.2,
                "evidence_ids": ["forged"],
            }
        )


def test_research_promotion_executor_requires_persisted_canonical_audit_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "audit.sqlite3"))
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )
    monkeypatch.setattr(
        promotion_authority,
        "build_default_research_promotion_candidate",
        lambda _id: candidate,
    )
    preview = prepare_research_fact_promotion_preview(
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=proposal.proposal_id,
            proposed_scope="service",
            proposed_confidence=0.8,
        ),
        store=workflow_store,
    )
    assert preview.action is not None and preview.snapshot is not None
    assert validate_research_fact_promotion_action_payload(preview.action.payload) == []
    digest = promotion_action_payload_digest(preview.action)
    details = {
        "research_promotion_snapshot_digest": preview.snapshot.context_digest,
        "research_promotion_action_payload_digest": digest,
    }
    events = [
        AuditEvent(
            id=f"audit_{index}",
            action_id=preview.action.id,
            event_type=event_type,
            actor="Wilku",
            summary=event_type,
            details=details,
        )
        for index, event_type in enumerate(
            (
                "action_preview_generated",
                "human_review_approved_for_prepare",
                "action_apply_confirmed",
                "action_impact_check_completed",
            ),
            start=1,
        )
    ]

    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: workflow_store)
    result, errors = action_service._execute_supported_mutation_adapter(
        preview.action,
        "content_research_fact_promotion_store",
    )

    assert result is None
    assert errors
    assert workflow_store.load_research_fact_promotion_receipt(preview.action.id) is None

    for event in events:
        action_service.stamp_authority_audit_context(preview.action, event)
        action_service.persist_action_audit(event)
    result, errors = action_service._execute_supported_mutation_adapter(
        preview.action,
        "content_research_fact_promotion_store",
    )

    assert result is None
    assert errors == ["promotion_reviewer_identity_unverified"]
    assert workflow_store.load_research_fact_promotion_receipt(preview.action.id) is None


def test_approved_promotion_receipt_merges_into_exact_source_fact_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )
    monkeypatch.setattr(
        promotion_authority,
        "build_default_research_promotion_candidate",
        lambda _id: candidate,
    )
    preview = prepare_research_fact_promotion_preview(
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=proposal.proposal_id,
            proposed_scope="service",
            proposed_confidence=0.8,
        ),
        store=workflow_store,
    )
    assert preview.action is not None and preview.snapshot is not None
    snapshot = preview.snapshot
    source_fact = ContentSourceFact(
        source_id=f"research_proposal_fact_{proposal.proposal_id}",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path=snapshot.source_url,
        extracted_fact=snapshot.proposed_claim,
        scope=snapshot.proposed_scope,
        freshness_date=snapshot.freshness_date,
        confidence=snapshot.proposed_confidence,
        review_status="approved",
        reviewer="fixture_reviewer",
        evidence_ids=list(snapshot.evidence_ids),
        source_connectors=list(snapshot.source_connectors),
        target_card_id=snapshot.target_card_id,
        target_card_type=snapshot.target_card_type,
        target_card_title=snapshot.target_card_title,
        allowed_claims=list(snapshot.allowed_claims),
        blocked_claims=list(snapshot.blocked_claims),
        evidence_requirements=list(snapshot.evidence_requirements),
    )
    receipt_payload = {
        "action_id": preview.action.id,
        "action_payload_digest": promotion_action_payload_digest(preview.action),
        "snapshot": snapshot.model_dump(mode="json"),
        "source_fact": source_fact.model_dump(mode="json"),
        "preview_audit_id": "audit_fixture_preview",
        "review_audit_id": "audit_fixture_review",
        "confirmation_audit_id": "audit_fixture_confirmation",
        "impact_audit_id": "audit_fixture_impact",
        "reviewed_by": "fixture_reviewer",
        "confirmed_by": "fixture_confirmer",
        "recorded_at": read_time.isoformat().replace("+00:00", "Z"),
    }
    receipt_digest = canonical_json_digest(receipt_payload)
    receipt = ContentResearchFactPromotionReceipt(
        receipt_id=f"content_research_fact_promotion_{receipt_digest[:24]}",
        receipt_digest=receipt_digest,
        **receipt_payload,
    )
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: workflow_store)
    baseline_facts = source_facts_module.ekologus_source_facts()
    baseline_registry_digest = source_fact_registry_digest(tuple(baseline_facts))
    assert workflow_store.record_research_fact_promotion_receipt(receipt)[0] == "created"

    receipt_payload_check = receipt.model_dump(mode="json")
    stored_receipt_digest = receipt_payload_check.pop("receipt_digest")
    stored_receipt_id = receipt_payload_check.pop("receipt_id")
    assert stored_receipt_digest == canonical_json_digest(receipt_payload_check)
    assert stored_receipt_id == (
        f"content_research_fact_promotion_{stored_receipt_digest[:24]}"
    )
    stored_receipt = workflow_store.list_research_fact_promotion_receipts()[0]
    stored_payload_check = stored_receipt.model_dump(mode="json")
    stored_payload_digest = stored_payload_check.pop("receipt_digest")
    stored_payload_check.pop("receipt_id")
    assert stored_payload_digest == canonical_json_digest(stored_payload_check)
    facts = source_facts_module.ekologus_source_facts()
    dynamic_id = source_fact.source_id
    assert dynamic_id in {fact.source_id for fact in facts}
    projection = build_research_promotion_candidate_projection(
        proposal=proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        facts=facts,
        checked_at=read_time,
    )
    assert projection.status == "ready_for_human_decisions"
    assert projection.existing_scope_projection is not None
    assert dynamic_id in {
        candidate.source_fact_id
        for candidate in projection.existing_scope_projection.eligible_candidates
    }
    registry_digest = source_fact_registry_digest(tuple(facts))
    facts_again = source_facts_module.ekologus_source_facts()
    assert facts == facts_again
    assert registry_digest == source_fact_registry_digest(tuple(facts_again))
    assert registry_digest != baseline_registry_digest
    collision_source_id = "ekologus_public_bdo_faq_2026_07_01"
    baseline_static_fact = next(
        fact for fact in baseline_facts if fact.source_id == collision_source_id
    )
    collision_fact = source_fact.model_copy(update={"source_id": collision_source_id})
    collision_payload = {
        **receipt_payload,
        "action_id": "act_content_research_fact_promotion_collision",
        "source_fact": collision_fact.model_dump(mode="json"),
    }
    collision_digest = canonical_json_digest(collision_payload)
    collision_receipt = ContentResearchFactPromotionReceipt(
        receipt_id=f"content_research_fact_promotion_{collision_digest[:24]}",
        receipt_digest=collision_digest,
        **collision_payload,
    )
    assert (
        workflow_store.record_research_fact_promotion_receipt(collision_receipt)[0]
        == "created"
    )
    collision_facts = source_facts_module.ekologus_source_facts()
    collision_matches = [
        fact for fact in collision_facts if fact.source_id == collision_source_id
    ]
    assert collision_matches == [baseline_static_fact]
    with monkeypatch.context() as stale_patch:
        stale_patch.setattr(
            evidence_snapshot_module,
            "current_page_receipt_is_fresh",
            lambda *_args, **_kwargs: False,
        )
        stale_facts = source_facts_module.ekologus_source_facts()
    assert dynamic_id not in {fact.source_id for fact in stale_facts}

    monkeypatch.setattr(
        workflow_store,
        "list_research_fact_promotion_receipts",
        lambda: [],
    )
    tampered_facts = source_facts_module.ekologus_source_facts()
    assert dynamic_id not in {fact.source_id for fact in tampered_facts}


def test_public_research_promotion_lifecycle_blocks_unverified_principal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "public-audit.sqlite3"))
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "service",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    proposal = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    ).start(run.run_id)
    stored_run = workflow_store.get_evidence_acquisition_run(run.run_id)
    assert stored_run is not None
    identity = workflow_store.load_content_delivery_identity(stored_run.identity_binding_id)
    assert identity is not None
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    candidate = build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=stored_run,
        identity=identity,
        classification=classification,
        checked_at=read_time,
    )
    monkeypatch.setattr(
        promotion_authority,
        "build_default_research_promotion_candidate",
        lambda _id: candidate,
    )
    preview = prepare_research_fact_promotion_preview(
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=proposal.proposal_id,
            proposed_scope="service",
            proposed_confidence=0.8,
        ),
        store=workflow_store,
    )
    assert preview.action is not None
    action_id = preview.action.id
    monkeypatch.setattr(action_catalog, "content_workflow_store", lambda: workflow_store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: workflow_store)
    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _connector: SimpleNamespace(
            configured=True,
            label="WordPress ekologus.pl",
        ),
    )
    client = TestClient(app)

    assert client.get(f"/api/actions/{action_id}").status_code == 200
    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200
    assert validation.json()["valid"] is True, validation.json()["errors"]
    assert client.post(f"/api/actions/{action_id}/preview").status_code == 200
    assert (
        client.post(
            f"/api/actions/{action_id}/review",
            json={
                "outcome": "approved_for_prepare",
                "reviewed_by": "attacker_label",
                "notes": "Prośba o promotion.",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/actions/{action_id}/confirm",
            json={
                "confirm": True,
                "confirmed_by": "attacker_label",
                "notes": "Potwierdzam.",
                "preview_acknowledged": True,
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/actions/{action_id}/impact-check",
            json={
                "checked_by": "attacker_label",
                "notes": "Sprawdzam gotowość.",
            },
        ).status_code
        == 200
    )
    audit_events = client.get(f"/api/audit/events?action_id={action_id}").json()
    assert [event["event_type"] for event in audit_events] == [
        "action_impact_check_completed",
        "action_apply_confirmed",
        "human_review_approved_for_prepare",
        "action_preview_generated",
    ]

    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "attacker_label"},
    )

    assert applied.status_code == 409
    assert "promotion_reviewer_identity_unverified" in applied.json()["detail"]["errors"]
    assert workflow_store.load_research_fact_promotion_receipt(action_id) is None


def test_research_model_only_and_legal_claims_are_typed_blockers(tmp_path: Path) -> None:
    workflow_store, acquisition, run, _read_time = _ready_acquisition_fixture(tmp_path)
    model_only = _FakeResearcher(
        {
            "proposed_claim": "Model-only claim.",
            "scope": "opis",
            "observation_ids": [],
            "contradictions": [],
            "unknowns": [],
        }
    )
    model_coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=model_only,
    )
    blocked_model = model_coordinator.start(run.run_id)
    assert blocked_model.status == "blocked"
    assert blocked_model.blockers[0].code == "research_model_only_claim"

    workflow_store_legal, acquisition_legal, run_legal, _ = _ready_acquisition_fixture(
        tmp_path / "legal"
    )
    legal = _FakeResearcher(
        {
            "proposed_claim": "To jest zgodne z prawem.",
            "scope": "legal",
            "observation_ids": [run_legal.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    legal_coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition_legal.read,
        proposal_store=workflow_store_legal,
        researcher=legal,
    )
    blocked_legal = legal_coordinator.start(run_legal.run_id)
    assert blocked_legal.status == "blocked"
    assert blocked_legal.blockers[0].code == "legal_claim_requires_official_source"


@pytest.mark.parametrize(
    ("claim", "expected_code"),
    [
        ("Bezpieczny\nresearcher   excerpt!!!", "researcher_excerpt_reproduction"),
        (
            "Przedsiębiorca musi złożyć sprawozdanie BDO.",
            "legal_claim_requires_official_source",
        ),
        ("token = sk - ABC123456789", "researcher_unsafe_output"),
    ],
)
def test_research_output_normalization_blocks_excerpt_legal_and_secret_variants(
    tmp_path: Path,
    claim: str,
    expected_code: str,
) -> None:
    workflow_store, acquisition, run, _read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": claim,
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
    )

    blocked = coordinator.start(run.run_id)
    stored = workflow_store.get_research_proposal(blocked.proposal_id)

    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == expected_code
    assert stored is not None
    assert stored.status == "blocked"
    assert stored.proposed_claim is None


def test_stale_acquisition_blocks_researcher_before_port_invocation(tmp_path: Path) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Nie powinno zostać użyte.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time.replace(day=15, hour=12),
    )

    blocked = coordinator.start(run.run_id)

    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == "current_page_snapshot_stale"
    assert researcher.requests == []


def test_start_rejects_retained_identity_without_material_read(tmp_path: Path) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    retained = workflow_store.record_content_delivery_identity(
        identity_command(retained=True)
    ).binding
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=workflow_store.load_production_classification_for_work_item,
        store=workflow_store,
    )

    run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(retained.binding_id),
            research_question="Sprawdź obserwacje historyczne.",
        )
    )

    assert run.status == "blocked"
    assert run.blockers[0].code == "identity_binding_not_exact_current"


def test_start_blocks_stale_classification_before_acquisition(tmp_path: Path) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    identity = workflow_store.record_content_delivery_identity(
        _exact_bdo_identity_command()
    ).binding
    current = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    assert current is not None
    stale = current.model_copy(
        update={
            "freshness": current.freshness.model_copy(
                update={"state": "stale", "requires_refresh": True}
            )
        }
    )
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=workflow_store.load_content_delivery_identity,
        classification_loader=lambda _work_item_id: stale,
        store=workflow_store,
    )

    run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject(identity.binding_id),
            research_question="Sprawdź bieżącą stronę.",
        )
    )

    assert run.status == "blocked"
    assert run.blockers[0].code == "classification_stale"


def test_start_is_idempotent_and_persists_only_safe_question(tmp_path: Path) -> None:
    coordinator, identity = _coordinator(tmp_path)
    command = EvidenceAcquisitionStartCommand(
        subject=_identity_subject(identity.binding_id),
        research_question="Check token=sk-THIS-MUST-NOT-BE-STORED-123456789.",
    )

    first = coordinator.start(command)
    second = coordinator.start(command)

    assert first.run_id == second.run_id
    assert first.request_digest == second.request_digest
    assert "sk-THIS-MUST-NOT-BE-STORED" not in first.research_question_safe
    with sqlite3.connect(tmp_path / "workflow.sqlite3") as connection:
        payload = connection.execute(
            "SELECT payload_json FROM content_evidence_acquisition_runs WHERE run_id = ?",
            (first.run_id,),
        ).fetchone()[0]
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'content_evidence_acquisition_runs'"
        ).fetchone()
    assert "sk-THIS-MUST-NOT-BE-STORED" not in payload
    assert table == (1,)
    assert 0 < schema_version <= SQLITE_SCHEMA_VERSION
    assert (tmp_path / "workflow.sqlite3").stat().st_mode & 0o777 == 0o600


def _create_pre_request_digest_table(path: Path, *, with_row: bool) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE content_evidence_acquisition_runs (
              run_id TEXT PRIMARY KEY,
              run_digest TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        if with_row:
            connection.execute(
                """
                INSERT INTO content_evidence_acquisition_runs (
                  run_id, run_digest, status, payload_json
                ) VALUES ('legacy_run', ?, 'blocked', '{}')
                """,
                ("a" * 64,),
            )
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")


def test_empty_pre_request_digest_table_migrates_safely(tmp_path: Path) -> None:
    path = tmp_path / "empty-legacy.sqlite3"
    _create_pre_request_digest_table(path, with_row=False)

    assert ContentWorkflowStore(path).get_evidence_acquisition_run("missing") is None

    with sqlite3.connect(path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(content_evidence_acquisition_runs)"
            )
        }
        indexes = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA index_list(content_evidence_acquisition_runs)"
            )
        }
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' AND name LIKE 'content_evidence_acquisition_runs_%'"
            )
        }
    assert "request_digest" in columns
    assert "uq_content_evidence_acquisition_runs_request_digest" in indexes
    assert triggers == {
        "content_evidence_acquisition_runs_no_update",
        "content_evidence_acquisition_runs_no_delete",
    }


def test_pre_request_digest_rows_fail_closed_with_typed_error(tmp_path: Path) -> None:
    path = tmp_path / "legacy-with-row.sqlite3"
    _create_pre_request_digest_table(path, with_row=True)

    with pytest.raises(ContentWorkflowSchemaMigrationError, match="request_digest"):
        ContentWorkflowStore(path).get_evidence_acquisition_run("legacy_run")


def test_missing_identity_has_no_placeholder_authority_fields(tmp_path: Path) -> None:
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _identity_id: None,
        classification_loader=lambda _work_item_id: pytest.fail("classification must not load"),
        store=ContentWorkflowStore(tmp_path / "missing.sqlite3"),
    )

    run = coordinator.start(
        EvidenceAcquisitionStartCommand(
            subject=_identity_subject("content_delivery_identity_missing"),
            research_question="Sprawdź exact źródła.",
        )
    )

    assert run.status == "blocked"
    assert run.identity_binding_digest is None
    assert run.current_work_item_id is None
    assert run.classification_run_digest is None
    assert run.inventory_evidence_ids == ()


def test_real_store_isolates_legacy_proposal_and_public_get_returns_typed_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    )
    valid = coordinator.start(run.run_id)
    assert valid.status == "ready_for_review"
    assert valid.recorded_proposal.contract_version == (
        "content_research_proposal_attempt_v2"
    )

    legacy_payload = valid.recorded_proposal.model_dump(mode="json")
    legacy_payload.update(
        {
            "contract_version": "content_research_proposal_attempt_v1",
            "input_digest": canonical_json_digest(
                {"legacy_research_attempt": valid.proposal_id}
            ),
            "source_url": "https://www.ekologus.pl/legacy/",
        }
    )
    legacy_digest_payload = {
        key: value
        for key, value in legacy_payload.items()
        if key not in {"proposal_id", "proposal_digest", "attempt_id", "recorded_at"}
    }
    legacy_digest = canonical_json_digest(legacy_digest_payload)
    legacy_id = f"content_research_proposal_{legacy_digest[:24]}"
    legacy_run_id = legacy_payload["acquisition_run_id"]
    legacy_payload.update(
        {
            "proposal_id": legacy_id,
            "proposal_digest": legacy_digest,
            "attempt_id": f"content_research_attempt_{legacy_digest[:24]}",
        }
    )
    with sqlite3.connect(tmp_path / "workflow.sqlite3") as connection:
        connection.execute(
            """
            INSERT INTO content_research_proposals (
              proposal_id, proposal_digest, attempt_id, input_digest,
              acquisition_run_id, acquisition_run_digest, status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_id,
                legacy_digest,
                legacy_payload["attempt_id"],
                legacy_payload["input_digest"],
                legacy_run_id,
                legacy_payload["acquisition_run_digest"],
                legacy_payload["status"],
                json.dumps(legacy_payload),
            ),
        )

    results = workflow_store.list_research_proposals_with_diagnostics()
    valid_rows = [item.proposal for item in results if item.proposal is not None]
    diagnostics = [item.diagnostic for item in results if item.diagnostic is not None]
    assert any(item.proposal_id == valid.proposal_id for item in valid_rows)
    assert [item.proposal_id for item in valid_rows] == [valid.proposal_id]
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "research_proposal_legacy_unreadable"
    assert diagnostics[0].stored_contract_version == (
        "content_research_proposal_attempt_v1"
    )
    assert diagnostics[0].source_url == "https://www.ekologus.pl/legacy/"
    with pytest.raises(ResearchProposalLegacyUnreadable) as error:
        workflow_store.get_research_proposal(legacy_id)
    assert error.value.diagnostic.code == "research_proposal_legacy_unreadable"
    assert error.value.diagnostic.stored_contract_version == (
        "content_research_proposal_attempt_v1"
    )
    assert workflow_store.list_research_proposals()[0].proposal_id == valid.proposal_id

    diagnostics_before_candidate_read = (
        workflow_store.list_research_proposals_with_diagnostics()
    )

    test_app = FastAPI()
    test_router = APIRouter()
    acquisition_router.register_content_evidence_acquisition_routes(test_router)
    test_app.include_router(test_router)
    monkeypatch.setattr(
        acquisition_router,
        "build_default_evidence_research_coordinator",
        lambda: coordinator,
    )
    client = TestClient(test_app, raise_server_exceptions=False)

    valid_response = client.get(
        f"/api/content/evidence-acquisition/research/{valid.proposal_id}"
    )
    assert valid_response.status_code == 200, valid_response.text
    legacy_response = client.get(
        f"/api/content/evidence-acquisition/research/{legacy_id}"
    )
    assert legacy_response.status_code == 409, legacy_response.text
    assert legacy_response.json()["detail"]["code"] == "research_proposal_legacy_unreadable"
    assert legacy_response.json()["detail"]["stored_contract_version"] == (
        "content_research_proposal_attempt_v1"
    )
    assert "payload_json" not in legacy_response.text

    monkeypatch.setattr(
        promotion_candidate_module,
        "build_default_evidence_research_coordinator",
        lambda: coordinator,
    )
    monkeypatch.setattr(
        workflow_store_module,
        "content_workflow_store",
        lambda: workflow_store,
    )
    candidate_legacy_response = client.get(
        f"/api/content/evidence-acquisition/research/{legacy_id}/promotion-candidate"
    )
    assert candidate_legacy_response.status_code == 409, candidate_legacy_response.text
    assert candidate_legacy_response.json()["detail"] == legacy_response.json()["detail"]
    assert "payload_json" not in candidate_legacy_response.text
    assert workflow_store.list_research_proposals_with_diagnostics() == (
        diagnostics_before_candidate_read
    )


def test_post_research_translates_legacy_input_collision_and_retries_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_store, acquisition, run, read_time = _ready_acquisition_fixture(tmp_path)
    researcher = _FakeResearcher(
        {
            "proposed_claim": "Strona opisuje zakres usługi.",
            "scope": "opis",
            "observation_ids": [run.observation.observation_id],
            "contradictions": [],
            "unknowns": [],
        }
    )
    valid_coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_time,
    )
    valid = valid_coordinator.start(run.run_id)

    legacy_store = ContentWorkflowStore(tmp_path / "legacy-workflow.sqlite3")
    assert legacy_store.list_research_proposals() == []
    legacy_payload = valid.recorded_proposal.model_dump(mode="json")
    legacy_payload["contract_version"] = "content_research_proposal_attempt_v1"
    legacy_digest_payload = {
        key: value
        for key, value in legacy_payload.items()
        if key not in {"proposal_id", "proposal_digest", "attempt_id", "recorded_at"}
    }
    legacy_digest = canonical_json_digest(legacy_digest_payload)
    legacy_payload.update(
        {
            "proposal_id": f"content_research_proposal_{legacy_digest[:24]}",
            "proposal_digest": legacy_digest,
            "attempt_id": f"content_research_attempt_{legacy_digest[:24]}",
        }
    )
    with sqlite3.connect(tmp_path / "legacy-workflow.sqlite3") as connection:
        connection.execute(
            """
            INSERT INTO content_research_proposals (
              proposal_id, proposal_digest, attempt_id, input_digest,
              acquisition_run_id, acquisition_run_digest, status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_payload["proposal_id"],
                legacy_digest,
                legacy_payload["attempt_id"],
                legacy_payload["input_digest"],
                legacy_payload["acquisition_run_id"],
                legacy_payload["acquisition_run_digest"],
                legacy_payload["status"],
                json.dumps(legacy_payload),
            ),
        )

    with pytest.raises(ResearchProposalLegacyUnreadable) as save_error:
        legacy_store.save_research_proposal(valid.recorded_proposal)
    assert save_error.value.diagnostic.stored_contract_version == (
        "content_research_proposal_attempt_v1"
    )

    legacy_coordinator = EvidenceResearchCoordinator(
        acquisition_reader=acquisition.read,
        proposal_store=legacy_store,
        researcher=researcher,
        clock=lambda: read_time,
    )
    test_app = FastAPI()
    test_router = APIRouter()
    acquisition_router.register_content_evidence_acquisition_routes(test_router)
    test_app.include_router(test_router)
    monkeypatch.setattr(
        acquisition_router,
        "build_default_evidence_research_coordinator",
        lambda: legacy_coordinator,
    )
    client = TestClient(test_app, raise_server_exceptions=False)

    legacy_response = client.post(
        f"/api/content/evidence-acquisition/{run.run_id}/research"
    )
    assert legacy_response.status_code == 409, legacy_response.text
    assert legacy_response.json()["detail"]["code"] == (
        "research_proposal_legacy_unreadable"
    )
    assert legacy_response.json()["detail"]["stored_contract_version"] == (
        "content_research_proposal_attempt_v1"
    )
    assert "payload_json" not in legacy_response.text

    monkeypatch.setattr(
        acquisition_router,
        "build_default_evidence_research_coordinator",
        lambda: valid_coordinator,
    )
    first_v2_response = client.post(
        f"/api/content/evidence-acquisition/{run.run_id}/research"
    )
    second_v2_response = client.post(
        f"/api/content/evidence-acquisition/{run.run_id}/research"
    )
    assert first_v2_response.status_code == 200, first_v2_response.text
    assert second_v2_response.status_code == 200, second_v2_response.text
    assert first_v2_response.json()["recorded_proposal"]["contract_version"] == (
        "content_research_proposal_attempt_v2"
    )
    assert second_v2_response.json()["proposal_id"] == valid.proposal_id
    assert len(researcher.requests) == 1


def test_old_preview_is_absent_and_start_command_rejects_caller_evidence() -> None:
    app = FastAPI()
    router = APIRouter()
    acquisition_router.register_content_evidence_acquisition_routes(router)
    app.include_router(router)
    openapi = app.openapi()
    paths = openapi["paths"]
    schemas = openapi["components"]["schemas"]

    assert "/api/content/evidence-acquisition/preview" not in paths
    assert "/api/content/evidence-acquisition" in paths
    assert "/api/content/evidence-acquisition/{run_id}" in paths
    assert "/api/content/evidence-acquisition/{run_id}/research" in paths
    assert "/api/content/evidence-acquisition/research/{proposal_id}" in paths
    assert "/api/content/evidence-acquisition/research/{proposal_id}/promotion-preview" in paths
    promotion_schema = paths[
        "/api/content/evidence-acquisition/research/{proposal_id}/promotion-preview"
    ]["post"]["requestBody"]["content"]["application/json"]["schema"]
    promotion_schema = schemas[promotion_schema["$ref"].rsplit("/", 1)[-1]]
    assert "proposal_id" not in promotion_schema["properties"]
    assert set(promotion_schema["properties"]) == {
        "proposed_scope",
        "proposed_confidence",
    }
    assert paths["/api/content/evidence-acquisition/{run_id}/research"]["post"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentResearchProposalCurrentProjection"
    )
    proposal_attempt_schema = schemas["ContentResearchProposalAttempt"]
    assert proposal_attempt_schema["properties"]["contract_version"]["const"] == (
        "content_research_proposal_attempt_v2"
    )
    post_schema = paths["/api/content/evidence-acquisition"]["post"]["responses"]["200"]
    get_schema = paths["/api/content/evidence-acquisition/{run_id}"]["get"]["responses"]["200"]
    assert post_schema["content"]["application/json"]["schema"]["$ref"].endswith(
        "EvidenceAcquisitionCurrentProjection"
    )
    assert get_schema["content"]["application/json"]["schema"]["$ref"].endswith(
        "EvidenceAcquisitionCurrentProjection"
    )
    invalid = TestClient(app).get("/api/content/evidence-acquisition/bad!")
    assert invalid.status_code == 422
    with pytest.raises(ValidationError):
        EvidenceAcquisitionStartCommand.model_validate(
            {
                "subject": {
                    "subject_kind": "identity_binding",
                    "identity_binding_id": "content_delivery_identity_x",
                },
                "research_question": "Pytanie testowe.",
                "evidence_ids": ["forged"],
            }
        )
