"""Compatibility facade for the consolidated regulatory repair module."""

from wilq.content.drafts.regulatory_repair import (
    _approved_facts_for_requirement,  # noqa: F401 - legacy private import surface
    ground_unmet_regulatory_assertions,
    repair_regulatory_assertions,
)

__all__ = ["ground_unmet_regulatory_assertions", "repair_regulatory_assertions"]
