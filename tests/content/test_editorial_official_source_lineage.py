from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.content.test_full_document_revision_v2 import _draft_package, _full_document_command
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.documents.official_source_lineage import (
    build_official_source_lineage_rebase_command,
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
