from __future__ import annotations

from wilq.schemas import ActionRisk, AdsCustomSegmentsReadContract, AdsDiagnosticSection


def build_custom_segments_section(
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for candidate in custom_segments_read_contract.candidates
        for fact in candidate.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_custom_segments",
        title="Segmenty z wyszukiwanych haseł",
        status=custom_segments_read_contract.status,
        summary=custom_segments_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować akcji do sprawdzenia segmentów tylko z realnych "
            "haseł źródłowych. Wzbogacenie Keyword Planner jest dodatkowym kontekstem, "
            "ale rozmiar odbiorców i skuteczność pozostają zablokowane bez osobnych "
            "danych."
        ),
        next_step=custom_segments_read_contract.next_step,
        source_connectors=custom_segments_read_contract.source_connectors,
        evidence_ids=custom_segments_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=custom_segments_read_contract.action_ids,
        blocked_claims=custom_segments_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )
