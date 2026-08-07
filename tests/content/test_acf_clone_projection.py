from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import httpx
import pytest

from wilq.connectors.wordpress.acf_source_snapshot import WordPressAcfFlexibleSnapshot
from wilq.connectors.wordpress.client import (
    WordPressDraftWriteError,
    create_wordpress_acf_draft,
)
from wilq.content.workflow.acf_clone_projection import (
    ContentAcfClonePlan,
    ContentAcfCloneReplacement,
    compile_acf_clone_payload,
)


def _snapshot(*, digest: str = "a" * 64) -> WordPressAcfFlexibleSnapshot:
    return WordPressAcfFlexibleSnapshot(
        object_id="2",
        content_type="pages",
        root_field="flexible-home",
        root_digest=digest,
        rows=[
            {
                "acf_fc_layout": "cta",
                "content": "Pierwsze CTA",
                "image": 101,
                "settings": {"theme": "dark"},
            },
            {
                "acf_fc_layout": "cta",
                "content": "Drugie CTA",
                "image": 202,
                "settings": {"theme": "light"},
            },
        ],
    )


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _full_snapshot() -> WordPressAcfFlexibleSnapshot:
    rows: list[dict[str, object]] = [
        {
            "acf_fc_layout": "hero",
            "heading": "Bezpieczna gospodarka odpadami",
            "lead": "Wsparcie dla firm i instytucji.",
            "image": 1101,
            "background_type": "image",
        },
        {
            "acf_fc_layout": "services",
            "heading": "Zakres usług",
            "items": [
                {"title": "Audyty", "icon": 1201, "url": "/audyty/"},
                {"title": "Doradztwo", "icon": 1202, "url": "/doradztwo/"},
                {"title": "Szkolenia", "icon": 1203, "url": "/szkolenia/"},
            ],
        },
        {
            "acf_fc_layout": "stats",
            "heading": "Doświadczenie",
            "items": [
                {"value": "15", "label": "lat praktyki"},
                {"value": "600", "label": "obsłużonych organizacji"},
            ],
        },
        {
            "acf_fc_layout": "about",
            "heading": "O zespole",
            "content": "Łączymy wiedzę prawną i środowiskową.",
            "image": {"id": 1301, "alt": "Zespół przy pracy"},
        },
        {
            "acf_fc_layout": "cta",
            "heading": "Potrzebujesz konsultacji?",
            "text": "Porozmawiaj z ekspertem.",
            "button_url": "/kontakt/",
        },
        {
            "acf_fc_layout": "mission",
            "heading": "Nasza misja",
            "content": "Upraszczamy odpowiedzialność środowiskową.",
        },
        {
            "acf_fc_layout": "partners",
            "heading": "Partnerzy",
            "logos": [1401, 1402, 1403],
        },
        {
            "acf_fc_layout": "newsletter",
            "heading": "Wiedza w skrzynce",
            "form_id": 1501,
            "consent_text": "Chcę otrzymywać informacje.",
        },
        {
            "acf_fc_layout": "database",
            "heading": "Baza wiedzy",
            "post_ids": [1601, 1602, 1603],
            "button_label": "Zobacz materiały",
        },
    ]
    fields: dict[str, object] = {
        "flexible-home": rows,
        "page_title": "Strona główna",
        "meta": {
            "description": "Syntetyczny opis strony do testu.",
            "featured_image": 1701,
        },
    }
    return WordPressAcfFlexibleSnapshot(
        object_id="2001",
        content_type="pages",
        root_field="flexible-home",
        root_digest=_digest(rows),
        rows=rows,
        fields_digest=_digest(fields),
        fields=fields,
    )


