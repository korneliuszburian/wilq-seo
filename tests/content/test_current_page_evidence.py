from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_model_routes
from apps.api.wilq_api.routers.content_material_review import (
    register_content_material_review_routes,
)
from wilq.content.workflow.evidence_acquisition_snapshot import (
    CurrentPageSnapshotReadError,
    WordPressCurrentPageSnapshotAdapter,
)
from wilq.content.workflow.material_review import MaterialReaderFactory, SelectedItemLoader
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
    inventory_work_item_id,
)

if TYPE_CHECKING:
    from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse

PAGE_A = "https://www.ekologus.pl/oferta/evidence-a/"
PAGE_B = "https://www.ekologus.pl/oferta/evidence-b/"
PAGE_URL_ONLY = "https://www.ekologus.pl/oferta/evidence-url-only/"


@dataclass
class _TestState:
    now: datetime
    freshness: str
    coverage: str
    wave: int
    latest_source_ids: tuple[str, ...]
    bodies: dict[str, str]


@dataclass
class _Harness:
    client: TestClient
    state: _TestState
    work_item_ids: dict[str, str]
    catalog: Callable[[], ContentInventoryCatalogResponse]


def test_public_current_page_evidence_tracks_exact_material_meaning_per_url(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    client = harness.client
    state = harness.state
    work_item_ids = harness.work_item_ids
    initial = client.get(
        f"/api/content/work-items/{work_item_ids[PAGE_A]}/current-page-evidence"
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "observed_material_current"

    digest_a_first = _get_page_evidence(client, work_item_ids[PAGE_A]).material_meaning_digest
    digest_b_first = _get_page_evidence(client, work_item_ids[PAGE_B]).material_meaning_digest
    wave_one_catalog = harness.catalog()
    state.wave = 2
    state.bodies[PAGE_B] = "B changed " + ("different material " * 360)
    wave_two_catalog = harness.catalog()
    drift = client.get(
        f"/api/content/work-items/{work_item_ids[PAGE_A]}/current-page-evidence"
    )
    assert drift.status_code == 200, drift.text
    assert drift.json()["blocker_code"] == "source_evidence_drift"
    state.latest_source_ids = tuple(wave_two_catalog.evidence_ids)

    result_a = _get_page_evidence(client, work_item_ids[PAGE_A])
    result_b = _get_page_evidence(client, work_item_ids[PAGE_B])
    assert result_a.status == "observed_material_current", result_a
    assert result_b.status == "observed_material_current", result_b
    assert result_a.material_meaning_digest == digest_a_first
    assert result_b.material_meaning_digest != digest_b_first
    assert result_a.generation_allowed is False
    assert result_a.catalog_evidence_ids != wave_one_catalog.evidence_ids
    assert [item.collected_at for item in wave_two_catalog.items] != [
        item.collected_at for item in wave_one_catalog.items
    ]
    assert result_a.current_evidence_ids
    assert result_a.material_meaning_digest not in result_a.current_evidence_ids

    url_only = _get_page_evidence(client, work_item_ids[PAGE_URL_ONLY])
    assert url_only.blocker_code == "page_material_url_only"
    state.freshness = "stale"
    stale_source = _get_page_evidence(client, work_item_ids[PAGE_A])
    assert stale_source.blocker_code == "source_freshness_blocked"
    state.freshness = "fresh"
    state.coverage = "partial"
    incomplete = _get_page_evidence(client, work_item_ids[PAGE_A])
    assert incomplete.blocker_code == "source_catalog_incomplete"


def test_public_current_page_evidence_observes_full_material_without_human_receipt(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    work_a = harness.work_item_ids[PAGE_A]
    work_b = harness.work_item_ids[PAGE_B]
    first_a = _get_page_evidence(harness.client, work_a)
    first_b = _get_page_evidence(harness.client, work_b)
    assert first_a.status == "observed_material_current"
    assert first_b.status == "observed_material_current"
    assert first_a.material_meaning_digest != first_b.material_meaning_digest
    assert first_a.generation_allowed is False
    assert first_a.current_evidence_ids
    review = harness.client.get(f"/api/content/work-items/{work_a}/material-review")
    assert review.status_code == 200
    assert review.json()["status"] == "missing"

    rotated = harness.catalog()
    harness.state.wave = 2
    refreshed = harness.catalog()
    harness.state.latest_source_ids = tuple(refreshed.evidence_ids)
    assert refreshed.evidence_ids != rotated.evidence_ids
    same_a = _get_page_evidence(harness.client, work_a)
    assert same_a.material_meaning_digest == first_a.material_meaning_digest
    harness.state.bodies[PAGE_B] += " changed"
    changed_b = _get_page_evidence(harness.client, work_b)
    assert changed_b.material_meaning_digest != first_b.material_meaning_digest


def test_public_current_page_evidence_keeps_url_drift_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = _build_harness(tmp_path)

    def wrong_url(*_args: object, **_kwargs: object) -> None:
        raise CurrentPageSnapshotReadError(
            "current_page_snapshot_lineage_mismatch", "Observed URL differs."
        )

    monkeypatch.setattr(WordPressCurrentPageSnapshotAdapter, "read", wrong_url)
    result = _get_page_evidence(harness.client, harness.work_item_ids[PAGE_A])
    assert result.status == "blocked"
    assert result.blocker_code == "current_page_snapshot_mismatch"
    assert result.blocker_owner == "WILQ content workflow"
    assert result.safe_next_step


def _build_harness(tmp_path: Path) -> _Harness:
    now = datetime.now(UTC)
    state = _TestState(
        now=now,
        freshness="fresh",
        coverage="complete",
        wave=1,
        latest_source_ids=(),
        bodies={
            PAGE_A: "A unchanged " + ("content " * 360),
            PAGE_B: "B before " + ("content " * 360),
            PAGE_URL_ONLY: "not read " * 360,
        },
    )
    urls = (PAGE_A, PAGE_B, PAGE_URL_ONLY)
    work_item_ids = {url: inventory_work_item_id(url) for url in urls}
    selected = {
        work_item_id: SimpleNamespace(
            id=work_item_id.removeprefix("content_work_item_"),
            final_canonical_url=url,
            source_public_url=url,
            normalized_page_path="/" + url.split("/", 3)[3],
            wordpress_content_material_confidence="review_required",
            wordpress_content_source_field_lineage=["public_html.main_or_article"],
        )
        for url, work_item_id in work_item_ids.items()
    }
    store = ContentWorkflowStore(tmp_path / "current-page-evidence.sqlite3")

    def catalog() -> ContentInventoryCatalogResponse:
        items = [
            ContentInventoryCatalogItem(
                catalog_id=f"catalog-{state.wave}-{index}",
                work_item_id=work_item_ids[url],
                url=url,
                path="/" + url.split("/", 3)[3],
                title=f"Evidence {index}",
                content_type="page",
                content_summary=None if url == PAGE_URL_ONLY else "Treść strony",
                content_word_count=None if url == PAGE_URL_ONLY else 361,
                section_count=None if url == PAGE_URL_ONLY else 1,
                material_status="url_only" if url == PAGE_URL_ONLY else "content_summary",
                source_connector="wordpress_ekologus",
                evidence_id=f"ev_inventory_{state.wave}_{index}",
                collected_at=now + timedelta(hours=state.wave, seconds=index),
            )
            for index, url in enumerate(urls, start=1)
        ]
        evidence_ids = [item.evidence_id for item in items]
        return ContentInventoryCatalogResponse(
            status="ready" if state.coverage == "complete" else "blocked",
            total_count=len(items),
            items=items,
            source_connectors=["wordpress_ekologus"],
            evidence_ids=evidence_ids,
            coverage=ContentInventoryCoverage(
                status=state.coverage,
                source_count=len(items),
                returned_count=len(items),
            ),
        )

    state.latest_source_ids = tuple(catalog().evidence_ids)

    def read_material(url: str) -> SimpleNamespace:
        return SimpleNamespace(
            url=url,
            content_text=state.bodies[url],
            extraction_region="public_html.main_or_article",
        )

    return _Harness(
        client=_test_client(state, store, catalog, selected, read_material),
        state=state,
        work_item_ids=work_item_ids,
        catalog=catalog,
    )


def _test_client(
    state: _TestState,
    store: ContentWorkflowStore,
    catalog: Callable[[], ContentInventoryCatalogResponse],
    selected: dict[str, SimpleNamespace],
    read_material: Callable[[str], SimpleNamespace],
) -> TestClient:
    router = APIRouter()
    selected_loader = cast(
        SelectedItemLoader,
        lambda work_item_id: selected.get(work_item_id),
    )
    material_factory = cast(MaterialReaderFactory, lambda: read_material)
    register_content_material_review_routes(
        router,
        store_factory=lambda: store,
        catalog_loader=catalog,
        selected_item_loader=selected_loader,
        material_reader_factory=material_factory,
    )
    register_current = getattr(
        content_model_routes,
        "register_content_current_page_evidence_route",
        None,
    )
    if callable(register_current):
        register_current(
            router,
            store_factory=lambda: store,
            catalog_loader=catalog,
            selected_item_loader=selected_loader,
            material_reader_factory=material_factory,
            freshness_loader=lambda: state.freshness,
            evidence_ids_loader=lambda: state.latest_source_ids,
        )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _get_page_evidence(
    client: TestClient,
    work_item_id: str,
) -> CurrentPageEvidenceResponse:
    response = client.get(
        f"/api/content/work-items/{work_item_id}/current-page-evidence"
    )
    assert response.status_code == 200, response.text
    from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse

    return CurrentPageEvidenceResponse.model_validate(response.json())
