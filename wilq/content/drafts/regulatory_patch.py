"""Compatibility facade for the consolidated regulatory repair module."""

from wilq.content.drafts.regulatory_repair import (
    RegulatoryAssertionRepairOutput,
    RegulatoryPatchMode,
    RegulatorySectionPatch,
    apply_regulatory_patches,
    regulatory_assertion_repair_output_schema,
    validated_patches_by_section,
)

__all__ = [
    "RegulatoryAssertionRepairOutput",
    "RegulatoryPatchMode",
    "RegulatorySectionPatch",
    "apply_regulatory_patches",
    "regulatory_assertion_repair_output_schema",
    "validated_patches_by_section",
]
