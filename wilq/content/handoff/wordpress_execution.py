from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff

ContentWordPressDraftExecutionMode = Literal["dry_run", "live"]
ContentWordPressDraftExecutionStatus = Literal["dry_run_ready", "created", "blocked"]
ContentWordPressDraftExecutionBlockerCode = Literal[
    "missing_handoff",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "handoff_not_draft_only",
    "live_write_not_enabled",
    "missing_live_adapter",
]


class ContentWordPressDraftPayload(BaseModel):
    connector: Literal["wordpress_ekologus"] = "wordpress_ekologus"
    endpoint_kind: Literal["posts"] = "posts"
    post_status: Literal["draft"] = "draft"
    title: str
    content_markdown: str
    final_canonical_url: str
    evidence_ids: list[str] = Field(default_factory=list)
    publish_allowed: bool = False
    destructive_update_allowed: bool = False


class ContentWordPressDraftExecutionBlocker(BaseModel):
    code: ContentWordPressDraftExecutionBlockerCode
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftExecutionResult(BaseModel):
    status: ContentWordPressDraftExecutionStatus
    mode: ContentWordPressDraftExecutionMode
    payload: ContentWordPressDraftPayload | None = None
    wordpress_post_id: str | None = None
    external_write_attempted: bool = False
    blockers: list[ContentWordPressDraftExecutionBlocker] = Field(default_factory=list)


def execute_content_wordpress_draft_handoff(
    *,
    handoff: ContentWordPressDraftHandoff | None,
    draft_package: ContentDraftPackage | None,
    mode: ContentWordPressDraftExecutionMode = "dry_run",
    live_write_enabled: bool = False,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None = None,
) -> ContentWordPressDraftExecutionResult:
    blockers = content_wordpress_draft_execution_blockers(
        handoff=handoff,
        draft_package=draft_package,
        mode=mode,
        live_write_enabled=live_write_enabled,
        create_draft=create_draft,
    )
    if blockers:
        return ContentWordPressDraftExecutionResult(
            status="blocked",
            mode=mode,
            blockers=blockers,
        )

    if handoff is None:
        raise RuntimeError("WordPress handoff passed execution blockers as None.")
    if draft_package is None:
        raise RuntimeError("Draft package passed WordPress execution blockers as None.")
    payload = content_wordpress_draft_payload(handoff, draft_package)
    if mode == "dry_run":
        return ContentWordPressDraftExecutionResult(
            status="dry_run_ready",
            mode=mode,
            payload=payload,
            external_write_attempted=False,
        )

    if create_draft is None:
        raise RuntimeError("Live WordPress draft creator passed execution blockers as None.")
    wordpress_post_id = create_draft(payload)
    return ContentWordPressDraftExecutionResult(
        status="created",
        mode=mode,
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
    if mode == "live":
        blockers.extend(_live_write_blockers(live_write_enabled, create_draft))
    return blockers


def content_wordpress_draft_payload(
    handoff: ContentWordPressDraftHandoff,
    draft_package: ContentDraftPackage,
) -> ContentWordPressDraftPayload:
    return ContentWordPressDraftPayload(
        title=handoff.title,
        content_markdown=_content_markdown_from_draft_package(draft_package),
        final_canonical_url=handoff.final_canonical_url,
        evidence_ids=handoff.evidence_ids,
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


def _live_write_blockers(
    live_write_enabled: bool,
    create_draft: Callable[[ContentWordPressDraftPayload], str] | None,
) -> list[ContentWordPressDraftExecutionBlocker]:
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
    return []


def _content_markdown_from_draft_package(draft_package: ContentDraftPackage) -> str:
    chunks = [f"# {draft_package.title}"]
    for section in draft_package.sections:
        chunks.append(f"## {section.heading}")
        chunks.append(section.purpose)
        if section.draft_notes:
            chunks.extend(f"- {note}" for note in section.draft_notes)
    return "\n\n".join(chunks)


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
