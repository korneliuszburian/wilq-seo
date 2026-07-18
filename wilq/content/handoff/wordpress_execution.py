from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.revision_document_renderer import revision_document_markdown
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding

ContentWordPressDraftExecutionMode = Literal["dry_run", "live"]
ContentWordPressDraftExecutionStatus = Literal["dry_run_ready", "created", "blocked"]
ContentWordPressMetaWriteStatus = Literal["not_present", "review_required", "mapped"]
ContentWordPressDraftExecutionBlockerCode = Literal[
    "missing_handoff",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "handoff_not_draft_only",
    "action_apply_required",
    "live_write_not_enabled",
    "missing_live_adapter",
    "missing_write_authorization",
    "invalid_write_authorization",
    "revision_section_overrides_mismatch",
    "live_adapter_failed",
]


class ContentWordPressDraftMetadataBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["missing_wordpress_meta_mapping"] = "missing_wordpress_meta_mapping"
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    endpoint_kind: Literal["posts"] = "posts"
    post_status: Literal["draft"] = "draft"
    title: str
    content_markdown: str
    meta_title: str | None = None
    meta_description: str | None = None
    meta_write_status: ContentWordPressMetaWriteStatus = "not_present"
    metadata_blockers: list[ContentWordPressDraftMetadataBlocker] = Field(default_factory=list)
    final_canonical_url: str
    evidence_ids: list[str] = Field(default_factory=list)
    publish_allowed: bool = False
    destructive_update_allowed: bool = False


class ContentWordPressDraftSectionOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    body_markdown: str
    evidence_ids: list[str] = Field(default_factory=list)


class ContentWordPressDraftExecutionBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentWordPressDraftExecutionBlockerCode
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftExecutionBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_operation: Literal["create_wordpress_draft"] = "create_wordpress_draft"
    dry_run_default: bool = True
    live_write_enabled: bool = False
    live_adapter_configured: bool = False
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False


class ContentWordPressDraftWriteAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    preview_audit_id: str
    review_audit_id: str
    confirmation_audit_id: str
    impact_audit_id: str | None = None
    apply_audit_id: str | None = None
    confirmed_by: str
    wordpress_draft_binding: ContentDraftRevisionBinding | None = None


class ContentWordPressDraftExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentWordPressDraftExecutionStatus
    mode: ContentWordPressDraftExecutionMode
    boundary: ContentWordPressDraftExecutionBoundary
    payload: ContentWordPressDraftPayload | None = None
    revision_binding: ContentDraftRevisionBinding | None = None
    wordpress_post_id: str | None = None
    external_write_attempted: bool = False
    blockers: list[ContentWordPressDraftExecutionBlocker] = Field(default_factory=list)


def wordpress_draft_execution_errors(
    execution: ContentWordPressDraftExecutionResult,
) -> list[str]:
    if execution.status in {"dry_run_ready", "created"}:
        return []
    blockers = [f"{blocker.label}: {blocker.reason}" for blocker in execution.blockers]
    if blockers:
        return blockers
    return ["WordPress draft execution contract blocked the adapter."]


def execute_content_wordpress_draft_handoff(
    *,
    handoff: ContentWordPressDraftHandoff | None,
    draft_package: ContentDraftPackage | None,
    mode: ContentWordPressDraftExecutionMode = "dry_run",
    live_write_enabled: bool = False,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None = None,
    action_apply_authorized: bool = False,
    write_authorization: ContentWordPressDraftWriteAuthorization | None = None,
    write_authorization_verified: bool = False,
    section_overrides: list[ContentWordPressDraftSectionOverride] | None = None,
    require_exact_section_overrides: bool = False,
) -> ContentWordPressDraftExecutionResult:
    blockers = content_wordpress_draft_execution_blockers(
        handoff=handoff,
        draft_package=draft_package,
        mode=mode,
        live_write_enabled=live_write_enabled,
        create_draft=create_draft,
        action_apply_authorized=action_apply_authorized,
        write_authorization=write_authorization,
        write_authorization_verified=write_authorization_verified,
        section_overrides=section_overrides,
        require_exact_section_overrides=require_exact_section_overrides,
    )
    if blockers:
        return ContentWordPressDraftExecutionResult(
            status="blocked",
            mode=mode,
            revision_binding=handoff.revision_binding if handoff is not None else None,
            boundary=_execution_boundary(
                live_write_enabled=live_write_enabled,
                create_draft=create_draft,
            ),
            blockers=blockers,
        )

    if handoff is None:
        raise RuntimeError("WordPress handoff passed execution blockers as None.")
    if draft_package is None:
        raise RuntimeError("Draft package passed WordPress execution blockers as None.")
    payload = content_wordpress_draft_payload(
        handoff,
        draft_package,
        section_overrides=section_overrides,
    )
    if mode == "dry_run":
        return ContentWordPressDraftExecutionResult(
            status="dry_run_ready",
            mode=mode,
            revision_binding=handoff.revision_binding,
            boundary=_execution_boundary(
                live_write_enabled=live_write_enabled,
                create_draft=create_draft,
            ),
            payload=payload,
            external_write_attempted=False,
        )

    if create_draft is None:
        raise RuntimeError("Live WordPress draft creator passed execution blockers as None.")
    try:
        wordpress_post_id = create_draft(payload)
    except Exception as exc:  # pragma: no cover - adapter failures are integration-specific
        return ContentWordPressDraftExecutionResult(
            status="blocked",
            mode=mode,
            revision_binding=handoff.revision_binding,
            boundary=_execution_boundary(
                live_write_enabled=live_write_enabled,
                create_draft=create_draft,
            ),
            payload=payload,
            external_write_attempted=True,
            blockers=[
                _blocker(
                    "live_adapter_failed",
                    "Adapter WordPress zwrócił błąd",
                    _adapter_error_reason(exc),
                    (
                        "Nie ponawiaj zapisu automatycznie. Sprawdź konfigurację "
                        "WordPress i wróć do podglądu szkicu."
                    ),
                )
            ],
        )
    return ContentWordPressDraftExecutionResult(
        status="created",
        mode=mode,
        revision_binding=handoff.revision_binding,
        boundary=_execution_boundary(
            live_write_enabled=live_write_enabled,
            create_draft=create_draft,
        ),
        payload=payload,
        wordpress_post_id=wordpress_post_id,
        external_write_attempted=True,
    )


def content_wordpress_draft_execution_blockers(
    *,
    handoff: ContentWordPressDraftHandoff | None,
    draft_package: ContentDraftPackage | None,
    mode: ContentWordPressDraftExecutionMode = "dry_run",
    live_write_enabled: bool = False,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None = None,
    action_apply_authorized: bool = False,
    write_authorization: ContentWordPressDraftWriteAuthorization | None = None,
    write_authorization_verified: bool = False,
    section_overrides: list[ContentWordPressDraftSectionOverride] | None = None,
    require_exact_section_overrides: bool = False,
) -> list[ContentWordPressDraftExecutionBlocker]:
    blockers: list[ContentWordPressDraftExecutionBlocker] = []
    if handoff is None:
        blockers.append(
            _blocker(
                "missing_handoff",
                "Brakuje zatwierdzonego przekazania",
                "Nie można przygotować szkicu WordPress bez zatwierdzonego przekazania.",
                "Najpierw zatwierdź szkic, zapisz audyt i przygotuj przekazanie do WordPress.",
            )
        )
    if draft_package is None:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "WordPress potrzebuje treści szkicu, a nie samego tytułu.",
                "Przygotuj paczkę szkicu z sekcjami i mapą dowodów.",
            )
        )
    if handoff is not None and draft_package is not None:
        blockers.extend(_handoff_payload_blockers(handoff, draft_package))
        if require_exact_section_overrides:
            blockers.extend(
                _exact_section_override_blockers(
                    draft_package,
                    section_overrides or [],
                )
            )
    if mode == "live":
        blockers.extend(
            _live_write_blockers(
                live_write_enabled,
                create_draft,
                action_apply_authorized,
                write_authorization,
                write_authorization_verified,
            )
        )
    return blockers


