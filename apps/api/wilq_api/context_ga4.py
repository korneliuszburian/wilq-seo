from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction


def compact_ga4_diagnostics_for_context(
    ga4_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(context_compaction.without_metric_facts(ga4_diagnostics))
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "full_endpoint": "/api/ga4/diagnostics",
    }
    return compact
