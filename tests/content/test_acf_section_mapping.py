from __future__ import annotations

import pytest

from wilq.content.workflow.target_discovery import (
    ContentTargetAuthoringLayout,
    ContentTargetAuthoringSurface,
    ContentTargetContract,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target_mapping import (
    ContentTargetMappingComponent,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingFieldBinding,
    ContentTargetMappingPreview,
    ContentTargetMappingRevision,
    ContentTargetMappingSelection,
    ContentTargetMappingSourceField,
    ContentTargetMappingTarget,
    validate_content_target_mapping_confirmation,
)


def _preview() -> ContentTargetMappingPreview:
    contract = ContentTargetContract(
        environment="dev",
        object_id="2",
        url="https://ekologus.dev.proudsite.pl/",
        post_type="page",
        post_status="publish",
        modified="2026-08-05T18:00:00",
        authoring_surface=ContentTargetAuthoringSurface(
            kind="acf_flexible_content",
            root_field="flexible-home",
            layouts=[
                ContentTargetAuthoringLayout(
                    name="cta", section_index=5, fields=["content"]
                ),
                ContentTargetAuthoringLayout(
                    name="cta", section_index=9, fields=["content"]
                ),
            ],
        ),
    )
    target = ContentTargetMappingTarget(
        target_contract=contract,
        target_contract_digest="a" * 64,
        observation_evidence=ContentTargetObservationEvidence(
            evidence_id="ev_target",
            connector_id="wordpress_ekologus",
            object_id="2",
            post_type="page",
            url=contract.url,
            post_status="publish",
            modified=contract.modified,
            observed_at="2026-08-05T18:00:01+00:00",
        ),
    )
    return ContentTargetMappingPreview(
        work_item_id="content_work_item_home",
        revision=ContentTargetMappingRevision(
            revision_id="revision_home", content_digest="b" * 64
        ),
        status="ready_for_human_mapping",
        target=target,
        binding_digest="c" * 64,
        components=[
            ContentTargetMappingComponent(
                component_id="section:cta",
                kind="rich_text",
                label="CTA",
                status="human_only",
                reason="Wymaga decyzji człowieka.",
                source_fields=[
                    ContentTargetMappingSourceField(key="content_html", label="Treść")
                ],
            )
        ],
    )


def _command(
    preview: ContentTargetMappingPreview, section_index: int | None
) -> ContentTargetMappingConfirmationCommand:
    assert preview.target is not None
    assert preview.binding_digest is not None
    return ContentTargetMappingConfirmationCommand(
        expected_revision_digest=preview.revision.content_digest,
        expected_target_contract_digest=preview.target.target_contract_digest,
        expected_binding_digest=preview.binding_digest,
        confirmed_by="Marta Kowalska",
        selections=[
            ContentTargetMappingSelection(
                component_id="section:cta",
                layout_name="cta",
                target_section_index=section_index,
                field_bindings=[
                    ContentTargetMappingFieldBinding(
                        source_field="content_html", target_field="content"
                    )
                ],
            )
        ],
    )


def test_acf_mapping_requires_the_exact_observed_section_position() -> None:
    preview = _preview()

    validate_content_target_mapping_confirmation(
        command=_command(preview, section_index=9), preview=preview
    )

    with pytest.raises(ValueError, match="dokładną pozycję sekcji"):
        validate_content_target_mapping_confirmation(
            command=_command(preview, section_index=None), preview=preview
        )
    with pytest.raises(ValueError, match="Wybrana sekcja"):
        validate_content_target_mapping_confirmation(
            command=_command(preview, section_index=7), preview=preview
        )
