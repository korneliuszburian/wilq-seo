from __future__ import annotations

from collections import Counter
from typing import Any

from apps.api.wilq_api import context_ads, context_compaction, context_ga4
from apps.api.wilq_api.context_scopes import SKILL_ACTION_ID_SCOPES
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
    DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    DEMAND_GEN_AD_READ_STATUS_FACT,
    DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
    DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
    DEMAND_GEN_LANDING_QUALITY_CONTRACT,
    DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
    DEMAND_GEN_READINESS_REVIEW_ACTION_ID,
    demand_gen_ad_group_ad_rows_from_facts,
    demand_gen_campaign_mode_review_rows_from_campaigns,
    demand_gen_campaign_status_label,
    demand_gen_channel_label,
    demand_gen_channel_labels,
    demand_gen_contract_has_ready_fact,
    demand_gen_contract_labels,
    demand_gen_creative_asset_rows_from_facts,
    demand_gen_landing_quality_rows_from_facts,
    demand_gen_readiness_review_payload,
)
from wilq.actions.service import demand_gen_readiness_preview_cards
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import evidence_count_label, source_connector_labels
from wilq.schemas import AdsCampaignMetricRow, DemandGenReadinessContract, MetricFact
from wilq.storage.metric_store import metric_store

DEMAND_GEN_CHANNEL_TYPES = {"DEMAND_GEN", "DISCOVERY"}
DEMAND_GEN_CAMPAIGN_ROW_LIMIT = 8

def demand_gen_diagnostics_for_context() -> dict[str, Any]:
    demand_gen_metric_facts = _demand_gen_google_ads_metric_facts()
    ga4_metric_facts = _demand_gen_ga4_metric_facts()
    ads_diagnostics = build_ads_diagnostics().model_dump(mode="json")
    ga4_diagnostics = _ga4_diagnostics_from_metric_facts(ga4_metric_facts)
    return {
        "ads_diagnostics": context_ads.compact_ads_diagnostics_for_lite_context(
            ads_diagnostics,
            allowed_decision_ids={
                "ads_review_campaign_activity",
                "ads_review_budget_context",
                "ads_review_impression_share",
            },
            allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-demand-gen-operator"],
        ),
        "ga4_diagnostics": context_ga4.compact_ga4_diagnostics_for_context(ga4_diagnostics),
        "demand_gen_readiness": _readiness_contract(
            ads_diagnostics,
            ga4_diagnostics,
            demand_gen_metric_facts,
            ga4_metric_facts,
        ).model_dump(mode="json"),
    }


def build_readiness_contract() -> DemandGenReadinessContract:
    demand_gen_metric_facts = _demand_gen_google_ads_metric_facts()
    ga4_metric_facts = _demand_gen_ga4_metric_facts()
    ads_diagnostics = build_ads_diagnostics(view="summary").model_dump(mode="json")
    ga4_diagnostics = _ga4_diagnostics_from_metric_facts(ga4_metric_facts)
    return _readiness_contract(
        ads_diagnostics,
        ga4_diagnostics,
        demand_gen_metric_facts,
        ga4_metric_facts,
    )


def _ga4_diagnostics_from_metric_facts(
    ga4_metric_facts: list[MetricFact],
) -> dict[str, Any]:
    evidence_ids = list(
        dict.fromkeys(fact.evidence_id for fact in ga4_metric_facts if fact.evidence_id)
    )
    return {
        "source_connectors": ["google_analytics_4"],
        "evidence_ids": evidence_ids,
        "metric_fact_count": len(ga4_metric_facts),
        "context_pack_compaction": {
            "metric_facts_removed": True,
            "sections_omitted": True,
            "sections_total": 0,
            "full_endpoint": "/api/ga4/diagnostics",
        },
    }


