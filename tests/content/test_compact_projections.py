from __future__ import annotations

from wilq.content.drafts.initial_full_draft_turn import compact_initial_draft_proposal
from wilq.content.planning.compact_projections import (
    PROPOSAL_EDITORIAL_KEYS,
    compact_proposal,
)
from wilq.content.quality.semantic_review_turn import compact_semantic_review_proposal


class _ProposalFixture:
    sections = [
        {
            "section_id": "keep",
            "heading": "Keep",
            "purpose": "Purpose",
            "reader_question": "Question",
            "query_terms": ["query"],
            "evidence_ids": ["evidence"],
            "regulatory_requirement_ids": ["requirement"],
            "claim_ids": ["claim"],
            "inventory_disposition": "create",
        },
        {
            "section_id": "remove",
            "heading": "Remove",
            "purpose": "Purpose",
            "reader_question": "Question",
            "query_terms": [],
            "evidence_ids": [],
            "regulatory_requirement_ids": [],
            "inventory_disposition": "remove_review_required",
        },
    ]

    def model_dump(self, *, mode: str, exclude_none: bool) -> dict[str, object]:
        assert mode == "json"
        assert exclude_none is True
        return {
            "work_item_id": "work-item",
            "planning_digest": "planning-digest",
            "proposal_id": "proposal",
            "sections": self.sections,
            "page_assets": {"title": "telemetry"},
            "inventory_mapping": [{"status": "mapped"}],
        }


def test_shared_proposal_projection_preserves_both_legacy_outputs() -> None:
    proposal = _ProposalFixture()
    expected_draft = {
        "work_item_id": "work-item",
        "planning_digest": "planning-digest",
        "proposal_id": "proposal",
        "sections": proposal.sections,
    }
    expected_semantic = {
        "work_item_id": "work-item",
        "planning_digest": "planning-digest",
        "proposal_id": "proposal",
        "sections": [
            {
                key: proposal.sections[0][key]
                for key in (
                    "section_id",
                    "heading",
                    "purpose",
                    "reader_question",
                    "query_terms",
                    "evidence_ids",
                    "regulatory_requirement_ids",
                )
            }
        ],
    }

    assert set(PROPOSAL_EDITORIAL_KEYS) == {
        "work_item_id",
        "planning_digest",
        "proposal_id",
        "planning_input_digest",
        "final_canonical_url",
        "service_card_id",
        "service_label",
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "angle",
        "value_proposition",
        "cta_direction",
        "sections",
        "faq",
        "cta_blocks",
        "internal_links",
        "evidence_ids",
        "source_connectors",
        "source_material_ids",
        "knowledge_card_ids",
    }
    assert compact_proposal(proposal, draftable_sections_only=False) == expected_draft
    assert compact_proposal(proposal, draftable_sections_only=True) == expected_semantic
    assert compact_initial_draft_proposal(proposal) == expected_draft
    assert compact_semantic_review_proposal(proposal) == expected_semantic
