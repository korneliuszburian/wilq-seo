"""Bounded assurance-repair orchestration for one transient draft candidate."""

from __future__ import annotations

from collections.abc import Callable

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.draft_assurance_runtime import (
    ContentDraftAssuranceFailure,
    run_regulatory_draft_assurance,
)
from wilq.content.drafts.initial_draft_validation import (
    _body_has_source_fact_signal,
    _distinctive_fact_tokens,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_turn import (
    _approved_planning_source_facts,
    _source_facts_by_section,
)
from wilq.content.drafts.regulatory_draft_repair import (
    _document_ready_fact_text,
    repair_regulatory_assertions,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.storage.local_state import LocalStateStore

AssuranceResult = ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure | None
AssureDraft = Callable[
    [ContentInitialDraftModelOutput, ContentCodexRuntimeTrace],
    AssuranceResult,
]
OutputBlocker = Callable[[ContentInitialDraftModelOutput], ContentInitialDraftBlocker | None]
_MISSING_SOURCE_FACT_SIGNAL_PREFIX = "missing_source_fact_signal:"
_MAX_GROUNDING_FACT_PARAGRAPHS = 3


def repair_missing_source_fact_signals(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    missing_codes: list[str],
) -> ContentInitialDraftModelOutput:
    """Append exact approved planning facts to shallow targeted sections."""

    missing_section_ids = {
        code.removeprefix(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
        for code in missing_codes
        if code.startswith(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
    }
    facts_by_section = _source_fact_summaries_by_section(planning_input, proposal)
    distinctive_tokens = _distinctive_fact_tokens(
        [fact.extracted_fact for fact in _approved_planning_source_facts(planning_input)]
    )
    sections = []
    for section in output.sections:
        fact_summaries = facts_by_section.get(section.section_id, [])
        if (
            section.section_id not in missing_section_ids
            or not fact_summaries
            or _body_has_source_fact_signal(
                section.body_markdown,
                fact_summaries,
                distinctive_tokens=distinctive_tokens,
            )
        ):
            sections.append(section)
            continue
        document_ready_facts = list(
            dict.fromkeys(
                fact_text
                for summary in fact_summaries
                if (
                    fact_text := _document_ready_fact_text(
                        summary,
                        protected_terms=None,
                    ).strip()
                )
            )
        )[:_MAX_GROUNDING_FACT_PARAGRAPHS]
        patch_text = "\n\n".join(document_ready_facts)
        if not patch_text or patch_text in section.body_markdown:
            sections.append(section)
            continue
        sections.append(
            section.model_copy(
                update={
                    "body_markdown": f"{section.body_markdown}\n\n{patch_text}",
                }
            )
        )
    return ContentInitialDraftModelOutput.model_validate(
        {
            **output.model_dump(mode="python"),
            "sections": [section.model_dump(mode="python") for section in sections],
        }
    )


def _source_fact_summaries_by_section(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> dict[str, list[str]]:
    projection: dict[str, list[str]] = {}
    for row in _source_facts_by_section(planning_input, proposal):
        section_id = row.get("section_id")
        source_facts = row.get("source_facts")
        if not isinstance(section_id, str) or not isinstance(source_facts, list):
            raise ValueError("Invalid source-fact section projection.")
        summaries: list[str] = []
        for source_fact in source_facts:
            if not isinstance(source_fact, dict):
                raise ValueError("Invalid source-fact section projection.")
            summary = source_fact.get("summary")
            if not isinstance(summary, str):
                raise ValueError("Invalid source-fact section projection.")
            summaries.append(summary)
        projection[section_id] = summaries
    return projection


def assure_and_repair_initial_draft(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: OutputBlocker,
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
        ),
        output_blocker=output_blocker,
    )


def repair_initial_output_blocker(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    output_blocker: OutputBlocker,
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
    )
    if repaired is not None:
        output, trace = repaired
        blocker = output_blocker(output)
        if blocker is None:
            return output, trace, None
    missing_source_fact_codes = [
        code
        for code in blocker.source_codes
        if code.startswith(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
    ]
    if missing_source_fact_codes:
        output = repair_missing_source_fact_signals(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            missing_codes=missing_source_fact_codes,
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
) -> AssuranceResult:
    """Run the independent critic before a regulated draft can be persisted."""

    return run_regulatory_draft_assurance(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        client=client,
        run_store=run_store,
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
        )
        if assertion_repair is not None:
            output, trace = assertion_repair
            blocker = output_blocker(output)
    if blocker is not None:
        return output, trace, assurance, blocker

    reassured = assure_draft(output, trace)
    if not isinstance(reassured, ContentDraftAssuranceFailure):
        return output, trace, reassured, None

    # Each deterministic repair canonicalizes at least one regulatory section
    # from approved official facts. The finite section count therefore bounds
    # successive critic failures without permitting an unbounded model loop.
    deterministic_repair_budget = len(
        {section.section_id for section in proposal.sections if section.regulatory_requirement_ids}
    )
    for _ in range(deterministic_repair_budget):
        deterministic = repair_regulatory_assertions(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            blocker=_assurance_blocker(reassured),
            client=client,
            force_deterministic_replace=True,
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


__all__ = [
    "assure_and_repair_initial_draft",
    "assure_regulated_draft",
    "repair_after_assurance_failure",
    "repair_initial_output_blocker",
    "repair_missing_source_fact_signals",
]
