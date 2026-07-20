from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.connectors.wordpress.client import WordPressDraftReadError, read_wordpress_draft_post
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionResult,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftReadback,
    ContentWordPressDraftReadbackBlocker,
    ContentWorkItemWorkflowSnapshotResponse,
)


@dataclass(frozen=True)
class ActivationProjectionCallbacks:
    readback: Callable[[ContentWordPressDraftExecutionResult], ContentWordPressDraftReadback | None]
    missing_step: Callable[..., str]
    missing_step_label: Callable[[str], str]
    missing_labels: Callable[..., list[str]]
    review_preview_label: Callable[[bool], str]
    checklist: Callable[..., list[str]]
    next_step: Callable[..., str]
    steps: Callable[..., list[str]]
    writes_enabled: Callable[[], bool]


def wordpress_draft_readback(
    execution: ContentWordPressDraftExecutionResult,
) -> ContentWordPressDraftReadback | None:
    if execution.status != "created":
        return None
    post_id = (execution.wordpress_post_id or "").strip()
    if not post_id:
        return ContentWordPressDraftReadback(
            status="blocked",
            wordpress_post_id=None,
            blockers=[
                ContentWordPressDraftReadbackBlocker(
                    code="missing_wordpress_post_id",
                    label="Brak ID szkicu WordPress",
                    reason=(
                        "WILQ zapisał wynik utworzenia szkicu, ale nie ma ID wpisu "
                        "potrzebnego do odczytu z dev WordPressa."
                    ),
                    next_step=(
                        "Utwórz szkic ponownie przez ActionObject albo sprawdź audit "
                        "wykonania zapisu."
                    ),
                )
            ],
        )
    try:
        readback = read_wordpress_draft_post(post_id)
    except WordPressDraftReadError as exc:
        return ContentWordPressDraftReadback(
            status="blocked",
            wordpress_post_id=post_id,
            blockers=[
                ContentWordPressDraftReadbackBlocker(
                    code="wordpress_draft_read_failed",
                    label="Nie udało się odczytać szkicu WordPress",
                    reason=exc.public_message,
                    next_step=(
                        "Sprawdź dostęp REST WordPress i odśwież panel szkicu. "
                        "Nie traktuj samego ID jako potwierdzenia treści."
                    ),
                )
            ],
        )
    return ContentWordPressDraftReadback(
        status="available",
        wordpress_post_id=readback.post_id,
        post_status=readback.status,
        title=readback.title,
        link=readback.link,
        edit_link=readback.edit_link,
        modified_gmt=readback.modified_gmt,
        content_summary=readback.content_summary,
        content_word_count=readback.content_word_count,
        acf_field_count=readback.acf_field_count,
        acf_field_names=readback.acf_field_names,
    )


def wordpress_draft_activation_missing_step(
    *, draft_package_ready: bool, human_review_ready: bool, audit_ready: bool,
    handoff_ready: bool, dry_run_ready: bool,
) -> Literal["draft_package", "human_review", "audit", "handoff", "dry_run", "ready"]:
    if not draft_package_ready:
        return "draft_package"
    if not human_review_ready:
        return "human_review"
    if not audit_ready:
        return "audit"
    if not handoff_ready:
        return "handoff"
    if not dry_run_ready:
        return "dry_run"
    return "ready"


def wordpress_draft_activation_missing_step_label(step: str) -> str:
    return {
        "draft_package": "przygotuj paczkę szkicu",
        "human_review": "zapisz review człowieka",
        "audit": "zapisz audit przekazania do WordPress",
        "handoff": "przygotuj handoff WordPress draft-only",
        "dry_run": "wygeneruj podgląd dry-run payloadu WordPress",
        "ready": "podgląd draft-only jest gotowy do review",
    }.get(step, "sprawdź paczkę aktywacji WordPress")


def wordpress_draft_activation_missing_labels(
    *, draft_package_ready: bool, human_review_ready: bool, audit_ready: bool,
    handoff_ready: bool, dry_run_ready: bool,
) -> list[str]:
    labels: list[str] = []
    if not draft_package_ready:
        labels.append("paczka szkicu")
    if not human_review_ready:
        labels.append("review człowieka")
    if not audit_ready:
        labels.append("audit przekazania")
    if not handoff_ready:
        labels.append("handoff WordPress")
    if not dry_run_ready:
        labels.append("podgląd dry-run")
    return labels


