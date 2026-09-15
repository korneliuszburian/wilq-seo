from __future__ import annotations

from types import SimpleNamespace

import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.decisions.production import (
    project_content_production_classification,
)
from wilq.content.workflow.workspace.production_decision import build_content_production_decision


def test_matching_url_without_persisted_identity_is_explicitly_missing() -> None:
    run = exact_public_bdo_run()
    projection = project_content_production_classification(run, run.rows[0])
    production = build_content_production_decision(
        projection.row.current_work_item_id or "content_work_item_bdo",
        classification=projection,
    )
    readiness = selected_workspace_module._identity_readiness(production, None)

    assert readiness.status == "missing"
    assert readiness.binding_id is None


def test_matching_url_with_foreign_work_item_is_not_bound() -> None:
    run = exact_public_bdo_run()
    projection = project_content_production_classification(run, run.rows[0])
    production = build_content_production_decision(
        projection.row.current_work_item_id or "content_work_item_bdo",
        classification=projection,
    )
    readiness = selected_workspace_module._identity_readiness(
        production,
        SimpleNamespace(
            binding=SimpleNamespace(
                status="exact_current",
                current_work_item_id="content_work_item_foreign",
                canonical_path=production.canonical_path,
                public_url=production.public_url,
                classification_run_id=production.run_id,
                classification_run_digest=production.run_digest,
                classification_decision_set_digest=production.decision_set_digest,
                binding_id="content_delivery_identity_foreign",
            )
        ),
    )

    assert readiness.status == "mismatch"
    assert readiness.binding_id is None


def test_matching_recorded_identity_uses_blocked_current_projection() -> None:
    run = exact_public_bdo_run()
    projection = project_content_production_classification(run, run.rows[0])
    production = build_content_production_decision(
        projection.row.current_work_item_id or "content_work_item_bdo",
        classification=projection,
    )
    binding = SimpleNamespace(
        status="exact_current",
        current_work_item_id=production.current_work_item_id,
        canonical_path=production.canonical_path,
        public_url=production.public_url,
        classification_run_id=production.run_id,
        classification_run_digest=production.run_digest,
        classification_decision_set_digest=production.decision_set_digest,
        binding_id="content_delivery_identity_exact",
    )
    readiness = selected_workspace_module._identity_readiness(
        production,
        SimpleNamespace(
            binding=binding,
            current=SimpleNamespace(
                current_status="blocked",
                current_safe_next_step="Odśwież exact S1/classification context.",
            ),
        ),
    )

    assert readiness.status == "mismatch"
    assert readiness.binding_id is None
