from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_queries import (
    V3_PLAN_GENERATION_LINKAGE_SELECT,
)
from wilq.content.planning.packet_input_binding import (
    bind_packet_identity_to_planning_input,
)
from wilq.content.planning.runtime_contract import planning_job_stale_after_seconds
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.schemas import CodexRun


def proposal_insert_values(
    proposal: ContentPlanningProposal, created_at: datetime
) -> tuple[str | int | None, ...]:
    subject = ContentPlanningSubject(
        content_kind=proposal.content_kind,
        service_card_id=proposal.service_card_id,
    )
    return (
        str(proposal.proposal_id),
        proposal.work_item_id,
        int(proposal.proposal_version or 0),
        subject.service_card_id,
        subject.content_kind,
        subject.subject_key,
        str(proposal.planning_input_digest),
        created_at.isoformat(),
        proposal.model_dump_json(),
    )


def table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def job_is_stale(updated_at: str) -> bool:
    try:
        timestamp = datetime.fromisoformat(updated_at).replace(tzinfo=UTC)
    except ValueError:
        return True
    return (datetime.now(UTC) - timestamp).total_seconds() > planning_job_stale_after_seconds()


def proposal_from_row(row: sqlite3.Row | None) -> ContentPlanningProposal | None:
    if row is None:
        return None
    proposal = ContentPlanningProposal.model_validate(json.loads(cast(str, row["payload_json"])))
    subject = ContentPlanningSubject(
        content_kind=proposal.content_kind, service_card_id=proposal.service_card_id
    )
    if (
        proposal.work_item_id,
        proposal.service_card_id,
        proposal.content_kind,
        subject.subject_key,
        proposal.planning_input_digest,
    ) != (
        row["work_item_id"],
        row["service_card_id"],
        row["content_kind"],
        row["subject_key"],
        row["planning_input_digest"],
    ):
        raise ValueError("Planning proposal scalar identity does not match its payload.")
    return proposal


def response_from_job_row(row: sqlite3.Row) -> ContentPlanningProposalResponse:
    response = ContentPlanningProposalResponse.model_validate(json.loads(row["payload_json"]))
    subject = ContentPlanningSubject(
        content_kind=response.content_kind, service_card_id=response.service_card_id
    )
    identity_mismatch = (
        response.work_item_id,
        response.service_card_id,
        response.content_kind,
        subject.subject_key,
    ) != (
        row["work_item_id"],
        row["service_card_id"],
        row["content_kind"],
        row["subject_key"],
    )
    digest_matches = (
        response.planning_input_digest is None
        or response.status == "stale"
        or response.planning_input_digest == row["planning_input_digest"]
    )
    if identity_mismatch or not digest_matches:
        raise ValueError("Planning job scalar identity does not match its payload.")
    return response


def v3_plan_generation_linkage_digest(
    row: sqlite3.Row | None,
    proposal: ContentPlanningProposal,
) -> str | None:
    """Validate one exact frozen input, job response, and persisted completed run."""
    if row is None or any(
        value is None
        for value in (
            proposal.proposal_id,
            proposal.codex_run_id,
            proposal.planning_input_digest,
            proposal.research_packet_id,
            proposal.research_packet_digest,
        )
    ):
        return None
    if not _v3_frozen_input_matches(row, proposal):
        return None
    response = _v3_job_response_for_proposal(row, proposal)
    if not _v3_job_status_matches(row, response, proposal):
        return None
    if not _v3_completed_run_matches(row, proposal):
        return None
    return proposal.planning_input_digest