def content_wordpress_draft_payload(
    handoff: ContentWordPressDraftHandoff,
    draft_package: ContentDraftPackage,
    *,
    section_overrides: list[ContentWordPressDraftSectionOverride] | None = None,
) -> ContentWordPressDraftPayload:
    document = handoff.revision_document
    if document is not None and document.schema_version == "wilq_content_draft_revision_v2":
        if document.page_assets is None:
            raise RuntimeError("Full-document revision passed validation without page assets.")
        return ContentWordPressDraftPayload(
            title=document.page_assets.wordpress_title,
            content_markdown=revision_document_markdown(document),
            meta_title=document.page_assets.meta_title,
            meta_description=document.page_assets.meta_description,
            meta_write_status="review_required",
            metadata_blockers=[_missing_meta_mapping_blocker()],
            final_canonical_url=handoff.final_canonical_url,
            evidence_ids=handoff.evidence_ids,
        )
    return ContentWordPressDraftPayload(
        title=handoff.title,
        content_markdown=_content_markdown_from_draft_package(
            draft_package,
            title=handoff.title,
            section_overrides=section_overrides,
        ),
        final_canonical_url=handoff.final_canonical_url,
        evidence_ids=handoff.evidence_ids,
    )


def _missing_meta_mapping_blocker() -> ContentWordPressDraftMetadataBlocker:
    return ContentWordPressDraftMetadataBlocker(
        label="Meta pola wymagają mapowania WordPress",
        reason=(
            "Pełny dokument zachowuje meta title i description, ale WILQ nie ma "
            "potwierdzonego profilu ACF/SEO dla automatycznego zapisu tych pól."
        ),
        next_step="Sprawdź mapowanie profilu WordPress; nie kopiuj pól w ciemno.",
    )


def _handoff_payload_blockers(
    handoff: ContentWordPressDraftHandoff,
    draft_package: ContentDraftPackage,
) -> list[ContentWordPressDraftExecutionBlocker]:
    blockers: list[ContentWordPressDraftExecutionBlocker] = []
    if handoff.draft_package_id != draft_package.id:
        blockers.append(
            _blocker(
                "draft_package_mismatch",
                "Paczka szkicu nie pasuje do przekazania",
                "Nie można wysłać do WordPress innej paczki szkicu niż ta, którą zatwierdzono.",
                "Użyj paczki szkicu powiązanej z zatwierdzonym przekazaniem.",
            )
        )
    if draft_package.publish_ready:
        blockers.append(
            _blocker(
                "draft_package_marked_publish_ready",
                "Szkic nie może udawać publikacji",
                "Ten krok tworzy wyłącznie szkic w WordPress, nie gotową publikację.",
                "Zatrzymaj status publikacji i zostaw treść jako szkic do sprawdzenia.",
            )
        )
    if (
        handoff.post_status != "draft"
        or handoff.publish_allowed
        or handoff.destructive_update_allowed
    ):
        blockers.append(
            _blocker(
                "handoff_not_draft_only",
                "Przekazanie nie jest bezpiecznym szkicem",
                "Ten krok może działać tylko na szkicu bez publikacji i bez nadpisywania treści.",
                "Wróć do kontraktu przekazania i ustaw tryb szkicu bez publikacji.",
            )
        )
    return blockers


def _exact_section_override_blockers(
    draft_package: ContentDraftPackage,
    section_overrides: list[ContentWordPressDraftSectionOverride],
) -> list[ContentWordPressDraftExecutionBlocker]:
    expected_headings = [_section_key(section.heading) for section in draft_package.sections]
    override_headings = [_section_key(section.heading) for section in section_overrides]
    if (
        override_headings == expected_headings
        and len(set(override_headings)) == len(override_headings)
        and all(section.body_markdown.strip() for section in section_overrides)
    ):
        return []
    return [
        _blocker(
            "revision_section_overrides_mismatch",
            "Treść wersji nie pasuje do planu sekcji",
            (
                "Zapis wersji wymaga dokładnie wszystkich sekcji w zatwierdzonej "
                "kolejności i bez pustej treści."
            ),
            "Wróć do aktualnej zatwierdzonej wersji i ponów podgląd ActionObject.",
        )
    ]


