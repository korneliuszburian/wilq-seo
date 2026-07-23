from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

import wilq.content.workflow.target_discovery as discovery_module
from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringDevPage,
    WordPressAuthoringDevSection,
)

WORK_ITEM_ID = "content_work_item_bdo"
PUBLIC_URL = "https://www.ekologus.pl/bdo/"


def _profile(*pages: WordPressAuthoringDevPage) -> SimpleNamespace:
    return SimpleNamespace(
        evidence_ids=["ev_wordpress_dev_read"],
        dev_content=SimpleNamespace(pages=list(pages)),
    )


def _page(
    url: str, *, content_type: Literal["page", "post"] = "page"
) -> WordPressAuthoringDevPage:
    return WordPressAuthoringDevPage(
        post_id="346",
        content_type=content_type,
        slug="bdo",
        title="BDO",
        link=url,
        status="draft",
        modified="2026-07-23T08:00:00",
        modified_gmt="2026-07-23T06:00:00",
        template="page-templates/content.php",
        acf_field_name="content_sections",
        section_count=1,
        sections=[
            WordPressAuthoringDevSection(
                section_index=0,
                acf_field_name="content_sections",
                layout_name="text_section",
                layout_label="Sekcja tekstowa",
                field_names=["title", "content"],
            )
        ],
    )


def test_target_discovery_reads_exact_dev_object_but_does_not_confirm_relation(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: (
            SimpleNamespace(source_public_url=PUBLIC_URL, final_canonical_url=None, page=PUBLIC_URL)
            if work_item_id == WORK_ITEM_ID
            else None
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(
            _page("https://dev.ekologus.pl/bdo/", content_type="post")
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.relation_status == "partial"
    assert discovery.target is not None
    assert discovery.target.object_id == "346"
    assert discovery.target.post_type == "post"
    assert discovery.target.post_status == "draft"
    assert discovery.target.observed_surfaces == ["acf_flexible_content"]
    assert discovery.evidence_ids == ["ev_wordpress_dev_read"]
    assert len(discovery.target.target_contract_digest) == 64
    assert "nie potwierdza" in discovery.reason


def test_target_discovery_does_not_infer_a_target_when_dev_path_differs(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(
            _page("https://dev.ekologus.pl/inna-strona/")
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.relation_status == "unavailable"
    assert discovery.target is None
    assert discovery.evidence_ids == ["ev_wordpress_dev_read"]