def _readiness_contract(
    ads_diagnostics: dict[str, Any],
    ga4_diagnostics: dict[str, Any],
    demand_gen_metric_facts: list[MetricFact],
    ga4_metric_facts: list[MetricFact],
) -> DemandGenReadinessContract:
    campaign_rows = [
        row
        for row in context_compaction.list_at(
            ads_diagnostics, "campaign_read_contract", "campaign_rows"
        )
        if isinstance(row, dict)
    ]
    channel_counts = _campaign_channel_counts(campaign_rows)
    campaign_channel_read_available = any(
        str(row.get("advertising_channel_type") or "").strip() for row in campaign_rows
    )
    demand_gen_campaign_rows = [
        _compact_campaign_row_for_demand_gen(row)
        for row in campaign_rows
        if _is_demand_gen_channel(row.get("advertising_channel_type"))
    ][:DEMAND_GEN_CAMPAIGN_ROW_LIMIT]
    demand_gen_ad_group_ad_rows = demand_gen_ad_group_ad_rows_from_facts(
        demand_gen_metric_facts,
    )
    demand_gen_creative_asset_rows = demand_gen_creative_asset_rows_from_facts(
        demand_gen_metric_facts,
    )
    demand_gen_campaign_row_dicts = [
        row.model_dump(mode="json") for row in demand_gen_campaign_rows
    ]
    demand_gen_landing_quality_rows = demand_gen_landing_quality_rows_from_facts(
        ga4_metric_facts,
        demand_gen_campaign_row_dicts,
    )
    demand_gen_campaign_mode_review_rows = demand_gen_campaign_mode_review_rows_from_campaigns(
        demand_gen_campaign_row_dicts,
    )
    demand_gen_ad_read_available = demand_gen_contract_has_ready_fact(
        demand_gen_metric_facts,
        status_fact_name=DEMAND_GEN_AD_READ_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    ) or bool(demand_gen_ad_group_ad_rows)
    demand_gen_creative_asset_read_available = demand_gen_contract_has_ready_fact(
        demand_gen_metric_facts,
        status_fact_name=DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    ) or bool(demand_gen_creative_asset_rows)
    evidence_ids = list(
        dict.fromkeys(
            [
                *(
                    fact.evidence_id
                    for fact in demand_gen_metric_facts
                    if fact.evidence_id and fact.name.startswith("demand_gen_")
                ),
                connector_evidence_id("google_ads"),
                connector_evidence_id("google_analytics_4"),
                *_top_level_evidence_ids(ads_diagnostics),
                *_top_level_evidence_ids(ga4_diagnostics),
            ]
        )
    )[:12]
    available_read_contracts = [
        "google_ads_campaign_activity",
        "google_ads_budget_context",
        "google_ads_impression_share_context",
        "ga4_landing_source_campaign_quality",
        DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    ]
    missing_read_contracts = [
        DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
        DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    ]
    if campaign_channel_read_available:
        available_read_contracts.append(DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
        labeled_channel_counts = demand_gen_channel_labels(channel_counts)
        channel_summary = (
            ", ".join(
                f"{label}: {channel_counts[channel]}"
                for channel, label in labeled_channel_counts.items()
            )
            or "brak rozpoznanych kanałów"
        )
        campaign_context = (
            f"WILQ ocenił {len(campaign_rows)} kampanii Ads. "
            f"Kanały w odczycie: {channel_summary}. "
            f"Kampanie Demand Gen/Discovery: {len(demand_gen_campaign_rows)}. "
        )
    else:
        missing_read_contracts.insert(0, DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
        campaign_context = "WILQ nie ma jeszcze pewnego odczytu typów kanałów kampanii Ads."
    if demand_gen_ad_read_available:
        available_read_contracts.append(DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT
        ]
    if demand_gen_creative_asset_read_available:
        available_read_contracts.append(DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT
        ]
    available_read_contracts.extend(
        [
            DEMAND_GEN_LANDING_QUALITY_CONTRACT,
            DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
        ]
    )
    available_contract_labels = demand_gen_contract_labels(available_read_contracts)
    missing_contract_labels = demand_gen_contract_labels(missing_read_contracts)
    operator_review_gates = [
        "demand_gen_specific_evidence_required",
        "human_strategy_review",
        "human_confirm_before_apply",
    ]
    missing_contract_summary = ", ".join(missing_contract_labels)
    title = (
        "Demand Gen: sprawdź istniejące kampanie bez uruchamiania zmian"
        if demand_gen_campaign_rows
        else "Demand Gen: brak kampanii do rekomendacji"
    )
    payload = demand_gen_readiness_review_payload(
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        demand_gen_campaign_rows=[row.model_dump(mode="json") for row in demand_gen_campaign_rows],
        demand_gen_ad_group_ad_rows=[
            row.model_dump(mode="json") for row in demand_gen_ad_group_ad_rows
        ],
        demand_gen_creative_asset_rows=[
            row.model_dump(mode="json") for row in demand_gen_creative_asset_rows
        ],
        demand_gen_landing_quality_rows=[
            row.model_dump(mode="json") for row in demand_gen_landing_quality_rows
        ],
        demand_gen_campaign_mode_review_rows=[
            row.model_dump(mode="json") for row in demand_gen_campaign_mode_review_rows
        ],
        available_read_contracts=available_read_contracts,
        missing_read_contracts=missing_read_contracts,
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
    )
    action_ids = [DEMAND_GEN_READINESS_REVIEW_ACTION_ID] if payload is not None else []
    payload_preview = payload["payload_preview"] if payload is not None else []
    preview_cards = demand_gen_readiness_preview_cards(payload) if payload is not None else []
    return DemandGenReadinessContract(
        status="blocked",
        title=title,
        summary=(
            f"{campaign_context} WILQ ma dowody Ads i GA4 do oceny ruchu. "
            "Odczyty reklam i kreacji Demand Gen są traktowane jako dostępne "
            "tylko wtedy, gdy API zwraca je w dostępnych danych. "
            + (
                f"Nadal brakuje danych: {missing_contract_summary}. "
                if missing_contract_summary
                else (
                    "WILQ nie wykrywa brakujących danych w tym odczycie, "
                    "ale nadal nie widzi kampanii Demand Gen/Discovery do rekomendacji. "
                )
            )
            + "To blokuje użyteczną rekomendację; nie jest to problem treści polecenia."
        ),
        metric_tiles={
            "kampanie Ads": len(campaign_rows),
            "kanały": len(channel_counts),
            "kampanie Demand Gen": len(demand_gen_campaign_rows),
            "reklamy Demand Gen": len(demand_gen_ad_group_ad_rows),
            "kreacje Demand Gen": len(demand_gen_creative_asset_rows),
            "strony wejścia Demand Gen": len(demand_gen_landing_quality_rows),
            "kontrola trybu": len(demand_gen_campaign_mode_review_rows),
            "braki": len(missing_read_contracts),
        },
        available_read_contracts=available_read_contracts,
        available_read_contract_labels=available_contract_labels,
        missing_read_contracts=missing_read_contracts,
        missing_read_contract_labels=missing_contract_labels,
        blocked_claims=DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
        source_connectors=["google_ads", "google_analytics_4"],
        source_connector_labels=source_connector_labels(["google_ads", "google_analytics_4"]),
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        action_ids=action_ids,
        operator_review_gates=operator_review_gates,
        operator_review_gate_labels=demand_gen_contract_labels(operator_review_gates),
        payload_preview=payload_preview,
        preview_cards=preview_cards,
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        campaign_channel_labels=demand_gen_channel_labels(channel_counts),
        demand_gen_campaign_rows=demand_gen_campaign_rows,
        demand_gen_ad_group_ad_rows=demand_gen_ad_group_ad_rows,
        demand_gen_creative_asset_rows=demand_gen_creative_asset_rows,
        demand_gen_landing_quality_rows=demand_gen_landing_quality_rows,
        demand_gen_campaign_mode_review_rows=demand_gen_campaign_mode_review_rows,
        next_step=(
            "Sprawdź gotowość Demand Gen w WILQ jako akcję tylko do przeglądu. "
            "Zanim WILQ pokaże propozycje uruchomienia albo zmiany trybu kampanii, "
            "potwierdź dostępność danych o jakości stron wejścia i kontroli trybu kampanii."
        ),
    )


def _top_level_evidence_ids(diagnostics: dict[str, Any]) -> list[str]:
    evidence_ids = diagnostics.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        return []
    return [str(evidence_id) for evidence_id in evidence_ids if evidence_id]


def _demand_gen_google_ads_metric_facts() -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id="google_ads", limit=5000)


def _demand_gen_ga4_metric_facts() -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id="google_analytics_4", limit=5000)