def _live_write_blockers(
    live_write_enabled: bool,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None,
    action_apply_authorized: bool,
    write_authorization: ContentWordPressDraftWriteAuthorization | None,
    write_authorization_verified: bool,
) -> list[ContentWordPressDraftExecutionBlocker]:
    if not action_apply_authorized:
        return [
            _blocker(
                "action_apply_required",
                "Zapis wymaga kanonicznej akcji apply",
                (
                    "Ten endpoint może przygotować podgląd szkicu, ale nie może "
                    "samodzielnie uruchamiać adaptera WordPress."
                ),
                (
                    "Użyj trybu dry-run. Realny zapis może wrócić dopiero przez "
                    "apply-capable ActionObject z preview, review, confirm i audytem."
                ),
            )
        ]
    if not live_write_enabled:
        return [
            _blocker(
                "live_write_not_enabled",
                "Zapis do WordPress jest wyłączony",
                "WILQ przygotował bezpieczny podgląd, ale nie ma zgody na realny zapis.",
                "Użyj trybu podglądu albo jawnie włącz osobny adapter zapisu szkicu.",
            )
        ]
    if create_draft is None:
        return [
            _blocker(
                "missing_live_adapter",
                "Brakuje adaptera zapisu",
                "Nie można zapisać szkicu bez adaptera, który tworzy wpis w WordPress.",
                "Podłącz adapter zapisu szkicu i zostaw publikację wyłączoną.",
            )
        ]
    if write_authorization is None or not _write_authorization_complete(write_authorization):
        return [
            _blocker(
                "missing_write_authorization",
                "Brakuje potwierdzenia ścieżki zapisu",
                (
                    "Realny szkic WordPress wymaga śladu: podgląd, review, "
                    "potwierdzenie i osoba potwierdzająca."
                ),
                (
                    "Przejdź przez ActionObject validate, preview, review, "
                    "confirm i audit przed uruchomieniem zapisu."
                ),
            )
        ]
    if not write_authorization_verified:
        return [
            _blocker(
                "invalid_write_authorization",
                "Ślad zgody nie pasuje do audytu",
                (
                    "WILQ dostał dane zgody, ale nie potwierdził ich w zapisanych "
                    "zdarzeniach audytu."
                ),
                (
                    "Wróć do akcji WordPress i zapisz kolejno: podgląd, review, "
                    "potwierdzenie oraz apply audit."
                ),
            )
        ]
    return []


def _write_authorization_complete(
    authorization: ContentWordPressDraftWriteAuthorization,
) -> bool:
    return all(
        bool(value.strip())
        for value in (
            authorization.action_id,
            authorization.preview_audit_id,
            authorization.review_audit_id,
            authorization.confirmation_audit_id,
            authorization.confirmed_by,
        )
    )


def _execution_boundary(
    *,
    live_write_enabled: bool,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None,
) -> ContentWordPressDraftExecutionBoundary:
    return ContentWordPressDraftExecutionBoundary(
        live_write_enabled=live_write_enabled,
        live_adapter_configured=create_draft is not None,
    )


def _adapter_error_reason(exc: Exception) -> str:
    public_message = getattr(exc, "public_message", None)
    if isinstance(public_message, str) and public_message.strip():
        return public_message.strip()
    return (
        f"Adapter przerwał zapis szkicu bez ujawniania danych technicznych ({type(exc).__name__})."
    )


def _content_markdown_from_draft_package(
    draft_package: ContentDraftPackage,
    *,
    title: str | None = None,
    section_overrides: list[ContentWordPressDraftSectionOverride] | None = None,
) -> str:
    overrides = _section_override_map(section_overrides or [])
    chunks = [f"# {title or draft_package.title}"]
    for section in draft_package.sections:
        chunks.append(f"## {section.heading}")
        override = overrides.get(_section_key(section.heading))
        if override is not None:
            chunks.append(override.body_markdown.strip())
        else:
            chunks.append(section.purpose)
        if override is None and section.draft_notes:
            chunks.extend(f"- {note}" for note in section.draft_notes)
    return "\n\n".join(chunks)


def _section_override_map(
    section_overrides: list[ContentWordPressDraftSectionOverride],
) -> dict[str, ContentWordPressDraftSectionOverride]:
    result: dict[str, ContentWordPressDraftSectionOverride] = {}
    for override in section_overrides:
        key = _section_key(override.heading)
        body = override.body_markdown.strip()
        if not key or not body:
            continue
        result[key] = ContentWordPressDraftSectionOverride(
            heading=override.heading.strip(),
            body_markdown=body,
            evidence_ids=override.evidence_ids,
        )
    return result


def _section_key(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _blocker(
    code: ContentWordPressDraftExecutionBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentWordPressDraftExecutionBlocker:
    return ContentWordPressDraftExecutionBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
