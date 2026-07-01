from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.measurement.window import (
    ContentMeasurementMetric,
    ContentMeasurementWindow,
    content_measurement_window_outcome_allowed,
)

ContentMeasurementOutcomeStatus = Literal[
    "not_ready",
    "insufficient_data",
    "noisy_inconclusive",
    "directional_improvement",
    "likely_underperformance",
    "measured_success",
]


class ContentMeasurementObservedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: ContentMeasurementMetric
    baseline_value: float | None = None
    observation_value: float | None = None
    source_connector: str
    evidence_ids: list[str] = Field(default_factory=list)


class ContentMeasurementOutcomeInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    measurement_window_id: str
    status: ContentMeasurementOutcomeStatus
    status_label: str
    conclusion: str
    confidence: Literal["none", "low", "medium", "high"]
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    success_claim_allowed: bool = False
    queue_feedback_allowed: bool = False
    safe_next_step: str


def interpret_content_measurement_outcome(
    *,
    window: ContentMeasurementWindow,
    observed_metrics: list[ContentMeasurementObservedMetric],
    as_of: date,
) -> ContentMeasurementOutcomeInterpretation:
    if not content_measurement_window_outcome_allowed(window, as_of=as_of):
        return _interpretation(
            window=window,
            status="not_ready",
            status_label="Za wcześnie na ocenę efektu",
            conclusion=(
                "WILQ może zbierać dane, ale nie wolno jeszcze mówić o sukcesie "
                "ani porażce treści."
            ),
            confidence="none",
            limitations=["Okno obserwacji nie jest jeszcze gotowe do oceny."],
            safe_next_step="Wróć do interpretacji po earliest_verdict_date.",
        )

    usable_metrics = [metric for metric in observed_metrics if _metric_has_required_data(metric)]
    if not usable_metrics:
        return _interpretation(
            window=window,
            status="insufficient_data",
            status_label="Za mało danych",
            conclusion=(
                "Okno pomiaru jest gotowe, ale WILQ nie ma metryk z dowodami, "
                "które pozwalają uczciwie ocenić wynik treści."
            ),
            confidence="low",
            limitations=["Brakuje wartości bazowej, wartości po obserwacji albo evidence ID."],
            safe_next_step="Odśwież źródła pomiaru i wróć do oceny.",
        )

    return _interpret_ready_outcome(window=window, usable_metrics=usable_metrics)


