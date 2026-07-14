from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, model_validator

ContentWorkflowOperatorStepId = Literal[
    "scope",
    "section_map",
    "draft",
    "review",
    "dev_draft",
]
ContentWorkflowOperatorStepPhase = Literal["complete", "current", "pending"]
ContentWorkflowOperatorStepReadiness = Literal["ready", "review_required", "blocked"]
ContentWorkflowSalesBriefSignalStatus = Literal["strong", "review_required", "thin"]
CONTENT_WORKFLOW_OPERATOR_STEP_ORDER: tuple[ContentWorkflowOperatorStepId, ...] = (
    "scope",
    "section_map",
    "draft",
    "review",
    "dev_draft",
)


class ContentWorkflowOperatorBlocker(BaseModel):
    code: str
    label: str
    reason: str


class ContentWorkflowOperatorStep(BaseModel):
    id: ContentWorkflowOperatorStepId
    title: str
    phase: ContentWorkflowOperatorStepPhase
    readiness: ContentWorkflowOperatorStepReadiness
    status_label: str
    summary: str
    can_open: bool
    can_submit: bool
    blocker: ContentWorkflowOperatorBlocker | None = None
    safe_next_step: str


ContentWorkflowOperatorSteps = tuple[
    ContentWorkflowOperatorStep,
    ContentWorkflowOperatorStep,
    ContentWorkflowOperatorStep,
    ContentWorkflowOperatorStep,
    ContentWorkflowOperatorStep,
]


class ContentWorkflowOperatorJourney(BaseModel):
    current_step_id: ContentWorkflowOperatorStepId
    steps: ContentWorkflowOperatorSteps

    @model_validator(mode="after")
    def require_canonical_steps(self) -> ContentWorkflowOperatorJourney:
        validate_content_workflow_operator_steps(
            current_step_id=self.current_step_id,
            steps=self.steps,
        )
        return self


def validate_content_workflow_operator_steps(
    *,
    current_step_id: ContentWorkflowOperatorStepId,
    steps: ContentWorkflowOperatorSteps,
) -> None:
    """Enforce the public five-step journey contract at every model boundary."""
    step_ids = tuple(step.id for step in steps)
    if len(set(step_ids)) != len(step_ids):
        raise ValueError("Content workflow operator step IDs must be unique.")
    if step_ids != CONTENT_WORKFLOW_OPERATOR_STEP_ORDER:
        raise ValueError("Content workflow operator steps must use the canonical order.")

    current_steps = [step for step in steps if step.phase == "current"]
    if len(current_steps) != 1:
        raise ValueError("Content workflow operator journey must have exactly one current step.")
    if current_steps[0].id != current_step_id:
        raise ValueError("Content workflow current_step_id must match the current step.")


@dataclass(frozen=True)
class ContentWorkflowOperatorFacts:
    sales_brief_present: bool
    sales_brief_signal_status: ContentWorkflowSalesBriefSignalStatus | None
    sales_brief_signal_reason: str | None
    sales_brief_safe_next_step: str
    sales_brief_blocker: ContentWorkflowOperatorBlocker | None
    section_map_present: bool
    section_map_blocker: ContentWorkflowOperatorBlocker | None
    section_map_safe_next_step: str
    structured_contract_present: bool
    structured_contract_blocker: ContentWorkflowOperatorBlocker | None
    structured_contract_safe_next_step: str