def _campaign_channel_counts(campaign_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in campaign_rows:
        channel = str(row.get("advertising_channel_type") or "UNKNOWN").strip()
        counts[channel or "UNKNOWN"] += 1
    return dict(sorted(counts.items()))


def _is_demand_gen_channel(channel: Any) -> bool:
    return str(channel or "").strip().upper() in DEMAND_GEN_CHANNEL_TYPES


def _compact_campaign_row_for_demand_gen(row: dict[str, Any]) -> AdsCampaignMetricRow:
    return AdsCampaignMetricRow(
        campaign_id=row.get("campaign_id"),
        campaign_name=row.get("campaign_name") or "campaign",
        campaign_status=row.get("campaign_status"),
        campaign_status_label=demand_gen_campaign_status_label(row.get("campaign_status")),
        advertising_channel_type=row.get("advertising_channel_type"),
        advertising_channel_type_label=demand_gen_channel_label(
            row.get("advertising_channel_type")
        ),
        clicks=row.get("clicks"),
        impressions=row.get("impressions"),
        cost_micros=row.get("cost_micros"),
        conversions=row.get("conversions"),
        conversion_value=row.get("conversion_value"),
        evidence_ids=row.get("evidence_ids") or [],
        metric_facts=[],
        missing_metrics=row.get("missing_metrics") or [],
        blocked_claims=row.get("blocked_claims") or [],
    )
