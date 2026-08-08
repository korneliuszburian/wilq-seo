"""Public content workflow contracts grouped by workflow phase."""

from importlib import import_module as _import_module

_PUBLIC_MODULES = (
    "target.acf_clone_projection",
    "decisions.ads_demand_source",
    "contracts.models",
    "pipeline_steps.operator_steps",
    "decisions.query_section_intent",
    "decisions.demand_evidence",
    "workspace.catalog",
    "target.new_page",
    "decisions.planning",
    "decisions.decision_mapping",
    "decisions.inventory_binding",
    "pipeline_steps.queue",
    "documents.content_html",
    "documents.revision_binding",
    "documents.revisions",
    "contracts.contracts",
    "pipeline_steps.snapshot_assembly",
    "pipeline_steps.stage_activation",
    "pipeline_steps.stage_preparation",
    "pipeline_steps.stage_drafts",
    "documents.codex_revision_commit",
    "documents.revision_persistence",
    "workspace.delivery_projection",
    "target.target_discovery",
    "target.target_mapping_blockers",
    "target.target_mapping_preview_models",
    "target.target_mapping_source_fields",
    "target.target_mapping",
    "store.store_queries",
    "documents.store_measurement",
    "documents.store_revision_review",
    "store.store_schema",
    "store.store",
    "pipeline_steps.stage_measurement",
    "pipeline_steps.stage_review",
    "pipeline_steps.stage_snapshot",
    "pipeline_steps.stage_write_readiness",
    "workspace.api",
    "pipeline_steps.decision_context",
    "target.dev_draft_action",
    "target.dev_draft_discard_action",
    "target.dev_draft_execution",
    "workspace.document_lineage",
    "workspace.document_workspace",
    "pipeline_steps.entry",
    "decisions.exact_demand_decision",
    "target.new_page_document",
    "target.new_page_revision_binding",
    "target.new_page_draft_action",
    "target.new_page_apply_capability",
    "target.new_page_draft_payload",
    "target.new_page_draft_execution",
    "target.new_page_draft_executor",
    "target.new_page_draft_validation",
    "target.new_page_revision",
    "target.new_page_initial_draft",
    "target.new_page_topics",
    "documents.revision_children",
    "documents.official_source_lineage",
    "documents.official_source_lineage_store",
    "pipeline_steps.operator",
    "workspace.selected_workspace",
    "decisions.service_selection",
    "pipeline_steps.stage_readiness",
    "store.store_new_page",
    "store.store_new_page_apply",
    "store.store_public_deployment",
)

__all__: list[str] = []


def __getattr__(name: str) -> object:
    """Resolve public workflow symbols without eagerly importing every phase."""
    if name.startswith("_"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    for module_name in _PUBLIC_MODULES:
        module = _import_module(f"{__name__}.{module_name}")
        public_names = getattr(module, "__all__", None)
        if public_names is not None and name not in public_names:
            continue
        if name not in vars(module):
            continue
        value = getattr(module, name)
        globals()[name] = value
        __all__.append(name)
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
