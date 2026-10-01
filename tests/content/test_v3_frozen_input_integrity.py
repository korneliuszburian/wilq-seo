"""Exact v3 planning reads reject altered frozen-input bytes."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tests.content.test_v3_packet_planning_status_read import (
    _approved_packet_with_read,
    _snapshot,
)
from wilq.content.planning.generated_proposal import read_content_planning_proposal


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

    response = read_content_planning_proposal(
        snapshot=_snapshot(), store=proposal_store
    )

    assert response.status == "blocked"
    assert response.proposal is None
    assert source_code in (response.blockers[0].source_codes or [])
