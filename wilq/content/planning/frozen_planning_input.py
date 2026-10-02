"""Persistence and exact identity checks for generated-plan input snapshots."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_rows import table_exists as _table_exists
from wilq.content.planning.packet_input_binding import (
    bind_packet_identity_to_planning_input,
    is_v3_research_packet_id,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.schemas import CodexRun


class _FrozenPlanningInputStore(Protocol):
    def frozen_planning_input(
        self,
        work_item_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningInput | None: ...


def validate_frozen_input_identity(
    proposal: ContentPlanningProposal,
    planning_input: ContentPlanningInput,
) -> None:
    _validate_frozen_input_scalar_identity(proposal, planning_input)
    if _is_v3_research_packet_id(proposal.research_packet_id):
        _validate_v3_packet_bound_input(proposal, planning_input)


def validate_v3_frozen_input_integrity(
    proposal: ContentPlanningProposal,
    planning_input: ContentPlanningInput,
) -> None:
    """Validate the exact packet-bound payload behind a v3 planning digest."""
    _validate_frozen_input_scalar_identity(proposal, planning_input)
    if not _is_v3_research_packet_id(proposal.research_packet_id):
        raise ValueError("Frozen planning input proposal does not identify a v3 packet.")
    _validate_v3_packet_bound_input(proposal, planning_input)


def _validate_frozen_input_scalar_identity(
    proposal: ContentPlanningProposal,
    planning_input: ContentPlanningInput,
) -> None:
    if (
        planning_input.work_item_id != proposal.work_item_id
        or planning_input.content_kind != proposal.content_kind
        or planning_input.confirmed_service_card_id != proposal.service_card_id
        or planning_input.planning_input_digest != proposal.planning_input_digest
    ):
        raise ValueError("Planning input snapshot must match the generated proposal identity.")


def _validate_v3_packet_bound_input(
    proposal: ContentPlanningProposal,
    planning_input: ContentPlanningInput,
) -> None:
    packet_id = proposal.research_packet_id
    packet_digest = proposal.research_packet_digest
    if (
        packet_id is None
        or packet_digest is None
        or planning_input.research_packet_id != packet_id
        or planning_input.research_packet_digest != packet_digest
    ):
        raise ValueError("Frozen planning input packet differs from its proposal.")
    _validate_v3_packet_bound_digest(planning_input)


def _validate_v3_packet_bound_digest(planning_input: ContentPlanningInput) -> None:
    packet_id = planning_input.research_packet_id
    packet_digest = planning_input.research_packet_digest
    if packet_id is None or packet_digest is None:
        raise ValueError("Frozen planning input is missing its v3 packet identity.")
    rebound = bind_packet_identity_to_planning_input(
        planning_input,
        work_item_id=planning_input.work_item_id,
        packet_id=packet_id,
        packet_digest=packet_digest,
    )
    if rebound.planning_input_digest != planning_input.planning_input_digest:
        raise ValueError("Frozen planning input payload digest does not match its contents.")


def _is_v3_research_packet_id(packet_id: str | None) -> bool:
    return packet_id is not None and is_v3_research_packet_id(packet_id)


def persist_frozen_planning_input(
    connection: sqlite3.Connection,
    planning_input: ContentPlanningInput | None,
    created_at: datetime,
) -> None:
    if planning_input is None:
        return
    if _is_v3_research_packet_id(planning_input.research_packet_id):
        _validate_v3_packet_bound_digest(planning_input)
    subject = ContentPlanningSubject(
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
    )
    connection.execute(
        """
        INSERT INTO content_planning_input_snapshots (
          snapshot_id, work_item_id, service_card_id, content_kind, subject_key,
          planning_input_digest, created_at, input_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(work_item_id, planning_input_digest)
        DO UPDATE SET service_card_id = excluded.service_card_id,
                      content_kind = excluded.content_kind,
                      subject_key = excluded.subject_key,
                      created_at = excluded.created_at,
                      input_json = excluded.input_json
        """,
        (
            f"content_planning_input_snapshot_{uuid4().hex}",
            planning_input.work_item_id,
            subject.service_card_id,
            subject.content_kind,
            subject.subject_key,
            planning_input.planning_input_digest,
            created_at.isoformat(),
            planning_input.model_dump_json(),
        ),
    )


def frozen_input_snapshot_time(
    proposal: ContentPlanningProposal,
    completed_run: CodexRun,
    planning_input: ContentPlanningInput | None,
) -> datetime:
    if planning_input is not None:
        validate_frozen_input_identity(proposal, planning_input)
    created_at = proposal.created_at or completed_run.completed_at
    if created_at is None:
        raise RuntimeError("Generated planning proposal is missing created_at.")
    return created_at


def read_frozen_input(
    connection_factory: Callable[[], sqlite3.Connection | None],
    work_item_id: str,
    planning_input_digest: str,
) -> ContentPlanningInput | None:
    connection = connection_factory()
    if connection is None:
        return None
    try:
        with connection:
            if not _table_exists(connection, "content_planning_input_snapshots"):
                return None
            row = connection.execute(
                """
                SELECT work_item_id, service_card_id, content_kind, subject_key,
                       planning_input_digest, input_json
                FROM content_planning_input_snapshots
                WHERE work_item_id = ? AND planning_input_digest = ?
                LIMIT 1
                """,
                (work_item_id, planning_input_digest),
            ).fetchone()
    finally:
        connection.close()
    return _frozen_planning_input_from_row(row, work_item_id, planning_input_digest)


def frozen_input_for_proposal(
    proposal: ContentPlanningProposal,
    store_factory: Callable[[], _FrozenPlanningInputStore],
) -> ContentPlanningInput | None:
    if proposal.planning_input_digest is None:
        return None
    frozen = store_factory().frozen_planning_input(
        proposal.work_item_id,
        proposal.planning_input_digest,
    )
    if frozen is None:
        return None
    try:
        validate_frozen_input_identity(proposal, frozen)
    except ValueError:
        return None
    return frozen


def _frozen_planning_input_from_row(
    row: sqlite3.Row | None,
    work_item_id: str,
    planning_input_digest: str,
) -> ContentPlanningInput | None:
    if row is None:
        return None
    try:
        planning_input = ContentPlanningInput.model_validate(json.loads(row["input_json"]))
        subject = ContentPlanningSubject(
            content_kind=planning_input.content_kind,
            service_card_id=planning_input.confirmed_service_card_id,
        )
        if (
            planning_input.work_item_id,
            planning_input.confirmed_service_card_id,
            planning_input.content_kind,
            subject.subject_key,
            planning_input.planning_input_digest,
        ) != (
            row["work_item_id"],
            row["service_card_id"],
            row["content_kind"],
            row["subject_key"],
            row["planning_input_digest"],
        ):
            return None
        if (
            planning_input.work_item_id != work_item_id
            or planning_input.planning_input_digest != planning_input_digest
        ):
            return None
        if _is_v3_research_packet_id(planning_input.research_packet_id):
            _validate_v3_packet_bound_digest(planning_input)
    except (KeyError, TypeError, ValueError):
        return None
    return planning_input
