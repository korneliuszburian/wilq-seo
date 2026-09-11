from __future__ import annotations

import json
from contextlib import contextmanager
from hashlib import sha256
from types import SimpleNamespace
from typing import Literal

import httpx
import pytest

import wilq.content.workflow.target.native_content_observation as native_observation_module
import wilq.content.workflow.target.target_discovery as discovery_module
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


@pytest.fixture(autouse=True)
def _disable_live_acf_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery_module, "read_wordpress_acf_rest_schema", lambda *_args: None)
    monkeypatch.setattr(discovery_module, "_source_acf_snapshot", lambda _item: None)


def _profile(*items: WordPressAuthoringDevContentObject) -> SimpleNamespace:
    return SimpleNamespace(
        authoring_target="dev",
        evidence_ids=["ev_wordpress_dev_read"],
        acf=SimpleNamespace(flexible_content_field_name=None, layouts=[]),
        dev_content=SimpleNamespace(status="available", items=list(items), blockers=[]),
    )


class _NativeResponseClient:
    def __init__(
        self,
        response: object,
        stream_calls: list[tuple[str, dict[str, object]]],
        client_kwargs: list[dict[str, object]],
        **kwargs: object,
    ) -> None:
        self.response = response
        self.stream_calls = stream_calls
        self.client_kwargs = client_kwargs
        client_kwargs.append(kwargs)

    def __enter__(self) -> _NativeResponseClient:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    @contextmanager
    def stream(self, _method: str, url: str, **kwargs: object):
        self.stream_calls.append((url, kwargs))
        yield self.response


def _patch_native_client(monkeypatch, response: object, stream_calls, client_kwargs) -> None:
    monkeypatch.setattr(
        native_observation_module.httpx,
        "Client",
        lambda **kwargs: _NativeResponseClient(response, stream_calls, client_kwargs, **kwargs),
    )


