from __future__ import annotations

from typing import Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.authoring import (
    WordPressAcfField,
    WordPressAcfFlexibleLayout,
    WordPressAuthoringProfile,
    build_wordpress_authoring_profile,
)
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff

ContentWordPressMetaWriteStatus = Literal["not_present", "review_required", "mapped"]
ContentWordPressAuthoringPreviewStatus = Literal["ready", "blocked"]
ContentWordPressAuthoringPreviewBlockerCode = Literal[
    "missing_handoff",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "acf_flexible_layouts_missing",
    "acf_flexible_field_name_missing",
    "acf_layout_field_mapping_incomplete",
    "missing_wordpress_meta_mapping",
]


class ContentWordPressAuthoringPreviewBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentWordPressAuthoringPreviewBlockerCode
    label: str
    reason: str
    next_step: str


class ContentWordPressRowCandidateField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    field_label: str
    field_type: str
    value_preview: str | None = None
    safe_to_autofill: bool = False
    note: str | None = None


class ContentWordPressFieldRowCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_type: Literal["acf_repeater_row", "acf_flexible_content_row"]
    row_label: str
    review_status: Literal["review_required"] = "review_required"
    note: str
    field_values: list[ContentWordPressRowCandidateField] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentWordPressFieldValuePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    field_label: str
    field_type: str
    value_preview: str | None = None
    safe_to_autofill: bool = False
    note: str | None = None
    nested_values: list[ContentWordPressFieldValuePreview] = Field(default_factory=list)
    row_candidates: list[ContentWordPressFieldRowCandidate] = Field(default_factory=list)


class ContentWordPressFlexibleSectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_name: str
    layout_label: str
    section_heading: str
    field_values: dict[str, str | None] = Field(default_factory=dict)
    field_previews: list[ContentWordPressFieldValuePreview] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentWordPressPageAssetsPreview(BaseModel):
    """Every full-document asset survives the dry-run, even when meta is manual."""

    model_config = ConfigDict(extra="forbid")

    wordpress_title: str
    h1: str
    lead: str
    meta_title: str
    meta_description: str
    meta_write_status: ContentWordPressMetaWriteStatus = "review_required"
    metadata_blockers: list[ContentWordPressAuthoringPreviewBlocker] = Field(
        default_factory=list
    )


class ContentWordPressAuthoringPayloadPreviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentWordPressAuthoringPreviewStatus
    mode: Literal["dry_run"] = "dry_run"
    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    endpoint_kind: Literal["posts"] = "posts"
    post_status: Literal["draft"] = "draft"
    authoring_mode: Literal["acf_flexible_content"] = "acf_flexible_content"
    flexible_content_field_name: str | None = None
    page_assets: ContentWordPressPageAssetsPreview | None = None
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
    page_assets = _page_assets_preview(handoff)
    blockers = _input_blockers(handoff=handoff, draft_package=draft_package)
    blockers.extend(_profile_blockers(profile))
    if blockers:
        return ContentWordPressAuthoringPayloadPreviewResult(
            status="blocked",
            flexible_content_field_name=profile.acf.flexible_content_field_name,
            page_assets=page_assets,
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
            page_assets=page_assets,
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
            page_assets=page_assets,
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
        page_assets=page_assets,
        sections=sections,
    )


