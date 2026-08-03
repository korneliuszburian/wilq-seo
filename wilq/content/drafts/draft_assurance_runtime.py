"""Execution owner for one isolated regulated-draft assurance turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.drafts.draft_assurance import (
    ContentDraftAssuranceCheckOutput,
    ContentDraftAssuranceModelOutput,
    ContentDraftAssuranceReceipt,
    draft_assurance_turn_request,
    regulatory_draft_assurance_constraints,
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
    repair_reasons: dict[str, str]


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
    constraints = regulatory_draft_assurance_constraints(profile)
    checks_or_failure = _collect_bounded_checks(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        profile=profile,
        constraints=constraints,
        client=client,
        run_store=run_store,
        critic_run=critic_run,
    )
    if isinstance(checks_or_failure, ContentDraftAssuranceFailure):
        return checks_or_failure
    checks = checks_or_failure
    assessment = ContentDraftAssuranceModelOutput(checks=checks)
    try:
        receipt = validate_draft_assurance_output(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            profile=profile,
            assessment=assessment,
            codex_run_id=critic_run.id,
        )
    except ValueError as error:
        invalid_output_code = _invalid_output_code(error)
        run_store.save_codex_run(
            critic_run.model_copy(
                update={
                    "status": "blocked",
                    "completed_at": utc_now(),
                    "error": f"draft_assurance_invalid_output|{invalid_output_code}",
                }
            )
        )
        return ContentDraftAssuranceFailure(
            code="draft_assurance_invalid_output",
            label="Kontrola merytoryczna zwróciła niepoprawny wynik",
            reason="Wynik krytyka nie przeszedł ścisłego kontraktu profilu i źródeł.",
            next_step="Odrzuć próbę i uruchom nową; WILQ nie zapisał dokumentu.",
            source_codes=[invalid_output_code],
            repair_reasons={},
        )
    run_store.save_codex_run(
        critic_run.model_copy(
            update={
                "status": "completed",
                "completed_at": utc_now(),
                "error": _assessment_audit_error(assessment, receipt),
            }
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
        repair_reasons={
            check.constraint_id: check.reason_code
            for check in assessment.checks
            if check.constraint_id in receipt.failed_constraint_ids
        },
    )


def _collect_bounded_checks(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    profile,
    constraints,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    critic_run: CodexRun,
) -> list[ContentDraftAssuranceCheckOutput] | ContentDraftAssuranceFailure:
    checks: list[ContentDraftAssuranceCheckOutput] = []
    for constraint in constraints:
        try:
            result = client.run_structured_turn(
                draft_assurance_turn_request(
                    planning_input=planning_input,
                    proposal=proposal,
                    output=output,
                    profile=profile,
                    constraints_override=[constraint],
                )
            )
        except Exception:
            result = CodexAppServerTurnResult(status="failed")
        if (
            result.external_call_attempted
            or result.status != "completed"
            or result.output_text is None
        ):
            return _failed_runtime_attempt(run_store, critic_run, result)
        try:
            assessment = ContentDraftAssuranceModelOutput.model_validate_json(result.output_text)
            if len(assessment.checks) != 1:
                raise ValueError("Draft assurance turn must return one constraint check.")
            checks.extend(assessment.checks)
        except ValueError as error:
            return _invalid_assurance_output(run_store, critic_run, error)
    return checks


def _invalid_assurance_output(
    store: LocalStateStore,
    run: CodexRun,
    error: ValueError,
) -> ContentDraftAssuranceFailure:
    invalid_output_code = _invalid_output_code(error)
    store.save_codex_run(
        run.model_copy(
            update={
                "status": "blocked",
                "completed_at": utc_now(),
                "error": f"draft_assurance_invalid_output|{invalid_output_code}",
            }
        )
    )
    return ContentDraftAssuranceFailure(
        code="draft_assurance_invalid_output",
        label="Kontrola merytoryczna zwróciła niepoprawny wynik",
        reason="Wynik krytyka nie przeszedł ścisłego kontraktu profilu i źródeł.",
        next_step="Odrzuć próbę i uruchom nową; WILQ nie zapisał dokumentu.",
        source_codes=[invalid_output_code],
        repair_reasons={},
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
        repair_reasons={},
    )


def _invalid_output_code(error: ValueError) -> str:
    """Classify validation failures without retaining model-provided text."""

    message = str(error)
    if "assess every constraint in canonical order" in message:
        return "assurance_check_order"
    if "must cite a candidate" in message and "section" in message:
        return "assurance_section_mismatch"
    if "must cite exact constraint evidence" in message:
        return "assurance_missing_evidence"
    if "must cite only exact constraint evidence" in message:
        return "assurance_evidence_mismatch"
    return "assurance_schema_invalid"


def _assessment_audit_error(
    assessment: ContentDraftAssuranceModelOutput,
    receipt: ContentDraftAssuranceReceipt,
) -> str | None:
    """Persist only controlled judge categories, never model prose or excerpts."""

    failure_codes = [
        f"{check.constraint_id}:{check.reason_code}"
        for check in assessment.checks
        if check.constraint_id in receipt.failed_constraint_ids
    ]
    return None if not failure_codes else "draft_assurance_failed|" + ",".join(failure_codes)
