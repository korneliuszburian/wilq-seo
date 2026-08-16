"""Small persistence helpers for the local initial-draft run audit record."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from wilq.codex.model_policy import (
    configured_codex_model,
    configured_codex_reasoning_effort,
)
from wilq.codex.prompts import resolve_prompt_template
from wilq.codex.safety import assess_codex_prompt
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.runtime.codex_run_lifecycle import (
    transition_codex_run_if_status,
)
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore
from wilq.storage.local_state_runs import supports_run_transaction


@dataclass(frozen=True, slots=True)
class InitialDraftClaim:
    run: CodexRun | None
    newly_claimed: bool
    canonical_revision: ContentDraftRevision | None = None


@dataclass(frozen=True, slots=True)
class InitialDraftClaimContext:
    proposal_id: str
    planning_digest: str
    planning_input_digest: str
    context_digest: str
    base_revision_id: str | None
    context_current: bool

    def matches_claim(
        self,
        *,
        proposal_id: str,
        planning_digest: str,
        planning_input_digest: str,
        context_digest: str | None,
        base_revision_id: str | None,
    ) -> bool:
        return (
            self.proposal_id == proposal_id
            and self.planning_digest == planning_digest
            and self.planning_input_digest == planning_input_digest
            and self.context_digest == context_digest
            and self.base_revision_id == base_revision_id
        )


@dataclass(frozen=True, slots=True)
class _InitialDraftRunMetadata:
    model: str | None
    model_reasoning_effort: str | None
    prompt_digest: str
    prompt_template_id: str


def _initial_draft_run_metadata(prompt: str | None = None) -> _InitialDraftRunMetadata:
    prompt_template = resolve_prompt_template("content_initial_draft")
    effective_prompt = prompt or prompt_template.render(regulatory_draft_directive="")
    safety = assess_codex_prompt(effective_prompt, dry_run=False)
    if not safety.allowed:
        raise ValueError(f"Unsafe initial draft prompt: {safety.reason}")
    return _InitialDraftRunMetadata(
        model=configured_codex_model(),
        model_reasoning_effort=configured_codex_reasoning_effort(),
        prompt_digest=safety.prompt_digest,
        prompt_template_id=prompt_template.registry_id,
    )


def _enrich_started_initial_draft_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    metadata: _InitialDraftRunMetadata,
    source_material_ids: list[str],
) -> CodexRun:
    update = {
        "model": metadata.model,
        "model_reasoning_effort": metadata.model_reasoning_effort,
        "prompt_digest": metadata.prompt_digest,
        "prompt_template_id": metadata.prompt_template_id,
        "source_material_ids": list(dict.fromkeys(source_material_ids)),
    }
    redacted_run = CodexRun.model_validate(
        redact_mapping(run.model_copy(update=update).model_dump(mode="json"))
    )
    if not supports_run_transaction(run_store):
        return run_store.save_codex_run(redacted_run)
    with run_store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT payload_json FROM codex_runs WHERE id = ?",
            (run.id,),
        ).fetchone()
        if row is None:
            raise ValueError("initial draft queued run is no longer executable")
        current = CodexRun.model_validate_json(row["payload_json"])
        if current.status != "started":
            raise ValueError("initial draft queued run is no longer executable")
        enriched = CodexRun.model_validate(
            redact_mapping(current.model_copy(update=update).model_dump(mode="json"))
        )
        cursor = connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = ? AND payload_json = ?",
            (
                json.dumps(
                    enriched.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                run.id,
                row["payload_json"],
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("initial draft queued run is no longer executable")
        return enriched


LEGACY_INITIAL_DRAFT_TIMEOUT_SECONDS = 2400.0


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


def _canonical_revision_for_claim(
    connection: sqlite3.Connection,
    work_item_id: str,
) -> ContentDraftRevision | None:
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


def _expire_claim_if_needed(
    connection: sqlite3.Connection,
    run: CodexRun,
    payload_json: str,
) -> bool:
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


def _current_context_matches_claim(
    current_context: Callable[[], InitialDraftClaimContext | None],
    *,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
    context_digest: str,
    base_revision_id: str | None,
) -> InitialDraftClaimContext | None:
    observed_context = current_context()
    if observed_context is None or not observed_context.matches_claim(
        proposal_id=proposal_id,
        planning_digest=planning_digest,
        planning_input_digest=planning_input_digest,
        context_digest=context_digest,
        base_revision_id=base_revision_id,
    ):
        return None
    return observed_context


def _canonical_initial_draft_claim(
    connection: sqlite3.Connection,
    runs: list[CodexRun],
    *,
    work_item_id: str,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
    context_digest: str,
    expected_base_revision_id: str | None,
    context_current: bool,
) -> InitialDraftClaim | None:
    canonical_revision = _canonical_revision_for_claim(connection, work_item_id)
    revision_is_newer = (
        canonical_revision is not None
        and canonical_revision.revision_id != expected_base_revision_id
    )
    if not (context_current or revision_is_newer) or canonical_revision is None:
        return None
    if (
        canonical_revision.planning_digest != planning_digest
        or canonical_revision.planning_input_digest != planning_input_digest
        or canonical_revision.proposal_metadata is None
        or not revision_matches_initial_draft_context(
            canonical_revision,
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            context_digest=context_digest,
        )
    ):
        return None
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
    if canonical_run is None:
        return None
    return InitialDraftClaim(
        run=canonical_run,
        newly_claimed=False,
        canonical_revision=canonical_revision,
    )


def claim_initial_draft_run(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    proposal_id: str,
    planning_digest: str,
    planning_input_digest: str,
    evidence_ids: list[str],
    source_material_ids: list[str] | None = None,
    timeout_seconds: float,
    context_digest: str,
    expected_base_revision_id: str | None,
    current_context: Callable[[], InitialDraftClaimContext | None],
) -> InitialDraftClaim:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    run_store.status()
    with run_store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        observed_context = _current_context_matches_claim(
            current_context,
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            context_digest=context_digest,
            base_revision_id=expected_base_revision_id,
        )
        if observed_context is None:
            return InitialDraftClaim(run=None, newly_claimed=False)
        rows = connection.execute(
            "SELECT payload_json FROM codex_runs ORDER BY started_at DESC, id DESC"
        ).fetchall()
        runs = [CodexRun.model_validate_json(row["payload_json"]) for row in rows]
        canonical_claim = _canonical_initial_draft_claim(
            connection,
            runs,
            work_item_id=work_item_id,
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            context_digest=context_digest,
            expected_base_revision_id=expected_base_revision_id,
            context_current=observed_context.context_current,
        )
        if canonical_claim is not None:
            return canonical_claim
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
        metadata = _initial_draft_run_metadata()
        run = CodexRun(
            id=f"codex_content_initial_draft_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
            status="started",
            model=metadata.model,
            model_reasoning_effort=metadata.model_reasoning_effort,
            prompt_digest=metadata.prompt_digest,
            prompt_template_id=metadata.prompt_template_id,
            used_endpoints=[endpoint],
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            source_material_ids=list(dict.fromkeys(source_material_ids or [])),
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
    if run.status != "started":
        return None
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
    updated = run.model_copy(
        update={"status": status, "completed_at": utc_now(), "error": error}
    )
    if not supports_run_transaction(run_store):
        return run_store.save_codex_run(updated)
    return transition_codex_run_if_status(
        run_store,
        updated,
    )


def start_initial_draft_run(
    run_store: LocalStateStore,
    *,
    work_item_id: str,
    evidence_ids: list[str],
    source_material_ids: list[str] | None = None,
    proposal_id: str,
    planning_input_digest: str,
    planning_digest: str | None = None,
    context_digest: str | None = None,
    run_id: str | None = None,
    run_id_prefix: str | None = None,
    hook: str | None = None,
    endpoint_path: str | None = None,
    prompt: str | None = None,
) -> CodexRun:
    metadata = _initial_draft_run_metadata(prompt)
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
            or (
                context_digest is not None
                and existing.initial_draft_context_digest != context_digest
            )
        ):
            raise ValueError("initial draft queued run lineage does not match proposal")
        return _enrich_started_initial_draft_run(
            run_store,
            existing,
            metadata=metadata,
            source_material_ids=source_material_ids or [],
        )
    effective_run_id_prefix = (
        "codex_content_initial_draft_" if run_id_prefix is None else run_id_prefix
    )
    effective_hook = "content_initial_full_draft" if hook is None else hook
    effective_endpoint_path = (
        f"/api/content/work-items/{work_item_id}/initial-draft"
        if endpoint_path is None
        else endpoint_path
    )
    return run_store.save_codex_run(
        CodexRun(
            id=f"{effective_run_id_prefix}{uuid4().hex}",
            skill="wilq-content-operator",
            hook=effective_hook,
            source="wilq_api",
            status="started",
            model=metadata.model,
            model_reasoning_effort=metadata.model_reasoning_effort,
            prompt_digest=metadata.prompt_digest,
            prompt_template_id=metadata.prompt_template_id,
            used_endpoints=[effective_endpoint_path],
            evidence_ids=evidence_ids,
            source_material_ids=list(dict.fromkeys(source_material_ids or [])),
            proposal_id=proposal_id,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            initial_draft_context_digest=context_digest,
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
    "InitialDraftClaimContext",
    "effective_initial_draft_deadline",
    "initial_draft_context_digest",
    "transition_initial_draft_run_if_status",
    "safe_initial_draft_run_error",
    "start_initial_draft_run",
]
