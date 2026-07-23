from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_authoring import (
    build_content_wordpress_authoring_payload_preview,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
)

WORDPRESS_AUTHORING_ENV = (
    "WORDPRESS_EKOLOGUS_URL",
    "WORDPRESS_EKOLOGUS_PUBLIC_URL",
    "WORDPRESS_EKOLOGUS_USERNAME",
    "WORDPRESS_EKOLOGUS_APP_PASSWORD",
    "WORDPRESS_EKOLOGUS_DISCOVERY_MODE",
    "WORDPRESS_EKOLOGUS_AUTHORING_TARGET",
    "WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES",
    "WORDPRESS_EKOLOGUS_ACF_ENABLED",
    "WORDPRESS_EKOLOGUS_ACF_REST_ENABLED",
    "WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH",
    "WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME",
    "WORDPRESS_EKOLOGUS_ACF_POST_TYPES",
    "WORDPRESS_EKOLOGUS_SSH_HOST",
    "WORDPRESS_EKOLOGUS_SSH_PORT",
    "WORDPRESS_EKOLOGUS_SSH_USER",
    "WORDPRESS_EKOLOGUS_SSH_KEY_PATH",
    "WORDPRESS_EKOLOGUS_SSH_PASSWORD",
    "WORDPRESS_EKOLOGUS_DOCROOT",
    "WORDPRESS_EKOLOGUS_WP_CLI_PATH",
    "WORDPRESS_EKOLOGUS_WP_CLI_PHP_PATH",
    "WORDPRESS_EKOLOGUS_WP_CLI_WORKING",
    "WORDPRESS_EKOLOGUS_HELPER_PLUGIN_ALLOWED",
    "WORDPRESS_EKOLOGUS_HELPER_PLUGIN_SHARED_SECRET",
    "EKOLOGUS_WP_STAGING_URL",
    "EKOLOGUS_WP_STAGING_USER",
    "EKOLOGUS_WP_STAGING_APP_PASSWORD",
    "MIS_PRIMARY_SITE_URL",
)


@pytest.fixture(autouse=True)
def isolated_wordpress_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty-access-pack"))
    for name in WORDPRESS_AUTHORING_ENV:
        monkeypatch.setenv(name, "")


def test_wordpress_authoring_profile_is_rest_first_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_rest(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_POST_TYPES", "page,post")

    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert profile.profile_version == "wordpress_authoring_profile_v1"
    assert profile.discovery_order == ["rest", "acf_rest", "wp_cli", "helper"]
    assert profile.rest_api.status == "configured"
    assert profile.rest_api.post_types == ["page", "post"]
    assert [fact.method for fact in profile.discovery_facts[:4]] == [
        "rest",
        "acf_rest",
        "wp_cli",
        "helper",
    ]
    assert profile.write_boundary.direct_vendor_write_allowed is False
    assert profile.write_boundary.live_write_enabled is False
    assert profile.write_boundary.publish_allowed is False
    assert profile.write_boundary.external_write_attempted is False
    assert profile.evidence_ids == ["ev_connector_wordpress_ekologus_status"]
    assert profile.source_connectors == ["wordpress_ekologus"]


def test_wordpress_authoring_profile_blocks_missing_acf_layouts() -> None:
    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert "wordpress_rest_not_configured" in {blocker.code for blocker in profile.blockers}
    assert "acf_flexible_layouts_missing" in {blocker.code for blocker in profile.blockers}
    assert profile.acf.layouts == []
    assert profile.wp_cli.status == "not_configured"
    assert profile.helper_plugin.status == "not_configured"


def test_wordpress_authoring_profile_marks_wp_cli_fallback_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_rest(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_HOST", "ssh.example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_USER", "deploy")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_PASSWORD", "password-only-test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_DOCROOT", "public_html")

    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert profile.wp_cli.status == "configured"
    assert profile.wp_cli.configured is True
    assert "acf_flexible_layouts_missing_wp_cli_ready" in {
        blocker.code for blocker in profile.blockers
    }


def test_wordpress_authoring_profile_does_not_mark_broken_wp_cli_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_rest(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_HOST", "ssh.example.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_USER", "deploy")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_SSH_PASSWORD", "password-only-test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_DOCROOT", "public_html")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_WP_CLI_PATH", "/usr/local/bin/wp")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_WP_CLI_WORKING", "false")

    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert profile.wp_cli.status == "not_configured"
    assert profile.wp_cli.configured is False
    assert "WORDPRESS_EKOLOGUS_WP_CLI_WORKING" in profile.wp_cli.missing_env
    assert "acf_flexible_layouts_missing_wp_cli_ready" not in {
        blocker.code for blocker in profile.blockers
    }
    assert "acf_flexible_layouts_missing" in {blocker.code for blocker in profile.blockers}


