from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.client import (
    WORDPRESS_CONNECTORS,
    WordPressAuthoringPageReadback,
    WordPressAuthoringReadError,
    WordPressAuthoringSectionReadback,
    read_wordpress_authoring_pages,
)
from wilq.credentials.runtime import variable_value
from wilq.evidence.registry import connector_evidence_id

WordPressAuthoringDiscoveryMethod = Literal[
    "rest",
    "acf_rest",
    "acf_export",
    "wp_cli",
    "helper",
    "env_config",
]
WordPressAuthoringReadiness = Literal[
    "available",
    "configured",
    "not_configured",
    "missing",
    "blocked",
    "unknown",
]
WordPressBooleanState = Literal["enabled", "disabled", "unknown"]


class WordPressAuthoringBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    reason: str
    next_step: str
    source_ref: str | None = None


class WordPressAuthoringDiscoveryFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    method: WordPressAuthoringDiscoveryMethod
    status: WordPressAuthoringReadiness
    source_ref: str


class WordPressAuthoringRestProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["rest"] = "rest"
    status: WordPressAuthoringReadiness
    base_url_configured: bool = False
    auth_configured: bool = False
    public_url_configured: bool = False
    post_types: list[str] = Field(default_factory=list)


class WordPressAuthoringFallbackProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["wp_cli", "helper"]
    status: WordPressAuthoringReadiness
    configured: bool = False
    missing_env: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class WordPressAcfField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    field_type: str
    required: bool = False
    source_method: WordPressAuthoringDiscoveryMethod
    sub_fields: list[WordPressAcfField] = Field(default_factory=list)


class WordPressAcfFlexibleLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    fields: list[WordPressAcfField] = Field(default_factory=list)
    source_method: WordPressAuthoringDiscoveryMethod
    required_field_names: list[str] = Field(default_factory=list)
    optional_field_names: list[str] = Field(default_factory=list)


class WordPressAcfAuthoringProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_state: WordPressBooleanState = "unknown"
    rest_enabled_state: WordPressBooleanState = "unknown"
    flexible_content_field_name: str | None = None
    post_types: list[str] = Field(default_factory=list)
    layouts: list[WordPressAcfFlexibleLayout] = Field(default_factory=list)
    source_method: WordPressAuthoringDiscoveryMethod | None = None
    layouts_discovered: bool = False


class WordPressAuthoringDevSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_index: int
    acf_field_name: str
    layout_name: str
    layout_label: str
    title: str = ""
    text_summary: str = ""
    field_names: list[str] = Field(default_factory=list)
    text_field_paths: list[str] = Field(default_factory=list)


class WordPressAuthoringDevPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_id: str
    content_type: Literal["page", "post"] = "page"
    slug: str
    title: str
    link: str
    status: str
    modified: str
    modified_gmt: str
    template: str = ""
    parent: str = ""
    acf_field_name: str | None = None
    section_count: int = 0
    sections: list[WordPressAuthoringDevSection] = Field(default_factory=list)


class WordPressAuthoringDevContentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WordPressAuthoringReadiness = "unknown"
    source_method: WordPressAuthoringDiscoveryMethod | None = None
    source_ref: str = ""
    page_count: int = 0
    pages: list[WordPressAuthoringDevPage] = Field(default_factory=list)
    blockers: list[WordPressAuthoringBlocker] = Field(default_factory=list)


class WordPressAuthoringWriteBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_operation: Literal["create_wordpress_draft"] = "create_wordpress_draft"
    direct_vendor_write_allowed: Literal[False] = False
    draft_writes_enabled_by_env: bool = False
    live_write_enabled: Literal[False] = False
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    external_write_attempted: Literal[False] = False
    required_action_contract: Literal["actionobject_validate_preview_review_confirm_audit"] = (
        "actionobject_validate_preview_review_confirm_audit"
    )


class WordPressAuthoringProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: Literal["wordpress_authoring_profile_v1"] = (
        "wordpress_authoring_profile_v1"
    )
    connector: str
    site_kind: str
    authoring_target: str
    discovery_mode: str
    discovery_order: list[WordPressAuthoringDiscoveryMethod]
    rest_api: WordPressAuthoringRestProfile
    acf: WordPressAcfAuthoringProfile
    dev_content: WordPressAuthoringDevContentProfile
    wp_cli: WordPressAuthoringFallbackProfile
    helper_plugin: WordPressAuthoringFallbackProfile
    write_boundary: WordPressAuthoringWriteBoundary
    discovery_facts: list[WordPressAuthoringDiscoveryFact] = Field(default_factory=list)
    blockers: list[WordPressAuthoringBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


def build_wordpress_authoring_profile(
    connector_id: str = "wordpress_ekologus",
    *,
    include_dev_content: bool = False,
    http_client: httpx.Client | None = None,
) -> WordPressAuthoringProfile:
    names = WORDPRESS_CONNECTORS.get(connector_id)
    if names is None:
        return _unknown_connector_profile(connector_id)

    prefix = _connector_prefix(connector_id)
    post_types = _list_env(f"{prefix}_ACF_POST_TYPES") or ["page", "post"]
    rest_profile = _rest_profile(names, post_types)
    wp_cli = _wp_cli_profile(prefix)
    helper = _helper_profile(prefix)
    layouts, layout_blockers = _acf_layouts_from_export(prefix)
    acf = WordPressAcfAuthoringProfile(
        enabled_state=_boolean_state(variable_value(f"{prefix}_ACF_ENABLED")),
        rest_enabled_state=_boolean_state(variable_value(f"{prefix}_ACF_REST_ENABLED")),
        flexible_content_field_name=_blank_to_none(
            variable_value(f"{prefix}_ACF_FLEX_FIELD_NAME")
        ),
        post_types=post_types,
        layouts=layouts,
        source_method="acf_export" if layouts else None,
        layouts_discovered=bool(layouts),
    )
    dev_content = _dev_content_profile(
        connector_id,
        prefix,
        rest_profile,
        acf,
        include_dev_content=include_dev_content,
        http_client=http_client,
    )

    blockers = [
        *_rest_blockers(prefix, rest_profile),
        *layout_blockers,
        *dev_content.blockers,
        *_acf_layout_blockers(prefix, acf, wp_cli, helper),
    ]
    return WordPressAuthoringProfile(
        connector=connector_id,
        site_kind=str(names["site_kind"]),
        authoring_target=variable_value(f"{prefix}_AUTHORING_TARGET") or "staging",
        discovery_mode=variable_value(f"{prefix}_DISCOVERY_MODE") or "rest_first",
        discovery_order=["rest", "acf_rest", "wp_cli", "helper"],
        rest_api=rest_profile,
        acf=acf,
        dev_content=dev_content,
        wp_cli=wp_cli,
        helper_plugin=helper,
        write_boundary=WordPressAuthoringWriteBoundary(
            draft_writes_enabled_by_env=_truthy(
                variable_value(f"{prefix}_ALLOW_DRAFT_WRITES")
            )
        ),
        discovery_facts=_discovery_facts(prefix, rest_profile, acf, wp_cli, helper),
        blockers=blockers,
        evidence_ids=[connector_evidence_id(connector_id)],
        source_connectors=[connector_id],
    )


def _unknown_connector_profile(connector_id: str) -> WordPressAuthoringProfile:
    fallback = WordPressAuthoringFallbackProfile(
        method="wp_cli",
        status="blocked",
        configured=False,
    )
    return WordPressAuthoringProfile(
        connector=connector_id,
        site_kind="unknown",
        authoring_target="unknown",
        discovery_mode="rest_first",
        discovery_order=["rest", "acf_rest", "wp_cli", "helper"],
        rest_api=WordPressAuthoringRestProfile(status="blocked"),
        acf=WordPressAcfAuthoringProfile(),
        dev_content=WordPressAuthoringDevContentProfile(
            status="blocked",
            blockers=[
                WordPressAuthoringBlocker(
                    code="unknown_wordpress_connector",
                    label="Nieznany connector WordPress",
                    reason="WILQ nie zna konfiguracji tego connectora WordPress.",
                    next_step="Użyj skonfigurowanego connectora albo dodaj definicję connectora.",
                )
            ],
        ),
        wp_cli=fallback,
        helper_plugin=WordPressAuthoringFallbackProfile(
            method="helper",
            status="blocked",
            configured=False,
        ),
        write_boundary=WordPressAuthoringWriteBoundary(),
        blockers=[
            WordPressAuthoringBlocker(
                code="unknown_wordpress_connector",
                label="Nieznany connector WordPress",
                reason="WILQ nie zna konfiguracji tego connectora WordPress.",
                next_step="Użyj skonfigurowanego connectora albo dodaj definicję connectora.",
            )
        ],
        source_connectors=[connector_id],
    )


def _rest_profile(
    names: dict[str, str],
    post_types: list[str],
) -> WordPressAuthoringRestProfile:
    base_url = variable_value(names["url"])
    username = variable_value(names["username"])
    app_password = variable_value(names["application_auth"])
    public_url = variable_value(names["public_url"]) or names.get("fallback_public_url", "")
    auth_configured = bool(username and app_password)
    base_url_configured = bool(base_url)
    return WordPressAuthoringRestProfile(
        status="configured" if base_url_configured and auth_configured else "missing",
        base_url_configured=base_url_configured,
        auth_configured=auth_configured,
        public_url_configured=bool(public_url),
        post_types=post_types,
    )


def _rest_blockers(
    prefix: str,
    rest_profile: WordPressAuthoringRestProfile,
) -> list[WordPressAuthoringBlocker]:
    if rest_profile.status != "missing":
        return []
    missing: list[str] = []
    if not rest_profile.base_url_configured:
        missing.append(f"{prefix}_URL")
    if not rest_profile.auth_configured:
        missing.extend([f"{prefix}_USERNAME", f"{prefix}_APP_PASSWORD"])
    return [
        WordPressAuthoringBlocker(
            code="wordpress_rest_not_configured",
            label="Brakuje konfiguracji REST WordPress",
            reason="Profil authoringu zaczyna od WP REST API, ale brakuje konfiguracji odczytu.",
            next_step=(
                "Uzupełnij brakujące zmienne WordPress albo zostaw profil jako "
                "readiness-only."
            ),
            source_ref=", ".join(missing),
        )
    ]


def _dev_content_profile(
    connector_id: str,
    prefix: str,
    rest_profile: WordPressAuthoringRestProfile,
    acf: WordPressAcfAuthoringProfile,
    *,
    include_dev_content: bool,
    http_client: httpx.Client | None,
) -> WordPressAuthoringDevContentProfile:
    source_ref = f"{prefix}_URL wp-json/wp/v2/pages,posts?context=edit"
    if not include_dev_content:
        return WordPressAuthoringDevContentProfile(status="unknown", source_ref=source_ref)
    if rest_profile.status != "configured":
        return WordPressAuthoringDevContentProfile(
            status="missing",
            source_method="rest",
            source_ref=source_ref,
            blockers=[
                WordPressAuthoringBlocker(
                    code="wordpress_dev_content_rest_missing",
                    label="Brakuje REST do odczytu stron dev",
                    reason=(
                        "WILQ nie może odczytać stron i sekcji dev WordPress bez "
                        "kompletnego REST."
                    ),
                    next_step=(
                        "Uzupełnij URL, użytkownika i application password dla WordPress dev."
                    ),
                    source_ref=source_ref,
                )
            ],
        )
    try:
        pages = [
            page
            for endpoint, content_type in (("pages", "page"), ("posts", "post"))
            for page in read_wordpress_authoring_pages(
                connector_id,
                preferred_flexible_field_name=acf.flexible_content_field_name,
                content_type=endpoint,
                http_client=http_client,
            )
        ]
    except WordPressAuthoringReadError as exc:
        return WordPressAuthoringDevContentProfile(
            status="blocked",
            source_method="acf_rest",
            source_ref=source_ref,
            blockers=[
                WordPressAuthoringBlocker(
                    code="wordpress_dev_content_rest_failed",
                    label="Nie udało się odczytać stron dev WordPress",
                    reason=exc.public_message,
                    next_step="Sprawdź WP REST, application password i uprawnienia użytkownika.",
                    source_ref=source_ref,
                )
            ],
        )

    dev_pages = [_dev_page_from_readback(page) for page in pages]
    status: WordPressAuthoringReadiness = "available" if dev_pages else "missing"
    blockers: list[WordPressAuthoringBlocker] = []
    if not dev_pages:
        blockers.append(
            WordPressAuthoringBlocker(
                code="wordpress_dev_pages_empty",
                label="Brak stron dev do odczytu",
                reason="WP REST działa, ale nie zwrócił stron authoringu z ACF.",
                next_step="Sprawdź, czy strony dev są typu page i czy ACF jest widoczny w REST.",
                source_ref=source_ref,
            )
        )
    return WordPressAuthoringDevContentProfile(
        status=status,
        source_method="acf_rest",
        source_ref=source_ref,
        page_count=len(dev_pages),
        pages=dev_pages,
        blockers=blockers,
    )


def _dev_page_from_readback(page: WordPressAuthoringPageReadback) -> WordPressAuthoringDevPage:
    return WordPressAuthoringDevPage(
        post_id=page.post_id,
        content_type="post" if page.content_type == "posts" else "page",
        slug=page.slug,
        title=page.title,
        link=page.link,
        status=page.status,
        modified=page.modified,
        modified_gmt=page.modified_gmt,
        template=page.template,
        parent=page.parent,
        acf_field_name=page.acf_field_name,
        section_count=page.section_count,
        sections=[_dev_section_from_readback(section) for section in page.sections],
    )


def _dev_section_from_readback(
    section: WordPressAuthoringSectionReadback,
) -> WordPressAuthoringDevSection:
    return WordPressAuthoringDevSection(
        section_index=section.section_index,
        acf_field_name=section.acf_field_name,
        layout_name=section.layout_name,
        layout_label=section.layout_label,
        title=section.title,
        text_summary=section.text_summary,
        field_names=section.field_names,
        text_field_paths=section.text_field_paths,
    )


def _wp_cli_profile(prefix: str) -> WordPressAuthoringFallbackProfile:
    required_base = [
        f"{prefix}_SSH_HOST",
        f"{prefix}_SSH_USER",
        f"{prefix}_DOCROOT",
    ]
    missing = [name for name in required_base if not variable_value(name)]
    key_name = f"{prefix}_SSH_KEY_PATH"
    password_name = f"{prefix}_SSH_PASSWORD"
    if not variable_value(key_name) and not variable_value(password_name):
        missing.append(f"{key_name} or {password_name}")
    working_name = f"{prefix}_WP_CLI_WORKING"
    working_state = _boolean_state(variable_value(working_name))
    if working_state == "disabled":
        missing.append(working_name)
    return WordPressAuthoringFallbackProfile(
        method="wp_cli",
        status="configured" if not missing else "not_configured",
        configured=not missing,
        missing_env=missing,
        source_refs=[
            *required_base,
            f"{prefix}_SSH_PORT",
            key_name,
            password_name,
            f"{prefix}_WP_CLI_PATH",
            f"{prefix}_WP_CLI_PHP_PATH",
            working_name,
        ],
    )


def _helper_profile(prefix: str) -> WordPressAuthoringFallbackProfile:
    allowed = _truthy(variable_value(f"{prefix}_HELPER_PLUGIN_ALLOWED"))
    has_secret = bool(variable_value(f"{prefix}_HELPER_PLUGIN_SHARED_SECRET"))
    missing = []
    if not allowed:
        missing.append(f"{prefix}_HELPER_PLUGIN_ALLOWED")
    if not has_secret:
        missing.append(f"{prefix}_HELPER_PLUGIN_SHARED_SECRET")
    return WordPressAuthoringFallbackProfile(
        method="helper",
        status="configured" if allowed and has_secret else "not_configured",
        configured=allowed and has_secret,
        missing_env=missing,
        source_refs=[
            f"{prefix}_HELPER_PLUGIN_ALLOWED",
            f"{prefix}_HELPER_PLUGIN_SHARED_SECRET",
        ],
    )


def _acf_layouts_from_export(
    prefix: str,
) -> tuple[list[WordPressAcfFlexibleLayout], list[WordPressAuthoringBlocker]]:
    env_name = f"{prefix}_ACF_FIELD_GROUPS_EXPORT_PATH"
    export_path = _blank_to_none(variable_value(env_name))
    if export_path is None:
        return [], []
    path = Path(export_path).expanduser()
    if not path.is_file():
        return [], [
            WordPressAuthoringBlocker(
                code="acf_export_not_readable",
                label="Eksport ACF nie jest dostępny",
                reason="WILQ widzi konfigurację eksportu ACF, ale plik nie jest czytelny.",
                next_step="Podaj poprawny lokalny eksport ACF field groups albo użyj WP-CLI.",
                source_ref=env_name,
            )
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], [
            WordPressAuthoringBlocker(
                code="acf_export_invalid",
                label="Eksport ACF nie jest poprawnym JSON",
                reason="WILQ nie może zbudować kontraktu Flexible Content z tego pliku.",
                next_step="Wyeksportuj field groups ACF jako JSON i wskaż plik w .env.",
                source_ref=env_name,
            )
        ]
    layouts = _acf_layouts_from_payload(
        payload,
        flexible_field_name=_blank_to_none(variable_value(f"{prefix}_ACF_FLEX_FIELD_NAME")),
    )
    if not layouts:
        return [], [
            WordPressAuthoringBlocker(
                code="acf_export_has_no_flexible_layouts",
                label="Eksport ACF nie zawiera Flexible Content",
                reason="WILQ znalazł eksport ACF, ale nie znalazł w nim layoutów Flexible Content.",
                next_step="Wskaż nazwę pola Flexible Content albo podaj pełniejszy eksport ACF.",
                source_ref=env_name,
            )
        ]
    return layouts, []


def _acf_layouts_from_payload(
    payload: Any,
    *,
    flexible_field_name: str | None,
) -> list[WordPressAcfFlexibleLayout]:
    groups = payload if isinstance(payload, list) else [payload]
    layouts: list[WordPressAcfFlexibleLayout] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field in fields:
            layouts.extend(
                _flexible_layouts_from_field(field, flexible_field_name=flexible_field_name)
            )
            if flexible_field_name is None:
                layout = _section_layout_from_field(field)
                if layout is not None:
                    layouts.append(layout)
        if not layouts:
            fallback = _field_group_layout_from_fields(group, fields)
            if fallback is not None:
                layouts.append(fallback)
    return layouts


def _flexible_layouts_from_field(
    field: Any,
    *,
    flexible_field_name: str | None,
) -> list[WordPressAcfFlexibleLayout]:
    if not isinstance(field, dict):
        return []
    if field.get("type") != "flexible_content":
        return []
    field_name = _text(field.get("name"))
    if flexible_field_name and field_name != flexible_field_name:
        return []
    raw_layouts = field.get("layouts")
    if isinstance(raw_layouts, dict):
        layout_values = list(raw_layouts.values())
    elif isinstance(raw_layouts, list):
        layout_values = raw_layouts
    else:
        layout_values = []
    layouts: list[WordPressAcfFlexibleLayout] = []
    for layout in layout_values:
        if not isinstance(layout, dict):
            continue
        fields = _acf_fields_from_payloads(layout.get("sub_fields", []))
        required = [field.name for field in fields if field.required]
        optional = [field.name for field in fields if not field.required]
        layout_name = _text(layout.get("name")) or _text(layout.get("key"))
        if not layout_name:
            continue
        layouts.append(
            WordPressAcfFlexibleLayout(
                name=layout_name,
                label=_text(layout.get("label")) or layout_name,
                fields=fields,
                source_method="acf_export",
                required_field_names=required,
                optional_field_names=optional,
            )
        )
    return layouts


def _section_layout_from_field(field: Any) -> WordPressAcfFlexibleLayout | None:
    if not isinstance(field, dict):
        return None
    field_type = _text(field.get("type"))
    if field_type not in {"group", "repeater"}:
        return None
    fields = _acf_fields_from_payloads(field.get("sub_fields", []))
    if not fields:
        return None
    layout_name = _text(field.get("name")) or _text(field.get("key"))
    if not layout_name:
        return None
    return _acf_layout(
        name=layout_name,
        label=_text(field.get("label")) or layout_name,
        fields=fields,
        source_method="acf_export",
    )


def _field_group_layout_from_fields(
    group: dict[str, Any],
    raw_fields: list[Any],
) -> WordPressAcfFlexibleLayout | None:
    fields = _acf_fields_from_payloads(raw_fields)
    if not fields:
        return None
    group_name = _text(group.get("title")) or _text(group.get("key"))
    if not group_name:
        return None
    return _acf_layout(
        name=_slug(group_name),
        label=group_name,
        fields=fields,
        source_method="acf_export",
    )


def _acf_layout(
    *,
    name: str,
    label: str,
    fields: list[WordPressAcfField],
    source_method: WordPressAuthoringDiscoveryMethod,
) -> WordPressAcfFlexibleLayout:
    required = [field.name for field in fields if field.required]
    optional = [field.name for field in fields if not field.required]
    return WordPressAcfFlexibleLayout(
        name=name,
        label=label,
        fields=fields,
        source_method=source_method,
        required_field_names=required,
        optional_field_names=optional,
    )


def _acf_fields_from_payloads(raw_fields: object) -> list[WordPressAcfField]:
    if not isinstance(raw_fields, list):
        return []
    fields: list[WordPressAcfField] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict):
            continue
        field = _acf_field_from_payload(raw_field)
        if field is not None:
            fields.append(field)
    return fields


