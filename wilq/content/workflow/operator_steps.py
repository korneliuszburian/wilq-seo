from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ContentWorkflowOperatorStep(BaseModel):
    id: str
    title: str
    status_label: str
    summary: str


def content_workflow_operator_steps(snapshot: Any) -> list[ContentWorkflowOperatorStep]:
    brief = snapshot.sales_brief.sales_brief_result.brief
    draft = snapshot.draft_package.draft_package_result.draft_package
    structured_contract = snapshot.structured_generation.structured_generation_result.contract
    structured_blocker = snapshot.structured_generation.structured_generation_result.blockers[0:1]
    review = snapshot.human_review.review
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    handoff_blocker = snapshot.wordpress_handoff.handoff_result.blockers[0:1]
    measurement_window = snapshot.measurement_window.measurement_window_result.window
    return [
        ContentWorkflowOperatorStep(
            id="content_preflight",
            title="Sprawdzenie pisania",
            status_label=_preflight_status_label(snapshot.preflight.preflight_verdict.status),
            summary=snapshot.preflight.preflight_verdict.next_step,
        ),
        ContentWorkflowOperatorStep(
            id="sales_brief",
            title="Plan sprzedażowy",
            status_label="gotowy do sprawdzenia" if brief else "zablokowany",
            summary=brief.buyer_problem if brief else "Brakuje planu sprzedażowego.",
        ),
        ContentWorkflowOperatorStep(
            id="draft_package",
            title="Paczka szkicu",
            status_label="konspekt do sprawdzenia" if draft else "zablokowany",
            summary="WILQ przygotowuje materiał do sprawdzenia człowieka, nie gotową publikację.",
        ),
        ContentWorkflowOperatorStep(
            id="structured_draft",
            title="Szkic treści",
            status_label="gotowy do próby" if structured_contract else "zablokowany",
            summary=_structured_draft_summary(structured_contract, structured_blocker),
        ),
        ContentWorkflowOperatorStep(
            id="human_review",
            title="Sprawdzenie człowieka",
            status_label="zatwierdzone" if review else "wymaga decyzji",
            summary=(
                "Bez zatwierdzenia człowieka przekazanie szkicu do WordPress "
                "pozostaje zablokowane."
            ),
        ),
        ContentWorkflowOperatorStep(
            id="wordpress_handoff",
            title="Szkic w WordPress",
            status_label="szkic" if handoff else "zablokowany",
            summary=_wordpress_handoff_summary(handoff, handoff_blocker),
        ),
        ContentWorkflowOperatorStep(
            id="measurement_window",
            title="Okno pomiaru",
            status_label=_measurement_window_status_label(
                None if measurement_window is None else measurement_window.status
            ),
            summary="WILQ planuje pomiar teraz, ale ocena efektu czeka na koniec obserwacji.",
        ),
    ]


def _structured_draft_summary(
    structured_contract: object | None,
    structured_blocker: list[Any],
) -> str:
    if structured_contract:
        return "WILQ może sprawdzić przygotowanie szkicu bez pisania na żywo."
    if structured_blocker:
        return str(structured_blocker[0].reason)
    return "Szkic pozostaje zablokowany, dopóki plan i twierdzenia nie przejdą bramek."


def _wordpress_handoff_summary(handoff: object | None, handoff_blocker: list[Any]) -> str:
    if handoff:
        return "WordPress dostaje tylko szkic po audycie. Publikacja nie jest automatyczna."
    if handoff_blocker:
        return str(handoff_blocker[0].reason)
    return "WordPress nie dostaje szkicu bez sprawdzenia człowieka i audytu."


def _preflight_status_label(status: str) -> str:
    labels = {
        "blocked": "zablokowane",
        "plan_allowed": "można planować",
        "brief_allowed": "można przygotować plan",
        "draft_allowed": "można przygotować szkic",
        "handoff_allowed": "można przekazać szkic",
    }
    return labels.get(status, "wymaga sprawdzenia")


def _measurement_window_status_label(status: str | None) -> str:
    if status is None:
        return "brak"
    labels = {
        "planned": "zaplanowane",
        "open": "pomiar trwa",
        "ready_for_review": "gotowe do oceny",
        "closed": "zamknięte",
    }
    return labels.get(status, "brak")