def build_content_workflow_operator_journey(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorJourney:
    """Project technical stages into one fail-closed marketer journey.

    A generation contract or a legacy draft-package review is not an immutable,
    review-bound text revision. Until that contract exists, the journey may reach
    ``draft`` but cannot advance to ``review`` or ``dev_draft``.
    """
    scope_complete = _scope_readiness(facts) != "blocked"
    section_map_complete = scope_complete and facts.section_map_present
    current_step_id: ContentWorkflowOperatorStepId
    if not scope_complete:
        current_step_id = "scope"
    elif not section_map_complete:
        current_step_id = "section_map"
    else:
        current_step_id = "draft"

    scope_phase = _phase_for("scope", current_step_id)
    section_map_phase = _phase_for("section_map", current_step_id)
    draft_phase = _phase_for("draft", current_step_id)
    review_phase = _phase_for("review", current_step_id)
    dev_draft_phase = _phase_for("dev_draft", current_step_id)

    scope_blocker = _scope_blocker(facts)
    section_map_blocker = _section_map_blocker(
        facts,
        scope_complete=scope_complete,
    )
    draft_blocker = _draft_blocker(
        facts,
        scope_complete=scope_complete,
        section_map_complete=section_map_complete,
    )
    review_blocker = ContentWorkflowOperatorBlocker(
        code="missing_revision_bound_draft",
        label="Brakuje zapisanej wersji szkicu",
        reason=(
            "Review paczki szkicu nie zatwierdza konkretnego tekstu. WILQ potrzebuje "
            "wersji szkicu powiązanej z późniejszą decyzją człowieka."
        ),
    )
    dev_draft_blocker = ContentWorkflowOperatorBlocker(
        code="missing_revision_bound_review",
        label="Brakuje review konkretnej wersji",
        reason=(
            "Szkic na devie nie może zostać odblokowany przez stare review paczki ani "
            "niepowiązany audyt."
        ),
    )

    return ContentWorkflowOperatorJourney(
        current_step_id=current_step_id,
        steps=(
            ContentWorkflowOperatorStep(
                id="scope",
                title="Zakres i cel",
                phase=scope_phase,
                readiness=_scope_readiness(facts),
                status_label=_scope_status_label(facts),
                summary=(
                    "Strona, intencja, usługa i ograniczenia twierdzeń są zebrane w jednym briefie."
                    if scope_complete
                    else "Najpierw trzeba ustalić bezpieczny zakres pracy nad treścią."
                ),
                can_open=scope_phase != "pending",
                can_submit=False,
                blocker=scope_blocker,
                safe_next_step=facts.sales_brief_safe_next_step,
            ),
            ContentWorkflowOperatorStep(
                id="section_map",
                title="Plan sekcji",
                phase=section_map_phase,
                readiness="ready" if section_map_complete else "blocked",
                status_label=(
                    "plan sekcji gotowy"
                    if section_map_complete
                    else ("czeka na zakres" if not scope_complete else "plan sekcji zablokowany")
                ),
                summary=(
                    "Sekcje szkicu mają cel i mapę dowodów."
                    if section_map_complete
                    else (
                        "Plan sekcji pozostaje zablokowany do domknięcia zakresu i celu."
                        if not scope_complete
                        else "Nie ma jeszcze bezpiecznego planu sekcji i dowodów."
                    )
                ),
                can_open=section_map_phase != "pending",
                can_submit=False,
                blocker=section_map_blocker,
                safe_next_step=(
                    facts.sales_brief_safe_next_step
                    if not scope_complete
                    else facts.section_map_safe_next_step
                ),
            ),
            ContentWorkflowOperatorStep(
                id="draft",
                title="Szkic treści",
                phase=draft_phase,
                readiness=(
                    "review_required"
                    if section_map_complete and facts.structured_contract_present
                    else "blocked"
                ),
                status_label=(
                    "wersja robocza wymaga zapisu"
                    if section_map_complete and facts.structured_contract_present
                    else (
                        "czeka na zakres"
                        if not scope_complete
                        else (
                            "czeka na plan sekcji"
                            if not section_map_complete
                            else "szkic zablokowany"
                        )
                    )
                ),
                summary=(
                    "Można pracować nad szkicem, ale krok kończy dopiero zapis "
                    "konkretnej wersji tekstu."
                    if section_map_complete and facts.structured_contract_present
                    else (
                        "Szkic pozostaje zablokowany do domknięcia zakresu i celu."
                        if not scope_complete
                        else (
                            "Szkic pozostaje zablokowany do domknięcia planu sekcji."
                            if not section_map_complete
                            else (
                                "WILQ nie ma jeszcze bezpiecznego kontraktu przygotowania szkicu."
                            )
                        )
                    )
                ),
                can_open=draft_phase != "pending",
                can_submit=False,
                blocker=draft_blocker,
                safe_next_step=(
                    "Przygotuj roboczy tekst. Nie uznawaj kroku za zakończony, dopóki "
                    "WILQ nie zapisze konkretnej wersji szkicu do późniejszego review."
                    if section_map_complete and facts.structured_contract_present
                    else (
                        facts.sales_brief_safe_next_step
                        if not scope_complete
                        else (
                            facts.section_map_safe_next_step
                            if not section_map_complete
                            else facts.structured_contract_safe_next_step
                        )
                    )
                ),
            ),
            ContentWorkflowOperatorStep(
                id="review",
                title="Sprawdzenie treści",
                phase=review_phase,
                readiness="blocked",
                status_label="czeka na wersję szkicu",
                summary="Review musi dotyczyć dokładnie tej wersji tekstu, która ma iść dalej.",
                can_open=False,
                can_submit=False,
                blocker=review_blocker,
                safe_next_step="Najpierw zapisz wersję szkicu powiązaną z tym work itemem.",
            ),
            ContentWorkflowOperatorStep(
                id="dev_draft",
                title="Szkic na devie",
                phase=dev_draft_phase,
                readiness="blocked",
                status_label="czeka na review wersji",
                summary=(
                    "Dev pozostaje draft-only i nie może użyć niepowiązanego review ani audytu."
                ),
                can_open=False,
                can_submit=False,
                blocker=dev_draft_blocker,
                safe_next_step=(
                    "Najpierw zatwierdź konkretną wersję tekstu, potem przejdź przez "
                    "ActionObject i podgląd zapisu draft-only."
                ),
            ),
        ),
    )


def _phase_for(
    step_id: ContentWorkflowOperatorStepId,
    current_step_id: ContentWorkflowOperatorStepId,
) -> ContentWorkflowOperatorStepPhase:
    if step_id == current_step_id:
        return "current"
    if CONTENT_WORKFLOW_OPERATOR_STEP_ORDER.index(
        step_id
    ) < CONTENT_WORKFLOW_OPERATOR_STEP_ORDER.index(current_step_id):
        return "complete"
    return "pending"


def _scope_readiness(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorStepReadiness:
    if not facts.sales_brief_present or facts.sales_brief_signal_status in {None, "thin"}:
        return "blocked"
    if facts.sales_brief_signal_status == "review_required":
        return "review_required"
    return "ready"


def _scope_status_label(facts: ContentWorkflowOperatorFacts) -> str:
    readiness = _scope_readiness(facts)
    labels: dict[ContentWorkflowOperatorStepReadiness, str] = {
        "ready": "zakres gotowy",
        "review_required": "zakres wymaga review",
        "blocked": "zakres zablokowany",
    }
    return labels[readiness]


def _scope_blocker(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorBlocker | None:
    if facts.sales_brief_signal_status == "review_required":
        return ContentWorkflowOperatorBlocker(
            code="scope_review_required",
            label="Zakres wymaga review",
            reason=facts.sales_brief_signal_reason
            or "Część wiedzy albo twierdzeń wymaga decyzji człowieka.",
        )
    if facts.sales_brief_signal_status == "thin":
        return ContentWorkflowOperatorBlocker(
            code="scope_signal_thin",
            label="Za mało dowodów do bezpiecznego zakresu",
            reason=facts.sales_brief_signal_reason
            or "Brief nie ma jeszcze wystarczającego śladu dowodowego.",
        )
    return facts.sales_brief_blocker


def _draft_blocker(
    facts: ContentWorkflowOperatorFacts,
    *,
    scope_complete: bool,
    section_map_complete: bool,
) -> ContentWorkflowOperatorBlocker:
    if not scope_complete:
        return _prerequisite_blocker("scope", "Najpierw domknij zakres i cel.")
    if not section_map_complete:
        return _prerequisite_blocker(
            "section_map",
            "Najpierw domknij plan sekcji i przypisane dowody.",
        )
    if not facts.structured_contract_present:
        return facts.structured_contract_blocker or ContentWorkflowOperatorBlocker(
            code="missing_structured_draft_contract",
            label="Brakuje kontraktu szkicu",
            reason="Najpierw trzeba domknąć bezpieczny plan sekcji i twierdzeń.",
        )
    return ContentWorkflowOperatorBlocker(
        code="missing_revision_bound_draft",
        label="Brakuje zapisanej wersji szkicu",
        reason=(
            "Kontrakt generacji jest gotowy, ale nie istnieje jeszcze wersja tekstu "
            "z identyfikatorem, którą można później jednoznacznie sprawdzić."
        ),
    )


def _section_map_blocker(
    facts: ContentWorkflowOperatorFacts,
    *,
    scope_complete: bool,
) -> ContentWorkflowOperatorBlocker | None:
    if not scope_complete:
        return _prerequisite_blocker("scope", "Najpierw domknij zakres i cel.")
    if facts.section_map_present:
        return None
    return facts.section_map_blocker or ContentWorkflowOperatorBlocker(
        code="missing_section_map",
        label="Brakuje planu sekcji",
        reason="Najpierw przygotuj plan sekcji i przypisz do nich dowody.",
    )


def _prerequisite_blocker(code: str, reason: str) -> ContentWorkflowOperatorBlocker:
    return ContentWorkflowOperatorBlocker(
        code=f"blocked_by_{code}",
        label="Najpierw zakończ wcześniejszy krok",
        reason=reason,
    )