def _acf_field_from_payload(payload: dict[str, Any]) -> WordPressAcfField | None:
    name = _text(payload.get("name")) or _text(payload.get("key"))
    if not name:
        return None
    sub_fields = [
        field
        for raw_field in payload.get("sub_fields", [])
        if isinstance(raw_field, dict)
        for field in [_acf_field_from_payload(raw_field)]
        if field is not None
    ]
    return WordPressAcfField(
        name=name,
        label=_text(payload.get("label")) or name,
        field_type=_text(payload.get("type")) or "unknown",
        required=_acf_required(payload.get("required")),
        source_method="acf_export",
        sub_fields=sub_fields,
    )


def _acf_layout_blockers(
    prefix: str,
    acf: WordPressAcfAuthoringProfile,
    wp_cli: WordPressAuthoringFallbackProfile,
    helper: WordPressAuthoringFallbackProfile,
) -> list[WordPressAuthoringBlocker]:
    if acf.layouts_discovered:
        return []
    if acf.rest_enabled_state == "enabled":
        return [
            WordPressAuthoringBlocker(
                code="acf_flexible_layouts_missing_acf_rest",
                label="Brakuje odczytu layoutów ACF",
                reason=(
                    "ACF REST wygląda na włączony, ale WILQ nie ma jeszcze layoutów "
                    "Flexible Content."
                ),
                next_step="Wykonaj odczyt ACF REST albo podaj eksport field groups.",
                source_ref=f"{prefix}_ACF_REST_ENABLED",
            )
        ]
    if wp_cli.configured:
        return [
            WordPressAuthoringBlocker(
                code="acf_flexible_layouts_missing_wp_cli_ready",
                label="ACF wymaga odczytu przez WP-CLI",
                reason="REST nie dostarczył layoutów ACF, ale fallback WP-CLI jest skonfigurowany.",
                next_step=(
                    "Uruchom read-only discovery przez WP-CLI i zapisz typed profile "
                    "layoutów."
                ),
                source_ref=", ".join(wp_cli.source_refs),
            )
        ]
    if helper.configured:
        return [
            WordPressAuthoringBlocker(
                code="acf_flexible_layouts_missing_helper_ready",
                label="ACF wymaga helpera read-only",
                reason="REST/WP-CLI nie dostarcza layoutów, a helper plugin jest dopuszczony.",
                next_step="Użyj read-only helpera do zrzutu field groups bez publikowania treści.",
                source_ref=", ".join(helper.source_refs),
            )
        ]
    return [
        WordPressAuthoringBlocker(
            code="acf_flexible_layouts_missing",
            label="Brakuje kontraktu ACF Flexible Content",
            reason=(
                "WILQ nie zna jeszcze layoutów i wymaganych pól, więc nie może udawać "
                "gotowości do szkicu ACF."
            ),
            next_step=(
                "Podaj eksport ACF field groups albo uzupełnij dostęp WP-CLI/SSH do "
                "read-only discovery."
            ),
            source_ref=f"{prefix}_ACF_FIELD_GROUPS_EXPORT_PATH",
        )
    ]