def test_wordpress_authoring_profile_loads_acf_flexible_layouts_from_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = _write_acf_export(tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME", "sections")

    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert profile.acf.flexible_content_field_name == "sections"
    assert profile.acf.layouts_discovered is True
    assert profile.acf.source_method == "acf_export"
    assert [layout.name for layout in profile.acf.layouts] == ["content_section"]
    layout = profile.acf.layouts[0]
    assert layout.required_field_names == ["heading", "body"]
    assert layout.optional_field_names == ["evidence_ids"]
    assert "acf_export_authoring_layouts" in {fact.id for fact in profile.discovery_facts}
    assert "acf_flexible_layouts_missing" not in {
        blocker.code for blocker in profile.blockers
    }


def test_wordpress_authoring_profile_reads_generic_dev_acf_rest_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_rest(monkeypatch)
    transport = httpx.MockTransport(_dev_pages_acf_rest_handler)
    with httpx.Client(transport=transport) as client:
        profile = build_wordpress_authoring_profile(
            "wordpress_ekologus",
            include_dev_content=True,
            http_client=client,
        )

    assert profile.dev_content.status == "available"
    assert profile.dev_content.source_method == "acf_rest"
    assert profile.dev_content.page_count == 3
    page = profile.dev_content.pages[0]
    assert page.content_type == "page"
    assert page.title == "Strona główna"
    assert page.acf_field_name == "sekcje_strony"
    assert page.section_count == 2
    first_section = page.sections[0]
    assert first_section.layout_name == "baner_startowy"
    assert first_section.layout_label == "Baner startowy"
    assert first_section.title == "Gospodarka odpadami dla firm"
    assert "Zbieramy i porządkujemy odpady" in first_section.text_summary
    assert "modul_naglowka" in first_section.field_names
    assert "obrazek" in first_section.field_names
    assert any("naglowek_modulu" in path for path in first_section.text_field_paths)
    assert "hero" not in {section.layout_name for section in page.sections}
    article = profile.dev_content.pages[1]
    assert article.content_type == "post"
    assert article.slug == "bdo-co-musi-wiedziec-przedsiebiorca"
    assert profile.dev_content.pages[2].slug == "kolejny-artykul"


def test_wordpress_authoring_profile_derives_layouts_from_acf_groups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = tmp_path / "acf-groups.json"
    export_path.write_text(
        json.dumps(
            [
                {
                    "key": "group_page",
                    "title": "Podstrona",
                    "fields": [
                        {
                            "key": "field_page_content",
                            "name": "podstrona",
                            "label": "Podstrona",
                            "type": "group",
                            "required": 0,
                            "sub_fields": [
                                {
                                    "key": "field_heading",
                                    "name": "tytul",
                                    "label": "Tytuł",
                                    "type": "text",
                                    "required": 1,
                                },
                                {
                                    "key": "field_body",
                                    "name": "opis",
                                    "label": "Opis",
                                    "type": "wysiwyg",
                                    "required": 0,
                                },
                            ],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))

    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    assert profile.acf.layouts_discovered is True
    assert [layout.name for layout in profile.acf.layouts] == ["podstrona"]
    layout = profile.acf.layouts[0]
    assert layout.required_field_names == ["tytul"]
    assert layout.optional_field_names == ["opis"]
    assert [field.field_type for field in layout.fields] == ["text", "wysiwyg"]


def test_wordpress_authoring_payload_preview_maps_draft_to_acf_without_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = _write_acf_export(tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME", "sections")
    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    result = build_content_wordpress_authoring_payload_preview(
        handoff=_handoff(),
        draft_package=_draft_package(),
        authoring_profile=profile,
    )

    assert result.status == "ready"
    assert result.mode == "dry_run"
    assert result.post_status == "draft"
    assert result.publish_allowed is False
    assert result.destructive_update_allowed is False
    assert result.external_write_attempted is False
    assert result.flexible_content_field_name == "sections"
    assert result.blockers == []
    assert len(result.sections) == 1
    section = result.sections[0]
    assert section.layout_name == "content_section"
    assert section.field_values["heading"] == "Kogo dotyczy BDO"
    assert "Wyjaśnij obowiązki" in (section.field_values["body"] or "")
    assert "<p>" in (section.field_values["body"] or "")
    assert "**" not in (section.field_values["body"] or "")
    assert section.field_values["evidence_ids"] == "ev_gsc_bdo"
    assert section.missing_required_fields == []


def test_wordpress_authoring_preview_preserves_full_document_assets_and_meta_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = _write_acf_export(tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME", "sections")
    profile = build_wordpress_authoring_profile("wordpress_ekologus")
    document = ContentDraftRevision(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="revision_bdo_v2",
        work_item_id="content_work_item_bdo",
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_package_bdo",
        draft_package_digest="b" * 64,
        planning_input_digest="c" * 64,
        service_card_id="ekologus_service_bdo_reporting",
        service_digest="d" * 64,
        inventory_digest="e" * 64,
        final_canonical_url="https://ekologus.pl/bdo/",
        title="BDO dla firm",
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO dla firm",
            meta_title="BDO dla firm — Ekologus",
            meta_description="Sprawdź obowiązki BDO swojej firmy.",
            h1="BDO dla firm",
            lead="Sprawdź obowiązki BDO swojej firmy.",
        ),
        sections=[ContentDraftRevisionSection(
            section_id="section_bdo",
            heading="Kogo dotyczy BDO",
            body_markdown="Wyjaśnij obowiązki BDO.",
            query_terms=["bdo dla firm"],
            evidence_ids=["ev_gsc_bdo"],
            claim_ids=["claim_bdo_scope"],
        )],
        publish_ready=False,
        created_by="codex",
        created_at=datetime.now(UTC),
    )
    result = build_content_wordpress_authoring_payload_preview(
        handoff=_handoff().model_copy(update={"revision_document": document}),
        draft_package=_draft_package(),
        authoring_profile=profile,
    )

    assert result.page_assets is not None
    assert result.page_assets.meta_title == "BDO dla firm — Ekologus"
    assert result.page_assets.h1 == "BDO dla firm"
    assert result.page_assets.meta_write_status == "review_required"
    assert result.page_assets.metadata_blockers[0].code == "missing_wordpress_meta_mapping"


def test_wordpress_authoring_payload_preview_prefers_content_layout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = tmp_path / "acf-layout-choice.json"
    export_path.write_text(
        json.dumps(
            [
                {
                    "key": "group_scripts",
                    "title": "Dodatkowe skrypty",
                    "fields": [
                        {
                            "key": "field_scripts",
                            "name": "skrypty",
                            "label": "Skrypty",
                            "type": "group",
                            "sub_fields": [
                                {
                                    "key": "field_html_head",
                                    "name": "html_head",
                                    "label": "HTML head",
                                    "type": "textarea",
                                }
                            ],
                        }
                    ],
                },
                {
                    "key": "group_page",
                    "title": "Podstrona",
                    "fields": [
                        {
                            "key": "field_page",
                            "name": "podstrona",
                            "label": "Podstrona",
                            "type": "group",
                            "sub_fields": [
                                {
                                    "key": "field_title",
                                    "name": "tytul",
                                    "label": "Tytuł",
                                    "type": "text",
                                },
                                {
                                    "key": "field_body",
                                    "name": "glowny_opis",
                                    "label": "Główny opis",
                                    "type": "wysiwyg",
                                },
                                {
                                    "key": "field_items",
                                    "name": "elementy",
                                    "label": "Elementy",
                                    "type": "repeater",
                                    "sub_fields": [
                                        {
                                            "key": "field_item_body",
                                            "name": "opis",
                                            "label": "Opis",
                                            "type": "wysiwyg",
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    result = build_content_wordpress_authoring_payload_preview(
        handoff=_handoff(),
        draft_package=_draft_package(),
        authoring_profile=profile,
    )

    assert result.status == "ready"
    assert result.sections[0].layout_name == "podstrona"
    assert result.sections[0].field_values["tytul"] == "Kogo dotyczy BDO"
    assert "Wyjaśnij obowiązki" in (result.sections[0].field_values["glowny_opis"] or "")
    assert result.sections[0].field_values["elementy"] is None
    previews = {field.field_name: field for field in result.sections[0].field_previews}
    assert previews["tytul"].value_preview == "Kogo dotyczy BDO"
    assert previews["glowny_opis"].safe_to_autofill is True
    assert "Wyjaśnij obowiązki" in (previews["glowny_opis"].value_preview or "")
    assert previews["elementy"].field_type == "repeater"
    assert previews["elementy"].safe_to_autofill is True
    assert "wybór layoutu/wierszy" in (previews["elementy"].note or "")
    repeater_nested = {field.field_name: field for field in previews["elementy"].nested_values}
    assert "Wyjaśnij obowiązki" in (repeater_nested["opis"].value_preview or "")
    row_candidates = previews["elementy"].row_candidates
    assert len(row_candidates) == 1
    assert row_candidates[0].row_type == "acf_repeater_row"
    assert row_candidates[0].review_status == "review_required"
    assert row_candidates[0].evidence_ids == ["ev_gsc_bdo"]
    assert "nie zapisuje nic w WordPress" in row_candidates[0].note
    assert [field.field_name for field in row_candidates[0].field_values] == ["opis"]


def test_wordpress_authoring_payload_preview_blocks_without_acf_contract() -> None:
    result = build_content_wordpress_authoring_payload_preview(
        handoff=_handoff(),
        draft_package=_draft_package(),
        authoring_profile=build_wordpress_authoring_profile("wordpress_ekologus"),
    )

    assert result.status == "blocked"
    assert result.external_write_attempted is False
    assert {
        "acf_flexible_field_name_missing",
        "acf_flexible_layouts_missing",
    }.issubset({blocker.code for blocker in result.blockers})


def test_wordpress_authoring_profile_api_exposes_read_only_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = _write_acf_export(tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME", "sections")
    from apps.api.wilq_api.routers import content_workflow

    monkeypatch.setattr(
        content_workflow,
        "build_wordpress_authoring_profile",
        lambda connector_id, include_dev_content=False: build_wordpress_authoring_profile(
            connector_id,
            include_dev_content=False,
        ),
    )

    response = TestClient(app).get("/api/content/wordpress/authoring-profile")

    assert response.status_code == 200
    data = response.json()
    assert data["profile_version"] == "wordpress_authoring_profile_v1"
    assert data["acf"]["layouts"][0]["name"] == "content_section"
    assert data["dev_content"]["status"] == "unknown"
    assert data["write_boundary"]["direct_vendor_write_allowed"] is False
    assert data["write_boundary"]["external_write_attempted"] is False


def test_wordpress_authoring_payload_preview_api_is_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_rest(monkeypatch)
    export_path = _write_acf_export(tmp_path)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FIELD_GROUPS_EXPORT_PATH", str(export_path))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME", "sections")
    profile = build_wordpress_authoring_profile("wordpress_ekologus")

    response = TestClient(app).post(
        "/api/content/work-items/wordpress-authoring-payload-preview",
        json={
            "handoff": _handoff().model_dump(mode="json"),
            "draft_package": _draft_package().model_dump(mode="json"),
            "authoring_profile": profile.model_dump(mode="json"),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preview_result"]["status"] == "ready"
    assert data["preview_result"]["mode"] == "dry_run"
    assert data["preview_result"]["external_write_attempted"] is False
    assert data["preview_result"]["sections"][0]["layout_name"] == "content_section"


def _configure_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://wp.example.test/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.example.test/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")


def _dev_pages_acf_rest_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/wp-json/wp/v2/posts":
        page = request.url.params.get("page", "1")
        if page == "2":
            return httpx.Response(
                200,
                headers={"X-WP-TotalPages": "2"},
                json=[
                    {
                        "id": 4,
                        "slug": "kolejny-artykul",
                        "link": "https://wp.example.test/kolejny-artykul/",
                        "title": {"rendered": "Kolejny artykuł"},
                        "status": "publish",
                        "modified": "2026-07-08T10:00:00",
                        "modified_gmt": "2026-07-08T08:00:00",
                        "template": "",
                        "parent": 0,
                        "acf": {},
                    }
                ],
            )
        return httpx.Response(
            200,
            headers={"X-WP-TotalPages": "2"},
            json=[
                {
                    "id": 3,
                    "slug": "bdo-co-musi-wiedziec-przedsiebiorca",
                    "link": "https://wp.example.test/bdo-co-musi-wiedziec-przedsiebiorca/",
                    "title": {"rendered": "BDO"},
                    "status": "publish",
                    "modified": "2026-07-08T10:00:00",
                    "modified_gmt": "2026-07-08T08:00:00",
                    "template": "",
                    "parent": 0,
                    "acf": {},
                }
            ],
        )
    assert request.url.path == "/wp-json/wp/v2/pages"
    return httpx.Response(
        200,
        json=[
            {
                "id": 2,
                "slug": "strona-glowna",
                "link": "https://wp.example.test/",
                "title": {"rendered": "Strona główna"},
                "status": "publish",
                "modified": "2026-07-08T10:00:00",
                "modified_gmt": "2026-07-08T08:00:00",
                "template": "",
                "parent": 0,
                "acf": {
                    "sekcje_strony": [
                        {
                            "acf_fc_layout": "baner_startowy",
                            "modul_naglowka": {
                                "naglowek_modulu": "Gospodarka odpadami dla firm",
                                "tekst_wprowadzajacy": (
                                    "Zbieramy i porządkujemy odpady zgodnie z procesem klienta."
                                ),
                            },
                            "obrazek": "https://wp.example.test/media/hero.jpg",
                        },
                        {
                            "acf_fc_layout": "lista_korzysci",
                            "wiersze": [
                                {
                                    "tytul_wiersza": "Stały odbiór",
                                    "opis_wiersza": "Harmonogram i dokumentacja w jednym miejscu.",
                                }
                            ],
                        },
                    ]
                },
            }
        ],
    )


def _write_acf_export(tmp_path: Path) -> Path:
    export_path = tmp_path / "acf-field-groups.json"
    export_path.write_text(
        json.dumps(
            [
                {
                    "key": "group_content",
                    "title": "Content sections",
                    "fields": [
                        {
                            "key": "field_sections",
                            "name": "sections",
                            "type": "flexible_content",
                            "layouts": {
                                "layout_content_section": {
                                    "key": "layout_content_section",
                                    "name": "content_section",
                                    "label": "Sekcja treści",
                                    "sub_fields": [
                                        {
                                            "key": "field_heading",
                                            "name": "heading",
                                            "label": "Nagłówek",
                                            "type": "text",
                                            "required": 1,
                                        },
                                        {
                                            "key": "field_body",
                                            "name": "body",
                                            "label": "Treść",
                                            "type": "wysiwyg",
                                            "required": 1,
                                        },
                                        {
                                            "key": "field_evidence",
                                            "name": "evidence_ids",
                                            "label": "Dowody",
                                            "type": "text",
                                            "required": 0,
                                        },
                                    ],
                                }
                            },
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    return export_path


def _handoff() -> ContentWordPressDraftHandoff:
    return ContentWordPressDraftHandoff(
        id="wordpress_draft_handoff_content_work_item_bdo",
        work_item_id="content_work_item_bdo",
        draft_package_id="draft_package_bdo",
        human_review_id="human_review_bdo",
        audit_id="audit_bdo",
        title="BDO dla firm",
        final_canonical_url="https://ekologus.pl/bdo/",
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
    )


def _draft_package() -> ContentDraftPackage:
    return ContentDraftPackage(
        id="draft_package_bdo",
        work_item_id="content_work_item_bdo",
        brief_id="sales_brief_bdo",
        claim_ledger_id="claim_ledger_bdo",
        title="BDO dla firm",
        sections=[
            {
                "heading": "Kogo dotyczy BDO",
                "purpose": "Wyjaśnij obowiązki BDO bez obietnicy wyniku.",
                "evidence_ids": ["ev_gsc_bdo"],
                "draft_notes": ["CTA: konsultacja obowiązków."],
            }
        ],
        section_to_evidence_map=[
            {
                "section_heading": "Kogo dotyczy BDO",
                "evidence_ids": ["ev_gsc_bdo"],
            }
        ],
        claims_used=[],
        publish_ready=False,
    )
