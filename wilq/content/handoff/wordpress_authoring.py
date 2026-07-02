from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.authoring import (
    WordPressAcfField,
    WordPressAcfFlexibleLayout,
    WordPressAuthoringProfile,
    build_wordpress_authoring_profile,
)
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff

ContentWordPressAuthoringPreviewStatus = Literal["ready", "blocked"]
ContentWordPressAuthoringPreviewBlockerCode = Literal[
    "missing_handoff",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "acf_flexible_layouts_missing",
    "acf_flexible_field_name_missing",
    "acf_layout_field_mapping_incomplete",
]


class ContentWordPressAuthoringPreviewBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentWordPressAuthoringPreviewBlockerCode
    label: str
    reason: str
    next_step: str


class ContentWordPressFlexibleSectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_name: str
    layout_label: str
    section_heading: str
    field_values: dict[str, str | None] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentWordPressAuthoringPayloadPreviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentWordPressAuthoringPreviewStatus
    mode: Literal["dry_run"] = "dry_run"
    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    endpoint_kind: Literal["posts"] = "posts"
    post_status: Literal["draft"] = "draft"
    flexible_content_field_name: str | None = None
    sections: list[ContentWordPressFlexibleSectionPayload] = Field(default_factory=list)
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    external_write_attempted: Literal[False] = False
    required_action_contract: Literal["actionobject_validate_preview_review_confirm_audit"] = (
        "actionobject_validate_preview_review_confirm_audit"
    )
    blockers: list[ContentWordPressAuthoringPreviewBlocker] = Field(default_factory=list)


def build_content_wordpress_authoring_payload_preview(
    *,
    handoff: ContentWordPressDraftHandoff | None,
    draft_package: ContentDraftPackage | None,
    authoring_profile: WordPressAuthoringProfile | None = None,
) -> ContentWordPressAuthoringPayloadPreviewResult:
    profile = authoring_profile or build_wordpress_authoring_profile("wordpress_ekologus")
    blockers = _input_blockers(handoff=handoff, draft_package=draft_package)
    blockers.extend(_profile_blockers(profile))
    if blockers:
        return ContentWordPressAuthoringPayloadPreviewResult(
            status="blocked",
            flexible_content_field_name=profile.acf.flexible_content_field_name,
            blockers=blockers,
        )

    if handoff is None:
        raise RuntimeError("WordPress handoff passed authoring blockers as None.")
    if draft_package is None:
        raise RuntimeError("Draft package passed authoring blockers as None.")

    layout = _choose_layout(profile.acf.layouts)
    if layout is None:
        return ContentWordPressAuthoringPayloadPreviewResult(
            status="blocked",
            flexible_content_field_name=profile.acf.flexible_content_field_name,
            blockers=[
                _blocker(
                    "acf_flexible_layouts_missing",
                    "Brakuje layoutów ACF",
                    "WILQ nie zna layoutu Flexible Content dla szkicu.",
                    "Najpierw uzupełnij profil authoringu WordPress/ACF.",
                )
            ],
        )

    sections = [_section_payload(layout, section) for section in draft_package.sections]
    missing_required = [
        field
        for section in sections
        for field in section.missing_required_fields
    ]
    if missing_required:
        return ContentWordPressAuthoringPayloadPreviewResult(
            status="blocked",
            flexible_content_field_name=profile.acf.flexible_content_field_name,
            sections=sections,
            blockers=[
                _blocker(
                    "acf_layout_field_mapping_incomplete",
                    "Mapowanie ACF jest niepełne",
                    "Nie wszystkie wymagane pola layoutu da się wypełnić z paczki szkicu.",
                    "Dopasuj layout ACF albo uzupełnij paczkę szkicu o brakujące pola.",
                )
            ],
        )

    return ContentWordPressAuthoringPayloadPreviewResult(
        status="ready",
        flexible_content_field_name=profile.acf.flexible_content_field_name,
        sections=sections,
    )


def _input_blockers(
    *,
    handoff: ContentWordPressDraftHandoff | None,
    draft_package: ContentDraftPackage | None,
) -> list[ContentWordPressAuthoringPreviewBlocker]:
    blockers: list[ContentWordPressAuthoringPreviewBlocker] = []
    if handoff is None:
        blockers.append(
            _blocker(
                "missing_handoff",
                "Brakuje przekazania WordPress",
                "Payload ACF może powstać dopiero po zatwierdzonym handoffie.",
                "Przygotuj handoff szkicu WordPress po review i audycie.",
            )
        )
    if draft_package is None:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Payload ACF potrzebuje sekcji, dowodów i tytułu szkicu.",
                "Przygotuj paczkę szkicu przed mapowaniem na ACF.",
            )
        )
    if handoff is not None and draft_package is not None:
        if handoff.draft_package_id != draft_package.id:
            blockers.append(
                _blocker(
                    "draft_package_mismatch",
                    "Paczka szkicu nie pasuje do handoffu",
                    "Nie można mapować innej paczki niż ta, którą zatwierdzono.",
                    "Użyj paczki szkicu powiązanej z przekazaniem WordPress.",
                )
            )
        if draft_package.publish_ready:
            blockers.append(
                _blocker(
                    "draft_package_marked_publish_ready",
                    "Szkic nie może udawać publikacji",
                    "Payload ACF jest tylko podglądem szkicu, nie publikacją.",
                    "Zatrzymaj status publish-ready i zostaw publikację do osobnej decyzji.",
                )
            )
    return blockers


