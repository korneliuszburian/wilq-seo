from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.evidence.registry import get_evidence, list_evidence
from wilq.operator_labels import (
    evidence_source_type_label,
    freshness_state_label,
    source_connector_label,
)
from wilq.schemas import Evidence

router = APIRouter()


@router.get("/api/evidence", response_model=list[Evidence])
def evidence_items() -> list[Evidence]:
    return [_label_evidence_item(item) for item in list_evidence()]


@router.get("/api/evidence/{evidence_id}", response_model=Evidence)
def evidence_detail(evidence_id: str) -> Evidence:
    evidence = get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Unknown evidence: {evidence_id}")
    return _label_evidence_item(evidence)


def _label_evidence_item(evidence: Evidence) -> Evidence:
    source_label = source_connector_label(evidence.source_connector)
    source_type_label = evidence_source_type_label(evidence.source_type)
    freshness_label = freshness_state_label(evidence.freshness.state)
    return evidence.model_copy(
        update={
            "title_label": f"Dowód z {source_label}",
            "source_connector_label": source_label,
            "source_type_label": source_type_label,
            "freshness_label": freshness_label,
            "trace_summary_label": f"{source_label}: {source_type_label}, {freshness_label}",
        }
    )
