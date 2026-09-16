"""Own the complete pre-persist repair policy for one initial draft.

The orchestrator (initial_full_draft) previously inlined a schedule over
three repair systems: deterministic scope repair, regulated assurance and
its repair cycle, and the readability last-writer. Each repair call
appeared three to four times with the same terminal blocker closures
duplicated inline. This module owns that schedule as one policy: the
stage order, every repair budget, the blocker-closure path, and the
intentional asymmetry that regulatory grounding fires only when a
readability pass leaves a blocker.

The module exposes a single interface; all terminal states (blocked,
assurance failure, ready) come back as typed results so the orchestrator
has exactly one exit to persist.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import (
    ContentDraftAssuranceReceipt,
    draft_assurance_fingerprint,
    regulatory_draft_assurance_profile,
)
from wilq.content.drafts.draft_assurance_runtime import (
    ContentDraftAssuranceFailure,
    run_regulatory_draft_assurance,
)
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan
from wilq.content.drafts.grounding import (
    _MISSING_SOURCE_FACT_SIGNAL_PREFIX,
    repair_missing_source_fact_signals,
)
from wilq.content.drafts.initial_draft_readability import (
    ReadabilityIssue,
    readability_issues_for_output,
    repair_readability_candidate,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.regulatory_repair import repair_regulatory_assertions
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.storage.local_state import LocalStateStore

OutputBlocker = Callable[
    [ContentInitialDraftModelOutput],
    ContentInitialDraftBlocker | None,
]
AssuranceResult = ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None
AssureDraft = Callable[
    [ContentInitialDraftModelOutput, ContentCodexRuntimeTrace],
    AssuranceResult,
]

_ALTERNATION_BUDGET = 2
_ASSURANCE_REPAIR_TURN_BUDGET_PER_REGULATORY_SECTION = 1
_READABILITY_REPAIR_TURN_BUDGET = 2


class DraftAlterationResult:
    """One terminal outcome of the pre-persist alternation policy.

    ``status`` is "ready", "blocked" or "assurance_failure". Exactly the
    matching payload is set; the orchestrator maps it to persistence or a
    terminal blocker without re-reading the schedule.
    """

    def __init__(
        self,
        *,
        status: Literal["ready", "blocked", "assurance_failure"],
        output: ContentInitialDraftModelOutput | None = None,
        trace: ContentCodexRuntimeTrace | None = None,
        assurance: ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None = None,
        blocker: ContentInitialDraftBlocker | None = None,
    ) -> None:
        self.status = status
        self.output = output
        self.trace = trace
        self.assurance = assurance
        self.blocker = blocker


def alter_draft_towards_persistence(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: OutputBlocker,
    prepared_plan: PreparedDraftPlan | None = None,
    assurance_cache: dict[str, AssuranceResult] | None = None,
) -> DraftAlterationResult:
    """Run the pre-persist alternation policy to one terminal state.

    Stage order (intentional, preserved from the previous orchestrator):

    1. Deterministic scope repair — ground missing source-fact signals and
       regulatory assertions before any assurance turn.
    2. Regulated assurance with its bounded repair cycle.
    3. Readability last-writer. A readability blocker re-grounds regulatory
       assertions (the asymmetry: regulatory repair fires only here) and
       re-runs readability once; if the re-grounded output still blocks, the
       draft is terminal.
    4. If assurance changed the output (grounded facts reintroduced after the
       readability pass), alternate assurance and readability within a bounded
       budget so the persisted document keeps both exact regulatory concepts
       and readable prose.
    """

    cache = {} if assurance_cache is None else assurance_cache
    output, trace, blocker = repair_initial_output_blocker(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        output_blocker=output_blocker,
        prepared_plan=prepared_plan,
    )
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)

    output, trace, assurance, blocker = assure_and_repair_initial_draft(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        run_store=run_store,
        output_blocker=output_blocker,
        prepared_plan=prepared_plan,
        assurance_cache=cache,
    )
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)
    if isinstance(assurance, ContentDraftAssuranceFailure):
        return DraftAlterationResult(
            status="assurance_failure", output=output, trace=trace, assurance=assurance
        )

    assured_output = output
    output, trace, blocker = assure_readability_and_repair(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        client=client,
        output_blocker=output_blocker,
    )
    if blocker is not None:
        repaired = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
            prepared_plan=prepared_plan,
        )
        if repaired is not None:
            output, trace = repaired
            blocker = output_blocker(output)
            if blocker is None:
                output, trace, blocker = assure_readability_and_repair(
                    planning_input=planning_input,
                    proposal=proposal,
                    output=output,
                    trace=trace,
                    client=client,
                    output_blocker=output_blocker,
                )
                if blocker is not None:
                    repaired = repair_regulatory_assertions(
                        planning_input=planning_input,
                        proposal=proposal,
                        output=output,
                        blocker=blocker,
                        client=client,
                        prepared_plan=prepared_plan,
                    )
                    if repaired is not None:
                        output, trace = repaired
                        blocker = output_blocker(output)
    if blocker is not None:
        return DraftAlterationResult(status="blocked", output=output, trace=trace, blocker=blocker)

    if output == assured_output:
        final_blocker = _final_candidate_blocker(
            planning_input=planning_input,
            output=output,
            assurance=assurance,
            prepared_plan=prepared_plan,
            output_blocker=output_blocker,
        )
        if final_blocker is not None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=final_blocker
            )
        return DraftAlterationResult(
            status="ready", output=output, trace=trace, assurance=assurance
        )

    for _ in range(_ALTERNATION_BUDGET):
        output, trace, assurance, blocker = assure_and_repair_initial_draft(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            trace=trace,
            client=client,
            run_store=run_store,
            output_blocker=output_blocker,
            prepared_plan=prepared_plan,
            assurance_cache=cache,
        )
        if blocker is not None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        if isinstance(assurance, ContentDraftAssuranceFailure):
            return DraftAlterationResult(
                status="assurance_failure", output=output, trace=trace, assurance=assurance
            )
        assured_output = output
        output, trace, blocker = assure_readability_and_repair(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            trace=trace,
            client=client,
            output_blocker=output_blocker,
        )
        if blocker is None:
            if output != assured_output:
                continue
            final_blocker = _final_candidate_blocker(
                planning_input=planning_input,
                output=output,
                assurance=assurance,
                prepared_plan=prepared_plan,
                output_blocker=output_blocker,
            )
            if final_blocker is None:
                return DraftAlterationResult(
                    status="ready", output=output, trace=trace, assurance=assurance
                )
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=final_blocker
            )
        repaired = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
            prepared_plan=prepared_plan,
        )
        if repaired is None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        output, trace = repaired
        blocker = output_blocker(output)
        if blocker is not None:
            return DraftAlterationResult(
                status="blocked", output=output, trace=trace, blocker=blocker
            )
        # The repair changed the candidate after its last assurance. Re-enter
        # the loop so the exact new fingerprint is assessed once.
        continue
    return DraftAlterationResult(
        status="blocked",
        output=output,
        trace=trace,
        blocker=_finalization_budget_blocker(),
    )


def assure_and_repair_initial_draft(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: OutputBlocker,
    prepared_plan: PreparedDraftPlan | None = None,
    assurance_cache: dict[str, AssuranceResult] | None = None,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    AssuranceResult,
    ContentInitialDraftBlocker | None,
]:
    """Run assurance and its bounded repair policy as one fail-closed step."""

    assurance = assure_regulated_draft(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        client=client,
        run_store=run_store,
        prepared_plan=prepared_plan,
        assurance_cache=assurance_cache,
    )
    if not isinstance(assurance, ContentDraftAssuranceFailure):
        return output, trace, assurance, None
    return repair_after_assurance_failure(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=trace,
        assurance=assurance,
        client=client,
        assure_draft=lambda candidate, _candidate_trace: assure_regulated_draft(
            planning_input=planning_input,
            proposal=proposal,
            output=candidate,
            client=client,
            run_store=run_store,
            prepared_plan=prepared_plan,
            assurance_cache=assurance_cache,
        ),
        output_blocker=output_blocker,
        prepared_plan=prepared_plan,
    )


def repair_initial_output_blocker(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    output_blocker: OutputBlocker,
    prepared_plan: PreparedDraftPlan | None = None,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    ContentInitialDraftBlocker | None,
]:
    """Repair deterministic scope failures before invoking assurance."""

    blocker = output_blocker(output)
    if blocker is None:
        return output, trace, None
    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=blocker,
        client=client,
        prepared_plan=prepared_plan,
    )
    if repaired is not None:
        output, trace = repaired
        blocker = output_blocker(output)
        if blocker is None:
            return output, trace, None
    missing_source_fact_codes = [
        code for code in blocker.source_codes if code.startswith(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
    ]
    if missing_source_fact_codes:
        output = repair_missing_source_fact_signals(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            missing_codes=missing_source_fact_codes,
            prepared_plan=prepared_plan,
        )
        return output, trace, output_blocker(output)
    return output, trace, blocker


def assure_regulated_draft(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    prepared_plan: PreparedDraftPlan | None = None,
    assurance_cache: dict[str, AssuranceResult] | None = None,
) -> AssuranceResult:
    """Run the independent critic before a regulated draft can be persisted."""

    try:
        profile = regulatory_draft_assurance_profile(planning_input)
    except AttributeError:
        profile = None
    cache_key = (
        None
        if profile is None or prepared_plan is None
        else draft_assurance_fingerprint(
            output=output,
            prepared_plan=prepared_plan,
            profile_id=profile.id,
            profile_version=profile.version,
        )
    )
    if cache_key is not None and assurance_cache is not None and cache_key in assurance_cache:
        return assurance_cache[cache_key]
    result = run_regulatory_draft_assurance(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        client=client,
        run_store=run_store,
        prepared_plan=prepared_plan,
    )
    if cache_key is not None and assurance_cache is not None:
        assurance_cache[cache_key] = result
    return result


def _final_assurance_blocker(
    *,
    planning_input: ContentPlanningInput,
    output: ContentInitialDraftModelOutput,
    assurance: AssuranceResult,
    prepared_plan: PreparedDraftPlan | None,
) -> ContentInitialDraftBlocker | None:
    try:
        profile = regulatory_draft_assurance_profile(planning_input)
    except AttributeError:
        profile = None
    coverage = planning_input.regulatory_coverage
    if getattr(coverage, "applicability_status", None) != "required":
        return None
    if profile is None:
        return ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Brakuje dokładnego profilu końcowej kontroli",
            reason="Wymagana treść regulowana nie ma bieżącego profilu i wersji assurance.",
            next_step="Odśwież profil regulacyjny i uruchom kontrolę finalnego dokumentu ponownie.",
            source_codes=["assurance_profile_missing_or_mismatch"],
        )
    source_codes = ["assurance_fingerprint_missing"]
    if not isinstance(assurance, ContentDraftAssuranceReceipt) or assurance.status != "passed":
        source_codes = ["assurance_pass_required"]
    elif prepared_plan is None:
        source_codes = ["assurance_prepared_plan_missing"]
    else:
        expected = draft_assurance_fingerprint(
            output=output,
            prepared_plan=prepared_plan,
            profile_id=profile.id,
            profile_version=profile.version,
        )
        if assurance.assurance_fingerprint == expected:
            return None
        source_codes = ["assurance_fingerprint_mismatch"]
    return ContentInitialDraftBlocker(
        code="draft_assurance_failed",
        label="Końcowa kontrola merytoryczna nie dotyczy finalnego dokumentu",
        reason="Wynik PASS nie ma fingerprintu zgodnego z finalnym dokumentem i kontekstem.",
        next_step="Uruchom nową próbę kontroli dla niezmienionego finalnego dokumentu.",
        source_codes=source_codes,
    )


def _final_candidate_blocker(
    *,
    planning_input: ContentPlanningInput,
    output: ContentInitialDraftModelOutput,
    assurance: AssuranceResult,
    prepared_plan: PreparedDraftPlan | None,
    output_blocker: OutputBlocker,
) -> ContentInitialDraftBlocker | None:
    deterministic = output_blocker(output)
    if deterministic is not None:
        return deterministic
    readability = readability_issues_for_output(output)
    if readability:
        return _readability_blocker(readability)
    return _final_assurance_blocker(
        planning_input=planning_input,
        output=output,
        assurance=assurance,
        prepared_plan=prepared_plan,
    )


def _finalization_budget_blocker() -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="draft_assurance_failed",
        label="Nie osiągnięto stabilnej wersji finalnego dokumentu",
        reason="Budżet napraw zakończył się przed zgodnym readability i exact PASS.",
        next_step="Popraw plan albo źródła i uruchom nową próbę; WILQ nie zapisze tej wersji.",
        source_codes=["draft_finalization_budget_exhausted"],
    )


def repair_after_assurance_failure(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    assurance: ContentDraftAssuranceFailure,
    client: CodexAppServerClientProtocol,
    assure_draft: AssureDraft,
    output_blocker: OutputBlocker,
    prepared_plan: PreparedDraftPlan | None = None,
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    AssuranceResult,
    ContentInitialDraftBlocker | None,
]:
    """Repair disclosed failures to a finite regulatory-section fixed point."""

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=_assurance_blocker(assurance),
        client=client,
        repair_reasons=assurance.repair_reasons,
        prepared_plan=prepared_plan,
    )
    if repaired is None:
        return output, trace, assurance, None
    output, trace = repaired
    blocker = output_blocker(output)
    if blocker is not None:
        assertion_repair = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=blocker,
            client=client,
            prepared_plan=prepared_plan,
        )
        if assertion_repair is not None:
            output, trace = assertion_repair
            blocker = output_blocker(output)
    if blocker is not None:
        return output, trace, assurance, blocker

    reassured = assure_draft(output, trace)
    if not isinstance(reassured, ContentDraftAssuranceFailure):
        return output, trace, reassured, None

    deterministic_repair_budget = (
        len(
            {
                section.section_id
                for section in proposal.sections
                if section.regulatory_requirement_ids
            }
        )
        * _ASSURANCE_REPAIR_TURN_BUDGET_PER_REGULATORY_SECTION
    )
    for _ in range(deterministic_repair_budget):
        deterministic = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=_assurance_blocker(reassured),
            client=client,
            force_deterministic_replace=True,
            prepared_plan=prepared_plan,
        )
        if deterministic is None:
            return output, trace, reassured, None
        output, trace = deterministic
        blocker = output_blocker(output)
        if blocker is not None:
            return output, trace, reassured, blocker
        reassured = assure_draft(output, trace)
        if not isinstance(reassured, ContentDraftAssuranceFailure):
            return output, trace, reassured, None
    return output, trace, reassured, None


def assure_readability_and_repair(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    output_blocker: Callable[[ContentInitialDraftModelOutput], ContentInitialDraftBlocker | None],
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    ContentInitialDraftBlocker | None,
]:
    """Repair readability issues within the module-owned turn budget."""

    issues = readability_issues_for_output(output)
    if not issues:
        return output, trace, None
    blocker = output_blocker(output)
    if blocker is not None:
        return output, trace, blocker
    repair_budget = min(
        len({section_id for _, section_id, _ in issues}),
        _READABILITY_REPAIR_TURN_BUDGET,
    )
    for _ in range(repair_budget):
        candidate = output
        turn_input_trace = trace
        output, trace = repair_readability_candidate(
            planning_input=planning_input,
            proposal=proposal,
            output=candidate,
            issues=issues,
            client=client,
        )
        issues = readability_issues_for_output(output)
        blocker = output_blocker(output)
        if blocker is not None:
            return output, trace, blocker
        if output is candidate and trace is not turn_input_trace:
            return output, trace, _readability_repair_failed_blocker(trace)
        if not issues:
            return output, trace, None
    return output, trace, _readability_blocker(issues)


def _assurance_blocker(
    assurance: ContentDraftAssuranceFailure,
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code=assurance.code,
        label=assurance.label,
        reason=assurance.reason,
        next_step=assurance.next_step,
        source_codes=assurance.source_codes,
    )


def _readability_blocker(
    issues: list[ReadabilityIssue],
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="readability_gate_failed",
        label="Tekst zawiera notatki robocze lub błędy czytelności",
        reason="; ".join(f"{section_id}: {reason}" for _, section_id, reason in issues[:3]),
        next_step=(
            "Usuń wskazane notatki robocze i błędy czytelności, a następnie uruchom "
            "nową próbę generowania."
        ),
        source_codes=list(dict.fromkeys(code for code, _, _ in issues)),
    )


def _readability_repair_failed_blocker(
    trace: ContentCodexRuntimeTrace,
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="readability_repair_failed",
        label="Naprawa czytelności nie powiodła się",
        reason=f"Tura naprawy czytelności nie zastosowała poprawki (status: {trace.status}).",
        next_step="Sprawdź blokadę runtime i uruchom nową próbę; WILQ nie zapisał tekstu.",
        source_codes=["readability_repair_turn_failed"],
    )


__all__ = [
    "DraftAlterationResult",
    "alter_draft_towards_persistence",
    "assure_and_repair_initial_draft",
    "assure_readability_and_repair",
    "assure_regulated_draft",
    "repair_after_assurance_failure",
    "repair_initial_output_blocker",
]
