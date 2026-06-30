from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.opportunities.engine import get_opportunity, list_opportunities
from wilq.schemas import Opportunity

router = APIRouter()


@router.get("/api/opportunities", response_model=list[Opportunity])
def opportunities() -> list[Opportunity]:
    return list_opportunities()


@router.get("/api/opportunities/{opportunity_id}", response_model=Opportunity)
def opportunity(opportunity_id: str) -> Opportunity:
    item = get_opportunity(opportunity_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Unknown opportunity: {opportunity_id}")
    return item


@router.post("/api/opportunities/recompute", response_model=list[Opportunity])
def recompute_opportunities() -> list[Opportunity]:
    return list_opportunities()
