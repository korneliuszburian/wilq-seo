from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.measurement.outcome import ContentMeasurementOutcomeInterpretation
from wilq.content.measurement.window import ContentMeasurementWindow

ContentLearningProposalVerdict = Literal[
    "noisy_inconclusive",
    "directional_improvement",
    "likely_underperformance",
    "measured_success",
]


class ContentLearningProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    measurement_window_id: str
    measurement_outcome_id: str
    verdict: ContentLearningProposalVerdict
    review_status: Literal["review_required"] = "review_required"
    decision_summary: str
    proposed_learning: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    metric_fact_ids: list[str] = Field(default_factory=list)
    refresh_run_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    human_acceptance_required: Literal[True] = True
    knowledge_update_allowed: Literal[False] = False
    queue_update_allowed: Literal[False] = False
    success_claim_allowed: Literal[False] = False


def build_content_learning_proposal(
    *,
    window: ContentMeasurementWindow,
    outcome: ContentMeasurementOutcomeInterpretation,
) -> ContentLearningProposal:
    if window.status != "closed":
        raise ValueError("Measurement window is not closed")
    if outcome.measurement_window_id != window.id or outcome.work_item_id != window.work_item_id:
        raise ValueError("Measurement outcome does not match the closed window")
    if outcome.status in {"not_ready", "insufficient_data"}:
        raise ValueError("Measurement outcome is not sufficient for a learning proposal")
    verdict = cast(ContentLearningProposalVerdict, outcome.status)
    return ContentLearningProposal(
        id=f"learning_proposal_{outcome.id}",
        work_item_id=window.work_item_id,
        measurement_window_id=window.id,
        measurement_outcome_id=outcome.id,
        verdict=verdict,
        decision_summary=_decision_summary(verdict),
        proposed_learning=_proposed_learning(verdict),
        evidence_ids=_unique([*window.evidence_ids, *outcome.evidence_ids]),
        source_connectors=_unique(
            [
                *outcome.source_connectors,
                *(
                    []
                    if window.publication_source_connector is None
                    else [window.publication_source_connector]
                ),
            ]
        ),
        metric_fact_ids=outcome.metric_fact_ids,
        refresh_run_ids=_unique(
            [
                *outcome.refresh_run_ids,
                *(
                    []
                    if window.publication_refresh_run_id is None
                    else [window.publication_refresh_run_id]
                ),
            ]
        ),
        limitations=outcome.limitations,
    )


def _decision_summary(verdict: ContentLearningProposalVerdict) -> str:
    return {
        "noisy_inconclusive": "Pomiar nie daje jeszcze jednoznacznej lekcji.",
        "directional_improvement": "Pomiar pokazuje kierunkowo pozytywny sygnał do przeglądu.",
        "likely_underperformance": "Pomiar wskazuje ryzyko słabszego wyniku do przeglądu.",
        "measured_success": "Pomiar pokazuje pozytywny sygnał, który nadal wymaga akceptacji.",
    }[verdict]


def _proposed_learning(verdict: ContentLearningProposalVerdict) -> str:
    return {
        "noisy_inconclusive": (
            "Nie zmieniaj wiedzy ani kolejki; zbierz kolejny porównywalny okres."
        ),
        "directional_improvement": (
            "Sprawdź, czy kierunek zmiany warto zachować jako hipotezę dla kolejnej rewizji."
        ),
        "likely_underperformance": (
            "Sprawdź brief, intencję i CTA przed zaproponowaniem kolejnej rewizji."
        ),
        "measured_success": (
            "Sprawdź, czy pozytywny sygnał warto zachować jako hipotezę, bez przypisywania "
            "pełnej przyczynowości."
        ),
    }[verdict]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
