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
ContentDraftRevisionWorkspaceStatus = Literal[
    "empty",
    "unreviewed",
    "needs_changes",
    "approved",
    "rejected",
    "deferred",
]
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
    revision_workspace_status: ContentDraftRevisionWorkspaceStatus = "empty"
    revision_context_current: bool = True
    revision_bound_wordpress_handoff_ready: bool = False
    scope_review_current: bool = False
    section_map_review_current: bool = False


def build_content_workflow_operator_journey(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorJourney:
    """Project technical stages into one fail-closed marketer journey.

    A generation contract or a legacy draft-package review is not an immutable,
    review-bound text revision. Only the revision workspace can advance the journey
    from ``draft`` to ``review`` and then to the blocked ``dev_draft`` boundary.
    """
    scope_complete = facts.scope_review_current and _scope_readiness(facts) != "blocked"
    section_map_complete = scope_complete and facts.section_map_present
    current_step_id: ContentWorkflowOperatorStepId
    if not scope_complete:
        current_step_id = "scope"
    elif not section_map_complete:
        current_step_id = "section_map"
    elif (
        facts.structured_contract_present
        and facts.revision_context_current
        and facts.revision_workspace_status in {"unreviewed", "deferred"}
    ):
        current_step_id = "review"
    elif (
        facts.structured_contract_present
        and facts.revision_context_current
        and facts.revision_workspace_status == "approved"
    ):
        current_step_id = "dev_draft"
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
    review_blocker = _review_blocker(facts)
    dev_draft_blocker = _dev_draft_blocker(facts)

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
                    else "Mapa sekcji została wyliczona automatycznie. Przejdź do szkicu treści."
                ),
            ),
            ContentWorkflowOperatorStep(
                id="draft",
                title="Szkic treści",
                phase=draft_phase,
                readiness=_draft_readiness(
                    facts,
                    scope_complete=scope_complete,
                    section_map_complete=section_map_complete,
                ),
                status_label=_draft_status_label(
                    facts,
                    scope_complete=scope_complete,
                    section_map_complete=section_map_complete,
                ),
                summary=(
                    _draft_summary(facts.revision_workspace_status)
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
                can_submit=(
                    draft_phase == "current"
                    and section_map_complete
                    and facts.structured_contract_present
                ),
                blocker=(
                    _current_draft_blocker(facts)
                    if section_map_complete and facts.structured_contract_present
                    else draft_blocker
                ),
                safe_next_step=_draft_safe_next_step(
                    facts,
                    scope_complete=scope_complete,
                    section_map_complete=section_map_complete,
                ),
            ),
            ContentWorkflowOperatorStep(
                id="review",
                title="Sprawdzenie treści",
                phase=review_phase,
                readiness=_review_readiness(facts),
                status_label=_review_status_label(facts),
                summary=(
                    "Sprawdzenie musi dotyczyć dokładnie tej wersji tekstu, "
                    "która ma iść dalej."
                ),
                can_open=review_phase != "pending",
                can_submit=review_phase == "current",
                blocker=review_blocker,
                safe_next_step=_review_safe_next_step(facts),
            ),
            ContentWorkflowOperatorStep(
                id="dev_draft",
                title="Szkic na devie",
                phase=dev_draft_phase,
                readiness=(
                    "ready"
                    if facts.revision_bound_wordpress_handoff_ready
                    else "blocked"
                ),
                status_label=(
                    "zatwierdzona wersja czeka na bezpieczne przekazanie"
                    if facts.revision_workspace_status == "approved"
                    and facts.revision_context_current
                    else "czeka na sprawdzenie wersji"
                ),
                summary=(
                    "Dev pozostaje wyłącznie szkicem i nie może użyć niepowiązanego "
                    "sprawdzenia ani audytu."
                ),
                can_open=dev_draft_phase == "current",
                can_submit=(
                    dev_draft_phase == "current"
                    and facts.revision_bound_wordpress_handoff_ready
                ),
                blocker=dev_draft_blocker,
                safe_next_step=_dev_draft_safe_next_step(facts),
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
    if facts.sales_brief_signal_status == "review_required" or not facts.scope_review_current:
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
    if not facts.scope_review_current:
        return ContentWorkflowOperatorBlocker(
            code="scope_review_missing",
            label="Zakres wymaga decyzji marketera",
            reason=(
                "Strona, usługa, intencja, odbiorca i CTA nie zostały jeszcze "
                "zatwierdzone jako jedna wersja planu."
            ),
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


def _draft_readiness(
    facts: ContentWorkflowOperatorFacts,
    *,
    scope_complete: bool,
    section_map_complete: bool,
) -> ContentWorkflowOperatorStepReadiness:
    if not scope_complete or not section_map_complete or not facts.structured_contract_present:
        return "blocked"
    if not facts.revision_context_current:
        return "review_required"
    if facts.revision_workspace_status in {"empty", "needs_changes", "rejected"}:
        return "review_required"
    return "ready"


def _draft_status_label(
    facts: ContentWorkflowOperatorFacts,
    *,
    scope_complete: bool,
    section_map_complete: bool,
) -> str:
    if not scope_complete:
        return "czeka na zakres"
    if not section_map_complete:
        return "czeka na plan sekcji"
    if not facts.structured_contract_present:
        return "szkic zablokowany"
    if not facts.revision_context_current:
        return "wymaga świeżej wersji z aktualnego planu"
    labels: dict[ContentDraftRevisionWorkspaceStatus, str] = {
        "empty": "pierwsza wersja wymaga zapisu",
        "unreviewed": "wersja zapisana do sprawdzenia",
        "needs_changes": "poprawki wymagane",
        "approved": "wersja zatwierdzona",
        "rejected": "wersja odrzucona",
        "deferred": "decyzja odłożona",
    }
    return labels[facts.revision_workspace_status]


def _draft_summary(status: ContentDraftRevisionWorkspaceStatus) -> str:
    if status == "needs_changes":
        return "Wprowadź wskazane poprawki i zapisz nową wersję tekstu."
    if status == "rejected":
        return "Odrzucona wersja nie może iść dalej; dalsza praca wymaga nowej wersji."
    return "Można pracować nad szkicem, ale krok kończy dopiero zapis konkretnej wersji tekstu."


def _current_draft_blocker(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorBlocker | None:
    status = facts.revision_workspace_status
    if not facts.revision_context_current:
        return ContentWorkflowOperatorBlocker(
            code="revision_context_changed",
            label="Wersja wymaga odświeżenia",
            reason=(
                "Zapisana wersja dotyczy wcześniejszego planu sekcji albo adresu. "
                "Zatwierdź aktualny plan i wygeneruj świeżą wersję; stara pozostaje historią."
            ),
        )
    if status == "needs_changes":
        return ContentWorkflowOperatorBlocker(
            code="revision_needs_changes",
            label="Wersja wymaga poprawek",
            reason="Decyzja człowieka wskazuje poprawki przed kolejnym sprawdzeniem.",
        )
    if status == "rejected":
        return ContentWorkflowOperatorBlocker(
            code="revision_rejected",
            label="Wersja została odrzucona",
            reason="Odrzuconego tekstu nie można przekazać dalej ani zatwierdzić po cichu.",
        )
    if status == "empty":
        return ContentWorkflowOperatorBlocker(
            code="missing_revision_bound_draft",
            label="Brakuje zapisanej wersji szkicu",
            reason="Zapisz dokładny tekst, aby późniejsza decyzja dotyczyła tej wersji.",
        )
    return None


def _draft_safe_next_step(
    facts: ContentWorkflowOperatorFacts,
    *,
    scope_complete: bool,
    section_map_complete: bool,
) -> str:
    if not scope_complete:
        return facts.sales_brief_safe_next_step
    if not section_map_complete:
        return facts.section_map_safe_next_step
    if not facts.structured_contract_present:
        return facts.structured_contract_safe_next_step
    if not facts.revision_context_current:
        return (
            "Zatwierdź aktualny plan, a następnie wygeneruj świeżą pełną wersję tekstu."
        )
    if facts.revision_workspace_status == "needs_changes":
        return "Wprowadź opisane poprawki i zapisz je jako kolejną wersję."
    if facts.revision_workspace_status == "rejected":
        return "Nie przekazuj odrzuconej wersji dalej; przygotuj i zapisz nową wersję."
    return "Zapisz dokładną wersję tekstu, która ma trafić do sprawdzenia."


def _review_blocker(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorBlocker | None:
    status = facts.revision_workspace_status
    if not facts.structured_contract_present:
        return ContentWorkflowOperatorBlocker(
            code="missing_structured_draft_contract",
            label="Brakuje aktualnego kontraktu szkicu",
            reason="Nie można sprawdzić wersji bez aktualnego planu i kontraktu szkicu.",
        )
    if not facts.revision_context_current:
        return ContentWorkflowOperatorBlocker(
            code="revision_context_changed",
            label="Wersja pochodzi z wcześniejszego planu",
            reason=(
                "Plan sekcji albo adres strony zmienił się po zapisaniu tej wersji. "
                "Najpierw wygeneruj świeżą wersję z aktualnego planu."
            ),
        )
    if status == "unreviewed":
        return ContentWorkflowOperatorBlocker(
            code="missing_revision_review",
            label="Wersja czeka na decyzję",
            reason="Ta zapisana wersja nie ma jeszcze decyzji człowieka.",
        )
    if status == "deferred":
        return ContentWorkflowOperatorBlocker(
            code="revision_review_deferred",
            label="Decyzja została odłożona",
            reason="Ta sama wersja pozostaje w sprawdzeniu do czasu jawnej decyzji.",
        )
    if status in {"empty", "needs_changes", "rejected"}:
        return ContentWorkflowOperatorBlocker(
            code="missing_revision_bound_draft",
            label="Brakuje wersji gotowej do sprawdzenia",
            reason="Najpierw zapisz nową wersję tekstu powiązaną z tym zadaniem.",
        )
    return None


def _review_readiness(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorStepReadiness:
    if not facts.structured_contract_present or not facts.revision_context_current:
        return "blocked"
    status = facts.revision_workspace_status
    if status in {"unreviewed", "deferred"}:
        return "review_required"
    if status == "approved":
        return "ready"
    return "blocked"


def _review_status_label(facts: ContentWorkflowOperatorFacts) -> str:
    if not facts.structured_contract_present:
        return "czeka na aktualny plan szkicu"
    if not facts.revision_context_current:
        return "czeka na wersję w aktualnym kontekście"
    status = facts.revision_workspace_status
    labels: dict[ContentDraftRevisionWorkspaceStatus, str] = {
        "empty": "czeka na wersję szkicu",
        "unreviewed": "wersja czeka na sprawdzenie",
        "needs_changes": "czeka na poprawioną wersję",
        "approved": "wersja zatwierdzona",
        "rejected": "czeka na nową wersję",
        "deferred": "decyzja odłożona",
    }
    return labels[status]


def _review_safe_next_step(facts: ContentWorkflowOperatorFacts) -> str:
    if not facts.structured_contract_present:
        return facts.structured_contract_safe_next_step
    if not facts.revision_context_current:
        return "Wygeneruj świeżą wersję powiązaną z aktualnym planem i adresem strony."
    status = facts.revision_workspace_status
    if status == "unreviewed":
        return "Sprawdź dokładną wersję i zapisz decyzję człowieka."
    if status == "deferred":
        return "Wróć do tej samej wersji i zapisz jawną decyzję, gdy review będzie możliwe."
    if status == "approved":
        return "Zachowaj zatwierdzenie tej wersji; nie przenoś go na późniejsze zmiany."
    return "Najpierw zapisz wersję szkicu gotową do sprawdzenia."


def _dev_draft_blocker(
    facts: ContentWorkflowOperatorFacts,
) -> ContentWorkflowOperatorBlocker | None:
    status = facts.revision_workspace_status
    if not facts.structured_contract_present:
        return ContentWorkflowOperatorBlocker(
            code="missing_structured_draft_contract",
            label="Brakuje aktualnego kontraktu szkicu",
            reason="Najpierw odtwórz aktualny plan i kontrakt tekstu.",
        )
    if not facts.revision_context_current:
        return ContentWorkflowOperatorBlocker(
            code="revision_context_changed",
            label="Zatwierdzenie dotyczy wcześniejszego planu",
            reason=(
                "Zmiana planu albo adresu wymaga wygenerowania i sprawdzenia świeżej wersji."
            ),
        )
    if status == "approved" and facts.revision_bound_wordpress_handoff_ready:
        return None
    if status == "approved":
        return ContentWorkflowOperatorBlocker(
            code="missing_revision_bound_wordpress_seam",
            label="Brakuje bezpiecznego przekazania zatwierdzonej wersji",
            reason=(
                "Zatwierdzenie konkretnej wersji nie jest jeszcze zgodą na zapis do WordPress. "
                "Potrzebny jest osobny kontrakt zapisu szkicu powiązany z tą samą wersją."
            ),
        )
    if status in {"unreviewed", "deferred"}:
        return ContentWorkflowOperatorBlocker(
            code="missing_revision_bound_review",
            label="Brakuje decyzji dla zapisanej wersji",
            reason="Szkic na devie wymaga zatwierdzenia dokładnej zapisanej wersji.",
        )
    return ContentWorkflowOperatorBlocker(
        code="missing_revision_bound_draft",
        label="Brakuje wersji gotowej do przekazania",
        reason="Najpierw zapisz i zatwierdź dokładną wersję tekstu.",
    )


def _dev_draft_safe_next_step(facts: ContentWorkflowOperatorFacts) -> str:
    status = facts.revision_workspace_status
    if not facts.structured_contract_present:
        return facts.structured_contract_safe_next_step
    if not facts.revision_context_current:
        return "Wygeneruj i sprawdź świeżą wersję powiązaną z aktualnym planem strony."
    if status == "approved":
        if facts.revision_bound_wordpress_handoff_ready:
            return (
                "Przejdź przez podgląd, review, potwierdzenie i kontrolę bezpieczeństwa "
                "tej samej wersji; zapis pozostaje wyłącznie szkicem."
            )
        return (
            "Zatrzymaj zapis do WordPress. Najpierw przygotuj podgląd tej samej wersji "
            "i jawnie zatwierdź zapis wyłącznie jako szkic."
        )
    if status in {"unreviewed", "deferred"}:
        return "Najpierw zapisz decyzję człowieka dla dokładnej wersji tekstu."
    return "Najpierw zapisz wersję szkicu i przeprowadź jej dokładne sprawdzenie."


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
