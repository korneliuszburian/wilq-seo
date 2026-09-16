"""Prepare the exact body targets allowed to reach the initial-draft writer."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)

DraftPlanBlockerCode = Literal[
    "draft_plan_source_support_missing",
    "draft_plan_merge_target_missing",
    "draft_plan_no_writable_targets",
]

_NON_BODY_TARGET_DISPOSITIONS = frozenset(
    {"remove", "remove_review_required", "defer", "deferred", "defer_review_required"}
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class PreparedDraftPlan:
    """Exact plan projection accepted by the initial-draft writer."""

    candidate: ContentPlanningProposal
    exact_source_snapshot: ContentPlanningInput
    body_targets: tuple[ContentPlanningSection, ...]


@dataclass(frozen=True, slots=True)
class DraftPlanBlocked:
    """Typed, Polish blocker preventing an unsafe plan from reaching a writer."""

    blocker: ContentInitialDraftBlocker


@dataclass(frozen=True, slots=True)
class _SourceSupport:
    evidence_ids: frozenset[str]
    source_material_ids: frozenset[str]


def prepare_draft_plan(
    candidate: ContentPlanningProposal,
    exact_source_snapshot: ContentPlanningInput,
) -> PreparedDraftPlan | DraftPlanBlocked:
    """Validate body targets against exact source-fact lineage.

    Inventory, demand, measurement and generic claim evidence are deliberately
    insufficient on their own. A target is writable only when its own plan
    lineage intersects an exact source-fact evidence or source-material ID.
    """

    if not _same_exact_input(candidate, exact_source_snapshot):
        return _blocked(
            "draft_plan_source_support_missing",
            "Plan nie odpowiada dokładnie bieżącemu wejściu źródłowemu.",
            (
                "Odśwież plan z tego samego current source snapshotu; nie uruchamiaj "
                "szkicu z historycznego wejścia."
            ),
            ("draft_plan_exact_input_mismatch",),
        )

    body_targets = tuple(
        section
        for section in _sections(candidate)
        if section.inventory_disposition not in _NON_BODY_TARGET_DISPOSITIONS
    )
    if not body_targets:
        return _blocked(
            "draft_plan_no_writable_targets",
            "Plan nie ma żadnego celu body do zapisania.",
            (
                "Pozostaw sekcje remove/defer poza szkicem albo przygotuj nowy plan "
                "z exact celem body."
            ),
            ("draft_plan_no_writable_targets",),
        )

    merge_targets = tuple(
        _target_code(section)
        for section in body_targets
        if section.inventory_disposition == "merge"
    )
    if merge_targets:
        return _blocked(
            "draft_plan_merge_target_missing",
            "Plan zawiera scalanie bez jawnego kontraktu destination dla docelowej strony.",
            (
                "inventory_section_id oznacza źródłową sekcję inventory, a nie destination. "
                "Uzupełnij osobny exact kontrakt celu scalania albo oznacz sekcję do "
                "osobnego review; scalanie nie może stać się osobnym celem body."
            ),
            merge_targets,
        )

    support = _source_support(exact_source_snapshot)
    unsupported = tuple(
        _target_code(section)
        for section in body_targets
        if not _has_exact_support(section, support)
    )
    if unsupported:
        return _blocked(
            "draft_plan_source_support_missing",
            (
                "Co najmniej jeden cel body nie ma merytorycznego wsparcia z bieżącego "
                "packetu ani source fact."
            ),
            (
                "Przypisz każdemu celowi dokładny source fact lub source material z "
                "bieżącego packetu; same inventory, popyt i pomiar nie wystarczają."
            ),
            unsupported,
        )

    return PreparedDraftPlan(
        candidate=candidate,
        exact_source_snapshot=exact_source_snapshot,
        body_targets=body_targets,
    )


def _same_exact_input(
    candidate: ContentPlanningProposal,
    exact_source_snapshot: ContentPlanningInput,
) -> bool:
    candidate_work_item_id = getattr(candidate, "work_item_id", None)
    source_work_item_id = getattr(exact_source_snapshot, "work_item_id", None)
    candidate_digest = getattr(candidate, "planning_input_digest", None)
    source_digest = getattr(exact_source_snapshot, "planning_input_digest", None)
    return (
        isinstance(candidate_work_item_id, str)
        and bool(candidate_work_item_id.strip())
        and candidate_work_item_id == source_work_item_id
        and isinstance(source_work_item_id, str)
        and bool(source_work_item_id.strip())
        and isinstance(candidate_digest, str)
        and _HEX64.fullmatch(candidate_digest) is not None
        and isinstance(source_digest, str)
        and _HEX64.fullmatch(source_digest) is not None
        and candidate_digest == source_digest
    )


def _sections(candidate: ContentPlanningProposal) -> tuple[ContentPlanningSection, ...]:
    return tuple(candidate.sections)


def _source_support(snapshot: ContentPlanningInput) -> _SourceSupport:
    evidence_ids: set[str] = set()
    source_material_ids: set[str] = set()
    for planning_source_fact in snapshot.source_facts:
        if not planning_source_fact.source_fact_ids:
            continue
        evidence_ids.update(planning_source_fact.evidence_ids)
        source_material_ids.update(planning_source_fact.source_material_ids)

    for regulatory_source_fact in snapshot.regulatory_coverage.source_facts:
        evidence_ids.update(regulatory_source_fact.evidence_ids)

    return _SourceSupport(
        evidence_ids=frozenset(evidence_ids),
        source_material_ids=frozenset(source_material_ids),
    )


def _has_exact_support(section: ContentPlanningSection, support: _SourceSupport) -> bool:
    section_evidence = set(section.evidence_ids)
    section_material = set(section.source_material_ids)
    return bool(
        section_evidence.intersection(support.evidence_ids)
        or section_material.intersection(support.source_material_ids)
    )


def _target_code(section: ContentPlanningSection) -> str:
    return section.section_id or section.heading or "unknown_body_target"


def _blocked(
    code: DraftPlanBlockerCode,
    reason: str,
    next_step: str,
    source_codes: Iterable[str],
) -> DraftPlanBlocked:
    return DraftPlanBlocked(
        blocker=ContentInitialDraftBlocker(
            code=code,
            label="Plan szkicu wymaga dokładnego pokrycia",
            reason=reason,
            next_step=next_step,
            source_codes=list(source_codes),
        )
    )


__all__ = [
    "DraftPlanBlocked",
    "DraftPlanBlockerCode",
    "PreparedDraftPlan",
    "prepare_draft_plan",
]
