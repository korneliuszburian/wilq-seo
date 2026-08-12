#!/usr/bin/env python3
"""Build the deterministic current-vs-revision content benchmark for Goal 005."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal

from wilq.content.canonical.landing_identity import (
    landing_page_metric_lookup_path,
    landing_page_metric_lookup_urls,
)
from wilq.content.handoff.revision_document_renderer import revision_document_markdown
from wilq.content.planning.proposal_quality import planning_heading_quality_errors
from wilq.content.quality.reading_quality import _WORKING_NOTE as WORKING_NOTE_PATTERN
from wilq.content.quality.semantic_review_contracts import CONTENT_SEMANTIC_DIMENSIONS
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryMaterialResponse,
    build_content_inventory_catalog,
    read_content_inventory_material,
)
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.local_state import local_state_store, state_db_path
from wilq.storage.metric_store import metric_store

REPORT_DATE = "2026-08-12"
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs/agents/reports/benchmark"
REPORT_PATH = REPORT_DIR / f"content-benchmark-{REPORT_DATE}.json"
JUDGE_INPUT_PATH = REPORT_DIR / "llm-judge-input.json"
NEAR_DUPLICATE_RATIO = 0.8

Numeric = int | float
Metrics = dict[str, Numeric]
Verdict = Literal["generated_better", "current_better", "mixed", "tie"]

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_MARKERS = re.compile(r"(?:^|\s)[#>*_~`-]+(?=\s|$)")


@dataclass(frozen=True)
class BenchmarkPage:
    slug: str
    label: str
    url: str
    revision_id: str


PAGES = (
    BenchmarkPage(
        slug="bdo",
        label="BDO – co musi wiedzieć przedsiębiorca",
        url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        revision_id="content_revision_f4c23cfcd5b6449c83281545b4883e2c",
    ),
    BenchmarkPage(
        slug="szkolenia",
        label="Szkolenia z ochrony środowiska",
        url="https://www.ekologus.pl/oferta/szkolenia/",
        revision_id="content_revision_66f7eec3ec9646a5a8ed5327a44e3da8",
    ),
    BenchmarkPage(
        slug="doradztwo",
        label="Doradztwo i outsourcing ekologiczny",
        url="https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
        revision_id="content_revision_62ef7b61f6fd4a399a41d3ab33094fc9",
    ),
    BenchmarkPage(
        slug="opracowania-dokumentacji",
        label="Opracowania dokumentacji i ekspertyz",
        url="https://www.ekologus.pl/oferta/opracowania-dokumentacji-ekspertyz/",
        revision_id="content_revision_b14c7fc23fcc4907aadf24c431cc656a",
    ),
    BenchmarkPage(
        slug="pomiary-i-analizy",
        label="Pomiary i analizy środowiska",
        url="https://www.ekologus.pl/oferta/pomiary-i-analizy/",
        revision_id="content_revision_787c4e52b3f941f3a048a63355e8cf45",
    ),
)


def _normalized_url(url: str) -> str:
    return url.rstrip("/").casefold()


def _catalog_item(
    catalog: ContentInventoryCatalogResponse,
    page: BenchmarkPage,
) -> ContentInventoryCatalogItem:
    item = next(
        (
            candidate
            for candidate in catalog.items
            if _normalized_url(candidate.url) == _normalized_url(page.url)
        ),
        None,
    )
    if item is None:
        raise RuntimeError(f"Brak URL w aktualnym inventory WordPress: {page.url}")
    return item


def _validated_material(
    item: ContentInventoryCatalogItem,
    catalog: ContentInventoryCatalogResponse,
) -> ContentInventoryMaterialResponse:
    material = read_content_inventory_material(item.url, catalog=catalog)
    if material.status != "ready":
        raise RuntimeError(
            f"Materiał WordPress jest niedostępny dla {item.url}: "
            f"{material.blocker_code or material.status}"
        )
    if not material.content_text or not material.content_text.strip():
        raise RuntimeError(f"Materiał WordPress nie zawiera treści dla {item.url}")
    if material.content_word_count is None:
        raise RuntimeError(f"Materiał WordPress nie zawiera word count dla {item.url}")
    return material


def _load_revisions() -> dict[str, ContentDraftRevision]:
    database_path = state_db_path().resolve()
    if not database_path.is_file():
        raise RuntimeError(f"Brak magazynu rewizji WILQ: {database_path}")
    placeholders = ",".join("?" for _ in PAGES)
    uri = f"{database_path.as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            f"SELECT revision_id, payload_json FROM content_draft_revisions "  # nosec B608
            f"WHERE revision_id IN ({placeholders})",
            tuple(page.revision_id for page in PAGES),
        ).fetchall()
    revisions = {
        str(revision_id): ContentDraftRevision.model_validate(json.loads(str(payload_json)))
        for revision_id, payload_json in rows
    }
    missing = [page.revision_id for page in PAGES if page.revision_id not in revisions]
    if missing:
        raise RuntimeError(f"Brak wymaganych rewizji w WILQ SQLite: {', '.join(missing)}")
    return revisions


def _latest_gsc_refresh() -> ConnectorRefreshRun:
    candidates = [
        run
        for run in local_state_store().list_connector_refresh_runs(
            connector_id="google_search_console"
        )
        if run.mode == ConnectorRefreshMode.vendor_read
        and run.status == ConnectorRefreshStatus.completed
        and run.metrics_persisted
        and run.evidence_ids
    ]
    if not candidates:
        raise RuntimeError(
            "Brak zakończonego i zapisanego odczytu vendor_read Google Search Console."
        )
    return max(candidates, key=lambda run: run.completed_at or run.started_at)


def _gsc_query_context(
    page: BenchmarkPage,
    latest_refresh: ConnectorRefreshRun,
) -> tuple[tuple[str, ...], list[MetricFact]]:
    content_path = landing_page_metric_lookup_path(page.url)
    if not content_path:
        raise RuntimeError(f"Nie można wyznaczyć landing identity dla {page.url}")
    candidate_facts = [
        fact
        for lookup_url in landing_page_metric_lookup_urls(page.url)
        for fact in metric_store().list_metric_facts_for_content_url(
            ["google_search_console"],
            lookup_url,
            content_path=content_path,
        )
    ]
    allowed_evidence_ids = set(latest_refresh.evidence_ids)
    facts = list(
        {
            fact.model_dump_json(): fact
            for fact in candidate_facts
            if fact.source_connector == "google_search_console"
            and fact.evidence_id in allowed_evidence_ids
            and str(fact.dimensions.get("query") or "").strip()
        }.values()
    )
    queries_by_identity: dict[str, str] = {}
    for fact in facts:
        query = str(fact.dimensions["query"]).strip()
        queries_by_identity.setdefault(query.casefold(), query)
    queries = tuple(sorted(queries_by_identity, key=str.casefold))
    return queries, facts


def _generated_body_texts(revision: ContentDraftRevision) -> list[str]:
    return [
        *(section.body_markdown for section in revision.sections),
        *(item.answer_markdown for item in revision.faq),
        *(item.body_markdown for item in revision.cta_blocks),
    ]


def _paragraphs(text: str) -> list[str]:
    return [
        normalized
        for paragraph in _PARAGRAPH_BREAK.split(text.replace("\r\n", "\n"))
        if (normalized := " ".join(paragraph.split()))
    ]


def _body_paragraphs(texts: list[str]) -> list[str]:
    return [paragraph for text in texts for paragraph in _paragraphs(text)]


def _normalized_paragraph(paragraph: str) -> str:
    normalized = unicodedata.normalize("NFKC", paragraph)
    normalized = _MARKDOWN_LINK.sub(r"\1", normalized)
    normalized = _MARKDOWN_MARKERS.sub(" ", normalized)
    return " ".join(normalized.casefold().split())


def _near_duplicate_pair_count(paragraphs: list[str]) -> int:
    normalized = [_normalized_paragraph(paragraph) for paragraph in paragraphs]
    pair_count = 0
    for index, candidate in enumerate(normalized):
        for other in normalized[index + 1 :]:
            if SequenceMatcher(None, candidate, other).ratio() >= NEAR_DUPLICATE_RATIO:
                pair_count += 1
    return pair_count


def _paragraph_uniqueness(
    candidate_paragraphs: list[str],
    reference_paragraphs: list[str],
) -> float:
    if not candidate_paragraphs:
        return 0.0
    normalized_reference = [_normalized_paragraph(paragraph) for paragraph in reference_paragraphs]
    unique_count = 0
    for paragraph in candidate_paragraphs:
        candidate = _normalized_paragraph(paragraph)
        if all(
            SequenceMatcher(None, candidate, reference).ratio() < NEAR_DUPLICATE_RATIO
            for reference in normalized_reference
        ):
            unique_count += 1
    return round(unique_count / len(candidate_paragraphs), 4)


def _heading_metrics(headings: list[str]) -> tuple[float, int]:
    if not headings:
        return 0.0, 0
    issue_count = sum(bool(planning_heading_quality_errors([heading])) for heading in headings)
    return round((len(headings) - issue_count) / len(headings), 4), issue_count


def _query_metrics(text: str, queries: tuple[str, ...]) -> tuple[float, int]:
    normalized_text = text.casefold()
    matched_count = sum(query.casefold() in normalized_text for query in queries)
    coverage = 0.0 if not queries else round(100 * matched_count / len(queries), 2)
    return coverage, matched_count


def _content_metrics(
    *,
    word_count: int,
    section_count: int,
    text: str,
    headings: list[str],
    paragraphs: list[str],
    queries: tuple[str, ...],
    uniqueness: float,
) -> Metrics:
    duplicate_pair_count = _near_duplicate_pair_count(paragraphs)
    heading_quality, heading_issue_count = _heading_metrics(headings)
    query_coverage, matched_query_count = _query_metrics(text, queries)
    return {
        "word_count": word_count,
        "section_count": section_count,
        "query_coverage": query_coverage,
        "query_term_count": len(queries),
        "matched_query_count": matched_query_count,
        "uniqueness": uniqueness,
        "paragraph_count": len(paragraphs),
        "duplicate_paragraph": int(duplicate_pair_count > 0),
        "duplicate_paragraph_pair_count": duplicate_pair_count,
        "heading_quality": heading_quality,
        "heading_issue_count": heading_issue_count,
        "working_note_count": sum(1 for _ in WORKING_NOTE_PATTERN.finditer(text)),
    }


def _delta(current: Metrics, generated: Metrics) -> Metrics:
    delta: Metrics = {}
    for key in current.keys() & generated.keys():
        value = generated[key] - current[key]
        delta[key] = round(value, 4) if isinstance(value, float) else value
    return dict(sorted(delta.items()))


def _comparison(generated_value: Numeric, current_value: Numeric, *, higher_is_better: bool) -> int:
    if generated_value == current_value:
        return 0
    generated_is_higher = generated_value > current_value
    return 1 if generated_is_higher == higher_is_better else -1


def _verdict(current: Metrics, generated: Metrics) -> tuple[Verdict, dict[str, int]]:
    signals = {
        "query_coverage": _comparison(
            generated["query_coverage"], current["query_coverage"], higher_is_better=True
        ),
        "uniqueness": _comparison(
            generated["uniqueness"], current["uniqueness"], higher_is_better=True
        ),
        "heading_quality": _comparison(
            generated["heading_quality"], current["heading_quality"], higher_is_better=True
        ),
        "duplicate_paragraph": _comparison(
            generated["duplicate_paragraph"],
            current["duplicate_paragraph"],
            higher_is_better=False,
        ),
        "working_note_count": _comparison(
            generated["working_note_count"],
            current["working_note_count"],
            higher_is_better=False,
        ),
    }
    improvements = sum(value > 0 for value in signals.values())
    regressions = sum(value < 0 for value in signals.values())
    if improvements == regressions == 0:
        verdict: Verdict = "tie"
    elif improvements > regressions:
        verdict = "generated_better"
    elif regressions > improvements:
        verdict = "current_better"
    else:
        verdict = "mixed"
    return verdict, signals


def _evidence_metadata(
    *,
    item: ContentInventoryCatalogItem,
    material: ContentInventoryMaterialResponse,
    revision: ContentDraftRevision,
    latest_gsc_refresh: ConnectorRefreshRun,
    gsc_facts: list[MetricFact],
) -> dict[str, Any]:
    return {
        "wordpress": {
            "source_connector": item.source_connector,
            "evidence_id": material.evidence_id or item.evidence_id,
            "catalog_collected_at": item.collected_at.isoformat(),
            "material_modified_gmt": material.modified_gmt,
            "source_kind": material.source_kind,
            "extraction_region": material.extraction_region,
            "material_confidence": material.material_confidence,
        },
        "google_search_console": {
            "source_connector": "google_search_console",
            "refresh_run_id": latest_gsc_refresh.id,
            "refresh_completed_at": (
                latest_gsc_refresh.completed_at or latest_gsc_refresh.started_at
            ).isoformat(),
            "evidence_ids": sorted({fact.evidence_id for fact in gsc_facts}),
            "periods": sorted({fact.period for fact in gsc_facts}),
        },
        "revision": {
            "revision_id": revision.revision_id,
            "content_digest": revision.content_digest,
            "created_at": revision.created_at.isoformat(),
            "publish_ready": revision.publish_ready,
        },
    }


def _judge_dimensions() -> list[dict[str, Any]]:
    return [
        {
            "name": dimension,
            "text_a": {"score_min": 1, "score_max": 5},
            "text_b": {"score_min": 1, "score_max": 5},
        }
        for dimension in CONTENT_SEMANTIC_DIMENSIONS
    ]


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _methodology() -> dict[str, Any]:
    return {
        "role": "current state / deterministic benchmark; not publication or human approval",
        "current_source": (
            "One build_content_inventory_catalog snapshot plus live "
            "read_content_inventory_material reads."
        ),
        "revision_source": "Exact immutable content_draft_revisions rows from read-only SQLite.",
        "word_count": (
            "Current uses material.content_word_count. Generated sums whitespace-token counts "
            "for section bodies, FAQ answers and CTA bodies only."
        ),
        "query_coverage": (
            "Percentage of unique, nonblank query dimensions from the latest completed and "
            "persisted GSC vendor_read batch for the exact landing identity. Matching uses "
            "casefolded substring containment; raw queries are not retained in the report."
        ),
        "uniqueness": (
            "Generated paragraph novelty versus current paragraphs at SequenceMatcher ratio "
            "below 0.8. The current baseline applies the same calculation to current "
            "paragraphs against themselves."
        ),
        "duplicate_paragraph": (
            "Near-duplicate paragraph pairs within each text at SequenceMatcher ratio >= 0.8."
        ),
        "heading_quality": (
            "Fraction of headings with no planning_heading_quality_errors; an empty heading "
            "inventory scores 0.0."
        ),
        "working_note_count": "Number of matches from the production reading-quality regex.",
        "verdict": (
            "Majority vote across higher query coverage, uniqueness and heading quality, plus "
            "lower duplicate-paragraph flag and working-note count. Equal nonzero votes are mixed."
        ),
        "gsc_caveat": (
            "GSC query/page detail can be row-limited; the benchmark describes the persisted "
            "latest batch, not guaranteed exhaustive search demand."
        ),
    }


def build_benchmark() -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = build_content_inventory_catalog()
    revisions = _load_revisions()
    latest_gsc_refresh = _latest_gsc_refresh()
    report_pages: list[dict[str, Any]] = []
    judge_pages: list[dict[str, Any]] = []

    for page in PAGES:
        item = _catalog_item(catalog, page)
        material = _validated_material(item, catalog)
        revision = revisions[page.revision_id]
        if revision.final_canonical_url is None or _normalized_url(
            revision.final_canonical_url
        ) != _normalized_url(page.url):
            raise RuntimeError(f"Rewizja {revision.revision_id} nie jest związana z URL {page.url}")

        current_text = material.content_text
        current_word_count = material.content_word_count
        if current_text is None or current_word_count is None:
            raise RuntimeError(f"Zweryfikowany materiał utracił treść lub word count: {page.url}")
        generated_text = revision_document_markdown(revision)
        generated_body_texts = _generated_body_texts(revision)
        current_paragraphs = _paragraphs(current_text)
        generated_paragraphs = _body_paragraphs(generated_body_texts)
        queries, gsc_facts = _gsc_query_context(page, latest_gsc_refresh)

        current = _content_metrics(
            word_count=current_word_count,
            section_count=len(material.section_headings),
            text=current_text,
            headings=list(material.section_headings),
            paragraphs=current_paragraphs,
            queries=queries,
            uniqueness=_paragraph_uniqueness(current_paragraphs, current_paragraphs),
        )
        generated = _content_metrics(
            word_count=sum(len(text.split()) for text in generated_body_texts),
            section_count=len(revision.sections),
            text=generated_text,
            headings=[section.heading for section in revision.sections],
            paragraphs=generated_paragraphs,
            queries=queries,
            uniqueness=_paragraph_uniqueness(generated_paragraphs, current_paragraphs),
        )
        verdict, verdict_signals = _verdict(current, generated)
        report_pages.append(
            {
                "slug": page.slug,
                "label": page.label,
                "url": page.url,
                "current": current,
                "generated": generated,
                "delta": _delta(current, generated),
                "verdict": verdict,
                "verdict_signals": verdict_signals,
                "evidence": _evidence_metadata(
                    item=item,
                    material=material,
                    revision=revision,
                    latest_gsc_refresh=latest_gsc_refresh,
                    gsc_facts=gsc_facts,
                ),
            }
        )
        judge_pages.append(
            {
                "text_a": current_text,
                "text_b": generated_text,
                "dimensions": _judge_dimensions(),
            }
        )

    report = {
        "benchmark_date": REPORT_DATE,
        "page_count": len(report_pages),
        "methodology": _methodology(),
        "pages": report_pages,
    }
    judge_input = {"pages": judge_pages}
    return report, judge_input


def _print_summary(report: dict[str, Any]) -> None:
    print("Benchmark jakości treści — CURRENT WordPress vs rewizja WILQ")
    for page in report["pages"]:
        current = page["current"]
        generated = page["generated"]
        delta = page["delta"]
        print(
            f"- {page['label']}: {page['verdict']} | słowa "
            f"{current['word_count']}→{generated['word_count']} "
            f"({delta['word_count']:+}); sekcje {current['section_count']}→"
            f"{generated['section_count']} ({delta['section_count']:+}); GSC "
            f"{current['query_coverage']:.2f}%→{generated['query_coverage']:.2f}% "
            f"({delta['query_coverage']:+.2f} pp); unikalność "
            f"{generated['uniqueness']:.2%}; notatki "
            f"{current['working_note_count']}→{generated['working_note_count']}"
        )
    print(f"Raport: {REPORT_PATH}")
    print(f"Ślepe wejście LLM: {JUDGE_INPUT_PATH}")


def main() -> None:
    report, judge_input = build_benchmark()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_PATH, report)
    _write_json(JUDGE_INPUT_PATH, judge_input)
    _print_summary(report)


if __name__ == "__main__":
    main()
