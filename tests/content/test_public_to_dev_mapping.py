from __future__ import annotations

from types import SimpleNamespace

import wilq.content.workflow.pipeline_steps.stage_readiness as stage_readiness_module
from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringDevContentObject,
    WordPressAuthoringDevSection,
)
from wilq.content.workflow.target.public_to_dev_mapping import (
    ContentPublicToDevMappingEvidence,
    build_content_public_to_dev_mapping,
)

PUBLIC_URL = "https://www.ekologus.pl/bdo/"
DEV_URL = "https://ekologus.dev.proudsite.pl/bdo/"


def _dev_object() -> WordPressAuthoringDevContentObject:
    return WordPressAuthoringDevContentObject(
        post_id="346",
        slug="bdo",
        title="BDO",
        link=DEV_URL,
        status="draft",
        modified="2026-08-14T08:00:00",
        modified_gmt="2026-08-14T06:00:00",
        section_count=1,
        sections=[
            WordPressAuthoringDevSection(
                section_index=1,
                acf_field_name="content_sections",
                layout_name="text_section",
                layout_label="Treść",
                title="Zakres BDO",
                text_summary="Bieżąca treść sekcji.",
            )
        ],
    )


def _profile(*items: WordPressAuthoringDevContentObject) -> SimpleNamespace:
    return SimpleNamespace(
        evidence_ids=["ev_wordpress_global_capability"],
        source_connectors=["wordpress_ekologus"],
        dev_content=SimpleNamespace(status="available", items=list(items)),
    )


def _snapshot() -> SimpleNamespace:
    return SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                id="content_work_item_bdo",
                source_public_url=PUBLIC_URL,
                evidence_ids=["ev_public_inventory_bdo"],
                source_connectors=["wordpress_ekologus"],
            )
        ),
        draft_package=SimpleNamespace(draft_package_result=SimpleNamespace(draft_package=None)),
    )


def test_observed_dev_target_with_relation_evidence_is_exact() -> None:
    mapping = build_content_public_to_dev_mapping(
        PUBLIC_URL,
        dev_content=_profile(_dev_object()).dev_content,
        relation_evidence=ContentPublicToDevMappingEvidence(
            public_url=PUBLIC_URL,
            dev_url=DEV_URL,
            dev_post_id="346",
            evidence_ids=["ev_public_dev_relation_bdo"],
            basis="exact_dev_url_match",
        ),
    )

    assert mapping.mapping_status == "exact"
    assert mapping.public_url == PUBLIC_URL
    assert mapping.dev_url == DEV_URL
    assert mapping.dev_post_id == "346"
    assert mapping.evidence_ids == ["ev_public_dev_relation_bdo"]
    assert mapping.basis == "exact_dev_url_match"
    assert mapping.blocker is None
    assert mapping.next_step is None


def test_global_authoring_profile_only_exposes_an_unverified_candidate() -> None:
    mapping = build_content_public_to_dev_mapping(
        PUBLIC_URL,
        dev_content=_profile(_dev_object()).dev_content,
    )

    assert mapping.mapping_status == "unverified"
    assert mapping.dev_url == DEV_URL
    assert mapping.dev_post_id == "346"
    assert mapping.evidence_ids == []
    assert mapping.basis == "observed_only"
    assert mapping.blocker == "public_to_dev_relation_unverified"
    assert mapping.next_step is not None
    assert mapping.mapping_status != "exact"


def test_readiness_does_not_expose_a_target_from_a_bare_path_scan(monkeypatch) -> None:
    monkeypatch.setattr(
        stage_readiness_module,
        "build_wordpress_authoring_profile",
        lambda *_args, **_kwargs: _profile(_dev_object()),
    )

    readiness = (
        stage_readiness_module.build_content_wordpress_existing_draft_update_readiness_response(
            _snapshot()
        )
    )

    assert readiness.target_post_id is None
    assert readiness.target_url is None
    assert readiness.current_state_available is False
    assert readiness.current_section_count == 0
    assert readiness.evidence_ids == []


def test_readiness_exposes_current_target_only_from_exact_relation_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        stage_readiness_module,
        "build_wordpress_authoring_profile",
        lambda *_args, **_kwargs: _profile(_dev_object()),
    )

    readiness = (
        stage_readiness_module.build_content_wordpress_existing_draft_update_readiness_response(
            _snapshot(),
            relation_evidence=ContentPublicToDevMappingEvidence(
                public_url=PUBLIC_URL,
                dev_url=DEV_URL,
                dev_post_id="346",
                evidence_ids=["ev_public_dev_relation_bdo"],
                basis="confirmed_inventory_relation",
            ),
        )
    )

    assert readiness.target_post_id == "346"
    assert readiness.target_url == DEV_URL
    assert readiness.current_state_available is True
    assert readiness.current_section_count == 1
    assert readiness.evidence_ids == ["ev_public_dev_relation_bdo"]
