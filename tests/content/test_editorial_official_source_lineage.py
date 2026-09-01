from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.api.wilq_api.routers.content_official_source_lineage import (
    _lineage_rebase_context_allowed,
)
from tests.content.test_full_document_revision_v2 import _draft_package, _full_document_command
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.documents.codex_revision_commit import (
    ContentDraftRevisionContext,
    current_editor_draft_context_guard,
)
from wilq.content.workflow.documents.official_source_lineage import (
    build_official_source_lineage_rebase_command,
)
from wilq.content.workflow.documents.official_source_lineage_store import (
    ContentOfficialSourceLineageStore,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionOfficialSourceReference,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_official_source_lineage_rebase_repairs_existing_editorial_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _full_document_command(_draft_package(), base_revision_id=None).model_copy(
        update={"content_kind": "editorial", "service_card_id": None, "service_digest": None}
    )
    current = ContentDraftRevisionOfficialSourceReference(
        source_fact_id="regulatory_source_fact_ekoportal",
        source_url="https://www.ekoportal.gov.pl/current-source.pdf",
        source_title="Wytyczne Ekoportal",
        verified_on="2026-09-01",
        evidence_ids=["ev_regulatory_ekoportal"],
        regulatory_requirement_ids=["initial_report"],
    )
    base = ContentWorkflowStore(tmp_path / "wilq.sqlite3").append_draft_revision(command).revision
    assert base is not None
    base = base.model_copy(
        update={
            "official_source_references": [
                current.model_copy(update={"source_url": "https://www.ekoportal.gov.pl/old.pdf"})
            ]
        }
    )
    monkeypatch.setattr(
        "wilq.content.workflow.documents.official_source_lineage.official_source_references_for_planning_input",
        lambda _input: [current],
    )
    planning_input = ContentPlanningInput.model_construct(
        planning_input_digest=base.planning_input_digest,
        confirmed_service_card_id=None,
    )
    proposal = SimpleNamespace(
        planning_digest=base.planning_digest,
        planning_input_digest=base.planning_input_digest,
        content_kind="editorial",
        service_card_id=None,
    )

    child = build_official_source_lineage_rebase_command(
        base_revision=base,
        planning_input=planning_input,
        proposal=proposal,  # type: ignore[arg-type]
        requested_by="wilku",
    )

    assert child.base_revision_id == base.revision_id
    assert child.official_source_references == [current]

    assert _lineage_rebase_context_allowed(
        context_current=False,
        base_revision=base,
        draft_package=_draft_package(),
    )
    changed_package = _draft_package().model_copy(
        update={"human_review_questions": ["Nowe pytanie właściciela"]}
    )
    assert not _lineage_rebase_context_allowed(
        context_current=False,
        base_revision=base,
        draft_package=changed_package,
    )


def test_lineage_rebase_store_rechecks_context_inside_transaction(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    base = store.append_draft_revision(
        _full_document_command(_draft_package(), base_revision_id=None)
    ).revision
    assert base is not None
    child = _full_document_command(
        _draft_package(),
        base_revision_id=base.revision_id,
    ).model_copy(update={"correction_reason": "official_source_lineage_rebase"})
    expected = ContentDraftRevisionContext.from_command(child)
    assert expected is not None
    changed = replace(expected, draft_package_digest="0" * 64)

    with current_editor_draft_context_guard(lambda: changed):
        result = ContentOfficialSourceLineageStore(tmp_path / "wilq.sqlite3").append_rebase(
            child,
            expected_latest_review_decision_id=None,
        )

    assert result.status == "conflict"
    assert result.conflict is not None
    assert result.conflict.code == "stale_context"
    assert store.load_draft_revision_state(base.work_item_id).revision_count == 1
