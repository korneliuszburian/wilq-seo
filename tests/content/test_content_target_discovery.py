from __future__ import annotations

import json
from hashlib import sha256
from types import SimpleNamespace
from typing import Literal

import wilq.content.workflow.target_discovery as discovery_module
from wilq.connectors.wordpress.acf_relationship_observation import (
    WordPressAcfRelationshipObservation,
)
from wilq.connectors.wordpress.acf_rest_schema import (
    WordPressAcfRestSchema,
    WordPressAcfRestSchemaField,
    WordPressAcfRestSchemaLayout,
)
from wilq.connectors.wordpress.acf_source_snapshot import WordPressAcfFlexibleSnapshot
from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringDevContentObject,
    WordPressAuthoringDevSection,
)

WORK_ITEM_ID = "content_work_item_bdo"
PUBLIC_URL = "https://www.ekologus.pl/bdo/"


def _profile(*items: WordPressAuthoringDevContentObject) -> SimpleNamespace:
    return SimpleNamespace(
        authoring_target="dev",
        evidence_ids=["ev_wordpress_dev_read"],
        acf=SimpleNamespace(flexible_content_field_name=None, layouts=[]),
        dev_content=SimpleNamespace(status="available", items=list(items), blockers=[]),
    )


def _page(
    url: str, *, content_type: Literal["page", "post"] = "page"
) -> WordPressAuthoringDevContentObject:
    return WordPressAuthoringDevContentObject(
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
                section_index=1,
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
    assert discovery.target.target_contract.authority == "observation_only"
    assert discovery.target.target_contract.write_authorized is False
    assert discovery.target.target_contract.authoring_surface is not None
    assert discovery.target.target_contract.authoring_surface.root_field == "content_sections"
    observed_layout = discovery.target.target_contract.authoring_surface.layouts[0]
    assert observed_layout.section_index == 1
    assert observed_layout.label == "Sekcja tekstowa"
    assert discovery.target.target_contract.authoring_surface.write_profile_status == "unavailable"
    assert discovery.target.target_contract.authoring_surface.layouts[0].writable_fields == []
    assert discovery.target.observation_evidence.object_id == "346"
    assert discovery.target.observation_evidence.evidence_id in discovery.evidence_ids
    assert "ev_wordpress_dev_read" in discovery.evidence_ids
    assert len(discovery.target.target_contract_digest) == 64
    assert (
        discovery.target.target_contract_digest
        == sha256(
            json.dumps(
                discovery.target.target_contract.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )
    assert "nie potwierdza" in discovery.reason


def test_target_discovery_exposes_exact_acf_schema_without_opening_acf_delivery(
    monkeypatch,
) -> None:
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
            _page("https://dev.ekologus.pl/bdo/")
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "read_wordpress_acf_rest_schema",
        lambda _connector_id, _item: WordPressAcfRestSchema(
            status="available",
            root_field="content_sections",
            schema_digest="a" * 64,
            source_ref="wp-json/wp/v2/pages/346 OPTIONS",
            reason="Schema ACF została odczytana przez OPTIONS.",
            layouts=[
                WordPressAcfRestSchemaLayout(
                    name="text_section",
                    label="Sekcja tekstowa",
                    source_method="acf_rest",
                    fields=[
                        WordPressAcfRestSchemaField(
                            name="title",
                            label="Tytuł",
                            field_type="string",
                            source_method="acf_rest",
                        ),
                        WordPressAcfRestSchemaField(
                            name="content",
                            label="Treść",
                            field_type="string",
                            source_method="acf_rest",
                        ),
                    ],
                )
            ],
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    surface = discovery.target.target_contract.authoring_surface
    assert surface is not None
    assert surface.schema_status == "available"
    assert surface.schema_digest == "a" * 64
    assert surface.layouts[0].schema_fields == ["title", "content"]
    assert surface.write_profile_status == "unavailable"
    assert "pełnego digesta źródłowego" in surface.write_profile_reason


def test_target_discovery_identifies_native_post_content_without_inventing_acf(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: (
            SimpleNamespace(source_public_url=PUBLIC_URL, final_canonical_url=None, page=PUBLIC_URL)
            if work_item_id == WORK_ITEM_ID
            else None
        ),
    )
    post = _page("https://dev.ekologus.pl/bdo/", content_type="post").model_copy(
        update={"acf_field_name": None, "section_count": 0, "sections": []}
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(post),
    )
    monkeypatch.setattr(discovery_module, "_native_post_content_observed", lambda _item: True)

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.target is not None
    surface = discovery.target.target_contract.authoring_surface
    assert surface is not None
    assert surface.kind == "wordpress_post_content"
    assert surface.root_field == "content"
    assert surface.layouts[0].fields == ["title", "content_html"]


def test_target_discovery_exposes_observed_acf_relationships_without_making_them_writable(
    monkeypatch,
) -> None:
    item = _page("https://dev.ekologus.pl/bdo/").model_copy(
        update={
            "sections": [
                WordPressAuthoringDevSection(
                    section_index=1,
                    acf_field_name="content_sections",
                    layout_name="services",
                    layout_label="Usługi",
                    field_names=["services_order"],
                )
            ]
        }
    )
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL, final_canonical_url=None, page=PUBLIC_URL
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(item),
    )
    monkeypatch.setattr(
        discovery_module,
        "read_wordpress_acf_rest_schema",
        lambda _connector_id, _item: WordPressAcfRestSchema(
            status="available",
            root_field="content_sections",
            layouts=[
                WordPressAcfRestSchemaLayout(
                    name="services",
                    label="Usługi",
                    fields=[
                        WordPressAcfRestSchemaField(
                            name="services_order",
                            label="Kolejność usług",
                            field_type="integer_array",
                        )
                    ],
                )
            ],
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "_source_acf_snapshot",
        lambda _item: WordPressAcfFlexibleSnapshot(
            object_id="346",
            content_type="pages",
            root_field="content_sections",
            root_digest="a" * 64,
            rows=[{"acf_fc_layout": "services", "services_order": [374, 352]}],
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "observe_wordpress_acf_panel_labels",
        lambda _url, _ids: WordPressAcfRelationshipObservation(
            status="available",
            source_url="https://dev.ekologus.pl/bdo/",
            labels_by_id={374: "EKOdokumentacje", 352: "Sprzedaż sorbentów"},
            reason="Publiczny układ dev potwierdza dokładne ID i etykiety relacji ACF.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    surface = discovery.target.target_contract.authoring_surface
    assert surface is not None
    relation = surface.layouts[0].relationships[0]
    assert relation.field_name == "services_order"
    assert [(item.relationship_id, item.label) for item in relation.items] == [
        (374, "EKOdokumentacje"),
        (352, "Sprzedaż sorbentów"),
    ]
    assert surface.layouts[0].writable_fields == []


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


def test_target_discovery_does_not_claim_no_match_when_dev_inventory_is_blocked(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    profile = _profile()
    profile.dev_content = SimpleNamespace(
        status="blocked",
        items=[],
        blockers=[
            SimpleNamespace(
                reason="WP REST nie odpowiedział podczas odczytu inventory dev.",
                next_step="Sprawdź dostęp do WP REST na dev.",
            )
        ],
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: profile,
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.relation_status == "unavailable"
    assert discovery.target is None
    assert discovery.label == "Nie można teraz odczytać obiektów dev"
    assert discovery.reason == "WP REST nie odpowiedział podczas odczytu inventory dev."
    assert "Nie znaleziono odpowiadającego obiektu" not in (f"{discovery.label} {discovery.reason}")


def test_target_discovery_requires_human_choice_for_same_path_page_and_post(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    page = _page("https://dev.ekologus.pl/bdo/", content_type="page")
    post = page.model_copy(update={"post_id": "347", "content_type": "post"})
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(page, post),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.relation_status == "ambiguous"
    assert discovery.target is None
    assert {candidate.object_id for candidate in discovery.candidates} == {"346", "347"}
    assert all(
        candidate.observation_evidence.evidence_id in discovery.evidence_ids
        for candidate in discovery.candidates
    )


def test_target_discovery_deduplicates_an_exact_repeated_dev_observation(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    item = _page("https://dev.ekologus.pl/bdo/", content_type="post")
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(item, item),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.relation_status == "partial"
    assert discovery.target is not None
    assert discovery.target.object_id == item.post_id
    assert discovery.candidates == []


def test_target_observation_evidence_changes_when_observed_state_changes(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    item = _page("https://dev.ekologus.pl/bdo/", content_type="post")
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(item),
    )
    first = discovery_module.build_content_target_discovery(WORK_ITEM_ID)
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(
            item.model_copy(update={"status": "publish", "modified": "2026-07-24T08:00:00"})
        ),
    )
    second = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert first is not None and first.target is not None
    assert second is not None and second.target is not None
    assert (
        first.target.observation_evidence.evidence_id
        != second.target.observation_evidence.evidence_id
    )


def test_target_discovery_does_not_invent_an_authoring_surface(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    item = _page("https://dev.ekologus.pl/bdo/", content_type="post").model_copy(
        update={"acf_field_name": None, "section_count": 0, "sections": []}
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(item),
    )
    monkeypatch.setattr(discovery_module, "_native_post_content_observed", lambda _item: False)

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    assert discovery.target.observed_surfaces == []
    assert discovery.target.target_contract.authoring_surface is None
