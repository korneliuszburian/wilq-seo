"""Small persistence helpers for the local initial-draft run audit record."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


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


def start_initial_draft_run(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    evidence_ids: list[str],
    proposal_id: str,
    planning_input_digest: str,
    run_id: str | None = None,
) -> CodexRun:
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
    "safe_initial_draft_run_error",
    "start_initial_draft_run",
]
