from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import cast

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
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
]