def wordpress_draft_review_preview_status_label(draft_package_ready: bool) -> str:
    if draft_package_ready:
        return "Paczka szkicu jest gotowa do review człowieka."
    return "Najpierw przygotuj paczkę szkicu z Claim Ledgerem i dowodami."


def wordpress_draft_human_review_checklist(
    *, draft_package_ready: bool, human_review_ready: bool
) -> list[str]:
    if human_review_ready:
        return ["Review człowieka jest zapisane; teraz sprawdź audyt i handoff WordPress."]
    if not draft_package_ready:
        return [
            "Przygotuj paczkę szkicu z tytułem, sekcjami, mapą dowodów i Claim Ledgerem.",
            "Nie oceniaj handoffu WordPress przed paczką szkicu.",
        ]
    return [
        "Czy tytuł, sekcje i kolejność odpowiadają intencji wybranego tematu?",
        "Czy każdy claim ma dowód albo jest jawnie zablokowany w Claim Ledger?",
        "Czy treść brzmi jak Ekologus, a nie jak generyczny artykuł SEO?",
        "Czy CTA jest konsultacyjne i nie obiecuje wyniku, decyzji ani braku kar?",
        "Czy materiał ma zostać tylko szkicem WordPress, bez publikacji i bez "
        "aktualizacji istniejącego wpisu?",
    ]


def build_content_wordpress_draft_activation_packet_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    callbacks: ActivationProjectionCallbacks,
    action_id: str = "act_apply_wordpress_draft_handoff",
    latest_execution_result: ContentWordPressDraftExecutionResult | None = None,
) -> ContentWordPressDraftActivationPacketResponse:
    item = snapshot.preflight.item
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff_result = snapshot.wordpress_handoff.handoff_result
    handoff = handoff_result.handoff
    execution = latest_execution_result or execute_content_wordpress_draft_handoff(
        handoff=handoff,
        draft_package=draft_package,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    handoff_blockers: list[str] = [blocker.code for blocker in handoff_result.blockers]
    execution_blockers: list[str] = [blocker.code for blocker in execution.blockers]
    execution_ready = execution.status in {"dry_run_ready", "created"}
    draft_readback = callbacks.readback(execution)
    human_review_ready = "missing_human_review" not in handoff_blockers
    audit_ready = "missing_audit" not in handoff_blockers
    missing_step = cast(
        Literal["draft_package", "human_review", "audit", "handoff", "dry_run", "ready"],
        callbacks.missing_step(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
            audit_ready=audit_ready,
            handoff_ready=handoff is not None,
            dry_run_ready=execution_ready,
        ),
    )
    return ContentWordPressDraftActivationPacketResponse(
        action_id=action_id,
        work_item_id=item.id,
        topic=item.topic,
        final_canonical_url=item.final_canonical_url,
        draft_package_ready=draft_package is not None,
        draft_package_id=draft_package.id if draft_package is not None else None,
        review_preview_ready=draft_package is not None,
        review_preview_status_label=callbacks.review_preview_label(draft_package is not None),
        human_review_checklist=callbacks.checklist(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
        ),
        human_review_ready=human_review_ready,
        audit_ready=audit_ready,
        handoff_ready=handoff is not None,
        handoff_id=handoff.id if handoff is not None else None,
        dry_run_ready=execution_ready,
        live_write_enabled_by_env=callbacks.writes_enabled(),
        handoff_blockers=handoff_blockers,
        execution_blockers=execution_blockers,
        activation_missing_step=missing_step,
        activation_missing_step_label=callbacks.missing_step_label(missing_step),
        activation_missing_readiness_labels=callbacks.missing_labels(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
            audit_ready=audit_ready,
            handoff_ready=handoff is not None,
            dry_run_ready=execution_ready,
        ),
        execution_result=execution,
        draft_readback=draft_readback,
        operator_next_step=callbacks.next_step(
            handoff_blockers,
            execution_blockers,
            execution_status=execution.status,
            draft_readback=draft_readback,
        ),
        next_steps=callbacks.steps(
            draft_package_ready=draft_package is not None,
            handoff_blockers=handoff_blockers,
            execution_blockers=execution_blockers,
            execution_status=execution.status,
        ),
        evidence_ids=item.evidence_ids,
        source_connectors=item.source_connectors,
    )
