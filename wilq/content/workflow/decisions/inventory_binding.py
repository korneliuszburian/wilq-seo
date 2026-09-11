from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from wilq.content.canonical.urls import (
    content_authoring_path_matches_public_url,
    content_normalized_path,
)
from wilq.content.operator_copy import unique
from wilq.content.planning.decisions import (
    content_decision_metrics,
    content_decision_title,
    content_decision_work_item_id_for_url,
)
from wilq.content.workflow.content_kind import (
    ContentKind,
    classify_content_kind_from_inventory,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryMaterialResponse,
    build_content_inventory_catalog_cached,
    inventory_metric_facts,
    inventory_work_item_id,
    latest_wordpress_vendor_read_evidence_ids,
    read_content_inventory_material,
)
from wilq.schemas import ActionRisk, ContentDecisionItem


def build_content_inventory_catalog() -> ContentInventoryCatalogResponse:
    """Keep the existing test seam while using the shared short-lived cache."""
    return build_content_inventory_catalog_cached()


@dataclass(frozen=True)
class ContentKindInventoryBinding:
    """The minimum trusted inventory identity needed to authorize editorial work."""

    work_item_id: str
    canonical_path: str
    public_url: str
    wordpress_content_type: str
    content_kind: ContentKind
    inventory_evidence_ids: tuple[str, ...]
    trusted: bool


@dataclass(frozen=True)
class ResolvedInventoryMaterial:
    """One narrowed view of the inventory material for the decision item.

    ``ready`` is the single source of readiness; all source fields are
    already narrowed to their ready/fallback value so callers never repeat
    the ``material is not None`` guard.
    """

    ready: bool
    content_text: str | None = None
    content_summary: str | None = None
    content_word_count: int | None = None
    section_headings: list[str] = field(default_factory=list)
    acf_headings: list[str] = field(default_factory=list)
    acf_fields: list[str] = field(default_factory=list)
    source_kind: str | None = None
    extraction_region: str | None = None
    material_confidence: str | None = None
    source_field_lineage: list[str] = field(default_factory=list)


def resolve_inventory_material(
    item: ContentInventoryCatalogItem,
    material: ContentInventoryMaterialResponse | None,
) -> ResolvedInventoryMaterial:
    """Resolve material fields onto the catalog item with one narrowed view.

    A REST-bound page can legitimately keep its body in exposed ACF fields
    while ``the_content`` is empty (for example a flexible homepage).  The
    live source is still resolved and must be surfaced to the workflow; an
    empty body remains an honest downstream drafting constraint rather than
    silently downgrading the page to stale inventory metadata.
    """
    ready = (
        material is not None
        and material.status == "ready"
        and (
            bool(material.content_text)
            or bool(material.acf_field_names)
            or bool(material.acf_section_headings)
            or material.source_kind == "wordpress_rest"
        )
    )
    if not ready or material is None:
        return ResolvedInventoryMaterial(
            ready=False,
            content_summary=item.content_summary,
            content_word_count=item.content_word_count,
            section_headings=item.acf_section_headings or item.section_headings,
            acf_headings=item.acf_section_headings,
            acf_fields=item.acf_field_names,
            source_field_lineage=[],
        )
    return ResolvedInventoryMaterial(
        ready=True,
        content_text=material.content_text or None,
        content_summary=material.content_summary,
        content_word_count=material.content_word_count,
        section_headings=(
            material.acf_section_headings
            or material.section_headings
            or item.acf_section_headings
            or item.section_headings
        ),
        acf_headings=material.acf_section_headings,
        acf_fields=material.acf_field_names,
        source_kind=material.source_kind,
        extraction_region=material.extraction_region,
        material_confidence=material.material_confidence,
        source_field_lineage=material.source_field_lineage,
    )


def _inventory_item_for_work_item(
    catalog: ContentInventoryCatalogResponse,
    work_item_id: str,
) -> ContentInventoryCatalogItem | None:
    matches = [
        candidate
        for candidate in catalog.items
        if inventory_work_item_id(candidate.url) == work_item_id
        or content_decision_work_item_id_for_url(candidate.url) == work_item_id
    ]
    # The diagnostics queue truncates URL slugs to a bounded ID. Refuse an
    # ambiguous catalog match rather than opening the wrong page.
    return matches[0] if len(matches) == 1 else None


def _inventory_decision_status(
    item: ContentInventoryCatalogItem,
    material_ready: bool,
    allow_material_pending: bool,
) -> Literal["ready", "blocked"]:
    # A selected item may enter the decision view before its heavier material
    # read finishes. This is not content readiness: later planning stays blocked.
    if allow_material_pending and not material_ready:
        return "ready"
    return "ready" if material_ready or item.material_status != "url_only" else "blocked"


def content_kind_inventory_binding_for_work_item(
    work_item_id: str,
) -> ContentKindInventoryBinding | None:
    """Resolve the current typed inventory identity without reading page material.

    A binding may name an editorial type while still being untrusted if the
    current WordPress vendor-read evidence is missing.  That lets callers
    reject it explicitly instead of silently falling back to a service path.
    """

    catalog = build_content_inventory_catalog()
    item = _inventory_item_for_work_item(catalog, work_item_id)
    if item is None:
        return None
    return _content_kind_inventory_binding(
        item,
        catalog,
        trusted_evidence_ids=set(latest_wordpress_vendor_read_evidence_ids()),
    )


