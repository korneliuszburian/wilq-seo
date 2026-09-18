"""Append-only persistence for review-only research proposal attempts."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Literal, cast

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.workflow.research_proposal import (
    ContentResearchProposalAttempt,
    ResearchProposalLegacyUnreadable,
    ResearchProposalReadDiagnostic,
    ResearchProposalReadResult,
)
from wilq.storage.model_json import model_json

_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"


class ResearchProposalStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_research_proposal(
        self, proposal: ContentResearchProposalAttempt
    ) -> ContentResearchProposalAttempt:
        accepted = ContentResearchProposalAttempt.model_validate_json(
            proposal.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_research_proposals "
                "WHERE proposal_id = ? OR input_digest = ?",
                (accepted.proposal_id, accepted.input_digest),
            ).fetchone()
            if existing is not None:
                existing_proposal = _proposal_from_row(existing)
                if existing_proposal is None:
                    raise RuntimeError("Existing research proposal row was empty.")
                return existing_proposal
            connection.execute(
                """
                INSERT INTO content_research_proposals (
                  proposal_id, proposal_digest, attempt_id, input_digest,
                  acquisition_run_id, acquisition_run_digest, status, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.proposal_id,
                    accepted.proposal_digest,
                    accepted.attempt_id,
                    accepted.input_digest,
                    accepted.acquisition_run_id,
                    accepted.acquisition_run_digest,
                    accepted.status,
                    model_json(accepted),
                ),
            )
        return accepted

    def get_research_proposal_by_input_digest(
        self, input_digest: str
    ) -> ContentResearchProposalAttempt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_research_proposals "
                "WHERE input_digest = ?",
                (input_digest,),
            ).fetchone()
        return _proposal_from_row(row)

    def get_research_proposal(
        self, proposal_id: str
    ) -> ContentResearchProposalAttempt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_research_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        return _proposal_from_row(row)

    def list_research_proposals(self) -> list[ContentResearchProposalAttempt]:
        return [
            result.proposal
            for result in self.list_research_proposals_with_diagnostics()
            if result.proposal is not None
        ]

    def list_research_proposals_with_diagnostics(self) -> list[ResearchProposalReadResult]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT proposal_id, acquisition_run_id, payload_json "
                "FROM content_research_proposals ORDER BY proposal_id"
            ).fetchall()
        return [_proposal_read_result(row) for row in rows]


def _proposal_from_row(row: sqlite3.Row | None) -> ContentResearchProposalAttempt | None:
    if row is None:
        return None
    result = _proposal_read_result(row)
    if result.diagnostic is not None:
        raise ResearchProposalLegacyUnreadable(result.diagnostic)
    return result.proposal


def _proposal_read_result(row: sqlite3.Row) -> ResearchProposalReadResult:
    payload_json = cast(str, row["payload_json"])
    try:
        proposal = ContentResearchProposalAttempt.model_validate_json(
            payload_json, strict=True
        )
    except ValueError:
        payload = _safe_payload(payload_json)
        return ResearchProposalReadResult(
            diagnostic=ResearchProposalReadDiagnostic(
                proposal_id=_safe_identifier(
                    payload.get("proposal_id")
                )
                or _safe_identifier(_row_value(row, "proposal_id")),
                acquisition_run_id=_safe_identifier(
                    payload.get("acquisition_run_id")
                )
                or _safe_identifier(_row_value(row, "acquisition_run_id")),
                stored_contract_version=_safe_legacy_contract_version(
                    payload.get("contract_version")
                ),
                source_url=_safe_source_url(payload_json),
                reason="Stored research proposal does not satisfy the current contract.",
                safe_next_step=(
                    "Zachowaj legacy proposal jako historyczny blocker i utwórz nową "
                    "próbę bez reinterpretacji starego digestu."
                ),
            )
        )
    return ResearchProposalReadResult(proposal=proposal)


def _safe_identifier(value: object) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(_SAFE_IDENTIFIER, value) else None


def _safe_payload(payload_json: str) -> dict[str, object]:
    try:
        payload = json.loads(payload_json)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _row_value(row: sqlite3.Row, key: str) -> object | None:
    try:
        return cast(object | None, row[key])
    except (IndexError, KeyError):
        return None


def _safe_source_url(payload_json: str) -> str | None:
    try:
        payload = json.loads(payload_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    source_url = payload.get("source_url")
    if isinstance(source_url, str) and content_is_safe_public_url(source_url):
        return source_url
    return None


def _safe_legacy_contract_version(
    value: object,
) -> Literal["content_research_proposal_attempt_v1"] | None:
    if value == "content_research_proposal_attempt_v1":
        return "content_research_proposal_attempt_v1"
    return None


__all__ = ["ResearchProposalStoreMixin"]
