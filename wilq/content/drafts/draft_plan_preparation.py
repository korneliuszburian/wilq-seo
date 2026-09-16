"""Prepare the exact body targets allowed to reach the initial-draft writer."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
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
class PreparedSourceFact:
    """Deep immutable snapshot of one planning source fact."""

    fact_id: str
    summary: str
    source_connector: str
    evidence_ids: tuple[str, ...]
    knowledge_card_ids: tuple[str, ...]
    source_fact_ids: tuple[str, ...]
    source_material_ids: tuple[str, ...]
    regulatory_requirement_ids: tuple[str, ...]

    @classmethod
    def from_model(cls, fact: ContentPlanningSourceFact) -> PreparedSourceFact:
        return cls(
            fact_id=fact.fact_id,
            summary=fact.summary,
            source_connector=fact.source_connector,
            evidence_ids=tuple(fact.evidence_ids),
            knowledge_card_ids=tuple(fact.knowledge_card_ids),
            source_fact_ids=tuple(fact.source_fact_ids),
            source_material_ids=tuple(fact.source_material_ids),
            regulatory_requirement_ids=tuple(fact.regulatory_requirement_ids),
        )


@dataclass(frozen=True, slots=True)
class PreparedDraftTarget:
    """One writable section and its exact source-fact support."""

    section: ContentPlanningSection
    source_facts: tuple[PreparedSourceFact, ...]


@dataclass(frozen=True, slots=True)
class DraftPlanBlocked:
    """Typed, Polish blocker preventing an unsafe plan from reaching a writer."""

    blocker: ContentInitialDraftBlocker


@dataclass(frozen=True, slots=True)
class PreparedDraftPlan:
    """Exact plan projection accepted by the initial-draft writer."""

    candidate: ContentPlanningProposal
    exact_source_snapshot: ContentPlanningInput
    body_targets: tuple[ContentPlanningSection, ...]
    target_supports: tuple[PreparedDraftTarget, ...]

    def source_facts_for_section(
        self,
        section_id: str,
    ) -> tuple[PreparedSourceFact, ...]:
        """Return the facts assigned to one exact writable section."""

        target = next(
            (item for item in self.target_supports if item.section.section_id == section_id),
            None,
        )
        return () if target is None else target.source_facts

    @property
    def source_facts_by_section(
        self,
    ) -> tuple[tuple[str, tuple[PreparedSourceFact, ...]], ...]:
        """Expose deterministic assignments without a mutable mapping."""

        return tuple(
            (target.section.section_id, target.source_facts) for target in self.target_supports
        )


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

    exact_facts = _exact_source_facts(exact_source_snapshot)
    target_supports: list[PreparedDraftTarget] = []
    unsupported: list[str] = []
    for section in body_targets:
        facts = _facts_for_target(section, exact_facts)
        if not facts:
            unsupported.extend(_missing_target_codes(section, exact_facts))
            continue
        target_supports.append(PreparedDraftTarget(section=section, source_facts=facts))
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
            tuple(unsupported),
        )

    return PreparedDraftPlan(
        candidate=candidate,
        exact_source_snapshot=exact_source_snapshot,
        body_targets=body_targets,
        target_supports=tuple(target_supports),
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


def _exact_source_facts(
    snapshot: ContentPlanningInput,
) -> tuple[PreparedSourceFact, ...]:
    """Return only substantive planning facts in a stable order."""

    facts = [
        PreparedSourceFact.from_model(fact)
        for fact in snapshot.source_facts
        if _nonblank_ids(fact.source_fact_ids)
        and (_nonblank_ids(fact.evidence_ids) or _nonblank_ids(fact.source_material_ids))
    ]
    return tuple(
        sorted(
            facts,
            key=lambda fact: (fact.fact_id, tuple(sorted(_nonblank_ids(fact.source_fact_ids)))),
        )
    )


def _facts_for_target(
    section: ContentPlanningSection,
    facts: tuple[PreparedSourceFact, ...],
) -> tuple[PreparedSourceFact, ...]:
    section_evidence = _nonblank_ids(section.evidence_ids)
    section_material = _nonblank_ids(section.source_material_ids)
    if section.regulatory_requirement_ids:
        requirement_ids = tuple(dict.fromkeys(section.regulatory_requirement_ids))
        matched = tuple(
            fact
            for fact in facts
            if section_evidence.intersection(_nonblank_ids(fact.evidence_ids))
            and any(
                requirement_id in _nonblank_ids(fact.regulatory_requirement_ids)
                for requirement_id in requirement_ids
            )
        )
        if any(
            not any(
                requirement_id in _nonblank_ids(fact.regulatory_requirement_ids) for fact in matched
            )
            for requirement_id in requirement_ids
        ):
            return ()
        return matched
    return tuple(
        fact
        for fact in facts
        if section_evidence.intersection(_nonblank_ids(fact.evidence_ids))
        or section_material.intersection(_nonblank_ids(fact.source_material_ids))
    )


def _missing_target_codes(
    section: ContentPlanningSection,
    facts: tuple[PreparedSourceFact, ...],
) -> tuple[str, ...]:
    target = _target_code(section)
    if not section.regulatory_requirement_ids:
        return (target,)
    section_evidence = _nonblank_ids(section.evidence_ids)
    covered = {
        requirement_id
        for fact in facts
        if section_evidence.intersection(_nonblank_ids(fact.evidence_ids))
        for requirement_id in _nonblank_ids(fact.regulatory_requirement_ids)
    }
    missing = tuple(
        requirement_id
        for requirement_id in dict.fromkeys(section.regulatory_requirement_ids)
        if requirement_id not in covered
    )
    return tuple(f"{target}:{requirement_id}" for requirement_id in missing)


def _nonblank_ids(values: Iterable[object]) -> frozenset[str]:
    return frozenset(value for value in values if isinstance(value, str) and value.strip())


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
    "PreparedSourceFact",
    "PreparedDraftTarget",
    "PreparedDraftPlan",
    "prepare_draft_plan",
]