def validate_v3_frozen_input_integrity(
    proposal: ContentPlanningProposal,
    frozen: ContentPlanningInput,
) -> None:
    """Validate the exact packet-bound payload behind a v3 planning digest."""
    from wilq.content.planning.frozen_planning_input import (
        validate_frozen_input_identity,
    )

    validate_frozen_input_identity(proposal, frozen)
    packet_id = proposal.research_packet_id
    packet_digest = proposal.research_packet_digest
    if (
        packet_id is None
        or packet_digest is None
        or frozen.research_packet_id != packet_id
        or frozen.research_packet_digest != packet_digest
    ):
        raise ValueError("Frozen planning input packet differs from its proposal.")
    rebound = bind_packet_identity_to_planning_input(
        frozen,
        work_item_id=proposal.work_item_id,
        packet_id=packet_id,
        packet_digest=packet_digest,
    )
    if rebound.planning_input_digest != frozen.planning_input_digest:
        raise ValueError("Frozen planning input payload digest does not match its contents.")


def _v3_frozen_input_matches(
    row: sqlite3.Row,
    proposal: ContentPlanningProposal,
) -> bool:
    frozen_json = row["frozen_input_json"]
    if frozen_json is None:
        return False
    frozen = ContentPlanningInput.model_validate_json(cast(str, frozen_json))
    frozen_subject = ContentPlanningSubject(
        content_kind=frozen.content_kind,
        service_card_id=frozen.confirmed_service_card_id,
    )
    frozen_row_identity = (
        row["frozen_work_item_id"],
        row["frozen_service_card_id"],
        row["frozen_content_kind"],
        row["frozen_subject_key"],
        row["frozen_planning_input_digest"],
    )
    frozen_payload_identity = (
        frozen.work_item_id,
        frozen_subject.service_card_id,
        frozen_subject.content_kind,
        frozen_subject.subject_key,
        frozen.planning_input_digest,
    )
    if frozen_row_identity != frozen_payload_identity:
        raise ValueError("Frozen planning input row differs from its payload.")
    validate_v3_frozen_input_integrity(proposal, frozen)
    return True


