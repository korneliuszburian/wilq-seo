from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tests.content.test_authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
)
from tests.content.test_authoring_inventory_receipt import _item as authoring_item
from wilq.content.workflow.authoring_inventory_receipt import (
    content_inventory_catalog_snapshot_digest,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBlocker
from wilq.content.workflow.research_proposal import (
    ResearchProposalReadDiagnostic,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)
from wilq.content.workflow.workspace.journal_evidence_readiness import (
    build_content_inventory_journal_readiness,
)


def test_redirect_path_observation_never_becomes_authoring_identity(tmp_path) -> None:
    journal = tmp_path / "content-status.csv"
    with journal.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["as_of", "path", "content_kind", "final_disposition", "next_action"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "as_of": "2026-09-10T12:00:00+02:00",
                "path": "/old-page",
                "content_kind": "editorial",
                "final_disposition": "redirect",
                "next_action": "configure_redirect",
            }
        )

    readiness = build_content_inventory_journal_readiness(
        [_catalog_item("/old-page/")],
        catalog_coverage_status="unknown",
        journal_path=journal,
    )

    assert readiness.status == "blocked"
    assert len(readiness.rows) == 1
    row = readiness.rows[0]
    assert row.final_disposition == "redirect"
    assert row.operational_owner == "WILQ sitemap operations"
    assert row.production_cohort is False
    assert row.current_catalog_state == "exact_path_observed"
    assert row.current_catalog_observation is not None
    assert set(row.current_catalog_observation.model_dump()) == {
        "path",
        "url",
        "content_type",
        "material_status",
        "source_connector",
        "evidence_id",
        "collected_at",
    }
    assert "work_item_id" not in readiness.model_dump_json()
    assert "revision" not in readiness.model_dump_json()
    assert "approval" not in readiness.model_dump_json()
    assert "draft" not in readiness.model_dump_json()

    incomplete_scope = build_content_inventory_journal_readiness(
        [_catalog_item("/old-page/")],
        catalog_coverage_status="complete",
        journal_path=journal,
    )
    assert incomplete_scope.status == "incomplete"


class _ReadOnlyEvidenceStore:
    def __init__(
        self,
        *,
        receipts=(),
        acquisitions=(),
        proposals=(),
        identities=(),
        promotions=(),
        proposal_diagnostics=(),
    ):
        self.receipts = list(receipts)
        self.acquisitions = list(acquisitions)
        self.proposals = list(proposals)
        self.identities = list(identities)
        self.promotions = list(promotions)
        self.proposal_diagnostics = list(proposal_diagnostics)
        self.calls: dict[str, int] = {}
        self.write_calls = 0

    def _read(self, name: str, values: list[object]) -> list[object]:
        self.calls[name] = self.calls.get(name, 0) + 1
        return list(values)

    def list_content_authoring_inventory_receipts(self):
        return self._read("receipts", self.receipts)

    def list_evidence_acquisition_runs(self):
        return self._read("acquisitions", self.acquisitions)

    def list_research_proposals(self):
        return self._read("proposals", self.proposals)

    def list_research_proposals_with_diagnostics(self):
        results = [
            SimpleNamespace(proposal=proposal, diagnostic=None)
            for proposal in self.proposals
        ]
        results.extend(
            SimpleNamespace(proposal=None, diagnostic=diagnostic)
            for diagnostic in self.proposal_diagnostics
        )
        return self._read("proposals", results)

    def list_content_delivery_identity_bindings(self):
        return self._read("identities", self.identities)

    def list_content_delivery_identity_current_projections(self):
        return self._read("identities", self.identities)

    def list_research_fact_promotion_receipts(self):
        return self._read("promotions", self.promotions)


