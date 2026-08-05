from __future__ import annotations

import httpx
import pytest

from wilq.connectors.wordpress.acf_rest_schema import read_wordpress_acf_rest_schema
from wilq.connectors.wordpress.authoring import WordPressAuthoringDevContentObject


def test_options_schema_normalizes_exact_flexible_layouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://wp.example.test/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    item = WordPressAuthoringDevContentObject(
        post_id="2",
        content_type="page",
        slug="strona-glowna",
        title="Strona główna",
        link="https://wp.example.test/",
        status="publish",
        modified="2026-08-05T10:00:00",
        modified_gmt="2026-08-05T08:00:00",
        acf_field_name="flexible-home",
    )

    with httpx.Client(transport=httpx.MockTransport(_options_handler)) as client:
        schema = read_wordpress_acf_rest_schema(
            "wordpress_ekologus", item, http_client=client
        )

    assert schema.status == "available"
    assert schema.root_field == "flexible-home"
    assert schema.schema_digest is not None
    assert [(layout.name, layout.required_field_names) for layout in schema.layouts] == [
        ("hero", ["heading"])
    ]
    assert [(field.name, field.field_type) for field in schema.layouts[0].fields] == [
        ("heading", "string"),
        ("settings", "object"),
    ]
    assert [field.name for field in schema.layouts[0].fields[1].sub_fields] == ["tone"]


def _options_handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "OPTIONS"
    assert request.url.path == "/wp-json/wp/v2/pages/2"
    return httpx.Response(
        200,
        json={
            "schema": {
                "properties": {
                    "acf": {
                        "properties": {
                            "flexible-home": {
                                "type": ["array", "null"],
                                "items": {
                                    "oneOf": [
                                        {
                                            "properties": {
                                                "acf_fc_layout": {"pattern": "^hero$"},
                                                "heading": {
                                                    "type": ["string", "null"],
                                                    "required": True,
                                                },
                                                "settings": {
                                                    "type": ["object", "null"],
                                                    "properties": {
                                                        "tone": {"type": ["string", "null"]}
                                                    },
                                                },
                                                "": {"type": ["string", "null"]},
                                            },
                                            "required": ["acf_fc_layout", "heading"],
                                        }
                                    ]
                                },
                            }
                        }
                    }
                }
            }
        },
    )