def _profile_blockers(
    profile: WordPressAuthoringProfile,
) -> list[ContentWordPressAuthoringPreviewBlocker]:
    blockers: list[ContentWordPressAuthoringPreviewBlocker] = []
    if not profile.acf.flexible_content_field_name and not profile.acf.layouts:
        blockers.append(
            _blocker(
                "acf_flexible_field_name_missing",
                "Brakuje nazwy pola Flexible Content",
                "WILQ musi znać nazwę pola ACF, do którego trafią sekcje.",
                "Uzupełnij WORDPRESS_EKOLOGUS_ACF_FLEX_FIELD_NAME albo odczytaj profil ACF.",
            )
        )
    if not profile.acf.layouts:
        blockers.append(
            _blocker(
                "acf_flexible_layouts_missing",
                "Brakuje layoutów ACF Flexible Content",
                "WILQ nie zna nazw layoutów ani wymaganych pól, więc nie przygotuje payloadu.",
                "Podaj eksport ACF field groups albo uruchom read-only discovery przez WP-CLI.",
            )
        )
    return blockers


def _choose_layout(
    layouts: list[WordPressAcfFlexibleLayout],
) -> WordPressAcfFlexibleLayout | None:
    if not layouts:
        return None
    return max(layouts, key=_layout_score)


def _layout_score(layout: WordPressAcfFlexibleLayout) -> int:
    text = " ".join(
        [
            layout.name,
            layout.label,
            *[field.name for field in layout.fields],
            *[field.label for field in layout.fields],
            *[field.field_type for field in layout.fields],
        ]
    ).lower()
    score = 0
    for token in ("podstrona", "content", "tekst", "section", "sekcja"):
        if token in text:
            score += 8
    for token in ("opis", "wysiwyg", "body"):
        if token in text:
            score += 5
    for token in ("tytul", "title", "heading", "naglowek"):
        if token in text:
            score += 4
    for token in ("hero", "cta", "baza_wiedzy", "nasze_uslugi"):
        if token in text:
            score += 2
    for token in ("skrypt", "script", "html_head", "html_body", "api"):
        if token in text:
            score -= 20
    return score


def _section_payload(
    layout: WordPressAcfFlexibleLayout,
    section: ContentDraftSection,
) -> ContentWordPressFlexibleSectionPayload:
    field_values: dict[str, str | None] = {}
    missing_required: list[str] = []
    for field in layout.fields:
        value = _field_value(field, section)
        field_values[field.name] = value
        if field.required and value is None:
            missing_required.append(field.name)
    return ContentWordPressFlexibleSectionPayload(
        layout_name=layout.name,
        layout_label=layout.label,
        section_heading=section.heading,
        field_values=field_values,
        missing_required_fields=missing_required,
        evidence_ids=section.evidence_ids,
    )


def _field_value(field: WordPressAcfField, section: ContentDraftSection) -> str | None:
    haystack = f"{field.name} {field.label} {field.field_type}".lower()
    if field.field_type in {"repeater", "flexible_content"}:
        return None
    if field.field_type == "group":
        nested_value = _nested_text_value(field, section)
        if nested_value is not None:
            return nested_value
        return None
    if any(
        token in haystack
        for token in ("heading", "headline", "title", "tytul", "naglowek")
    ):
        return section.heading
    if any(token in haystack for token in ("body", "content", "tekst", "opis", "wysiwyg")):
        return _section_body(section)
    if "purpose" in haystack or "cel" in haystack:
        return section.purpose
    if "evidence" in haystack or "dowod" in haystack:
        return ", ".join(section.evidence_ids) if section.evidence_ids else None
    return None


def _nested_text_value(field: WordPressAcfField, section: ContentDraftSection) -> str | None:
    nested_names = " ".join(
        f"{sub_field.name} {sub_field.label} {sub_field.field_type}"
        for sub_field in field.sub_fields
    ).lower()
    if not nested_names:
        return None
    if any(token in nested_names for token in ("opis", "wysiwyg", "body", "content")):
        return _section_body(section)
    if any(token in nested_names for token in ("tytul", "title", "heading", "naglowek")):
        return section.heading
    return None


def _section_body(section: ContentDraftSection) -> str:
    chunks = [section.purpose]
    chunks.extend(section.draft_notes)
    return "\n".join(chunk for chunk in chunks if chunk)


def _blocker(
    code: ContentWordPressAuthoringPreviewBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentWordPressAuthoringPreviewBlocker:
    return ContentWordPressAuthoringPreviewBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