def test_journal_uses_current_identity_projection_for_classification_drift(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "content-status.csv"
    _write_journal(journal, ["/"])
    binding = SimpleNamespace(
        binding_id="content_delivery_identity_home",
        binding_digest="a" * 64,
        canonical_path="/",
        recorded_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
    )
    current_projection = SimpleNamespace(
        recorded_binding=binding,
        recorded_status="exact_current",
        current_status="blocked",
        current_blocker=ContentDeliveryIdentityBlocker(
            seam="classification_identity",
            reason="identity_classification_drift",
            evidence_ids=("ev_identity",),
            next_step="Odśwież exact S1/classification context.",
        ),
        current_safe_next_step="Odśwież exact S1/classification context.",
    )
    acquisition = _ready_run(
        path="/",
        subject_kind="identity_binding",
        subject_id=binding.binding_id,
        evidence_id="ev_home_observation",
        run_id="content_evidence_acquisition_home",
    )
    store = _ReadOnlyEvidenceStore(
        identities=[current_projection], acquisitions=[acquisition]
    )

    readiness = build_content_inventory_journal_readiness(
        [_catalog_item("/")],
        catalog_coverage_status="partial",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )

    identity = readiness.rows[0].content_evidence_readiness.identity
    acquisition_readiness = readiness.rows[0].content_evidence_readiness.evidence_acquisition
    assert identity.status == "blocked"
    assert identity.blockers[0].code == "identity_classification_drift"
    assert identity.blockers[0].reason == (
        "Current identity classification_identity blocker: identity_classification_drift."
    )
    assert identity.blockers[0].evidence_ids == ("ev_identity",)
    assert identity.blockers[0].safe_next_step == "Odśwież exact S1/classification context."
    assert acquisition_readiness.current_status == "blocked"
    assert acquisition_readiness.blockers[0].code == "identity_classification_drift"
    assert readiness.content_evidence_readiness.identity_exact_current_count == 0
    assert readiness.content_evidence_readiness.identity_blocked_count == 1
    assert readiness.content_evidence_readiness.acquisition_ready_count == 0
    assert readiness.content_evidence_readiness.acquisition_blocked_count == 1


def _catalog_item(path: str) -> ContentInventoryCatalogItem:
    return ContentInventoryCatalogItem(
        catalog_id="content_inventory_old_page",
        work_item_id="content_work_item_inventory_old_page",
        url=f"https://www.ekologus.pl{path}",
        path=path,
        content_type="post",
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id="ev_inventory_current",
        collected_at=datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
    )


def _write_journal(path: Path, paths: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["as_of", "path", "content_kind", "final_disposition", "next_action"],
        )
        writer.writeheader()
        for item in paths:
            writer.writerow(
                {
                    "as_of": "2026-09-13",
                    "path": item,
                    "content_kind": "service",
                    "final_disposition": "keep",
                    "next_action": "review",
                }
            )


def _ready_run(
    *,
    path: str,
    subject_kind: str,
    subject_id: str,
    evidence_id: str,
    run_id: str,
) -> Any:
    observation = SimpleNamespace(
        evidence_ids=(evidence_id,),
        read_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
        source_url=f"https://www.ekologus.pl{path}/" if path != "/" else "https://www.ekologus.pl/",
        canonical_path=path,
    )
    return SimpleNamespace(
        status="ready_for_researcher",
        run_id=run_id,
        run_digest="a" * 64,
        attempt=0,
        subject_kind=subject_kind,
        canonical_path=path,
        identity_binding_id=subject_id if subject_kind == "identity_binding" else None,
        authoring_inventory_receipt_id=(
            subject_id if subject_kind == "authoring_inventory_receipt" else None
        ),
        authoring_inventory_receipt_digest=None,
        observation=observation,
        blockers=(),
        safe_next_step="Przekaż exact observation do researchera.",
    )


def _ready_proposal(
    *,
    path: str,
    run_id: str,
    proposal_id: str,
    acquisition_run_digest: str = "a" * 64,
) -> Any:
    return SimpleNamespace(
        status="ready_for_review",
        proposal_id=proposal_id,
        proposal_digest="b" * 64,
        acquisition_run_id=run_id,
        acquisition_run_digest=acquisition_run_digest,
        source_url=f"https://www.ekologus.pl{path}/" if path != "/" else "https://www.ekologus.pl/",
        review_required=True,
        approved=False,
        blockers=(),
        safe_next_step="Przekaż propozycję do human review.",
    )


def test_evidence_readiness_indexes_exact_homepage_bdo_and_missing_rows(tmp_path: Path) -> None:
    homepage = _catalog_item("/")
    bdo = authoring_item(
        path="/bdo-co-musi-wiedziec-przedsiebiorca/",
        url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        collected_at=datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
    )
    catalog = ContentInventoryCatalogResponse(
        total_count=2,
        items=[homepage, bdo],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[homepage.evidence_id, bdo.evidence_id],
    )
    receipt = _build_content_authoring_inventory_receipt_from_catalog(
        item=bdo,
        catalog=catalog,
        recorded_by="current_inventory_reconciler",
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )
    homepage_run = _ready_run(
        path="/",
        subject_kind="identity_binding",
        subject_id="content_delivery_identity_home",
        evidence_id="ev_home_observation",
        run_id="content_evidence_acquisition_home",
    )
    homepage_older_run = _ready_run(
        path="/",
        subject_kind="identity_binding",
        subject_id="content_delivery_identity_home",
        evidence_id="ev_home_observation_older",
        run_id="content_evidence_acquisition_home_older",
    )
    bdo_run = _ready_run(
        path="/bdo-co-musi-wiedziec-przedsiebiorca",
        subject_kind="authoring_inventory_receipt",
        subject_id=receipt.receipt_id,
        evidence_id="ev_bdo_observation",
        run_id="content_evidence_acquisition_bdo",
    )
    bdo_run.authoring_inventory_receipt_digest = receipt.receipt_digest
    homepage_proposal = _ready_proposal(
        path="/",
        run_id=homepage_run.run_id,
        proposal_id="content_research_proposal_home",
    )
    bdo_proposal = _ready_proposal(
        path="/bdo-co-musi-wiedziec-przedsiebiorca",
        run_id=bdo_run.run_id,
        proposal_id="content_research_proposal_bdo",
    )
    legacy_diagnostic = ResearchProposalReadDiagnostic(
        proposal_id="content_research_proposal_legacy",
        acquisition_run_id=homepage_older_run.run_id,
        reason="Stored legacy proposal is not current-contract readable.",
        safe_next_step="Utwórz nową próbę bez reinterpretacji starego digestu.",
    )
    homepage_identity = SimpleNamespace(
        status="exact_current",
        binding_id="content_delivery_identity_home",
        binding_digest="c" * 64,
        canonical_path="/",
        blocker=None,
    )
    store = _ReadOnlyEvidenceStore(
        receipts=[receipt],
        acquisitions=[homepage_older_run, homepage_run, bdo_run],
        proposals=[homepage_proposal, bdo_proposal],
        proposal_diagnostics=[legacy_diagnostic],
        identities=[homepage_identity],
    )
    journal = tmp_path / "content-status.csv"
    _write_journal(journal, ["/", bdo.path.rstrip("/"), "/missing"])

    readiness = build_content_inventory_journal_readiness(
        catalog.items,
        catalog_coverage_status="partial",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        catalog_snapshot_digest=content_inventory_catalog_snapshot_digest(catalog),
    )
    with_journal = catalog.model_copy(update={"journal_readiness": readiness})
    assert content_inventory_catalog_snapshot_digest(with_journal) == (
        content_inventory_catalog_snapshot_digest(catalog)
    )

    by_path = {row.canonical_path: row for row in readiness.rows}
    home = by_path["/"].content_evidence_readiness
    assert home.identity.status == "exact_current"
    assert home.research_proposal.proposal_id == homepage_proposal.proposal_id
    assert home.research_proposal.approved is False
    assert home.service_card.status == "review_required"
    assert "service_card_review_required" in {item.code for item in home.blockers}
    assert home.generation_allowed is False
    bdo_readiness = by_path[bdo.path.rstrip("/")].content_evidence_readiness
    assert bdo_readiness.authoring_inventory_receipt.status == "current"
    assert bdo_readiness.authoring_inventory_receipt.receipt_id == receipt.receipt_id
    assert bdo_readiness.evidence_acquisition.current_status == "ready_for_researcher"
    assert bdo_readiness.evidence_acquisition.run_id == bdo_run.run_id
    assert bdo_readiness.research_proposal.status == "ready_for_review"
    assert bdo_readiness.research_proposal.proposal_id == bdo_proposal.proposal_id
    assert "research_proposal_legacy_unreadable" in {
        item.code for item in home.blockers
    }
    assert "research_proposal_legacy_unreadable" not in {
        item.code for item in bdo_readiness.blockers
    }
    assert bdo_readiness.identity.status == "missing"
    assert "identity_binding_missing" in {item.code for item in bdo_readiness.blockers}
    missing = by_path["/missing"].content_evidence_readiness
    assert missing.authoring_inventory_receipt.status == "missing"
    assert missing.evidence_acquisition.current_status == "missing"
    assert "current_catalog_observation_missing" in {item.code for item in missing.blockers}
    assert readiness.content_evidence_readiness.total_count == 3
    assert store.calls == {
        "receipts": 1,
        "acquisitions": 1,
        "proposals": 1,
        "identities": 1,
        "promotions": 1,
    }
    assert store.write_calls == 0
    assert len(readiness.rows) == 3
    assert all(
        row.content_evidence_readiness.generation_allowed is False
        for row in readiness.rows
    )
    assert all(row.final_disposition == "keep" for row in readiness.rows)


def test_evidence_readiness_preserves_canonical_214_row_count_without_store_writes(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "content-status-214.csv"
    paths = [f"/journal-row-{index}" for index in range(214)]
    _write_journal(journal, paths)
    store = _ReadOnlyEvidenceStore()

    readiness = build_content_inventory_journal_readiness(
        [],
        catalog_coverage_status="unknown",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
    )

    assert len(readiness.rows) == 214
    assert readiness.journal_record_count == 214
    assert readiness.content_evidence_readiness.total_count == 214
    assert readiness.content_evidence_readiness.generation_allowed is False
    assert store.calls == {
        "receipts": 1,
        "acquisitions": 1,
        "proposals": 1,
        "identities": 1,
        "promotions": 1,
    }
    assert store.write_calls == 0


def test_old_research_proposal_blocks_against_newer_acquisition_run(
    tmp_path: Path,
) -> None:
    homepage = _catalog_item("/")
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[homepage],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[homepage.evidence_id],
    )
    older_run = _ready_run(
        path="/",
        subject_kind="identity_binding",
        subject_id="content_delivery_identity_home",
        evidence_id="ev_home_observation_old",
        run_id="content_evidence_acquisition_home_old",
    )
    current_run = _ready_run(
        path="/",
        subject_kind="identity_binding",
        subject_id="content_delivery_identity_home",
        evidence_id="ev_home_observation_current",
        run_id="content_evidence_acquisition_home_current",
    )
    current_run.attempt = 1
    proposal = _ready_proposal(
        path="/",
        run_id=older_run.run_id,
        proposal_id="content_research_proposal_old_home",
        acquisition_run_digest=older_run.run_digest,
    )
    identity = SimpleNamespace(
        status="exact_current",
        binding_id="content_delivery_identity_home",
        binding_digest="c" * 64,
        canonical_path="/",
        blocker=None,
    )
    store = _ReadOnlyEvidenceStore(
        acquisitions=[older_run, current_run],
        proposals=[proposal],
        identities=[identity],
    )
    journal = tmp_path / "content-status.csv"
    _write_journal(journal, ["/"])

    readiness = build_content_inventory_journal_readiness(
        catalog.items,
        catalog_coverage_status="partial",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        catalog_snapshot_digest=content_inventory_catalog_snapshot_digest(catalog),
    )

    row = readiness.rows[0].content_evidence_readiness
    assert row.evidence_acquisition.run_id == current_run.run_id
    assert row.research_proposal.status == "blocked"
    assert row.research_proposal.proposal_id == proposal.proposal_id
    assert row.research_proposal.review_required is True
    assert row.research_proposal.approved is False
    assert row.research_proposal.blockers[0].code == (
        "research_proposal_acquisition_drift"
    )
    assert readiness.content_evidence_readiness.research_ready_count == 0
    assert readiness.content_evidence_readiness.research_blocked_count == 1
    assert store.calls == {
        "receipts": 1,
        "acquisitions": 1,
        "proposals": 1,
        "identities": 1,
        "promotions": 1,
    }


def test_unrelated_catalog_row_change_stales_receipt_and_acquisition(
    tmp_path: Path,
) -> None:
    target = authoring_item(
        path="/bdo-co-musi-wiedziec-przedsiebiorca/",
        url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        collected_at=datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
    )
    unrelated = _catalog_item("/unrelated")
    baseline_catalog = ContentInventoryCatalogResponse(
        total_count=2,
        items=[target, unrelated],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=sorted({target.evidence_id, unrelated.evidence_id}),
    )
    receipt = _build_content_authoring_inventory_receipt_from_catalog(
        item=target,
        catalog=baseline_catalog,
        recorded_by="current_inventory_reconciler",
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )
    run = _ready_run(
        path="/bdo-co-musi-wiedziec-przedsiebiorca",
        subject_kind="authoring_inventory_receipt",
        subject_id=receipt.receipt_id,
        evidence_id="ev_bdo_observation",
        run_id="content_evidence_acquisition_bdo",
    )
    run.authoring_inventory_receipt_digest = receipt.receipt_digest
    store = _ReadOnlyEvidenceStore(receipts=[receipt], acquisitions=[run])
    journal = tmp_path / "content-status.csv"
    _write_journal(journal, [target.path.rstrip("/"), unrelated.path.rstrip("/")])

    baseline = build_content_inventory_journal_readiness(
        baseline_catalog.items,
        catalog_coverage_status="partial",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        catalog_snapshot_digest=content_inventory_catalog_snapshot_digest(baseline_catalog),
    )
    target_baseline = {
        row.canonical_path: row.content_evidence_readiness for row in baseline.rows
    }[target.path.rstrip("/")]
    assert target_baseline.authoring_inventory_receipt.status == "current"
    assert target_baseline.evidence_acquisition.current_status == "ready_for_researcher"

    changed_unrelated = unrelated.model_copy(
        update={"content_summary": "Nowsza treść niezwiązanej strony."}
    )
    changed_catalog = ContentInventoryCatalogResponse(
        total_count=2,
        items=[target, changed_unrelated],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=sorted({target.evidence_id, changed_unrelated.evidence_id}),
    )
    store.calls.clear()
    changed = build_content_inventory_journal_readiness(
        changed_catalog.items,
        catalog_coverage_status="partial",
        journal_path=journal,
        evidence_store=store,
        assessed_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        catalog_snapshot_digest=content_inventory_catalog_snapshot_digest(changed_catalog),
    )
    target_changed = {
        row.canonical_path: row.content_evidence_readiness for row in changed.rows
    }[target.path.rstrip("/")]
    assert target_changed.authoring_inventory_receipt.status == "stale"
    assert target_changed.evidence_acquisition.current_status == "blocked"
    assert target_changed.evidence_acquisition.blockers[0].code == (
        "authoring_inventory_receipt_stale"
    )
    assert store.calls == {
        "receipts": 1,
        "acquisitions": 1,
        "proposals": 1,
        "identities": 1,
        "promotions": 1,
    }
    assert store.write_calls == 0
