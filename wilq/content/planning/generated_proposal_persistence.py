"""Atomic persistence and immutable lineage assembly for generated planning proposals."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.section_mapping import build_inventory_mapping
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.store.refresh_preparation_atomic import RefreshPreparationAtomicityError
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def persist_generated_proposal(
    *,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    proposal: ContentPlanningProposal,
    completed_run: CodexRun,
    started_run: CodexRun,
    trace: ContentCodexRuntimeTrace | None,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
    pre_persistence_guard: Callable[[], ContentPlanningProposalResponse | None] | None,
    finish_run: Callable[[LocalStateStore, CodexRun, Literal["blocked", "failed"], str], None],
    runtime_failure_response: Callable[
        [
            ContentPlanningInput,
            ContentPlanningProposalBlocker,
            Literal["blocked", "failed"],
            ContentCodexRuntimeTrace | None,
            str,
        ],
        ContentPlanningProposalResponse,
    ],
    runtime_trace_with_run_id: Callable[
        [ContentCodexRuntimeTrace | None, str], ContentCodexRuntimeTrace
    ],
) -> ContentPlanningProposalResponse:
    if pre_persistence_guard is not None:
        guarded = pre_persistence_guard()
        if guarded is not None:
            finish_run(run_store, started_run, "blocked", guarded.blockers[0].code)
            return guarded
    try:
        store_status, stored = store.save_generated(
            proposal,
            completed_run,
            replace_existing_exact_input=(
                request.regenerate_stale_mapping or request.regenerate_after_review
            ),
        )
    except RefreshPreparationAtomicityError as error:
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code=error.code,
            label="Autoryzacja refresh nie jest już aktualna",
            reason=(
                "Atomowy zapis wykrył zmianę klasyfikacji, autoryzacji albo "
                "źródłowego inputu."
            ),
            next_step=(
                "Odśwież przygotowanie refresh i uruchom nową próbę dla "
                "bieżącego receipt."
            ),
        )
        finish_run(run_store, started_run, "blocked", blocker.code)
        return runtime_failure_response(
            planning_input,
            blocker,
            "blocked",
            trace,
            started_run.id,
        )
    except Exception:
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code="persistence_failed",
            label="Nie zapisano planu",
            reason="Atomowy zapis planu i zakończonego CodexRun nie powiódł się.",
            next_step=(
                "Sprawdź prywatny store i uruchom nową próbę; częściowy plan nie jest "
                "dostępny."
            ),
        )
        finish_run(run_store, started_run, "failed", blocker.code)
        return runtime_failure_response(
            planning_input,
            blocker,
            "failed",
            trace,
            started_run.id,
        )
    return ContentPlanningProposalResponse(
        status="idempotent" if store_status == "idempotent" else "created",
        work_item_id=planning_input.work_item_id,
        content_kind=planning_input.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        proposal=stored,
        refresh_preparation_binding=stored.refresh_preparation_binding,
        runtime=runtime_trace_with_run_id(trace, started_run.id),
        safe_next_step="Sprawdź strategię i każdą sekcję; plan pozostaje niezatwierdzony.",
    )


def proposal_from_output(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
    run: CodexRun,
    *,
    refresh_preparation_binding: ContentRefreshPreparationBinding | None,
) -> ContentPlanningProposal:
    proposal_id = f"content_planning_proposal_{uuid4().hex}"
    sections = [
        ContentPlanningSection(
            section_id=f"{proposal_id}_section_{index:02d}",
            source_material_ids=_lineage_ids_for_evidence(
                planning_input.source_facts,
                section.evidence_ids,
                field="source_material_ids",
            ),
            knowledge_card_ids=_lineage_ids_for_evidence(
                planning_input.source_facts,
                section.evidence_ids,
                field="knowledge_card_ids",
            ),
            **section.model_dump(),
        )
        for index, section in enumerate(output.sections, start=1)
    ]
    proposal = ContentPlanningProposal(
        work_item_id=planning_input.work_item_id,
        planning_digest="0" * 64,
        proposal_id=proposal_id,
        codex_run_id=run.id,
        generation_status="codex_generated",
        input_schema_version=planning_input.schema_name,
        criteria_version=planning_input.criteria_version,
        planning_input_digest=planning_input.planning_input_digest,
        content_kind=planning_input.content_kind,
        final_canonical_url=planning_input.final_canonical_url,
        service_card_id=planning_input.confirmed_service_card_id,
        service_label=planning_input.service_label,
        service_selection_confirmed=planning_input.content_kind == "service",
        target_reader=output.target_reader,
        buyer_problem=output.buyer_problem,
        buyer_trigger=output.buyer_trigger,
        search_intent=output.search_intent,
        angle=output.angle,
        value_proposition=output.value_proposition,
        cta_direction=(
            output.cta_blocks[0].copy_direction
            if output.cta_blocks
            else planning_input.baseline_cta_direction
        ),
        internal_link_directions=[
            f"{item.placement}: {item.target_url} ({item.anchor_direction})"
            for item in output.internal_links
        ],
        sections=sections,
        inventory_mapping=build_inventory_mapping(
            planning_input,
            output,
            [section.section_id for section in sections],
        ),
        search_demand=planning_input.query_portfolio,
        page_assets=output.page_assets,
        faq=output.faq,
        cta_blocks=output.cta_blocks,
        internal_links=output.internal_links,
        conditional_hypotheses=output.conditional_hypotheses,
        measurement_plan=output.measurement_plan,
        measurement_metrics=planning_input.measurement_metrics,
        measurement_baseline_evidence_ids=planning_input.measurement_baseline_evidence_ids,
        evidence_ids=planning_input.evidence_ids,
        source_connectors=planning_input.source_connectors,
        source_material_ids=sorted(
            {
                source_material_id
                for fact in planning_input.source_facts
                for source_material_id in fact.source_material_ids
            }
        ),
        knowledge_card_ids=planning_input.knowledge_card_ids,
        refresh_preparation_binding=refresh_preparation_binding,
        created_at=run.completed_at,
    )
    digest_payload = proposal.model_dump(
        mode="json",
        exclude={"planning_digest", "proposal_version", "created_at"},
    )
    digest = sha256(
        json.dumps(
            digest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return proposal.model_copy(update={"planning_digest": digest})


def _lineage_ids_for_evidence(
    source_facts: Iterable[object],
    evidence_ids: Iterable[str],
    *,
    field: Literal["source_material_ids", "knowledge_card_ids"],
) -> list[str]:
    allowed_evidence = set(evidence_ids)
    values: set[str] = set()
    for fact in source_facts:
        fact_evidence_ids = getattr(fact, "evidence_ids", [])
        if allowed_evidence.intersection(fact_evidence_ids):
            values.update(getattr(fact, field, []))
    return sorted(values)


__all__ = ["persist_generated_proposal", "proposal_from_output"]
