from __future__ import annotations

from wilq.content.workflow.contracts import (
    ContentStructuredGenerationReadiness,
    ContentStructuredGenerationReadinessBlocker,
    ContentWorkItemBrowserWorkflowSnapshotResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.models import ContentWorkItem


def _browser_item(item: ContentWorkItem) -> ContentWorkItem:
    """Keep the workflow snapshot small; full HTML is served by inventory."""

    return item.model_copy(
        update={"wordpress_content_text": None, "metric_facts": []}
    )


def project_content_work_item_browser_snapshot(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentWorkItemBrowserWorkflowSnapshotResponse:
    """Expose browser-safe readiness without leaking the server execution contract."""

    generation_result = snapshot.structured_generation.structured_generation_result
    blockers = [
        ContentStructuredGenerationReadinessBlocker.model_validate(
            blocker.model_dump(mode="python")
        )
        for blocker in generation_result.blockers
    ]
    contract = generation_result.contract
    current_step = next(
        step for step in snapshot.operator_steps if step.phase == "current"
    )
    journey_blocker = None
    if (
        not blockers
        and current_step.id in {"scope", "section_map"}
        and current_step.blocker is not None
    ):
        journey_blocker = ContentStructuredGenerationReadinessBlocker(
            code=current_step.blocker.code,
            label=current_step.blocker.label,
            reason=current_step.blocker.reason,
            next_step=current_step.safe_next_step,
        )
    if blockers:
        readiness = ContentStructuredGenerationReadiness(
            status="blocked",
            blockers=blockers,
            safe_next_step=blockers[0].next_step,
        )
    elif journey_blocker is not None:
        readiness = ContentStructuredGenerationReadiness(
            status="blocked",
            blockers=[journey_blocker],
            safe_next_step=journey_blocker.next_step,
        )
    elif contract is None:
        blocker = ContentStructuredGenerationReadinessBlocker(
            code="missing_structured_draft_contract",
            label="Brakuje bezpiecznego kontraktu szkicu",
            reason=(
                "WILQ nie zbudował jeszcze zamkniętego kontraktu dla sekcji tego "
                "zadania."
            ),
            next_step=(
                "Uzupełnij brakujące dane wskazane w etapach zakresu i mapy sekcji, "
                "a potem odśwież zadanie."
            ),
        )
        readiness = ContentStructuredGenerationReadiness(
            status="blocked",
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )
    else:
        headings = [section.heading for section in contract.model_input.sections]
        normalized_headings = [heading.strip() for heading in headings]
        headings_are_editable = (
            bool(headings)
            and all(normalized_headings)
            and len(set(normalized_headings)) == len(normalized_headings)
        )
        if headings_are_editable:
            readiness = ContentStructuredGenerationReadiness(
                status="ready",
                editable_section_headings=headings,
                safe_next_step=(
                    "Wybierz zapisane sekcje, które Codex ma poprawić, i sprawdź "
                    "propozycję przed decyzją człowieka."
                ),
            )
        else:
            blocker = ContentStructuredGenerationReadinessBlocker(
                code="invalid_editable_sections",
                label="Mapa sekcji wymaga poprawy",
                reason=(
                    "Zapisana mapa nie zawiera jednoznacznych, unikalnych nagłówków "
                    "sekcji do poprawy."
                ),
                next_step=(
                    "Popraw i zapisz mapę sekcji, a następnie odśwież zadanie."
                ),
            )
            readiness = ContentStructuredGenerationReadiness(
                status="blocked",
                blockers=[blocker],
                safe_next_step=blocker.next_step,
            )

    return ContentWorkItemBrowserWorkflowSnapshotResponse(
        freshness_assessment=snapshot.freshness_assessment,
        candidate=snapshot.candidate,
        service_profile_context=snapshot.service_profile_context,
        claim_ledger=snapshot.claim_ledger,
        preflight=snapshot.preflight.model_copy(
            update={"item": _browser_item(snapshot.preflight.item)}
        ),
        sales_brief=snapshot.sales_brief.model_copy(
            update={"item": _browser_item(snapshot.sales_brief.item)}
        ),
        draft_package=snapshot.draft_package.model_copy(
            update={"item": _browser_item(snapshot.draft_package.item)}
        ),
        structured_generation_readiness=readiness,
        human_review=snapshot.human_review.model_copy(
            update={
                "item": _browser_item(snapshot.human_review.item),
                "reviewed_item": _browser_item(snapshot.human_review.reviewed_item),
            }
        ),
        wordpress_handoff=snapshot.wordpress_handoff.model_copy(
            update={"item": _browser_item(snapshot.wordpress_handoff.item)}
        ),
        measurement_window=snapshot.measurement_window.model_copy(
            update={
                "item": _browser_item(snapshot.measurement_window.item),
                "updated_item": _browser_item(snapshot.measurement_window.updated_item),
            }
        ),
        revision_workspace=snapshot.revision_workspace,
        planning_workspace=snapshot.planning_workspace,
        current_step_id=snapshot.current_step_id,
        operator_steps=snapshot.operator_steps,
    )


def revision_conflict_next_step(code: str) -> str:
    if code == "apply_in_progress":
        return (
            "Trwa zapis dokładnie zatwierdzonej wersji do WordPress. Poczekaj na wynik "
            "tej próby, odśwież snapshot i dopiero potem zapisz lub oceń nową wersję."
        )
    if code == "stale_base":
        return (
            "Na serwerze jest nowsza wersja. Zachowaj swój tekst, porównaj zmiany "
            "i dopiero potem zapisz kolejną wersję na aktualnej bazie."
        )
    if code == "stale_revision":
        return (
            "Ta wersja nie jest już najnowsza. Odśwież snapshot i sprawdź aktualną "
            "wersję bez przenoszenia starej decyzji."
        )
    if code == "stale_review":
        return (
            "Ktoś zapisał decyzję dla tej wersji wcześniej. Odśwież snapshot, "
            "przeczytaj aktualną decyzję i dopiero potem zdecyduj ponownie."
        )
    if code == "digest_mismatch":
        return (
            "Identyfikator treści nie pasuje do zapisanej wersji. Odśwież snapshot "
            "i sprawdź dokładny tekst przed decyzją."
        )
    return "Odśwież snapshot zadania i wybierz istniejącą zapisaną wersję."


__all__ = [
    "project_content_work_item_browser_snapshot",
    "revision_conflict_next_step",
]
