from pathlib import Path
from typing import cast

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning import dynamic_input
from wilq.content.planning.input_sources import ContentPlanningInventory
from wilq.content.planning.internal_link_candidates import (
    load_content_internal_link_candidates,
)
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.schemas import MetricFact
from wilq.storage.metric_store import DuckDbMetricStore


class _MetricStore:
    def __init__(self, path: Path, facts: list[MetricFact]) -> None:
        self.path = path
        self.facts = facts

    def list_metric_facts_for_content_url(
        self,
        connector_ids: list[str],
        content_url: str,
        *,
        content_path: str,
    ) -> list[MetricFact]:
        assert connector_ids == ["wordpress_ekologus"]
        assert content_url.startswith("https://www.ekologus.pl/")
        assert content_path.startswith("/")
        return self.facts


def _fact(
    evidence_id: str,
    target_url: str,
    *,
    status: str = "published",
) -> MetricFact:
    return MetricFact(
        name="content_object_seen",
        value=1,
        period="connector_refresh",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        dimensions={
            "content_url": target_url,
            "canonical_url": target_url,
            "status": status,
            "title_or_h1": "Kontakt",
        },
    )


def _store(tmp_path: Path, facts: list[MetricFact]) -> DuckDbMetricStore:
    store_path = tmp_path / "metrics.duckdb"
    store_path.touch()
    return cast(DuckDbMetricStore, _MetricStore(store_path, facts))


def test_internal_link_candidates_require_exact_target_evidence_and_are_deduplicated(
    tmp_path: Path,
) -> None:
    exact = _fact("ev_wp_contact", "https://www.ekologus.pl/kontakt/")
    swapped = _fact("ev_wp_about", "https://www.ekologus.pl/o-nas/")
    store = _store(tmp_path, [swapped, exact])

    candidates = load_content_internal_link_candidates(
        [
            "https://ekologus.pl/kontakt/",
            "https://ekologus.pl/kontakt/",
            "https://example.com/kontakt/",
            "https://www.ekologus.pl/nieznany/",
        ],
        allowed_evidence_ids=["ev_wp_contact", "ev_wp_about"],
        store=store,
    )

    assert [candidate.model_dump() for candidate in candidates] == [
        {
            "target_url": "https://www.ekologus.pl/kontakt",
            "anchor_hint": "Kontakt",
            "source_connector": "wordpress_ekologus",
            "evidence_ids": ["ev_wp_contact"],
        }
    ]
    assert load_content_internal_link_candidates(
        ["https://ekologus.pl/kontakt/"],
        allowed_evidence_ids=["ev_wp_about"],
        store=store,
    ) == []
    assert load_content_internal_link_candidates(
        ["https://ekologus.pl/kontakt/"],
        allowed_evidence_ids=[],
        store=store,
    ) == []


def test_dynamic_input_keeps_only_loader_bound_candidates_in_its_digest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    contact = _fact("ev_wp_contact", "https://www.ekologus.pl/kontakt/")
    swapped = _fact("ev_wp_about", "https://www.ekologus.pl/o-nas/")
    store = _store(tmp_path, [swapped, contact])

    def loader(directions, *, allowed_evidence_ids):
        return load_content_internal_link_candidates(
            directions,
            allowed_evidence_ids=allowed_evidence_ids,
            store=store,
        )

    monkeypatch.setattr(dynamic_input, "load_content_internal_link_candidates", loader)
    monkeypatch.setattr(
        dynamic_input,
        "_planning_evidence_ids",
        lambda **_: ["ev_wp_contact", "ev_wp_about"],
    )
    candidate = ContentWorkItemServiceCandidate(
        service_card_id="service_card",
        service_label="Usługa",
        lifecycle_status="approved_current",
        lifecycle_label="Zatwierdzona",
        matched_terms=["usługa"],
        match_reasons=["Dokładny temat"],
        recommended=True,
    )
    payload = dynamic_input._planning_payload(
        item=ContentWorkItem.model_construct(id="work_item"),
        service_profile=ContentWorkItemServiceProfileContext.model_construct(
            service_candidates=[candidate]
        ),
        candidate=candidate,
        brief=ContentSalesBrief.model_construct(
            internal_link_direction=[
                "https://ekologus.pl/kontakt/",
                "https://www.ekologus.pl/nieznany/",
            ],
            final_canonical_url="https://www.ekologus.pl/usluga/",
            target_reader="Firma",
            buyer_problem="Problem",
            buyer_trigger="Trigger",
            search_intent="Informacyjna",
            measurement_plan=type(
                "MeasurementPlan",
                (),
                {
                    "metrics_to_watch": [],
                    "baseline_evidence_ids": [],
                    "earliest_verdict_note": "Nie oceniaj przed pełnym oknem.",
                    "success_claim_rule": "Nie zgaduj wyniku.",
                },
            )(),
            knowledge_card_ids=[],
        ),
        baseline=ContentPlanningProposal.model_construct(
            search_demand=ContentSearchDemandEvidence(
                status="missing",
                optional_ads_status="not_exactly_mapped",
                safe_next_step="Nie wnioskuj o popycie bez dokładnych danych.",
            ),
            cta_direction="Kontakt",
        ),
        inventory=ContentPlanningInventory(status="missing"),
        source_facts=[],
        source_assessments=[],
        regulatory_coverage=ContentRegulatoryCoverage(),
        claim_ledger=ContentClaimLedger.model_construct(entries=[]),
        metric_comparisons=[],
    )

    assert [item.model_dump() for item in payload["internal_link_candidates"]] == [
        {
            "target_url": "https://www.ekologus.pl/kontakt",
            "anchor_hint": "Kontakt",
            "source_connector": "wordpress_ekologus",
            "evidence_ids": ["ev_wp_contact"],
        }
    ]
    rejected_payload = {**payload, "internal_link_candidates": []}
    assert dynamic_input._digest(payload) != dynamic_input._digest(rejected_payload)
