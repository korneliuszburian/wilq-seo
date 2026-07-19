from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.content.planning.decisions import (
    content_decision_metrics,
    content_decision_work_item_id_for_url,
)
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
    inventory_metric_facts,
    inventory_work_item_id,
    read_content_inventory_material,
)
from wilq.schemas import ActionRisk, ContentDecisionItem


def build_content_inventory_catalog() -> ContentInventoryCatalogResponse:
    """Keep the existing test seam while using the shared short-lived cache."""
    return build_content_inventory_catalog_cached()


def inventory_decision_for_work_item(
    work_item_id: str,
    *,
    read_material: bool = True,
    allow_material_pending: bool = False,
) -> ContentDecisionItem | None:
    catalog = build_content_inventory_catalog()
    matches = [
        candidate
        for candidate in catalog.items
        if inventory_work_item_id(candidate.url) == work_item_id
        or content_decision_work_item_id_for_url(candidate.url) == work_item_id
    ]
    # The diagnostics queue truncates URL slugs to a bounded ID. Refuse an
    # ambiguous catalog match rather than opening the wrong page.
    item = matches[0] if len(matches) == 1 else None
    if item is None:
        return None
    material = (
        read_content_inventory_material(item.url, catalog=catalog)
        if read_material
        else None
    )
    material_ready = (
        material is not None
        and material.status == "ready"
        and bool(material.content_text)
    )
    content_text = (
        material.content_text if material_ready and material is not None else None
    )
    content_summary = (
        material.content_summary
        if material_ready and material is not None
        else item.content_summary
    )
    content_word_count = (
        material.content_word_count
        if material_ready and material is not None
        else item.content_word_count
    )
    section_headings = (
        material.section_headings
        if material_ready and material is not None
        else item.section_headings or item.acf_section_headings
    )
    acf_headings = (
        material.acf_section_headings
        if material_ready and material is not None
        else item.acf_section_headings
    )
    acf_fields = (
        material.acf_field_names
        if material_ready and material is not None
        else item.acf_field_names
    )
    facts = [
        fact
        for fact in inventory_metric_facts(item.url, item.path)
        if fact.source_connector == "google_search_console"
    ]
    queries = _unique(str(fact.dimensions.get("query") or "") for fact in facts)
    metrics = content_decision_metrics(facts, queries)
    evidence_ids = _unique([item.evidence_id, *(fact.evidence_id for fact in facts)])
    source_connectors = _unique([item.source_connector, *(fact.source_connector for fact in facts)])
    title = item.title or item.path
    decision_status: Literal["ready", "blocked"] = (
        "ready" if material_ready or item.material_status != "url_only" else "blocked"
    )
    # An explicitly selected inventory item may enter the decision view before
    # the heavier WordPress material read finishes. This is not content
    # readiness: the missing material remains visible on the decision and
    # snapshot surfaces and still blocks planning/draft generation later.
    if allow_material_pending and not material_ready:
        decision_status = "ready"
    return ContentDecisionItem(
        id=work_item_id.removeprefix("content_work_item_"),
        decision_type="refresh_or_merge",
        status=decision_status,
        title=title,
        summary=content_summary or "Istniejący adres WordPress do odczytu i decyzji contentowej.",
        page=item.url,
        normalized_page_path=item.path,
        queries=queries,
        query_count=len(queries),
        primary_query=metrics.primary_query,
        total_clicks=metrics.total_clicks,
        total_impressions=metrics.total_impressions,
        aggregate_ctr=metrics.aggregate_ctr,
        best_average_position=metrics.best_average_position,
        wordpress_match="found",
        wordpress_match_confidence="high",
        wordpress_title_or_h1=item.title,
        wordpress_inventory_source=item.source_connector,
        wordpress_section_headings=section_headings,
        wordpress_section_count=len(section_headings) if section_headings else item.section_count,
        wordpress_section_inventory_status="available" if section_headings else "missing",
        wordpress_content_summary=content_summary,
        wordpress_content_text=content_text,
        wordpress_content_source_kind=(
            material.source_kind if material_ready and material is not None else None
        ),
        wordpress_content_extraction_region=(
            material.extraction_region
            if material_ready and material is not None
            else None
        ),
        wordpress_content_material_confidence=(
            material.material_confidence
            if material_ready and material is not None
            else None
        ),
        wordpress_content_source_field_lineage=(
            material.source_field_lineage
            if material_ready and material is not None
            else []
        ),
        wordpress_content_word_count=content_word_count,
        wordpress_content_inventory_status=(
            "available" if content_summary or content_text else "missing"
        ),
        wordpress_content_inventory_note=(
            None
            if content_summary
            else "Pełny materiał zostanie odczytany dynamicznie przed planem."
        ),
        wordpress_acf_section_inventory_status=(
            "available" if acf_headings or acf_fields else "missing"
        ),
        wordpress_acf_section_headings=acf_headings,
        wordpress_acf_section_count=(
            len(acf_headings) if acf_headings else item.acf_section_count
        ),
        source_public_url=item.url,
        intended_final_url=item.url,
        final_canonical_url=item.url,
        inventory_gate_status="confirmed_current_inventory",
        canonical_gate_status="resolved",
        duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
        content_gate_summary="Istniejąca treść wymaga decyzji odświeżenia; nie twórz duplikatu.",
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        metric_facts=facts[:8],
        rationale=(
            "Adres został wybrany bezpośrednio z pełnego inventory WordPress, "
            "a nie z okazji wygenerowanej z brainstormingu."
        ),
        next_step="Sprawdź dynamiczny materiał, wybierz usługę i wygeneruj plan.",
        risk=ActionRisk.low,
    )


def _unique(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


__all__ = ["inventory_decision_for_work_item"]