def _full_clone_plan(
    snapshot: WordPressAcfFlexibleSnapshot,
    *,
    replacements: list[ContentAcfCloneReplacement] | None = None,
) -> ContentAcfClonePlan:
    return ContentAcfClonePlan(
        source_object_id=snapshot.object_id,
        root_field=snapshot.root_field,
        source_acf_digest=snapshot.root_digest,
        source_acf_fields_digest=snapshot.fields_digest,
        replacements=replacements
        or [
            ContentAcfCloneReplacement(
                section_index=1,
                layout_name="hero",
                field_name="heading",
                value="Nowy nagłówek strony",
                value_kind="plain_text",
            ),
            ContentAcfCloneReplacement(
                section_index=5,
                layout_name="cta",
                field_name="text",
                value="Umów bezpieczną konsultację.",
                value_kind="plain_text",
            ),
        ],
    )


def _schema_for_value(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {key: _schema_for_value(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "items": _schema_for_value(value[0]) if value else {},
        }
    if isinstance(value, str):
        return {"type": "string"}
    if type(value) is int:
        return {"type": "integer"}
    raise AssertionError(f"Fixture zawiera nieobsługiwany typ: {type(value).__name__}")


def _full_acf_schema(acf: dict[str, object]) -> dict[str, object]:
    schema = _schema_for_value(acf)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    root_schema = properties["flexible-home"]
    assert isinstance(root_schema, dict)
    rows = acf["flexible-home"]
    assert isinstance(rows, list)
    layout_schemas: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        layout_name = row["acf_fc_layout"]
        assert isinstance(layout_name, str)
        row_schema = _schema_for_value(row)
        row_properties = row_schema["properties"]
        assert isinstance(row_properties, dict)
        layout_schemas.append(
            {
                **row_schema,
                "properties": {
                    **row_properties,
                    "acf_fc_layout": {
                        "type": "string",
                        "pattern": f"^{layout_name}$",
                    },
                },
            }
        )
    root_schema["items"] = {"oneOf": layout_schemas}
    return schema


def _acf_draft_payload(acf: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        connector="wordpress_ekologus",
        endpoint="pages",
        post_status="draft",
        create_only=True,
        publish_allowed=False,
        update_allowed=False,
        delete_allowed=False,
        title="Pełny syntetyczny szkic ACF",
        acf=acf,
    )


def test_full_multi_layout_clone_preserves_unedited_layouts_media_and_siblings() -> None:
    snapshot = _full_snapshot()
    source_rows = deepcopy(snapshot.rows)

    payload = compile_acf_clone_payload(_full_clone_plan(snapshot), snapshot)

    rows = payload["flexible-home"]
    assert isinstance(rows, list)
    assert [row["acf_fc_layout"] for row in rows] == [
        "hero",
        "services",
        "stats",
        "about",
        "cta",
        "mission",
        "partners",
        "newsletter",
        "database",
    ]
    assert rows[0]["heading"] == "Nowy nagłówek strony"
    assert rows[4]["text"] == "Umów bezpieczną konsultację."
    assert rows[5:] == source_rows[5:]
    assert rows[0]["image"] == source_rows[0]["image"] == 1101
    assert rows[0]["background_type"] == source_rows[0]["background_type"] == "image"
    assert rows[1]["items"] == source_rows[1]["items"]
    assert payload["page_title"] == snapshot.fields["page_title"]
    assert payload["meta"] == snapshot.fields["meta"]
    assert snapshot.rows == source_rows


def test_full_multi_layout_readback_subset_match_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl/")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "synthetic-app-password")
    snapshot = _full_snapshot()
    acf_payload = compile_acf_clone_payload(_full_clone_plan(snapshot), snapshot)
    schema = _full_acf_schema(acf_payload)

    def client_for_readback(*, mismatch: bool) -> tuple[httpx.Client, list[httpx.Request]]:
        requests: list[httpx.Request] = []
        sent_acf: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "OPTIONS":
                return httpx.Response(
                    200,
                    json={"endpoints": [{"methods": ["POST"], "args": {"acf": schema}}]},
                )
            if request.method == "POST":
                body = json.loads(request.content)
                assert body == {
                    "status": "draft",
                    "title": "Pełny syntetyczny szkic ACF",
                    "acf": acf_payload,
                }
                sent_acf.update(deepcopy(body["acf"]))
                return httpx.Response(201, json={"id": 3201, "status": "draft"})

            assert request.method == "GET"
            assert request.url.path == "/wp-json/wp/v2/pages/3201"
            observed_acf = deepcopy(sent_acf)
            observed_rows = observed_acf["flexible-home"]
            assert isinstance(observed_rows, list)
            observed_rows[0]["background"] = "default"
            if mismatch:
                observed_rows[4]["text"] = "Wartość zmieniona po zapisie"
            return httpx.Response(
                200,
                json={
                    "id": 3201,
                    "status": "draft",
                    "title": {"raw": "Pełny syntetyczny szkic ACF"},
                    "content": {"raw": ""},
                    "acf": observed_acf,
                },
            )

        return httpx.Client(transport=httpx.MockTransport(handler)), requests

    matching_client, matching_requests = client_for_readback(mismatch=False)
    with matching_client:
        draft_id = create_wordpress_acf_draft(
            _acf_draft_payload(acf_payload),
            action_apply_authorized=True,
            http_client=matching_client,
        )

    assert draft_id == "3201"
    assert [request.method for request in matching_requests] == ["OPTIONS", "POST", "GET"]

    mismatched_client, mismatched_requests = client_for_readback(mismatch=True)
    with mismatched_client, pytest.raises(WordPressDraftWriteError) as exc_info:
        create_wordpress_acf_draft(
            _acf_draft_payload(acf_payload),
            action_apply_authorized=True,
            http_client=mismatched_client,
        )

    assert getattr(exc_info.value, "code", None) == "wordpress_draft_acf_mismatch"
    assert [request.method for request in mismatched_requests] == ["OPTIONS", "POST", "GET"]


def test_single_section_change_keeps_other_sections_digest_stable() -> None:
    snapshot = _full_snapshot()
    source_rows = deepcopy(snapshot.rows)
    source_fields = deepcopy(snapshot.fields)
    root_digest = snapshot.root_digest
    fields_digest = snapshot.fields_digest
    one_replacement = ContentAcfCloneReplacement(
        section_index=1,
        layout_name="hero",
        field_name="heading",
        value="Nagłówek po dokładnie jednej zmianie",
        value_kind="plain_text",
    )

    payload = compile_acf_clone_payload(
        _full_clone_plan(snapshot, replacements=[one_replacement]),
        snapshot,
    )

    rows = payload["flexible-home"]
    assert isinstance(rows, list)
    assert _digest(rows) != root_digest
    assert _digest(payload) != fields_digest
    assert [_digest(row) for row in rows[1:]] == [_digest(row) for row in source_rows[1:]]
    assert _digest({"page_title": payload["page_title"], "meta": payload["meta"]}) == (
        _digest({"page_title": source_fields["page_title"], "meta": source_fields["meta"]})
    )
    assert snapshot.root_digest == root_digest == _digest(source_rows)
    assert snapshot.fields_digest == fields_digest == _digest(source_fields)
    assert snapshot.rows == source_rows
    assert snapshot.fields == source_fields


def test_media_and_repeater_are_never_constructed_by_wilq() -> None:
    snapshot = _full_snapshot()
    one_replacement = ContentAcfCloneReplacement(
        section_index=5,
        layout_name="cta",
        field_name="text",
        value="Jedyna nowa wartość pochodzi z zatwierdzonego planu.",
        value_kind="plain_text",
    )

    payload = compile_acf_clone_payload(
        _full_clone_plan(snapshot, replacements=[one_replacement]),
        snapshot,
    )

    rows = payload["flexible-home"]
    assert isinstance(rows, list)
    assert rows[0]["image"] == snapshot.rows[0]["image"]
    assert rows[1]["items"] == snapshot.rows[1]["items"]
    assert rows[2]["items"] == snapshot.rows[2]["items"]
    assert rows[3]["image"] == snapshot.rows[3]["image"]
    assert rows[6]["logos"] == snapshot.rows[6]["logos"]
    assert rows[8]["post_ids"] == snapshot.rows[8]["post_ids"]
    assert payload["meta"] == snapshot.fields["meta"]


def test_acf_clone_projection_replaces_exact_row_and_preserves_other_values() -> None:
    snapshot = _snapshot()
    plan = ContentAcfClonePlan(
        source_object_id="2",
        root_field="flexible-home",
        source_acf_digest=snapshot.root_digest,
        replacements=[
            ContentAcfCloneReplacement(
                section_index=2,
                layout_name="cta",
                field_name="content",
                value="Nowe CTA",
                value_kind="html",
            )
        ],
    )

    payload = compile_acf_clone_payload(plan, snapshot)

    assert payload == {
        "flexible-home": [
            {
                "acf_fc_layout": "cta",
                "content": "Pierwsze CTA",
                "image": 101,
                "settings": {"theme": "dark"},
            },
            {
                "acf_fc_layout": "cta",
                "content": "Nowe CTA",
                "image": 202,
                "settings": {"theme": "light"},
            },
        ]
    }
    assert snapshot.rows[1]["content"] == "Drugie CTA"


def test_acf_clone_projection_preserves_top_level_acf_fields_and_blocks_their_drift() -> None:
    source_fields = {
        "flexible-home": [
            {"acf_fc_layout": "cta", "content": "Pierwsze CTA"},
            {"acf_fc_layout": "cta", "content": "Drugie CTA"},
        ],
        "icon": 1126,
        "services_related": [374, 352, 116],
    }
    source_digest = "c" * 64
    snapshot = WordPressAcfFlexibleSnapshot(
        object_id="2",
        content_type="pages",
        root_field="flexible-home",
        root_digest="a" * 64,
        rows=source_fields["flexible-home"],
        fields_digest=source_digest,
        fields=source_fields,
    )
    plan = ContentAcfClonePlan(
        source_object_id="2",
        root_field="flexible-home",
        source_acf_digest="a" * 64,
        source_acf_fields_digest=source_digest,
        replacements=[
            ContentAcfCloneReplacement(
                section_index=2,
                layout_name="cta",
                field_name="content",
                value="Nowe CTA",
                value_kind="html",
            )
        ],
    )

    payload = compile_acf_clone_payload(plan, snapshot)

    assert payload["icon"] == 1126
    assert payload["services_related"] == [374, 352, 116]
    assert payload["flexible-home"] == [
        {"acf_fc_layout": "cta", "content": "Pierwsze CTA"},
        {"acf_fc_layout": "cta", "content": "Nowe CTA"},
    ]

    changed_fields = WordPressAcfFlexibleSnapshot(
        object_id="2",
        content_type="pages",
        root_field="flexible-home",
        root_digest="a" * 64,
        rows=source_fields["flexible-home"],
        fields_digest="d" * 64,
        fields=source_fields,
    )
    try:
        compile_acf_clone_payload(plan, changed_fields)
    except ValueError as error:
        assert "Inne pola ACF" in str(error)
    else:
        raise AssertionError("Zmiana pomocniczego pola ACF musi zablokować klon.")


def test_acf_clone_projection_fails_closed_on_source_drift_or_layout_change() -> None:
    snapshot = _snapshot()
    plan = ContentAcfClonePlan(
        source_object_id="2",
        root_field="flexible-home",
        source_acf_digest="b" * 64,
        replacements=[
            ContentAcfCloneReplacement(
                section_index=2,
                layout_name="cta",
                field_name="content",
                value="Nowe CTA",
                value_kind="html",
            )
        ],
    )

    try:
        compile_acf_clone_payload(plan, snapshot)
    except ValueError as error:
        assert "zmienił się" in str(error)
    else:
        raise AssertionError("Drift ACF nie może utworzyć payloadu.")

    mismatched_layout = _snapshot()
    mismatched_layout.rows[1]["acf_fc_layout"] = "hero"
    exact_plan = plan.model_copy(update={"source_acf_digest": mismatched_layout.root_digest})
    try:
        compile_acf_clone_payload(exact_plan, mismatched_layout)
    except ValueError as error:
        assert "Układ zatwierdzonej sekcji" in str(error)
    else:
        raise AssertionError("Zmiana layoutu nie może utworzyć payloadu.")