def _discovery_facts(
    prefix: str,
    rest: WordPressAuthoringRestProfile,
    acf: WordPressAcfAuthoringProfile,
    wp_cli: WordPressAuthoringFallbackProfile,
    helper: WordPressAuthoringFallbackProfile,
) -> list[WordPressAuthoringDiscoveryFact]:
    facts = [
        WordPressAuthoringDiscoveryFact(
            id="wordpress_rest_authoring_discovery",
            label="WP REST jako pierwszy odczyt authoringu",
            method="rest",
            status=rest.status,
            source_ref=f"{prefix}_URL",
        ),
        WordPressAuthoringDiscoveryFact(
            id="acf_rest_authoring_discovery",
            label="ACF REST dla layoutów i pól",
            method="acf_rest",
            status=_acf_rest_status(acf),
            source_ref=f"{prefix}_ACF_REST_ENABLED",
        ),
        WordPressAuthoringDiscoveryFact(
            id="wp_cli_authoring_fallback",
            label="WP-CLI jako fallback read-only",
            method="wp_cli",
            status=wp_cli.status,
            source_ref=", ".join(wp_cli.source_refs),
        ),
        WordPressAuthoringDiscoveryFact(
            id="helper_authoring_fallback",
            label="Helper read-only jako ostatni fallback",
            method="helper",
            status=helper.status,
            source_ref=", ".join(helper.source_refs),
        ),
    ]
    if acf.source_method == "acf_export":
        facts.append(
            WordPressAuthoringDiscoveryFact(
                id="acf_export_authoring_layouts",
                label="Lokalny eksport ACF field groups",
                method="acf_export",
                status="available",
                source_ref=f"{prefix}_ACF_FIELD_GROUPS_EXPORT_PATH",
            )
        )
    return facts


def _acf_rest_status(acf: WordPressAcfAuthoringProfile) -> WordPressAuthoringReadiness:
    if acf.layouts_discovered and acf.source_method == "acf_rest":
        return "available"
    if acf.rest_enabled_state == "enabled":
        return "configured"
    if acf.rest_enabled_state == "disabled":
        return "blocked"
    return "unknown"


def _connector_prefix(connector_id: str) -> str:
    return connector_id.upper()


def _boolean_state(value: str | None) -> WordPressBooleanState:
    if value is None or value.strip() == "":
        return "unknown"
    if _truthy(value):
        return "enabled"
    if value.strip().lower() in {"0", "false", "no", "off", "disabled"}:
        return "disabled"
    return "unknown"


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on", "enabled"})


def _list_env(name: str) -> list[str]:
    value = variable_value(name)
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _slug(value: str) -> str:
    return "_".join(value.strip().lower().split())


def _acf_required(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False