def _v3_job_response_for_proposal(
    row: sqlite3.Row,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposalResponse:
    response = ContentPlanningProposalResponse.model_validate_json(
        cast(str, row["job_payload_json"])
    )
    subject = ContentPlanningSubject(
        content_kind=proposal.content_kind,
        service_card_id=proposal.service_card_id,
    )
    row_identity = (
        row["job_work_item_id"],
        row["job_service_card_id"],
        row["job_content_kind"],
        row["job_subject_key"],
        row["job_planning_input_digest"],
    )
    expected_identity = (
        proposal.work_item_id,
        subject.service_card_id,
        subject.content_kind,
        subject.subject_key,
        proposal.planning_input_digest,
    )
    response_identity = (
        response.work_item_id,
        response.service_card_id,
        response.content_kind,
        ContentPlanningSubject(
            content_kind=response.content_kind,
            service_card_id=response.service_card_id,
        ).subject_key,
        response.planning_input_digest,
    )
    if row_identity != expected_identity or response_identity != row_identity:
        raise ValueError("V3 planning job identity differs from its exact persisted key.")
    if (
        response.research_packet_id != proposal.research_packet_id
        or response.research_packet_digest != proposal.research_packet_digest
    ):
        raise ValueError("V3 planning job packet differs from its exact proposal.")
    return response


def _v3_job_status_matches(
    row: sqlite3.Row,
    response: ContentPlanningProposalResponse,
    proposal: ContentPlanningProposal,
) -> bool:
    if row["job_status"] == "finished":
        if response.status not in {"created", "idempotent", "ready"}:
            raise ValueError("Finished planning job has a non-ready response.")
        terminal_proposal = response.proposal
        if terminal_proposal is None or (
            terminal_proposal.proposal_id,
            terminal_proposal.codex_run_id,
            terminal_proposal.work_item_id,
            terminal_proposal.content_kind,
            terminal_proposal.service_card_id,
            terminal_proposal.planning_input_digest,
            terminal_proposal.research_packet_id,
            terminal_proposal.research_packet_digest,
            response.runtime.run_id,
            response.runtime.status,
        ) != (
            proposal.proposal_id,
            proposal.codex_run_id,
            proposal.work_item_id,
            proposal.content_kind,
            proposal.service_card_id,
            proposal.planning_input_digest,
            proposal.research_packet_id,
            proposal.research_packet_digest,
            proposal.codex_run_id,
            "completed",
        ):
            raise ValueError("Finished planning job names a different proposal or run.")
    elif row["job_status"] == "queued":
        if response.status != "generating" or response.proposal is not None:
            raise ValueError("Queued planning job has an inconsistent response.")
    elif row["job_status"] == "failed":
        if response.status != "failed" or response.proposal is not None:
            raise ValueError("Failed planning job has an inconsistent response.")
    elif row["job_status"] in {"blocked", "stale"}:
        if response.status != row["job_status"]:
            raise ValueError("Planning job status differs from its response.")
        return False
    else:
        raise ValueError("Planning job has an unsupported status.")
    return True


def _v3_completed_run_matches(
    row: sqlite3.Row,
    proposal: ContentPlanningProposal,
) -> bool:
    if row["persisted_run_id"] != proposal.codex_run_id:
        return False
    run_payload = row["persisted_run_payload_json"]
    if run_payload is None:
        return False
    run = CodexRun.model_validate_json(cast(str, run_payload))
    return not (
        run.id != proposal.codex_run_id
        or run.status != "completed"
        or run.completed_at is None
        or (
            run.planning_input_digest is not None
            and run.planning_input_digest != proposal.planning_input_digest
        )
    )


def v3_plan_generation_linkage_exact(
    connection_factory: Callable[[], sqlite3.Connection | None],
    proposal: ContentPlanningProposal,
) -> str | None:
    """Read only the exact generation key and its frozen input and run rows."""
    if any(
        value is None
        for value in (
            proposal.proposal_id,
            proposal.codex_run_id,
            proposal.planning_input_digest,
            proposal.research_packet_id,
            proposal.research_packet_digest,
        )
    ):
        return None
    connection = connection_factory()
    if connection is None:
        return None
    try:
        with connection:
            if not all(
                table_exists(connection, table)
                for table in (
                    "content_planning_generation_jobs",
                    "content_planning_input_snapshots",
                    "codex_runs",
                )
            ):
                return None
            subject = ContentPlanningSubject(
                content_kind=proposal.content_kind,
                service_card_id=proposal.service_card_id,
            )
            row = connection.execute(
                V3_PLAN_GENERATION_LINKAGE_SELECT,
                (
                    proposal.codex_run_id,
                    proposal.work_item_id,
                    subject.content_kind,
                    subject.subject_key,
                    proposal.planning_input_digest,
                ),
            ).fetchone()
    finally:
        connection.close()
    return v3_plan_generation_linkage_digest(row, proposal)


def validate_generated_proposal(proposal: ContentPlanningProposal, completed_run: CodexRun) -> None:
    if any(
        value is None
        for value in (
            proposal.proposal_id,
            proposal.codex_run_id,
            proposal.planning_input_digest,
            proposal.created_at,
            completed_run.completed_at,
        )
    ):
        raise ValueError("Generated planning proposal requires immutable binding fields.")
    ContentPlanningSubject(
        content_kind=proposal.content_kind, service_card_id=proposal.service_card_id
    )
    if proposal.generation_status != "codex_generated":
        raise ValueError("Planning proposal store accepts only Codex-generated proposals.")
    if proposal.codex_run_id != completed_run.id or completed_run.status != "completed":
        raise ValueError("Planning proposal requires its exact completed Codex run.")


__all__ = [
    "job_is_stale",
    "proposal_from_row",
    "proposal_insert_values",
    "response_from_job_row",
    "table_exists",
    "validate_generated_proposal",
    "validate_v3_frozen_input_integrity",
    "v3_plan_generation_linkage_digest",
    "v3_plan_generation_linkage_exact",
]
