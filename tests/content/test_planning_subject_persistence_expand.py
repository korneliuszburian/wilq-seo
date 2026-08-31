import hashlib
import json
import sqlite3
from datetime import UTC, datetime

import pytest

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_claim_store import ContentPlanningGenerationClaimStore
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment
from wilq.content.planning.input_summary import ContentPlanningInputSummary
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.schemas import CodexRun


def _legacy_claim_key(work_item_id: str, service_card_id: str, digest: str) -> str:
    payload = json.dumps(
        [work_item_id, service_card_id, digest],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_legacy_planning_rows_gain_exact_service_subject_without_payload_changes(
    tmp_path,
) -> None:
    path = tmp_path / "planning-v1.sqlite3"
    work_item_id = "content_work_item_service"
    service_card_id = "service_card"
    digest = "a" * 64
    claim_key = _legacy_claim_key(work_item_id, service_card_id, digest)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE content_planning_proposals (
              proposal_id TEXT PRIMARY KEY, work_item_id TEXT NOT NULL,
              proposal_version INTEGER NOT NULL, service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL, created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (work_item_id, proposal_version),
              UNIQUE (work_item_id, service_card_id, planning_input_digest)
            );
            CREATE TABLE content_planning_proposal_repairs (
              proposal_id TEXT PRIMARY KEY, work_item_id TEXT NOT NULL,
              proposal_version INTEGER NOT NULL, service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL, supersedes_proposal_id TEXT NOT NULL,
              created_at TEXT NOT NULL, payload_json TEXT NOT NULL,
              UNIQUE (work_item_id, proposal_version)
            );
            CREATE TABLE content_planning_generation_jobs (
              work_item_id TEXT NOT NULL, service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL, status TEXT NOT NULL,
              payload_json TEXT NOT NULL, updated_at TEXT NOT NULL,
              PRIMARY KEY (work_item_id, service_card_id, planning_input_digest)
            );
            CREATE TABLE content_planning_generation_claims (
              claim_key TEXT PRIMARY KEY, work_item_id TEXT NOT NULL,
              service_card_id TEXT NOT NULL, planning_input_digest TEXT NOT NULL,
              status TEXT NOT NULL, claim_owner TEXT NOT NULL,
              claim_version INTEGER NOT NULL DEFAULT 1,
              claimed_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              UNIQUE (work_item_id, service_card_id, planning_input_digest)
            );
            """
        )
        connection.execute(
            "INSERT INTO content_planning_proposals VALUES (?, ?, 1, ?, ?, ?, ?)",
            ("proposal", work_item_id, service_card_id, digest, "2026-08-31", '{"v":1}'),
        )
        connection.execute(
            "INSERT INTO content_planning_generation_jobs VALUES (?, ?, ?, ?, ?, ?)",
            (work_item_id, service_card_id, digest, "queued", '{"v":1}', "2026-08-31"),
        )
        connection.execute(
            "INSERT INTO content_planning_generation_claims VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                claim_key,
                work_item_id,
                service_card_id,
                digest,
                "claimed",
                "worker",
                datetime(2026, 8, 31, tzinfo=UTC).isoformat(),
                datetime(2026, 8, 31, tzinfo=UTC).isoformat(),
            ),
        )

    with ContentPlanningProposalStore(path).run_transaction():
        pass
    claim_store = ContentPlanningGenerationClaimStore(path)
    assert claim_store.finish(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="worker",
        claim_version=1,
        status="finished",
    )

    with sqlite3.connect(path) as connection:
        for table in (
            "content_planning_proposals",
            "content_planning_generation_jobs",
            "content_planning_generation_claims",
        ):
            row = connection.execute(
                f"SELECT content_kind, subject_key FROM {table}"  # nosec B608
            ).fetchone()
            assert row == ("service", service_card_id)
        proposal_payload = connection.execute(
            "SELECT payload_json FROM content_planning_proposals"
        ).fetchone()[0]
        stored_claim = connection.execute(
            "SELECT claim_key, status FROM content_planning_generation_claims"
        ).fetchone()

    assert proposal_payload == '{"v":1}'
    assert stored_claim == (claim_key, "finished")


def test_editorial_job_and_claim_persist_without_a_fake_service(tmp_path) -> None:
    path = tmp_path / "editorial.sqlite3"
    digest = "e" * 64
    subject = ContentPlanningSubject(content_kind="editorial", service_card_id=None)
    summary = ContentPlanningInputSummary(
        final_canonical_url="https://www.ekologus.pl/artykul/",
        content_kind="editorial",
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="missing",
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Testowy stan źródła.",
            )
            for source in (
                "wordpress",
                "service_profile",
                "gsc",
                "ga4",
                "google_ads",
                "ahrefs",
                "keyword_planner",
                "merchant",
                "localo",
                "social",
            )
        ],
        source_fact_count=0,
        evidence_id_count=0,
        knowledge_card_count=0,
    )
    response = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="content_work_item_editorial",
        content_kind="editorial",
        service_card_id=None,
        planning_input_digest=digest,
        input_summary=summary,
        safe_next_step="Poczekaj na plan.",
    )
    store = ContentPlanningProposalStore(path)

    created = store.enqueue_subject_pending(
        work_item_id=response.work_item_id,
        subject=subject,
        planning_input_digest=digest,
        response=response,
    )
    repeated = store.enqueue_subject_pending(
        work_item_id=response.work_item_id,
        subject=subject,
        planning_input_digest=digest,
        response=response,
    )
    claim_store = ContentPlanningGenerationClaimStore(path)
    claim = claim_store.claim(
        work_item_id=response.work_item_id,
        content_kind="editorial",
        service_card_id=None,
        planning_input_digest=digest,
        claim_owner="worker",
    )

    assert created == "queued"
    assert repeated == "existing"
    assert store.queued_subject_response(response.work_item_id, subject, digest) == response
    assert claim.outcome == "acquired"
    assert claim_store.finish(
        work_item_id=response.work_item_id,
        content_kind="editorial",
        service_card_id=None,
        planning_input_digest=digest,
        claim_owner="worker",
        claim_version=claim.claim_version,
        status="finished",
    )


def test_editorial_claim_key_cannot_collide_with_legacy_service_id(tmp_path) -> None:
    store = ContentPlanningGenerationClaimStore(tmp_path / "claim-namespace.sqlite3")
    common = {
        "work_item_id": "content_work_item_shared",
        "planning_input_digest": "9" * 64,
        "claim_owner": "worker",
    }

    service = store.claim(service_card_id="editorial:editorial", **common)
    editorial = store.claim(
        content_kind="editorial",
        service_card_id=None,
        **common,
    )

    assert service.outcome == "acquired"
    assert editorial.outcome == "acquired"
    with sqlite3.connect(store.path) as connection:
        keys = connection.execute(
            "SELECT claim_key FROM content_planning_generation_claims"
        ).fetchall()
    assert len({row[0] for row in keys}) == 2


def test_editorial_proposal_persists_and_reads_by_neutral_subject(tmp_path) -> None:
    path = tmp_path / "editorial-proposal.sqlite3"
    digest = "f" * 64
    created_at = datetime(2026, 8, 31, tzinfo=UTC)
    proposal = ContentPlanningProposal(
        work_item_id="content_work_item_editorial",
        planning_digest="d" * 64,
        proposal_id="proposal-editorial",
        codex_run_id="run-editorial",
        generation_status="codex_generated",
        planning_input_digest=digest,
        content_kind="editorial",
        service_card_id=None,
        final_canonical_url="https://www.ekologus.pl/artykul/",
        target_reader="Czytelnik",
        buyer_problem="Brak uporządkowanej informacji.",
        buyer_trigger="Zmiana obowiązków.",
        search_intent="informacyjny",
        cta_direction="Sprawdź źródła i dalsze kroki.",
        sections=[ContentPlanningSection(heading="Zakres", purpose="Wyjaśnia temat.")],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych.",
        ),
        created_at=created_at,
    )
    run = CodexRun(
        id="run-editorial",
        status="completed",
        started_at=created_at,
        completed_at=created_at,
    )
    store = ContentPlanningProposalStore(path)

    outcome, stored = store.save_generated(proposal, run)

    assert outcome == "created"
    assert stored.service_card_id is None
    assert (
        store.for_subject_input(
            proposal.work_item_id,
            ContentPlanningSubject(content_kind="editorial", service_card_id=None),
            digest,
        )
        == stored
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE content_planning_proposals
            SET content_kind = 'service', service_card_id = 'fake_service',
                subject_key = 'fake_service'
            WHERE proposal_id = 'proposal-editorial'
            """
        )
    with pytest.raises(ValueError, match="scalar identity"):
        store.latest(proposal.work_item_id)