def _page(
    url: str, *, content_type: Literal["page", "post"] = "page"
) -> WordPressAuthoringDevContentObject:
    return WordPressAuthoringDevContentObject(
        post_id="346",
        content_type=content_type,
        rest_endpoint="posts" if content_type == "post" else "pages",
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
            _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post")
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.relation_status == "partial"
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
            _page("https://ekologus.dev.proudsite.pl/bdo/")
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
    post = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post").model_copy(
        update={"acf_field_name": None, "section_count": 0, "sections": []}
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(post),
    )
    monkeypatch.setattr(
        discovery_module,
        "_native_post_content_observation",
        lambda _item: discovery_module._NativePostContentObservation(
            status="available",
            source_ref="https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346",
            blocker_code=None,
            reason="Treść jest dostępna.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    surface = discovery.target.target_contract.authoring_surface
    assert surface is not None
    assert surface.kind == "wordpress_post_content"
    assert surface.root_field == "content"
    assert surface.layouts[0].fields == ["title", "content_html"]


def test_native_post_content_get_is_limited_to_https_dev_host(monkeypatch) -> None:
    stream_calls: list[tuple[str, dict[str, object]]] = []
    client_kwargs: list[dict[str, object]] = []
    response = httpx.Response(
        200,
        json={"id": 346, "content": {"rendered": "<p>Treść dev</p>"}},
        request=httpx.Request(
            "GET", "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346"
        ),
    )
    _patch_native_client(monkeypatch, response, stream_calls, client_kwargs)
    allowed = _page(
        "https://ekologus.dev.proudsite.pl/bdo/", content_type="post"
    )
    foreign = allowed.model_copy(update={"link": "https://attacker.example/bdo/"})
    insecure = allowed.model_copy(
        update={"link": "http://ekologus.dev.proudsite.pl/bdo/"}
    )
    with_userinfo = allowed.model_copy(
        update={
            "link": "https://" + "user:" + "password" + "@ekologus.dev.proudsite.pl/bdo/"
        }
    )

    assert discovery_module._native_post_content_observed(foreign) is False
    assert discovery_module._native_post_content_observed(insecure) is False
    assert discovery_module._native_post_content_observed(with_userinfo) is False
    assert stream_calls == []
    assert discovery_module._native_post_content_observed(allowed) is True
    assert [call[0] for call in stream_calls] == [
        "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346"
    ]
    assert client_kwargs == [{"timeout": 3, "follow_redirects": False}]
    assert stream_calls[0][1] == {
        "params": {"_fields": "id,content"},
        "follow_redirects": False,
    }


def test_native_page_content_get_uses_the_pages_rest_endpoint(monkeypatch) -> None:
    stream_calls: list[tuple[str, dict[str, object]]] = []
    client_kwargs: list[dict[str, object]] = []
    response = httpx.Response(
        200,
        json={"id": 346, "content": {"rendered": "<p>Treść strony dev</p>"}},
        request=httpx.Request(
            "GET", "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/pages/346"
        ),
    )
    _patch_native_client(monkeypatch, response, stream_calls, client_kwargs)
    page = _page(
        "https://ekologus.dev.proudsite.pl/bdo/",
        content_type="page",
    ).model_copy(update={"acf_field_name": None, "section_count": 0, "sections": []})

    assert discovery_module._native_post_content_observed(page) is True
    assert [call[0] for call in stream_calls] == [
        "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/pages/346"
    ]
    assert client_kwargs == [{"timeout": 3, "follow_redirects": False}]
    assert stream_calls[0][1]["params"] == {"_fields": "id,content"}
    assert stream_calls[0][1]["follow_redirects"] is False


def test_target_discovery_exposes_native_page_content_surface(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL,
            final_canonical_url=None,
            page=PUBLIC_URL,
        ),
    )
    page = _page(
        "https://ekologus.dev.proudsite.pl/bdo/",
        content_type="page",
    ).model_copy(update={"acf_field_name": None, "section_count": 0, "sections": []})
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(page),
    )
    monkeypatch.setattr(
        discovery_module,
        "_native_post_content_observation",
        lambda _item: discovery_module._NativePostContentObservation(
            status="available",
            source_ref="https://ekologus.dev.proudsite.pl/wp-json/wp/v2/pages/346",
            blocker_code=None,
            reason="Treść jest dostępna.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    surface = discovery.target.target_contract.authoring_surface
    assert surface is not None
    assert surface.kind == "wordpress_post_content"
    assert surface.root_field == "content"


def test_target_discovery_exposes_observed_acf_relationships_without_making_them_writable(
    monkeypatch,
) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/").model_copy(
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
            fields_digest="b" * 64,
            fields={
                "content_sections": [
                    {"acf_fc_layout": "services", "services_order": [374, 352]}
                ],
                "icon": 1126,
            },
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
    assert surface.source_acf_fields_digest == "b" * 64
    assert surface.source_acf_root_field_count == 2
    assert surface.source_acf_row_count == 1


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
            _page("https://ekologus.dev.proudsite.pl/inna-strona/")
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.relation_status == "unavailable"
    assert discovery.target is None
    assert discovery.evidence_ids == ["ev_wordpress_dev_read"]


def test_target_discovery_reports_missing_public_canonical_as_typed_blocker(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=None, final_canonical_url=None, page=None
        ),
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.relation_status == "unavailable"
    assert discovery.blocker_code == "missing_public_canonical"


def test_target_discovery_rejects_foreign_matching_dev_url(monkeypatch) -> None:
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
        lambda _connector_id, include_dev_content=False: _profile(
            _page("https://attacker.example/bdo/")
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.relation_status == "unavailable"
    assert discovery.target is None
    assert discovery.blocker_code == "wordpress_dev_target_url_invalid"


def test_target_discovery_rejects_malformed_inventory_url_without_raising(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery_module,
        "inventory_decision_for_work_item",
        lambda _work_item_id, **_kwargs: SimpleNamespace(
            source_public_url=PUBLIC_URL, final_canonical_url=None, page=PUBLIC_URL
        ),
    )
    malformed = _page("https://[")
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(malformed),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None
    assert discovery.target is None
    assert discovery.blocker_code == "wordpress_dev_target_url_invalid"


def test_native_post_content_rejects_non_decimal_post_id_without_request(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post").model_copy(
        update={"post_id": "346/../../wp-json/wp/v2/users/1"}
    )
    monkeypatch.setattr(
        native_observation_module.httpx,
        "Client",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("request was made")),
    )

    observation = discovery_module._native_post_content_observation(item)

    assert observation.status == "unavailable"
    assert observation.blocker_code == "wordpress_native_content_target_invalid"


def test_native_post_content_rejects_mismatched_response_identity(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post")
    response = httpx.Response(
        200,
        json={"id": 999, "content": {"rendered": "<p>Nie ten obiekt</p>"}},
        request=httpx.Request(
            "GET", "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346"
        ),
    )
    _patch_native_client(monkeypatch, response, [], [])

    observation = discovery_module._native_post_content_observation(item)

    assert observation.status == "unavailable"
    assert observation.blocker_code == "wordpress_native_content_identity_mismatch"


def test_target_discovery_rejects_invalid_post_id_before_emitting_identity(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post").model_copy(
        update={"post_id": ""}
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

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is None
    assert discovery.blocker_code == "wordpress_dev_target_id_invalid"


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
                code="wordpress_dev_content_rest_failed",
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

    assert discovery is not None and discovery.relation_status == "unavailable"
    assert discovery.target is None
    assert discovery.label == "Nie można teraz odczytać obiektów dev"
    assert discovery.blocker_code == "wordpress_dev_content_rest_failed"
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
    page = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="page").model_copy(
        update={"acf_field_name": None, "section_count": 0, "sections": []}
    )
    post = page.model_copy(update={"post_id": "347", "content_type": "post"})
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(page, post),
    )
    native_calls: list[str] = []
    monkeypatch.setattr(
        discovery_module,
        "_native_post_content_observation",
        lambda item: native_calls.append(item.post_id)
        or discovery_module._NativePostContentObservation(
            status="available",
            source_ref=item.link,
            blocker_code=None,
            reason="Treść jest dostępna.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.relation_status == "ambiguous"
    assert discovery.target is None
    assert {candidate.object_id for candidate in discovery.candidates} == {"346", "347"}
    assert native_calls == []
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
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post")
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
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post")
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
    item = _page("https://ekologus.dev.proudsite.pl/bdo/", content_type="post").model_copy(
        update={"acf_field_name": None, "section_count": 0, "sections": []}
    )
    monkeypatch.setattr(
        discovery_module,
        "build_wordpress_authoring_profile",
        lambda _connector_id, include_dev_content=False: _profile(item),
    )
    monkeypatch.setattr(
        discovery_module,
        "_native_post_content_observation",
        lambda _item: discovery_module._NativePostContentObservation(
            status="unavailable",
            source_ref="https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346",
            blocker_code="wordpress_native_content_http_error",
            reason="REST nie udostępnił treści.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    assert discovery.target.observed_surfaces == []
    assert discovery.target.target_contract.authoring_surface is None


def test_native_post_content_failures_are_typed_and_fail_closed(monkeypatch) -> None:
    item = _page(
        "https://ekologus.dev.proudsite.pl/bdo/", content_type="post"
    ).model_copy(update={"acf_field_name": None, "section_count": 0, "sections": []})
    request = httpx.Request(
        "GET", "https://ekologus.dev.proudsite.pl/wp-json/wp/v2/posts/346"
    )

    _patch_native_client(monkeypatch, httpx.Response(503, request=request), [], [])
    assert (
        discovery_module._native_post_content_observation(item).blocker_code
        == "wordpress_native_content_http_error"
    )

    _patch_native_client(
        monkeypatch,
        httpx.Response(
            302,
            headers={"location": "https://attacker.example/wp-json/wp/v2/posts/346"},
            request=request,
        ),
        [],
        [],
    )
    assert (
        discovery_module._native_post_content_observation(item).blocker_code
        == "wordpress_native_content_redirect"
    )

    _patch_native_client(
        monkeypatch, httpx.Response(200, content=b"not-json", request=request), [], []
    )
    assert (
        discovery_module._native_post_content_observation(item).blocker_code
        == "wordpress_native_content_invalid_payload"
    )
    _patch_native_client(
        monkeypatch,
        httpx.Response(200, content=b"x" * 1_000_001, request=request),
        [],
        [],
    )
    assert (
        discovery_module._native_post_content_observation(item).blocker_code
        == "wordpress_native_content_response_too_large"
    )


def test_native_post_content_blocker_reaches_discovery(monkeypatch) -> None:
    item = _page(
        "https://ekologus.dev.proudsite.pl/bdo/", content_type="page"
    ).model_copy(update={"acf_field_name": None, "section_count": 0, "sections": []})
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
    native_calls: list[str] = []
    monkeypatch.setattr(
        discovery_module,
        "_native_post_content_observation",
        lambda _item: native_calls.append(_item.post_id)
        or discovery_module._NativePostContentObservation(
            status="unavailable",
            source_ref="https://ekologus.dev.proudsite.pl/wp-json/wp/v2/pages/346",
            blocker_code="wordpress_native_content_http_error",
            reason="REST nie udostępnił treści.",
        ),
    )

    discovery = discovery_module.build_content_target_discovery(WORK_ITEM_ID)

    assert discovery is not None and discovery.target is not None
    assert discovery.blocker_code == "wordpress_native_content_http_error"
    assert discovery.target.target_contract.authoring_surface is None
    assert "REST nie udostępnił treści" in discovery.reason
    assert native_calls == ["346"]


def test_unavailable_acf_relationship_is_retained_without_outbound_unsafe_read(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/").model_copy(
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
    schema = WordPressAcfRestSchema(
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
    )
    snapshot = WordPressAcfFlexibleSnapshot(
        object_id="346",
        content_type="pages",
        root_field="content_sections",
        root_digest="a" * 64,
        rows=[{"acf_fc_layout": "services", "services_order": [374]}],
        fields_digest="b" * 64,
        fields={},
    )
    monkeypatch.setattr(
        discovery_module,
        "observe_wordpress_acf_panel_labels",
        lambda _url, _ids: WordPressAcfRelationshipObservation(
            status="unavailable",
            source_url="https://ekologus.dev.proudsite.pl/bdo/",
            labels_by_id={},
            reason="Publiczny układ nie potwierdza relacji.",
        ),
    )
    relationships = discovery_module._observed_relationships(
        item, acf_schema=schema, source_snapshot=snapshot
    )
    relationship = relationships[1][0]
    assert relationship.status == "unavailable"
    assert relationship.items == []
    assert relationship.reason == "Publiczny układ nie potwierdza relacji."

    unsafe_item = item.model_copy(update={"link": "https://attacker.example/bdo/"})
    monkeypatch.setattr(
        discovery_module,
        "observe_wordpress_acf_panel_labels",
        lambda *_args: (_ for _ in ()).throw(AssertionError("unsafe URL was requested")),
    )
    unsafe_relationship = discovery_module._observed_relationships(
        unsafe_item, acf_schema=schema, source_snapshot=snapshot
    )[1][0]
    assert unsafe_relationship.status == "unavailable"
    assert unsafe_relationship.source_ref == ""


def test_acf_observations_ignore_sections_from_a_different_root(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/").model_copy(
        update={
            "sections": [
                WordPressAuthoringDevSection(
                    section_index=1,
                    acf_field_name="content_sections",
                    layout_name="services",
                    layout_label="Usługi",
                    field_names=["services_order"],
                ),
                WordPressAuthoringDevSection(
                    section_index=2,
                    acf_field_name="other_sections",
                    layout_name="services",
                    layout_label="Obcy root",
                    field_names=["services_order"],
                ),
            ]
        }
    )
    schema = WordPressAcfRestSchema(
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
    )
    snapshot = WordPressAcfFlexibleSnapshot(
        object_id="346",
        content_type="pages",
        root_field="content_sections",
        root_digest="a" * 64,
        rows=[
            {"acf_fc_layout": "services", "services_order": [374]},
            {"acf_fc_layout": "services", "services_order": [352]},
        ],
        fields_digest="b" * 64,
        fields={},
    )
    monkeypatch.setattr(
        discovery_module,
        "observe_wordpress_acf_panel_labels",
        lambda _url, ids: WordPressAcfRelationshipObservation(
            status="available",
            source_url="https://ekologus.dev.proudsite.pl/bdo/",
            labels_by_id={value: str(value) for value in ids},
            reason="Relacja potwierdzona.",
        ),
    )

    relationships = discovery_module._observed_relationships(
        item, acf_schema=schema, source_snapshot=snapshot
    )
    writable_fields, _reason = discovery_module._acf_writable_fields(
        item, acf_schema=schema, source_acf_digest="a" * 64
    )

    assert sorted(relationships) == [1]
    assert relationships[1][0].items[0].relationship_id == 374
    assert writable_fields == {}


def test_acf_relationship_items_dedupe_ids_before_dashboard_render(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/").model_copy(
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
    schema = WordPressAcfRestSchema(
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
    )
    snapshot = WordPressAcfFlexibleSnapshot(
        object_id="346",
        content_type="pages",
        root_field="content_sections",
        root_digest="a" * 64,
        rows=[{"acf_fc_layout": "services", "services_order": [374, 374]}],
        fields_digest="b" * 64,
        fields={},
    )
    monkeypatch.setattr(
        discovery_module,
        "observe_wordpress_acf_panel_labels",
        lambda _url, ids: WordPressAcfRelationshipObservation(
            status="available",
            source_url="https://ekologus.dev.proudsite.pl/bdo/",
            labels_by_id={374: "EKOdokumentacje"},
            reason="Relacja potwierdzona.",
        ),
    )

    relationships = discovery_module._observed_relationships(
        item, acf_schema=schema, source_snapshot=snapshot
    )

    assert [entry.relationship_id for entry in relationships[1][0].items] == [374]


def test_acf_relationship_observation_skips_non_positive_section_index(monkeypatch) -> None:
    item = _page("https://ekologus.dev.proudsite.pl/bdo/").model_copy(
        update={
            "sections": [
                WordPressAuthoringDevSection(
                    section_index=0,
                    acf_field_name="content_sections",
                    layout_name="services",
                    layout_label="Usługi",
                    field_names=["services_order"],
                )
            ]
        }
    )
    schema = WordPressAcfRestSchema(
        status="available",
        root_field="content_sections",
        layouts=[WordPressAcfRestSchemaLayout(name="services", label="Usługi")],
    )
    snapshot = WordPressAcfFlexibleSnapshot(
        object_id="346",
        content_type="pages",
        root_field="content_sections",
        root_digest="a" * 64,
        rows=[{"acf_fc_layout": "services", "services_order": [374]}],
        fields_digest="b" * 64,
        fields={},
    )

    assert discovery_module._observed_relationships(
        item, acf_schema=schema, source_snapshot=snapshot
    ) == {}
