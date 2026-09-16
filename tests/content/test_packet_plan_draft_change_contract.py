from __future__ import annotations

import re
from pathlib import Path


def _repository_source(relative: str) -> str:
    root = Path(__file__).resolve().parents[2]
    path = root / relative
    assert path.is_file(), f"required source is missing: {relative}"
    return path.read_text(encoding="utf-8")


def test_research_packet_public_surface_is_read_only() -> None:
    from fastapi import APIRouter, FastAPI
    from fastapi.testclient import TestClient

    from apps.api.wilq_api.routers.content_research_packet import (
        register_content_research_packet_routes,
    )

    router = APIRouter()
    register_content_research_packet_routes(router)
    application = FastAPI()
    application.include_router(router)

    response = TestClient(application).post(
        "/api/content/research-packets",
        json={"packet_id": "content_research_packet_contract"},
    )

    assert response.status_code in {404, 405}


def test_research_packet_identifier_contract_keeps_regulatory_prefix_and_secret_guard() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "wilq/content/workflow/research_packet_contracts.py").read_text(
        encoding="utf-8"
    )

    assert '"regulatory_source_fact_"' in source
    assert "_SECRET_LIKE = re.compile(" in source
    assert "sk-[A-Za-z0-9_-]{20,}" in source
    assert "gho_[A-Za-z0-9_]{20,}" in source
    assert "ya29\\.[A-Za-z0-9._-]{20,}" in source


def test_research_packet_cta_fallback_contract_is_exact_and_evidence_bound() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "wilq/content/workflow/research_packet_derivation.py").read_text(
        encoding="utf-8"
    )

    exact_count = "if len(planning_input.internal_link_candidates) != 1:"
    first_candidate = "candidate = planning_input.internal_link_candidates[0]"
    assert exact_count in source
    assert '{"ekologus.pl", "www.ekologus.pl"}' in source
    assert 'content_normalized_path(target_url) != "/kontakt"' in source
    assert "set(evidence_ids).issubset(planning_evidence_ids)" in source
    assert "internal_link_candidates[0].target_url" not in source
    assert source.index(exact_count) < source.index(first_candidate)


def test_research_packet_freshness_projection_contract_is_complete() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "wilq/content/workflow/research_packet_derivation.py").read_text(
        encoding="utf-8"
    )

    excluded_match = re.search(
        r"_FRESHNESS_NON_SEMANTIC_FIELDS\s*=\s*frozenset\(\s*\{(?P<fields>[^}]*)\}",
        source,
        flags=re.DOTALL,
    )
    assert excluded_match is not None
    excluded_fields = {
        field.strip().strip("'\"")
        for field in excluded_match.group("fields").split(",")
        if field.strip()
    }
    assert excluded_fields == {"checked_at", "state_label", "summary", "next_step"}

    projection_start = source.index("def _freshness_semantic_projection")
    projection_end = source.index("\ndef _jsonable", projection_start)
    projection = source[projection_start:projection_end]
    assert "for field, field_value in payload.items()" in projection
    assert "if field not in _FRESHNESS_NON_SEMANTIC_FIELDS" in projection
    assert "for fact in sorted(facts, key=lambda item: item.source_id)" in source


def test_selected_source_pack_projection_is_exact_and_editorial_only() -> None:
    source = _repository_source("wilq/content/planning/source_pack_projection.py")

    assert "def project_selected_source_pack_facts(" in source
    assert 'fact.review_status != "approved"' in source
    assert "fact.source_id: fact for fact in registry" in source
    assert 'if getattr(planning_input, "content_kind", "service") != "editorial":' in source
    assert "source_material_ids=[]" in source


def test_bdo_profile_owns_the_editorial_canonical_path() -> None:
    source = _repository_source("wilq/content/regulatory/profiles.json")

    assert '"id": "bdo"' in source
    assert '"/bdo-co-musi-wiedziec-przedsiebiorca"' in source


def test_packet_context_partitions_use_the_projected_planning_input() -> None:
    source = _repository_source("wilq/content/workflow/research_packet_derivation.py")

    assert "def _evidence_partitions(" in source
    assert "planning_input=projected_planning_input" in source


def test_editorial_initial_draft_requires_a_current_research_packet() -> None:
    source = _repository_source("wilq/content/drafts/initial_full_draft.py")

    assert 'or getattr(planning.proposal, "content_kind", "service") == "editorial"' in source
    assert 'if proposal.content_kind == "editorial":' in source
    assert '"research_packet_missing"' in source
