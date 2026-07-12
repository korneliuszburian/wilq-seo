from collections.abc import Callable
from typing import Any

from wilq.actions.metric_utils import prioritize_action_metrics, unique_values
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
Label = Callable[[Any], str]
SourceLabels = Callable[[list[str]], list[str]]
MetricLabel = Callable[[str], str]


def social_draft_input_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    source_connector_labels: SourceLabels,
    metric_fact_label: MetricLabel,
    plain_metric_value_label: Label,
    apply_state_label: Label,
) -> list[ActionPreviewCardViewModel]:
    source_inputs = [item for item in payload.get("source_inputs", []) if isinstance(item, dict)]
    connector_label = source_connector_labels([str(payload.get("connector") or "social")])[0]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(source_inputs[:4]):
        rows = [
            preview_row(
                "Źródło danych",
                source_connector_labels([str(item.get("source_connector") or "")])[0],
            ),
            preview_row(
                "Sygnał",
                metric_fact_label(str(item.get("metric_name") or "")),
            ),
            preview_row("Wartość", plain_metric_value_label(item.get("value"))),
            preview_row(
                "Kontekst",
                str(item.get("context_summary") or "sygnał źródłowy WILQ"),
            ),
        ]
        draft_constraint_labels = string_list(payload.get("draft_constraint_labels"))
        if draft_constraint_labels:
            rows.append(preview_row("Ograniczenia", ", ".join(draft_constraint_labels[:4])))
        blocked_claim_labels = string_list(payload.get("blocked_claim_labels"))
        if not blocked_claim_labels:
            blocked_claim_labels = string_list(payload.get("blocked_claims"))
        if blocked_claim_labels:
            rows.append(
                preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"social_draft_input_{index}",
                kind="social_draft_input_review",
                title_label="Materiał do posta do sprawdzenia",
                subtitle_label=f"{connector_label}: źródło do szkicu bez publikacji",
                status_label="publikacja zablokowana",
                rows=rows,
                apply_state_label=apply_state_label(False),
                system_readiness_label="wymaga sprawdzenia przez człowieka",
            )
        )
    return cards


def social_draft_actions(social_facts: list[MetricFact]) -> dict[str, ActionObject]:
    actions: dict[str, ActionObject] = {}
    social_source_facts = [fact for fact in social_facts if _is_social_source_metric(fact)]
    social_metrics = prioritize_action_metrics(
        social_source_facts,
        required_names={
            "clicks",
            "impressions",
            "issue_product_count",
            "active_users",
            "content_object_seen",
        },
    )[:10]
    evidence_ids = unique_values(
        [
            *[fact.evidence_id for fact in social_metrics],
            connector_evidence_id("linkedin"),
            connector_evidence_id("facebook"),
        ]
    )
    common_payload = {
        "mode": "prepare_only",
        "source_connectors": unique_values(
            fact.source_connector for fact in social_source_facts
        ),
        "source_metric_names": unique_values(fact.name for fact in social_source_facts),
        "draft_constraints": [
            "use_only_wilq_evidence",
            "write_in_polish",
            "no_performance_claims_without_source_metric",
            "no_publishing_without_connector_credentials",
            "require_social_history_duplicate_review",
            "require_human_review_before_apply",
        ],
        "source_inputs": _social_source_inputs(social_metrics),
        "blocked_claims": [
            "zwrot z reklam",
            "przychód",
            "wzrost konwersji",
            "wdrożona poprawka produktu",
            "brak powtórzeń historycznych postów",
        ],
        "destructive": False,
    }
    for connector_id, action_type, title in (
        (
            "linkedin",
            "linkedin_post_candidate",
            "Przygotuj propozycje postów LinkedIn z dowodów WILQ",
        ),
        (
            "facebook",
            "facebook_post_candidate",
            "Przygotuj propozycje postów Facebook z dowodów WILQ",
        ),
    ):
        action = ActionObject(
            id=f"act_prepare_{connector_id}_social_drafts",
            title=title,
            domain=OpportunityDomain.social,
            connector=connector_id,
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=evidence_ids,
            metrics=social_metrics,
            human_diagnosis=(
                "WILQ ma realne dane GSC/GA4/Merchant/WordPress, które można "
                "przełożyć na bezpieczne do sprawdzenia kierunki postów. Brak uprawnień social "
                "blokuje publikację, ale nie blokuje przygotowania materiału do oceny."
            ),
            recommended_reason=(
                "W procesie social pokaż tylko propozycje szkiców z dowodami. "
                "Nie publikuj, nie planuj wysyłki i nie dopisuj obietnic bez metryk."
            ),
            payload={
                **common_payload,
                "action_type": action_type,
                "connector": connector_id,
            },
            validation_status="not_validated",
            created_by="system_metric_seed",
        )
        actions[action.id] = action
    return actions


def _is_social_source_metric(fact: MetricFact) -> bool:
    if fact.name == "content_object_seen":
        return any(
            isinstance(fact.dimensions.get(key), str) and fact.dimensions.get(key)
            for key in ("final_canonical_url", "source_public_url", "canonical_url")
        )
    return bool(fact.name)


def _social_source_inputs(facts: list[MetricFact]) -> list[dict[str, object]]:
    inputs: list[dict[str, object]] = []
    for fact in facts[:8]:
        inputs.append(
            {
                "source_connector": fact.source_connector,
                "metric_name": fact.name,
                "value": fact.value,
                "context_summary": _social_source_context_summary(fact),
                "evidence_id": fact.evidence_id,
            }
        )
    return inputs


def _social_source_context_summary(fact: MetricFact) -> str:
    dimensions: dict[str, Any] = fact.dimensions
    if fact.source_connector == "google_merchant_center":
        return "zgłoszenie problemu danych produktowych Merchant Center"
    if fact.source_connector == "wordpress_ekologus":
        title = dimensions.get("title_or_h1")
        url = dimensions.get("canonical_url") or dimensions.get("content_url")
        parts = [str(value) for value in (title, url) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "wpis lub strona z publicznego spisu treści"
    if fact.source_connector == "google_search_console":
        query = dimensions.get("query")
        page = dimensions.get("page")
        parts = [str(value) for value in (query, page) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "sygnał z Google Search Console"
    if fact.source_connector == "google_analytics_4":
        page = dimensions.get("landing_page") or dimensions.get("page_path")
        source = dimensions.get("session_source_medium") or dimensions.get("source_medium")
        parts = [str(value) for value in (page, source) if isinstance(value, str) and value]
        return " | ".join(parts[:2]) or "sygnał z GA4"
    return "sygnał źródłowy WILQ"