def _page_assets_preview(
    handoff: ContentWordPressDraftHandoff | None,
) -> ContentWordPressPageAssetsPreview | None:
    document = handoff.revision_document if handoff is not None else None
    if document is None or document.page_assets is None:
        return None
    return ContentWordPressPageAssetsPreview(
        wordpress_title=document.page_assets.wordpress_title,
        h1=document.page_assets.h1,
        lead=document.page_assets.lead,
        meta_title=document.page_assets.meta_title,
        meta_description=document.page_assets.meta_description,
        meta_write_status="review_required",
        metadata_blockers=[
            ContentWordPressAuthoringPreviewBlocker(
                code="missing_wordpress_meta_mapping",
                label="Meta pola wymagają mapowania WordPress",
                reason=(
                    "Tytuł i opis meta są zachowane, ale profil SEO/ACF nie "
                    "potwierdza pola zapisu."
                ),
                next_step="Przekaż meta ręcznie albo potwierdź dokładne pola profilu WordPress.",
            )
        ],
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
    field_previews: list[ContentWordPressFieldValuePreview] = []
    missing_required: list[str] = []
    for field in layout.fields:
        value = _field_value(field, section)
        field_values[field.name] = value
        field_previews.append(_field_preview(field, section))
        if field.required and value is None:
            missing_required.append(field.name)
    return ContentWordPressFlexibleSectionPayload(
        layout_name=layout.name,
        layout_label=layout.label,
        section_heading=section.heading,
        field_values=field_values,
        field_previews=field_previews,
        missing_required_fields=missing_required,
        evidence_ids=section.evidence_ids,
    )


def _field_value(field: WordPressAcfField, section: ContentDraftSection) -> str | None:
    return _field_scalar_value(field, section)


def _field_preview(
    field: WordPressAcfField,
    section: ContentDraftSection,
) -> ContentWordPressFieldValuePreview:
    nested = [_field_preview(sub_field, section) for sub_field in field.sub_fields]
    value = _field_scalar_value(field, section)
    row_candidates = _row_candidates(field, section, nested=nested)
    note = _field_preview_note(field, value=value, nested=nested)
    return ContentWordPressFieldValuePreview(
        field_name=field.name,
        field_label=field.label,
        field_type=field.field_type,
        value_preview=value,
        safe_to_autofill=bool(value) or any(item.safe_to_autofill for item in nested),
        note=note,
        nested_values=nested,
        row_candidates=row_candidates,
    )


def _row_candidates(
    field: WordPressAcfField,
    section: ContentDraftSection,
    *,
    nested: list[ContentWordPressFieldValuePreview],
) -> list[ContentWordPressFieldRowCandidate]:
    if field.field_type not in {"repeater", "flexible_content"}:
        return []
    mapped_fields = _row_candidate_fields(nested)
    if not mapped_fields:
        return []
    row_type: Literal["acf_repeater_row", "acf_flexible_content_row"] = (
        "acf_flexible_content_row"
        if field.field_type == "flexible_content"
        else "acf_repeater_row"
    )
    label = (
        f"Wiersz do ręcznego przeglądu: {section.heading}"
        if section.heading
        else "Wiersz do ręcznego przeglądu z paczki szkicu"
    )
    return [
        ContentWordPressFieldRowCandidate(
            row_type=row_type,
            row_label=label,
            note=(
                "WILQ proponuje tylko kandydat wiersza ACF do ręcznego przeglądu; "
                "nie wybiera finalnego layoutu i nie zapisuje nic w WordPress."
            ),
            field_values=mapped_fields,
            evidence_ids=section.evidence_ids,
        )
    ]


def _row_candidate_fields(
    nested: list[ContentWordPressFieldValuePreview],
) -> list[ContentWordPressRowCandidateField]:
    fields: list[ContentWordPressRowCandidateField] = []
    seen: set[tuple[str, str]] = set()
    for item in sorted(nested, key=_row_candidate_field_score, reverse=True):
        if not item.value_preview or not item.safe_to_autofill:
            continue
        if item.field_type in {
            "image",
            "file",
            "post_object",
            "google_map",
            "select",
            "true_false",
        }:
            continue
        key = (item.field_name, item.field_label)
        if key in seen:
            continue
        seen.add(key)
        fields.append(
            ContentWordPressRowCandidateField(
                field_name=item.field_name,
                field_label=item.field_label,
                field_type=item.field_type,
                value_preview=item.value_preview,
                safe_to_autofill=item.safe_to_autofill,
                note=item.note,
            )
        )
        if len(fields) >= 4:
            break
    return fields


def _row_candidate_field_score(item: ContentWordPressFieldValuePreview) -> int:
    text = f"{item.field_name} {item.field_label} {item.field_type}".lower()
    words = set(text.replace("_", " ").replace("-", " ").split())
    score = 0
    if item.value_preview:
        score += 20
    for token in ("tytul", "title", "heading", "naglowek", "nagłówek"):
        if token in words:
            score += 8
    for token in ("opis", "content", "tresc", "treść", "body", "wysiwyg"):
        if token in words:
            score += 7
    for token in ("lead", "intro", "podtytul", "podtytuł"):
        if token in words:
            score += 5
    if item.field_type == "group":
        score -= 3
    if item.field_type in {"repeater", "flexible_content"}:
        score -= 10
    return score


def _field_scalar_value(field: WordPressAcfField, section: ContentDraftSection) -> str | None:
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
    if any(token in haystack for token in ("lead", "intro", "wstep", "wstęp")):
        return section.purpose
    if "purpose" in haystack or "cel" in haystack:
        return section.purpose
    if "evidence" in haystack or "dowod" in haystack:
        return ", ".join(section.evidence_ids) if section.evidence_ids else None
    return None


def _field_preview_note(
    field: WordPressAcfField,
    *,
    value: str | None,
    nested: list[ContentWordPressFieldValuePreview],
) -> str | None:
    if field.field_type == "group":
        if any(item.safe_to_autofill for item in nested):
            return "Grupa ACF: WILQ mapuje jej pod pola w podglądzie."
        return "Grupa ACF wymaga ręcznego dopasowania pod pól."
    if field.field_type in {"repeater", "flexible_content"}:
        if any(item.safe_to_autofill for item in nested):
            return (
                "Pole zagnieżdżone: WILQ pokazuje możliwe mapowanie pod pól, "
                "ale wybór layoutu/wierszy wymaga osobnego ręcznego przeglądu."
            )
        return "Pole zagnieżdżone wymaga osobnego layoutu, mediów albo ręcznego przeglądu."
    if value is not None:
        return None
    if field.required:
        return "Wymagane pole ACF nie ma bezpiecznej wartości ze szkicu."
    if field.field_type in {"image", "file", "post_object", "google_map", "select", "true_false"}:
        return "To pole wymaga ręcznego wyboru wartości w WordPress/ACF."
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
    markdown = "\n".join(chunk for chunk in chunks if chunk)
    return str(MarkdownIt("commonmark", {"html": False, "linkify": False}).render(markdown))


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
