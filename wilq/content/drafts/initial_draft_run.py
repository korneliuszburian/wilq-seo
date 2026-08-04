"""Small persistence helpers for the local initial-draft run audit record."""

from __future__ import annotations

import json
import sqlite3
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
    run: CodexRun | None
    newly_claimed: bool
    canonical_revision: ContentDraftRevision | None = None
    stale_context: bool = False


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


def revision_matches_initial_draft_context(
    revision: ContentDraftRevision,
    *,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
    context_digest: str | None,
) -> bool:
    if context_digest is None:
        return False
    return context_digest == initial_draft_context_digest(
        base_revision_id=revision.revision_id,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        final_canonical_url=revision.final_canonical_url,
        service_card_id=revision.service_card_id,
        proposal_id=proposal_id,
        planning_digest=planning_digest,
        planning_input_digest=planning_input_digest,
    )


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


def ensure_initial_draft_context_schema(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS initial_draft_context_authority (
          work_item_id TEXT PRIMARY KEY,
          context_digest TEXT NOT NULL,
          base_revision_id TEXT,
          version INTEGER NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )


def record_initial_draft_context(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    context_digest: str,
    base_revision_id: str | None,
) -> int:
    try:
        with run_store._connect() as connection:
            connection.execute("PRAGMA busy_timeout = 1")
            connection.execute("BEGIN IMMEDIATE")
            ensure_initial_draft_context_schema(connection)
            row = connection.execute(
                """
            SELECT version, context_digest
            FROM initial_draft_context_authority
            WHERE work_item_id = ?
            """,
                (work_item_id,),
            ).fetchone()
            if row is None:
                version = 1
            elif row["context_digest"] == context_digest:
                version = int(row["version"])
            else:
                version = int(row["version"]) + 1
            connection.execute(
                """
            INSERT INTO initial_draft_context_authority
              (work_item_id, context_digest, base_revision_id, version, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(work_item_id) DO UPDATE SET
              context_digest=excluded.context_digest,
              base_revision_id=excluded.base_revision_id,
              version=excluded.version,
              updated_at=excluded.updated_at
            """,
                (work_item_id, context_digest, base_revision_id, version, utc_now().isoformat()),
            )
            return version
    except sqlite3.OperationalError as error:
        if "locked" not in str(error).lower():
            raise
        return 0


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


def _claim_context_authority(
    connection,
    *,
    work_item_id: str,
    context_digest: str | None,
    expected_base_revision_id: str | None,
    enforce: bool,
) -> bool:
    ensure_initial_draft_context_schema(connection)
    row = connection.execute(
        "SELECT context_digest FROM initial_draft_context_authority WHERE work_item_id = ?",
        (work_item_id,),
    ).fetchone()
    if row is None:
        if context_digest is None:
            return True
        connection.execute(
            """
            INSERT INTO initial_draft_context_authority
              (work_item_id, context_digest, base_revision_id, version, updated_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (work_item_id, context_digest, expected_base_revision_id, utc_now().isoformat()),
        )
        return True
    if row["context_digest"] == context_digest:
        return True
    if enforce:
        return False
    connection.execute(
        """
        UPDATE initial_draft_context_authority
        SET context_digest = ?, base_revision_id = ?,
            version = version + 1, updated_at = ?
        WHERE work_item_id = ?
        """,
        (context_digest, expected_base_revision_id, utc_now().isoformat(), work_item_id),
    )
    return True


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
    enforce_context_authority: bool = False,
) -> InitialDraftClaim:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    run_store.status()
    with run_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if not _claim_context_authority(
            connection,
            work_item_id=work_item_id,
            context_digest=context_digest,
            expected_base_revision_id=expected_base_revision_id,
            enforce=enforce_context_authority,
        ):
            return InitialDraftClaim(run=None, newly_claimed=False, stale_context=True)
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
            and revision_matches_initial_draft_context(
                canonical_revision,
                proposal_id=proposal_id,
                planning_digest=planning_digest,
                planning_input_digest=planning_input_digest,
                context_digest=context_digest,
            )
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
        # Only the request matching the durable authority may retire older claims.
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
            (
                run.id,
                run.started_at.isoformat(),
                json.dumps(run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            ),
        )
        return InitialDraftClaim(run=run, newly_claimed=True)


def finish_initial_draft_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun | None:
    return transition_initial_draft_run_if_status(run_store, run, status=status, error=error)


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
