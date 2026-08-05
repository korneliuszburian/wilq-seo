from __future__ import annotations

from wilq.content.drafts.codex_section_proposal_schema import _section_schema_for_heading
from wilq.content.workflow.revisions import ContentDraftRevisionSection


def test_selected_section_schema_allows_only_claims_grounded_in_its_evidence() -> None:
    schema = {
        "properties": {
            "heading": {},
            "evidence_ids": {},
            "claims_used": {},
        }
    }
    section = ContentDraftRevisionSection.model_construct(
        heading="Ewidencja BDO",
        evidence_ids=["ev_bdo"],
        claim_ids=["claim_refresh"],
    )

    result = _section_schema_for_heading(
        schema,
        section,
        claim_marker_by_id={
            "claim_refresh": ("Strona wymaga odświeżenia.", ["ev_refresh"])
        },
    )

    claims = result["properties"]["claims_used"]
    assert claims["items"] == {"enum": ["__WILQ_EMPTY_ARRAY_ONLY__"], "type": "string"}
    assert claims["minItems"] == 0
    assert claims["maxItems"] == 0
