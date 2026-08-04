"""Small persistence helpers for the local initial-draft run audit record."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class InitialDraftClaim:
    run: CodexRun
    newly_claimed: bool
    canonical_revision: ContentDraftRevision | None = None


LEGACY_INITIAL_DRAFT_TIMEOUT_SECONDS = 900.0


def effective_initial_draft_deadline(run: CodexRun) -> datetime:
    return run.deadline_at or (
        run.started_at + timedelta(seconds=LEGACY_INITIAL_DRAFT_TIMEOUT_SECONDS)
    )


def initial_draft_context_digest(
    *,
    base_revision_id: str | None,
    draft_package_id: str | None,
    draft_package_digest: str | None,
    final_canonical_url: str | None,
    service_card_id: str | None,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
) -> str:
    payload = "\n".join(
        (
            base_revision_id or "",
            draft_package_id or "",
            draft_package_digest or "",
            final_canonical_url or "",
            service_card_id or "",
            proposal_id,
            planning_digest,
            planning_input_digest,
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _canonical_revision_for_claim(connection, work_item_id: str) -> ContentDraftRevision | None:
    has_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'content_draft_revisions'"
    ).fetchone()
    if has_table is None:
        return None
    row = connection.execute(
        """SELECT payload_json FROM content_draft_revisions
           WHERE work_item_id = ? ORDER BY revision_number DESC LIMIT 1""",
        (work_item_id,),
    ).fetchone()
    return None if row is None else ContentDraftRevision.model_validate_json(row["payload_json"])


def _expire_claim_if_needed(connection, run: CodexRun, payload_json: str) -> bool:
    if utc_now() < effective_initial_draft_deadline(run):
        return False
    expired = run.model_copy(
        update={"status": "failed", "completed_at": utc_now(), "error": "initial_draft_timeout"}
    )
    connection.execute(
        "UPDATE codex_runs SET payload_json = ? WHERE id = ? AND payload_json = ?",
        (
            json.dumps(expired.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            run.id,
            payload_json,
        ),
    )
    return True


def _terminalize_stale_contexts(
    connection, rows, endpoint: str, context_digest: str | None
) -> None:
    for row in rows:
        run = CodexRun.model_validate_json(row["payload_json"])
        if not (
            run.status == "started"
            and run.hook == "content_initial_full_draft"
            and endpoint in run.used_endpoints
            and run.initial_draft_context_digest is not None
            and run.initial_draft_context_digest != context_digest
        ):
            continue
        stale = run.model_copy(
            update={
                "status": "blocked",
                "completed_at": utc_now(),
                "error": "stale_initial_draft_context",
            }
        )
        connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = ? AND payload_json = ?",
            (
                json.dumps(stale.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
                run.id,
                row["payload_json"],
            ),
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
    context_current: bool = True,
    context_digest: str | None = None,
    expected_base_revision_id: str | None = None,
) -> InitialDraftClaim:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    run_store.status()
    with run_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT payload_json FROM codex_runs ORDER BY started_at DESC, id DESC"
        ).fetchall()
        runs = [CodexRun.model_validate_json(row["payload_json"]) for row in rows]
        canonical_revision = _canonical_revision_for_claim(connection, work_item_id)
        revision_is_newer = (
            canonical_revision is not None
            and canonical_revision.revision_id != expected_base_revision_id
        )
        if (context_current or revision_is_newer) and (
            canonical_revision is not None
            and canonical_revision.planning_digest == planning_digest
            and canonical_revision.planning_input_digest == planning_input_digest
            and canonical_revision.proposal_metadata is not None
        ):
            canonical_run = next(
                (
                    run
                    for run in runs
                    if run.id == canonical_revision.proposal_metadata.codex_run_id
                    and run.status == "completed"
                    and run.proposal_id == proposal_id
                    and run.planning_input_digest == planning_input_digest
                ),
                None,
            )
            if canonical_run is not None:
                return InitialDraftClaim(
                    run=canonical_run,
                    newly_claimed=False,
                    canonical_revision=canonical_revision,
                )
        _terminalize_stale_contexts(connection, rows, endpoint, context_digest)
        for row in rows:
            run = CodexRun.model_validate_json(row["payload_json"])
            if (
                run.status == "started"
                and run.hook == "content_initial_full_draft"
                and run.proposal_id == proposal_id
                and run.planning_digest == planning_digest
                and run.planning_input_digest == planning_input_digest
                and run.initial_draft_context_digest == context_digest
                and endpoint in run.used_endpoints
            ):
                if _expire_claim_if_needed(connection, run, row["payload_json"]):
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
            initial_draft_context_digest=context_digest,
            initial_draft_base_revision_id=expected_base_revision_id,
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
) -> CodexRun | None:
    return transition_initial_draft_run_if_status(
        run_store, run, status=status, error=error
    )


def transition_initial_draft_run_if_status(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun | None:
    if run.status != "started":
        return None
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
    "initial_draft_context_digest",
    "transition_initial_draft_run_if_status",
    "safe_initial_draft_run_error",
    "start_initial_draft_run",
]