def _content_kind_inventory_binding(
    item: ContentInventoryCatalogItem,
    catalog: ContentInventoryCatalogResponse,
    *,
    trusted_evidence_ids: set[str] | None = None,
) -> ContentKindInventoryBinding:
    wordpress_content_type, content_kind = classify_content_kind_from_inventory(
        item.content_type,
        public_url=item.url,
        dev_objects=[
            (rest_object.url, rest_object.content_type)
            for rest_object in catalog.rest_content_objects
        ],
    )
    fallback_used = wordpress_content_type != item.content_type and content_kind != "ambiguous"
    fallback_evidence_ids = (
        [
            rest_object.evidence_id
            for rest_object in catalog.rest_content_objects
            if content_authoring_path_matches_public_url(item.url, rest_object.url)
            and rest_object.content_type == wordpress_content_type
        ]
        if fallback_used
        else []
    )
    inventory_evidence_ids = tuple(unique([item.evidence_id, *fallback_evidence_ids]))
    return ContentKindInventoryBinding(
        work_item_id=item.work_item_id,
        canonical_path=content_normalized_path(item.url),
        public_url=item.url,
        wordpress_content_type=wordpress_content_type or item.content_type,
        content_kind=content_kind,
        inventory_evidence_ids=inventory_evidence_ids,
        trusted=(
            bool(trusted_evidence_ids)
            and set(inventory_evidence_ids).issubset(trusted_evidence_ids)
        )
        if trusted_evidence_ids is not None
        else True,
    )


def _decision_evidence_ids(
    binding: ContentKindInventoryBinding,
    metric_facts: list[Any],
) -> list[str]:
    return unique(
        [
            *binding.inventory_evidence_ids,
            *(str(fact.evidence_id) for fact in metric_facts),
        ]
    )


def inventory_decision_for_work_item(
    work_item_id: str,
    *,
    read_material: bool = True,
    allow_material_pending: bool = False,
    include_all_metric_facts: bool = False,
) -> ContentDecisionItem | None:
    catalog = build_content_inventory_catalog()
    item = _inventory_item_for_work_item(catalog, work_item_id)
    if item is None:
        return None
    content_kind_binding = _content_kind_inventory_binding(item, catalog)
    material = read_content_inventory_material(item.url, catalog=catalog) if read_material else None
    resolved = resolve_inventory_material(item, material)
    content_summary = resolved.content_summary
    section_headings = resolved.section_headings
    acf_headings = resolved.acf_headings
    acf_fields = resolved.acf_fields
    all_metric_facts = inventory_metric_facts(item.url, item.path)
    facts = [fact for fact in all_metric_facts if fact.source_connector == "google_search_console"]
    queries = unique(str(fact.dimensions.get("query") or "") for fact in facts)
    metrics = content_decision_metrics(facts, queries)
    evidence_ids = _decision_evidence_ids(content_kind_binding, all_metric_facts)
    source_connectors = unique(
        [item.source_connector, *(fact.source_connector for fact in all_metric_facts)]
    )
    title = content_decision_title(
        decision_type="refresh_or_merge",
        page=item.url,
        query_count=len(queries),
        metrics=metrics,
    )
    decision_status = _inventory_decision_status(item, resolved.ready, allow_material_pending)
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
        wordpress_content_type=content_kind_binding.wordpress_content_type,
        content_kind=content_kind_binding.content_kind,
        wordpress_title_or_h1=item.title,
        wordpress_inventory_source=item.source_connector,
        wordpress_section_headings=section_headings,
        wordpress_section_count=len(section_headings) if section_headings else item.section_count,
        wordpress_section_inventory_status="available" if section_headings else "missing",
        wordpress_content_summary=content_summary,
        wordpress_content_text=resolved.content_text,
        wordpress_content_source_kind=resolved.source_kind,
        wordpress_content_extraction_region=resolved.extraction_region,
        wordpress_content_material_confidence=resolved.material_confidence,
        wordpress_content_source_field_lineage=resolved.source_field_lineage,
        wordpress_content_word_count=resolved.content_word_count,
        wordpress_content_inventory_status=(
            "available" if content_summary or resolved.content_text else "missing"
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
        wordpress_acf_field_names=acf_fields,
        wordpress_acf_section_count=(len(acf_headings) if acf_headings else item.acf_section_count),
        source_public_url=item.url,
        intended_final_url=item.url,
        final_canonical_url=item.url,
        inventory_gate_status="confirmed_current_inventory",
        canonical_gate_status="resolved",
        duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
        content_gate_summary="Istniejąca treść wymaga decyzji odświeżenia; nie twórz duplikatu.",
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        # Keep the bounded GSC preview for the queue, but retain exact GA4
        # landing facts so planning can bind behavior to the selected page.
        metric_facts=[
            *(facts if include_all_metric_facts else facts[:8]),
            *[fact for fact in all_metric_facts if fact.source_connector == "google_analytics_4"],
        ],
        rationale=(
            "Adres został wybrany bezpośrednio z pełnego inventory WordPress, "
            "a nie z okazji wygenerowanej z brainstormingu."
        ),
        next_step="Sprawdź dynamiczny materiał, wybierz usługę i wygeneruj plan.",
        risk=ActionRisk.low,
    )




__all__ = [
    "ContentKindInventoryBinding",
    "content_kind_inventory_binding_for_work_item",
    "inventory_decision_for_work_item",
    "resolve_inventory_material",
    "ResolvedInventoryMaterial",
]
