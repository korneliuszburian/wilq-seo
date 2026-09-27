"""Per-URL readiness over the newest current-acceptance wave row."""

from __future__ import annotations

from wilq.content.workflow.current_acceptance_contracts import CurrentAcceptanceRow


class _FakeStore:
    def __init__(
        self,
        *,
        work_item_row: CurrentAcceptanceRow | None,
        path_row: CurrentAcceptanceRow | None = None,
    ) -> None:
        self.work_item_row = work_item_row
        self.path_row = path_row
        self.path_queries: list[str] = []

    def load_latest_current_acceptance_row_for_work_item(
        self,
        current_work_item_id: str,
    ) -> CurrentAcceptanceRow | None:
        return self.work_item_row

    def load_latest_current_acceptance_row_for_path(
        self,
        *,
        canonical_path: str,
    ) -> CurrentAcceptanceRow | None:
        self.path_queries.append(canonical_path)
        return self.path_row


def _blocked_row(
    *,
    path: str = "/candidates",
    blocker_code: str = "service_binding_missing",
    work_item_id: str = "wi_current_acceptance",
) -> CurrentAcceptanceRow:
    return CurrentAcceptanceRow(
        canonical_path=path,
        public_url=f"https://www.ekologus.pl{path}/",
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=work_item_id,
        blocker_code=blocker_code,
        blocker_owner="WILQ content workflow",
        safe_next_step="Utwórz exact reviewed powiązanie strony z profilem usługi.",
    )


def _keep_row(*, work_item_id: str = "wi_current_acceptance") -> CurrentAcceptanceRow:
    return CurrentAcceptanceRow(
        canonical_path="/candidates",
        public_url="https://www.ekologus.pl/candidates/",
        scope_disposition="eligible",
        decision="keep",
        current_work_item_id=work_item_id,
        page_material_status="reviewed_material_current",
        identity_id="content_current_page_identity_v3_test",
        identity_digest="a" * 64,
        page_evidence_digest="b" * 64,
        observation_id="content_per_url_decision_observation_test",
        observation_digest="c" * 64,
        semantic_row_digest="d" * 64,
        source_fact_ids=("fact_test",),
        evidence_ids=("ev_wp_run",),
        safe_next_step="Otwórz review exact page i zatwierdzonych faktów; bez publikacji.",
    )


def test_per_url_readiness_requires_a_current_acceptance_row() -> None:
    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_per_url_preparation_readiness,
    )

    readiness = resolve_current_per_url_preparation_readiness(
        _FakeStore(work_item_row=None),
        "wi_current_acceptance",
    )

    assert readiness.status == "blocked"
    assert readiness.code == "current_acceptance_row_missing"
    assert readiness.safe_next_step_pl


def test_per_url_readiness_copies_a_blocked_wave_row() -> None:
    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_per_url_preparation_readiness,
    )

    store = _FakeStore(work_item_row=_blocked_row())
    readiness = resolve_current_per_url_preparation_readiness(store, "wi_current_acceptance")

    assert readiness.status == "blocked"
    assert readiness.code == "service_binding_missing"
    assert readiness.safe_next_step_pl == (
        "Utwórz exact reviewed powiązanie strony z profilem usługi."
    )


def test_per_url_readiness_fails_closed_without_acceptance_loaders() -> None:
    from typing import cast

    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_per_url_preparation_readiness,
    )
    from wilq.content.workflow.current_preparation_readiness_contracts import (
        CurrentPerUrlPreparationReadinessStore,
    )

    readiness = resolve_current_per_url_preparation_readiness(
        cast(CurrentPerUrlPreparationReadinessStore, object()),
        "wi_current_acceptance",
    )

    assert readiness.status == "blocked"
    assert readiness.code == "current_acceptance_row_missing"


def test_per_url_readiness_uses_the_newest_path_row() -> None:
    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_per_url_preparation_readiness,
    )

    store = _FakeStore(
        work_item_row=_keep_row(),
        path_row=_blocked_row(blocker_code="current_acceptance_work_item_rebound"),
    )
    readiness = resolve_current_per_url_preparation_readiness(store, "wi_current_acceptance")

    assert store.path_queries == ["/candidates"]
    assert readiness.status == "blocked"
    assert readiness.code == "current_acceptance_work_item_rebound"


def test_per_url_readiness_stops_at_the_human_keep_receipt_gate() -> None:
    from wilq.content.workflow.current_preparation_readiness import (
        resolve_current_per_url_preparation_readiness,
    )

    store = _FakeStore(work_item_row=_keep_row(), path_row=_keep_row())
    readiness = resolve_current_per_url_preparation_readiness(store, "wi_current_acceptance")

    assert readiness.status == "blocked"
    assert readiness.code == "approved_keep_receipt_required"
