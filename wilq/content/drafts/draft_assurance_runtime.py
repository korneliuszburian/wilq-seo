"""Execution owner for one isolated regulated-draft assurance turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.drafts.draft_assurance import (
    ContentDraftAssuranceModelOutput,
    ContentDraftAssuranceReceipt,
    draft_assurance_turn_request,
    regulatory_draft_assurance_profile,
    validate_draft_assurance_output,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class ContentDraftAssuranceFailure:
    code: Literal[
        "draft_assurance_failed",
        "draft_assurance_runtime_failed",
        "draft_assurance_invalid_output",
    ]
    label: str
    reason: str
    next_step: str
    source_codes: list[str]


def run_regulatory_draft_assurance(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
) -> ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None:
    """Return a passed receipt or typed failure; this function never persists a draft."""

    profile = regulatory_draft_assurance_profile(planning_input)
    if profile is None:
        return None
    critic_run = run_store.save_codex_run(
        CodexRun(
            id=f"codex_content_draft_assurance_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_regulatory_draft_assurance",
            source="wilq_api",
            status="started",
            used_endpoints=[f"/api/content/work-items/{planning_input.work_item_id}/initial-draft"],
            evidence_ids=planning_input.regulatory_coverage.evidence_ids,
            proposal_id=proposal.proposal_id,
            planning_input_digest=planning_input.planning_input_digest,
        )
    )
    try:
        result = client.run_structured_turn(
            draft_assurance_turn_request(
                planning_input=planning_input,
                output=output,
                profile=profile,
            )
        )
    except Exception:
        result = CodexAppServerTurnResult(status="failed")
    if result.external_call_attempted or result.status != "completed" or result.output_text is None:
        return _failed_runtime_attempt(run_store, critic_run, result)
    try:
        assessment = ContentDraftAssuranceModelOutput.model_validate_json(result.output_text)
        receipt = validate_draft_assurance_output(
            planning_input=planning_input,
            output=output,
            profile=profile,
            assessment=assessment,
            codex_run_id=critic_run.id,
        )
    except ValueError:
        run_store.save_codex_run(
            critic_run.model_copy(
                update={
                    "status": "blocked",
                    "completed_at": utc_now(),
                    "error": "draft_assurance_invalid_output",
                }
            )
        )
        return ContentDraftAssuranceFailure(
            code="draft_assurance_invalid_output",
            label="Kontrola merytoryczna zwróciła niepoprawny wynik",
            reason="Wynik krytyka nie przeszedł ścisłego kontraktu profilu i źródeł.",
            next_step="Odrzuć próbę i uruchom nową; WILQ nie zapisał dokumentu.",
            source_codes=[],
        )
    run_store.save_codex_run(
        critic_run.model_copy(
            update={"status": "completed", "completed_at": utc_now(), "error": None}
        )
    )
    if receipt.status == "passed":
        return receipt
    return ContentDraftAssuranceFailure(
        code="draft_assurance_failed",
        label="Tekst nie przeszedł niezależnej kontroli merytorycznej",
        reason="Krytyk wskazał niespełnione wymagania regulacyjne w dokładnym profilu źródeł.",
        next_step=(
            "Popraw wymagania wskazane przez kontrolę i uruchom nową próbę; "
            "WILQ nie zapisał dokumentu."
        ),
        source_codes=receipt.failed_constraint_ids,
    )


def _failed_runtime_attempt(
    store: LocalStateStore,
    run: CodexRun,
    result: CodexAppServerTurnResult,
) -> ContentDraftAssuranceFailure:
    store.save_codex_run(
        run.model_copy(
            update={
                "status": "blocked",
                "completed_at": utc_now(),
                "error": "draft_assurance_runtime_failed",
            }
        )
    )
    return ContentDraftAssuranceFailure(
        code="draft_assurance_runtime_failed",
        label="Niezależna kontrola merytoryczna nie zakończyła się",
        reason="WILQ nie zapisze regulowanego tekstu bez zakończonej kontroli krytyka.",
        next_step="Sprawdź runtime i uruchom nową próbę; dokument nie został zapisany.",
        source_codes=[item.code for item in result.blockers],
    )