def _interpret_ready_outcome(
    *,
    window: ContentMeasurementWindow,
    usable_metrics: list[ContentMeasurementObservedMetric],
) -> ContentMeasurementOutcomeInterpretation:
    deltas = [_relative_delta(metric) for metric in usable_metrics]
    positive = sum(1 for delta in deltas if delta >= 0.1)
    negative = sum(1 for delta in deltas if delta <= -0.1)
    flat = len(deltas) - positive - negative
    evidence_ids = _unique(
        [evidence for metric in usable_metrics for evidence in metric.evidence_ids]
    )
    source_connectors = _unique([metric.source_connector for metric in usable_metrics])

    if flat == len(deltas):
        return _interpretation(
            window=window,
            status="noisy_inconclusive",
            status_label="Wynik niejednoznaczny",
            conclusion=(
                "Zmiany są zbyt małe albo zbyt płaskie, żeby robić z nich "
                "wniosek o sukcesie lub porażce treści."
            ),
            confidence="low",
            evidence_ids=evidence_ids,
            source_connectors=source_connectors,
            limitations=["Brak wyraźnego kierunku zmiany w obserwowanych metrykach."],
            safe_next_step="Zostaw treść w obserwacji albo sprawdź dodatkowe źródła.",
        )

    if positive == len(deltas):
        return _interpretation(
            window=window,
            status="measured_success",
            status_label="Zmiana pozytywna w mierzonych danych",
            conclusion=(
                "Wszystkie użyte metryki poprawiły się względem baseline. To pozwala "
                "mówić o zmierzonym wyniku, ale bez udawania pełnej przyczynowości."
            ),
            confidence="high" if len(deltas) > 1 else "medium",
            evidence_ids=evidence_ids,
            source_connectors=source_connectors,
            limitations=[
                "Interpretacja pokazuje zmianę w oknie pomiaru, nie pełny dowód przyczyny."
            ],
            success_claim_allowed=True,
            queue_feedback_allowed=True,
            safe_next_step="Zapisz wynik jako pozytywny sygnał i użyj go w kolejnych decyzjach.",
        )

    if positive > negative:
        return _interpretation(
            window=window,
            status="directional_improvement",
            status_label="Kierunkowo lepiej",
            conclusion=(
                "Część metryk poprawiła się, ale obraz nie jest wystarczająco czysty "
                "na claim sukcesu."
            ),
            confidence="medium",
            evidence_ids=evidence_ids,
            source_connectors=source_connectors,
            limitations=["Nie wszystkie metryki potwierdzają tę samą zmianę."],
            queue_feedback_allowed=True,
            safe_next_step="Użyj tego jako sygnału do kolejki, nie jako publicznego claimu.",
        )

    if negative > positive:
        return _interpretation(
            window=window,
            status="likely_underperformance",
            status_label="Prawdopodobnie słabszy wynik",
            conclusion=(
                "Więcej metryk pogorszyło się niż poprawiło, więc treść wymaga "
                "przeglądu albo kolejnej poprawki."
            ),
            confidence="medium",
            evidence_ids=evidence_ids,
            source_connectors=source_connectors,
            limitations=[
                "To jest sygnał operacyjny, nie dowód, że sama treść była przyczyną spadku."
            ],
            queue_feedback_allowed=True,
            safe_next_step="Wróć do briefu, intencji i jakości CTA przed kolejną zmianą.",
        )

    return _interpretation(
        window=window,
        status="noisy_inconclusive",
        status_label="Wynik mieszany",
        conclusion="Metryki pokazują mieszany obraz, więc WILQ nie powinien claimować efektu.",
        confidence="low",
        evidence_ids=evidence_ids,
        source_connectors=source_connectors,
        limitations=["Tyle samo sygnałów wspiera poprawę i pogorszenie."],
        safe_next_step="Sprawdź dodatkowe dane albo wydłuż obserwację.",
    )


def _metric_has_required_data(metric: ContentMeasurementObservedMetric) -> bool:
    return (
        metric.baseline_value is not None
        and metric.observation_value is not None
        and bool(metric.evidence_ids)
    )


def _relative_delta(metric: ContentMeasurementObservedMetric) -> float:
    if metric.baseline_value is None or metric.observation_value is None:
        return 0.0
    if metric.baseline_value == 0:
        return 1.0 if metric.observation_value > 0 else 0.0
    return (metric.observation_value - metric.baseline_value) / abs(metric.baseline_value)


def _interpretation(
    *,
    window: ContentMeasurementWindow,
    status: ContentMeasurementOutcomeStatus,
    status_label: str,
    conclusion: str,
    confidence: Literal["none", "low", "medium", "high"],
    limitations: list[str],
    safe_next_step: str,
    evidence_ids: list[str] | None = None,
    source_connectors: list[str] | None = None,
    success_claim_allowed: bool = False,
    queue_feedback_allowed: bool = False,
) -> ContentMeasurementOutcomeInterpretation:
    return ContentMeasurementOutcomeInterpretation(
        id=f"measurement_outcome_{window.id}",
        work_item_id=window.work_item_id,
        measurement_window_id=window.id,
        status=status,
        status_label=status_label,
        conclusion=conclusion,
        confidence=confidence,
        evidence_ids=evidence_ids or [],
        source_connectors=source_connectors or [],
        limitations=limitations,
        success_claim_allowed=success_claim_allowed,
        queue_feedback_allowed=queue_feedback_allowed,
        safe_next_step=safe_next_step,
    )


def _unique(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values
