"""Public contract for bounded regulatory document patches."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wilq.content.codex_turn import mapping, require_all_object_properties
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftInternalLinkOutput,
    ContentInitialDraftModelOutput,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionPageAssets,
    validate_no_inline_link,
)

RegulatoryPatchMode = Literal["append", "replace"]


class RegulatorySectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", title="_RegulatorySectionPatch")

    section_id: str = Field(min_length=1)
    mode: RegulatoryPatchMode
    body_markdown: str = Field(min_length=1)

    @field_validator("body_markdown")
    @classmethod
    def require_visible_text_without_inline_links(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Regulatory repair body cannot be blank.")
        return validate_no_inline_link(value)


class RegulatoryAssertionRepairOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="_RegulatoryAssertionRepairOutput",
    )

    sections: list[RegulatorySectionPatch] = Field(min_length=1)
    publish_ready: Literal[False] = False


def regulatory_assertion_repair_output_schema(
    section_ids: list[str],
) -> dict[str, object]:
    """Build the bounded turn schema without changing its legacy wire shape."""

    schema = deepcopy(RegulatoryAssertionRepairOutput.model_json_schema())
    require_all_object_properties(schema)
    definitions = mapping(schema, "$defs")
    public_definition_name = RegulatorySectionPatch.__name__
    schema_definition = mapping(definitions, public_definition_name)
    del definitions[public_definition_name]
    legacy_definition_name = "_RegulatorySectionPatch"
    definitions[legacy_definition_name] = schema_definition
    sections = mapping(mapping(schema, "properties"), "sections")
    section_items = mapping(sections, "items")
    section_items["$ref"] = f"#/$defs/{legacy_definition_name}"
    section_properties = mapping(schema_definition, "properties")
    section_id = mapping(section_properties, "section_id")
    section_id["enum"] = section_ids
    sections["minItems"] = len(section_ids)
    sections["maxItems"] = len(section_ids)
    return schema


def validated_patches_by_section(
    output: RegulatoryAssertionRepairOutput,
    *,
    expected_section_ids: Collection[str] | None = None,
    expected_modes: Mapping[str, RegulatoryPatchMode] | None = None,
) -> dict[str, RegulatorySectionPatch] | None:
    """Return one patch per exact target, or reject the complete patch set."""

    patches = {patch.section_id: patch for patch in output.sections}
    if output.publish_ready or len(patches) != len(output.sections):
        return None
    if expected_section_ids is not None and set(patches) != set(expected_section_ids):
        return None
    if expected_modes is not None and {
        section_id: patch.mode for section_id, patch in patches.items()
    } != dict(expected_modes):
        return None
    return patches


def apply_regulatory_patches(
    output: ContentInitialDraftModelOutput,
    patches: Mapping[str, RegulatorySectionPatch],
) -> ContentInitialDraftModelOutput:
    """Apply validated regulatory patches to document sections and revalidate."""

    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _patched_regulatory_section_body(
                            section.body_markdown,
                            patches.get(section.section_id),
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )
    return ContentInitialDraftModelOutput.model_validate(patched.model_dump(mode="json"))


def apply_readability_patches(
    output: ContentInitialDraftModelOutput,
    patches: Mapping[str, RegulatorySectionPatch],
) -> ContentInitialDraftModelOutput:
    """Apply validated readability patches to every supported document target."""

    patched = output.model_copy(
        update={
            "page_assets": _patched_page_assets(output.page_assets, patches),
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _patched_readability_section_body(
                            section.body_markdown,
                            patches.get(section.section_id),
                        )
                    }
                )
                for section in output.sections
            ],
            "faq": [
                item.model_copy(
                    update={
                        "answer_markdown": _patched_auxiliary_body(
                            item.answer_markdown,
                            patches.get(f"faq:{index}"),
                        )
                    }
                )
                for index, item in enumerate(output.faq, start=1)
            ],
            "cta_blocks": [
                item.model_copy(
                    update={
                        "body_markdown": _patched_auxiliary_body(
                            item.body_markdown,
                            patches.get(f"cta:{index}"),
                        )
                    }
                )
                for index, item in enumerate(output.cta_blocks, start=1)
            ],
            "internal_links": _patched_internal_links(output.internal_links, patches),
        }
    )
    return ContentInitialDraftModelOutput.model_validate(patched.model_dump(mode="json"))


def _patched_regulatory_section_body(
    existing: str,
    patch: RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode == "replace":
        return patch.body_markdown
    if patch.mode != "append" or patch.body_markdown in existing:
        return existing
    return f"{existing}\n\n{patch.body_markdown}"


def _patched_page_assets(
    page_assets: ContentDraftRevisionPageAssets,
    patches: Mapping[str, RegulatorySectionPatch],
) -> ContentDraftRevisionPageAssets:
    return page_assets.model_copy(
        update={
            "wordpress_title": _patched_short_target(
                page_assets.wordpress_title,
                patches.get("page_assets:wordpress_title"),
            ),
            "meta_title": _patched_short_target(
                page_assets.meta_title,
                patches.get("page_assets:meta_title"),
            ),
            "meta_description": _patched_short_target(
                page_assets.meta_description,
                patches.get("page_assets:meta_description"),
            ),
            "h1": _patched_short_target(
                page_assets.h1,
                patches.get("page_assets:h1"),
            ),
            "lead": _patched_short_target(
                page_assets.lead,
                patches.get("page_assets:lead"),
            ),
        }
    )


def _patched_internal_links(
    internal_links: list[ContentInitialDraftInternalLinkOutput],
    patches: Mapping[str, RegulatorySectionPatch],
) -> list[ContentInitialDraftInternalLinkOutput]:
    return [
        item.model_copy(
            update={
                "anchor_text": _patched_short_target(
                    item.anchor_text,
                    patches.get(f"link:{index}"),
                )
            }
        )
        for index, item in enumerate(internal_links, start=1)
    ]


def _patched_short_target(
    existing: str,
    patch: RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode != "replace":
        raise ValueError("Page asset and link readability patches must use replace mode.")
    return patch.body_markdown


def _patched_readability_section_body(
    existing: str,
    patch: RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode == "replace":
        return patch.body_markdown
    return f"{existing}\n\n{patch.body_markdown}"


def _patched_auxiliary_body(
    existing: str,
    patch: RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode != "replace":
        raise ValueError("FAQ and CTA readability patches must use replace mode.")
    return patch.body_markdown


__all__ = [
    "RegulatoryAssertionRepairOutput",
    "RegulatoryPatchMode",
    "RegulatorySectionPatch",
    "apply_readability_patches",
    "apply_regulatory_patches",
    "regulatory_assertion_repair_output_schema",
    "validated_patches_by_section",
]
