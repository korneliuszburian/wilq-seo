from datetime import UTC, datetime

from wilq.content.quality.editorial_integrity import build_content_editorial_integrity_report
from wilq.content.workflow.content_html import content_html_from_markdown
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionSection


def _revision(
    revision_id: str,
    digest: str,
    *,
    base_revision_id: str | None,
    body: str,
    content_html: str | None,
) -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        revision_id=revision_id,
        work_item_id="content_work_item_integrity",
        revision_number=int(revision_id[-1]),
        base_revision_id=base_revision_id,
        content_digest=digest,
        draft_package_id="draft_package_integrity",
        draft_package_digest="a" * 64,
        planning_digest="b" * 64,
        final_canonical_url="https://www.ekologus.pl/integrity",
        title="Treść BDO",
        sections=[
            ContentDraftRevisionSection(
                section_id="section_bdo",
                heading="Ewidencja odpadów",
                body_markdown=body,
                content_html=content_html,
                evidence_ids=["ev_bdo"],
                claim_ids=["claim_bdo"],
            )
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
        created_by="operator_local_dashboard",
        created_at=datetime.now(UTC),
    )


def test_editorial_integrity_separates_invalid_html_loss_and_restored_content() -> None:
    source = "Sprawdź rodzaje i ilości odpadów oraz wykonywane operacje."
    r8 = _revision(
        "revision_8",
        "8" * 64,
        base_revision_id=None,
        body=source,
        content_html=content_html_from_markdown(source),
    )
    reduced = "Sprawdź zakres danych dotyczących odpadów."
    r9 = _revision(
        "revision_9",
        "9" * 64,
        base_revision_id=r8.revision_id,
        body=reduced,
        content_html=r8.sections[0].content_html,
    )
    r10 = _revision(
        "revision_10",
        "a" * 64,
        base_revision_id=r9.revision_id,
        body=reduced,
        content_html=content_html_from_markdown(reduced),
    )
    r11 = _revision(
        "revision_11",
        "b" * 64,
        base_revision_id=r10.revision_id,
        body=source,
        content_html=content_html_from_markdown(source),
    )
    revisions = [r8, r9, r10, r11]

    r9_report = build_content_editorial_integrity_report(
        work_item_id=r8.work_item_id,
        revision_id=r9.revision_id,
        revisions=revisions,
    )
    r10_report = build_content_editorial_integrity_report(
        work_item_id=r8.work_item_id,
        revision_id=r10.revision_id,
        revisions=revisions,
    )
    r11_report = build_content_editorial_integrity_report(
        work_item_id=r8.work_item_id,
        revision_id=r11.revision_id,
        revisions=revisions,
    )

    assert r9_report.result == "invalid_representation"
    assert {item.status for item in r9_report.representation_alignment} == {"mismatch"}
    assert any(unit.status == "removed" for unit in r10_report.protected_content_units)
    assert {item.status for item in r10_report.representation_alignment} == {"aligned"}
    assert r11_report.result == "pass"
    assert {unit.status for unit in r11_report.protected_content_units} == {"preserved"}
