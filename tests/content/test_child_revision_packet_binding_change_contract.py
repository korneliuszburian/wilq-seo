"""Parent-safe observer for child proposal packet binding."""

from __future__ import annotations

import importlib
from types import SimpleNamespace


def test_child_proposal_metadata_inherits_base_packet_binding() -> None:
    try:
        proposal_module = importlib.import_module("wilq.content.drafts.codex_section_proposal")
        proposal_metadata_builder = getattr(proposal_module, "_proposal_metadata", None)
    except (AttributeError, ImportError):
        proposal_metadata_builder = None

    assert callable(proposal_metadata_builder), "section proposal metadata builder is required"

    base_revision = SimpleNamespace(
        research_packet_id="content_research_packet_parent_safe",
        research_packet_digest="f" * 64,
        sections=[
            SimpleNamespace(
                heading="Zakres",
                source_material_ids=[],
                knowledge_card_ids=[],
            )
        ],
        cta_blocks=[],
    )
    output = SimpleNamespace(
        sections=[
            SimpleNamespace(
                heading="Zakres",
                evidence_ids=["evidence_parent_safe"],
                claims_used=[],
            )
        ]
    )
    contract = SimpleNamespace(model_input=SimpleNamespace(claim_markers=[]))
    quality_review = SimpleNamespace(verdict="reviewable", findings=[])

    metadata = proposal_metadata_builder(
        run=SimpleNamespace(id="codex_run_parent_safe"),
        output=output,
        contract=contract,
        quality_review=quality_review,
        selected_headings=["Zakres"],
        selected_cta_ids=[],
        base_revision=base_revision,
    )

    assert metadata.research_packet_id == base_revision.research_packet_id
    assert metadata.research_packet_digest == base_revision.research_packet_digest
