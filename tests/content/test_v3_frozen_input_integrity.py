"""Exact v3 planning reads reject altered frozen-input bytes."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.content.test_v3_packet_planning_status_read import (
    _approved_packet_with_read,
    _snapshot,
)
from wilq.content.planning.frozen_planning_input import frozen_input_for_proposal
from wilq.content.planning.generated_proposal import read_content_planning_proposal
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.schemas import CodexRun


@pytest.mark.parametrize(
    ("tamper_location", "source_code"),
    [
        ("persisted_input", "research_packet_v3_generation_linkage_invalid"),
        ("second_read", "research_packet_v3_frozen_input_identity_mismatch"),
    ],
)
def test_v3_frozen_input_payload_tampering_blocks_public_status_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper_location: str,
    source_code: str,
) -> None:
    proposal_store, packet, _source_pack, _fact, planning_input_digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )
    control = read_content_planning_proposal(
        snapshot=_snapshot(), store=proposal_store
    )
    assert control.status == "ready", (control.blockers, control.safe_next_step)
    assert control.proposal is not None
    frozen_control = proposal_store.frozen_planning_input(
        packet.work_item_id, planning_input_digest
    )
    assert frozen_control is not None
    assert frozen_input_for_proposal(
        control.proposal, lambda: proposal_store
    ) == frozen_control

    changed_target_reader = "Inny odbiorca zachowujący poprawną polską wartość."
    if tamper_location == "persisted_input":
        with sqlite3.connect(proposal_store.path) as connection:
            row = connection.execute(
                """
                SELECT input_json FROM content_planning_input_snapshots
                WHERE work_item_id = ? AND planning_input_digest = ?
                """,
                (packet.work_item_id, planning_input_digest),
            ).fetchone()
            assert row is not None
            frozen_payload = json.loads(row[0])
            frozen_payload["target_reader"] = changed_target_reader
            connection.execute(
                """
                UPDATE content_planning_input_snapshots
                SET input_json = ?
                WHERE work_item_id = ? AND planning_input_digest = ?
                """,
                (
                    json.dumps(frozen_payload),
                    packet.work_item_id,
                    planning_input_digest,
                ),
            )
        assert proposal_store.frozen_planning_input(
            packet.work_item_id, planning_input_digest
        ) is None
        assert frozen_input_for_proposal(
            control.proposal, lambda: proposal_store
        ) is None
    else:
        frozen = proposal_store.frozen_planning_input(
            packet.work_item_id, planning_input_digest
        )
        assert frozen is not None
        changed_frozen = frozen.model_copy(
            update={"target_reader": changed_target_reader}
        )
        monkeypatch.setattr(
            proposal_store,
            "frozen_planning_input",
            lambda *_args: changed_frozen,
        )
        assert frozen_input_for_proposal(
            control.proposal, lambda: proposal_store
        ) is None

    response = read_content_planning_proposal(
        snapshot=_snapshot(), store=proposal_store
    )

    assert response.status == "blocked"
    assert response.proposal is None
    assert source_code in (response.blockers[0].source_codes or [])


def test_frozen_input_for_proposal_rejects_same_identity_changed_content_from_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, planning_input_digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )
    control = read_content_planning_proposal(
        snapshot=_snapshot(), store=proposal_store
    )
    assert control.status == "ready"
    assert control.proposal is not None
    frozen = proposal_store.frozen_planning_input(
        packet.work_item_id, planning_input_digest
    )
    assert frozen is not None
    changed = frozen.model_copy(
        update={"target_reader": "Inny odbiorca zachowujący poprawną polską wartość."}
    )

    def fake_store_factory() -> SimpleNamespace:
        return SimpleNamespace(frozen_planning_input=lambda *_args: changed)

    assert frozen_input_for_proposal(control.proposal, fake_store_factory) is None


def test_save_generated_rejects_tampered_v3_input_without_writing_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, planning_input_digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )
    subject = ContentPlanningSubject(content_kind="editorial", service_card_id=None)
    original = proposal_store.for_subject_input(
        packet.work_item_id, subject, planning_input_digest
    )
    assert original is not None
    frozen = proposal_store.frozen_planning_input(
        packet.work_item_id, planning_input_digest
    )
    assert frozen is not None
    tampered = frozen.model_copy(
        update={"target_reader": "Inny odbiorca zachowujący poprawną polską wartość."}
    )
    proposal = original.model_copy(
        update={
            "proposal_id": "proposal-v3-integrity-replacement",
            "codex_run_id": "run-v3-integrity-replacement",
        }
    )
    completed_at = datetime.now(UTC)
    completed_run = CodexRun(
        id="run-v3-integrity-replacement",
        skill="wilq-content-operator",
        hook="content_planning_proposal",
        source="wilq_api",
        status="completed",
        used_endpoints=[
            f"/api/content/work-items/{packet.work_item_id}/planning-proposals"
        ],
        evidence_ids=list(tampered.evidence_ids),
        planning_input_digest=planning_input_digest,
        started_at=completed_at,
        completed_at=completed_at,
    )

    def persisted_state() -> tuple[object, ...]:
        with sqlite3.connect(proposal_store.path) as connection:
            row_counts = tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "content_planning_input_snapshots",
                    "content_planning_proposals",
                    "content_planning_proposal_repairs",
                    "codex_runs",
                )
            )
            frozen_identity = connection.execute(
                """
                SELECT snapshot_id, work_item_id, service_card_id, content_kind,
                       subject_key, planning_input_digest
                FROM content_planning_input_snapshots
                WHERE work_item_id = ? AND planning_input_digest = ?
                """,
                (packet.work_item_id, planning_input_digest),
            ).fetchone()
        latest = proposal_store.latest(packet.work_item_id)
        exact = proposal_store.for_subject_input(
            packet.work_item_id, subject, planning_input_digest
        )
        proposal_identities = tuple(
            None if item is None else (item.proposal_id, item.proposal_version)
            for item in (latest, exact)
        )
        return row_counts, frozen_identity, proposal_identities

    before = persisted_state()
    with pytest.raises(ValueError):
        proposal_store.save_generated(
            proposal,
            completed_run,
            planning_input=tampered,
            replace_existing_exact_input=True,
        )

    assert persisted_state() == before
