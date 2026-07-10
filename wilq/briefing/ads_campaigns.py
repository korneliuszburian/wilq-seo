from __future__ import annotations

from wilq.actions.google_ads.campaign_review import CAMPAIGN_REVIEW_ACTION_ID
from wilq.schemas import (
    ActionRisk,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsDerivedKpiReadContract,
    AdsDiagnosticSection,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_business_context_section(
    business_context_read_contract: AdsBusinessContextReadContract,
) -> AdsDiagnosticSection:
    return AdsDiagnosticSection(
        id="ads_business_context",
        title="Kontekst biznesowy Google Ads",
        status=business_context_read_contract.status,
        summary=business_context_read_contract.summary,
        diagnosis=(
            "WILQ oddziela wyliczone wskaźniki od decyzji biznesowej. Marża, cel biznesowy, "
            "cel budżetu, docelowy zwrot z reklam i docelowy koszt pozyskania celu "
            "są kontraktem operatora, nie danymi z Google Ads."
        ),
        next_step=business_context_read_contract.next_step,
        source_connectors=business_context_read_contract.source_connectors,
        evidence_ids=business_context_read_contract.evidence_ids,
        action_ids=business_context_read_contract.target_interpretation.action_ids,
        blocked_claims=business_context_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_derived_kpi_section(
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
) -> AdsDiagnosticSection:
    return AdsDiagnosticSection(
        id="ads_derived_kpi",
        title="Wyliczone wskaźniki kampanii Google Ads",
        status=derived_kpi_read_contract.status,
        summary=derived_kpi_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać współczynnik kliknięć, koszt kliknięcia, współczynnik konwersji, "
            "koszt pozyskania celu i zwrot z reklam jako obliczenia z bieżących danych kampanii. "
            "To nie jest jeszcze diagnoza rentowności, ocena zmarnowanego budżetu "
            "ani zgoda na zmianę budżetu."
        ),
        next_step=derived_kpi_read_contract.next_step,
        source_connectors=derived_kpi_read_contract.source_connectors,
        evidence_ids=derived_kpi_read_contract.evidence_ids,
        action_ids=[],
        blocked_claims=derived_kpi_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_campaign_overview_section(
    action_ids: list[str],
    campaign_read_contract: AdsCampaignReadContract,
    *,
    fallback_evidence_ids: list[str],
) -> AdsDiagnosticSection:
    campaign_facts = [
        fact for row in campaign_read_contract.campaign_rows for fact in row.metric_facts
    ]
    campaign_action_ids = [
        action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID
    ]
    if campaign_facts:
        return AdsDiagnosticSection(
            id="ads_campaign_overview",
            title="Aktywność kampanii Google Ads",
            status="ready",
            summary=campaign_read_contract.summary,
            diagnosis=(
                "WILQ ma wymiarowe wiersze aktywności kampanii z Google Ads. To wystarcza "
                "do pierwszego przeglądu aktywności kampanii, ale nadal nie wystarcza "
                "do diagnozy kosztu pozyskania celu, zwrotu z reklam, "
                "strat budżetu na zapytaniach ani wykluczeń."
            ),
            next_step=campaign_read_contract.next_step,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=campaign_read_contract.evidence_ids,
            metric_facts=campaign_facts[:12],
            action_ids=campaign_action_ids,
            blocked_claims=campaign_read_contract.blocked_claims,
            risk=ActionRisk.low,
        )
    return AdsDiagnosticSection(
        id="ads_campaign_overview",
        title="Aktywność kampanii Google Ads",
        status="blocked",
        summary="Brak metryk kampanii z Google Ads.",
        diagnosis=(
            "Nie ma aktualnych wierszy kampanii, więc dashboard nie pokazuje kosztu ani trendów "
            "kampanii. To jest blokada, nie puste miejsce na estymację."
        ),
        next_step="Napraw OAuth i wykonaj odczyt danych Google Ads.",
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=fallback_evidence_ids,
        action_ids=[],
        blocked_claims=["wydatki reklamowe", "kliknięcia", "wyświetlenia", "trend kampanii"],
        risk=ActionRisk.medium,
    )
