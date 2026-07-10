from __future__ import annotations

from wilq.schemas import ActionRisk, AdsDiagnosticSection, AdsNegativeKeywordsReadContract


def build_negative_keywords_section(
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for candidate in negative_keywords_read_contract.candidates
        for fact in candidate.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_negative_keyword_safety",
        title="Ocena wykluczeń z wyszukiwanych haseł",
        status=negative_keywords_read_contract.status,
        summary=negative_keywords_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować tylko kolejkę oceny. Zero konwersji w bieżących "
            "dowodach nie jest jeszcze dowodem przepalonego budżetu ani zgodą na wykluczenie."
        ),
        next_step=negative_keywords_read_contract.next_step,
        source_connectors=negative_keywords_read_contract.source_connectors,
        evidence_ids=negative_keywords_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=negative_keywords_read_contract.action_ids,
        blocked_claims=negative_keywords_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )
