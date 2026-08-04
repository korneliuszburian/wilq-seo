"""Small persistence helpers for the local initial-draft run audit record."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class InitialDraftClaim:
    run: CodexRun
    newly_claimed: bool


LEGACY_INITIAL_DRAFT_TIMEOUT_SECONDS = 900.0


def effective_initial_draft_deadline(run: CodexRun) -> datetime:
    return run.deadline_at or (
        run.started_at + timedelta(seconds=LEGACY_INITIAL_DRAFT_TIMEOUT_SECONDS)
    )


def claim_initial_draft_run(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
    evidence_ids: list[str],
    timeout_seconds: float,
) -> InitialDraftClaim:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    run_store.status()
    with run_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT payload_json FROM codex_runs ORDER BY started_at DESC, id DESC"
        ).fetchall()
        for row in rows:
            run = CodexRun.model_validate_json(row["payload_json"])
            if (
                run.status == "started"
                and run.hook == "content_initial_full_draft"
                and run.proposal_id == proposal_id
                and run.planning_digest == planning_digest
                and run.planning_input_digest == planning_input_digest
                and endpoint in run.used_endpoints
            ):
                if utc_now() >= effective_initial_draft_deadline(run):
                    expired = run.model_copy(
                        update={
                            "status": "failed",
                            "completed_at": utc_now(),
                            "error": "initial_draft_timeout",
                        }
                    )
                    connection.execute(
                        "UPDATE codex_runs SET payload_json = ? WHERE id = ? AND payload_json = ?",
                        (
                            json.dumps(
                                expired.model_dump(mode="json"),
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            run.id,
                            row["payload_json"],
                        ),
                    )
                    continue
                return InitialDraftClaim(run=run, newly_claimed=False)
        run = CodexRun(
            id=f"codex_content_initial_draft_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
            status="started",
            used_endpoints=[endpoint],
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            deadline_at=utc_now() + timedelta(seconds=timeout_seconds),
        )
        connection.execute(
            "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
            (run.id, run.started_at.isoformat(), json.dumps(
                run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )),
        )
        return InitialDraftClaim(run=run, newly_claimed=True)


def finish_initial_draft_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun:
    return run_store.save_codex_run(
        run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})
    )


def transition_initial_draft_run_if_status(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun | None:
    updated = run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})
    if not hasattr(run_store, "_connect"):
        return run_store.save_codex_run(updated)
    with run_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = ? AND payload_json = ?",
            (
                json.dumps(updated.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
                run.id,
                json.dumps(run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            ),
        )
        return updated if cursor.rowcount == 1 else None


def start_initial_draft_run(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    evidence_ids: list[str],
    proposal_id: str,
    planning_input_digest: str,
    planning_digest: str | None = None,
    run_id: str | None = None,
) -> CodexRun:
    if run_id is not None:
        existing = next(
            (item for item in run_store.list_codex_runs() if item.id == run_id),
            None,
        )
        if existing is None or existing.status != "started":
            raise ValueError("initial draft queued run is no longer executable")
        if (
            existing.proposal_id != proposal_id
            or existing.planning_input_digest != planning_input_digest
            or set(existing.evidence_ids) != set(evidence_ids)
        ):
            raise ValueError("initial draft queued run lineage does not match proposal")
        return existing
    return run_store.save_codex_run(
        CodexRun(
            id=run_id or f"codex_content_initial_draft_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
            status="started",
            used_endpoints=[f"/api/content/work-items/{work_item_id}/initial-draft"],
            evidence_ids=evidence_ids,
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
        )
    )


def safe_initial_draft_run_error(blocker: ContentInitialDraftBlocker) -> str:
    """Keep only bounded blocker identifiers in the immutable run record."""

    return (
        blocker.code
        if not blocker.source_codes
        else f"{blocker.code}|{','.join(blocker.source_codes[:12])}"
    )


__all__ = [
    "finish_initial_draft_run",
    "claim_initial_draft_run",
    "InitialDraftClaim",
    "effective_initial_draft_deadline",
    "transition_initial_draft_run_if_status",
    "safe_initial_draft_run_error",
    "start_initial_draft_run",
]
