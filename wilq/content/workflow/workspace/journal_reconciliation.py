"""Read-only coverage reconciliation for the canonical per-URL content journal."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.urls import content_normalized_path

_EXPECTED_JOURNAL_RECORD_COUNT = 214


class _CatalogPath(Protocol):
    path: str


class ContentInventoryJournalReconciliation(BaseModel):
    """Coverage only; it deliberately contains no inferred inventory identity."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "incomplete", "blocked"]
    journal_record_count: int = Field(ge=0)
    matched_catalog_count: int = Field(ge=0)
    missing_inventory_binding_count: int = Field(ge=0)
    catalog_outside_journal_count: int = Field(ge=0)
    matched_authoring_source_count: int = Field(ge=0)
    missing_authoring_source_count: int = Field(ge=0)
    missing_inventory_by_content_kind: dict[str, int] = Field(default_factory=dict)
    caveat: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


def build_content_inventory_journal_reconciliation(
    catalog_items: Iterable[_CatalogPath],
    *,
    authoring_source_paths: Iterable[str] = (),
    journal_path: Path | None = None,
) -> ContentInventoryJournalReconciliation:
    """Compare exact path sets without turning a path match into a work-item binding."""

    journal = _load_journal(journal_path or _canonical_journal_path())
    if journal is None:
        return ContentInventoryJournalReconciliation(
            status="blocked",
            journal_record_count=0,
            matched_catalog_count=0,
            missing_inventory_binding_count=0,
            catalog_outside_journal_count=0,
            matched_authoring_source_count=0,
            missing_authoring_source_count=0,
            caveat="Nie można odczytać kanonicznego journalu treści do porównania coverage.",
            safe_next_step="Napraw i zweryfikuj kanoniczny journal przed klasyfikacją treści.",
        )
    canonical_journal = _load_journal(_canonical_journal_path())
    if canonical_journal is None:
        return ContentInventoryJournalReconciliation(
            status="blocked",
            journal_record_count=len(journal),
            matched_catalog_count=0,
            missing_inventory_binding_count=0,
            catalog_outside_journal_count=0,
            matched_authoring_source_count=0,
            missing_authoring_source_count=0,
            caveat="Nie można odczytać niezależnego zakresu kanonicznego journalu treści.",
            safe_next_step="Napraw i zweryfikuj docs/content-status-214.csv przed oceną coverage.",
        )
    journal_paths = set(journal)
    canonical_paths = set(canonical_journal)
    catalog_paths = {_normalized_path(item.path) for item in catalog_items if item.path.strip()}
    authoring_paths = {
        content_normalized_path(path) for path in authoring_source_paths if path.strip()
    }
    missing_paths = journal_paths - catalog_paths
    catalog_outside = catalog_paths - journal_paths
    authoring_matches = journal_paths & authoring_paths
    missing_by_kind = dict(sorted(Counter(journal[path] for path in missing_paths).items()))
    journal_scope_complete = journal_paths == canonical_paths
    incomplete = bool(missing_paths or catalog_outside or not journal_scope_complete)
    return ContentInventoryJournalReconciliation(
        status="incomplete" if incomplete else "complete",
        journal_record_count=len(journal_paths),
        matched_catalog_count=len(journal_paths & catalog_paths),
        missing_inventory_binding_count=len(missing_paths),
        catalog_outside_journal_count=len(catalog_outside),
        matched_authoring_source_count=len(authoring_matches),
        missing_authoring_source_count=len(journal_paths - authoring_paths),
        missing_inventory_by_content_kind=missing_by_kind,
        caveat=(
            (
                f"Journal ma {len(journal_paths)} rekordów, lecz jego znormalizowany zbiór "
                f"ścieżek nie jest dokładnie równy kanonicznemu zbiorowi "
                f"{len(canonical_paths)} ścieżek; nie traktuj coverage jako pełnego."
            )
            if not journal_scope_complete
            else "Część kanonicznych URL-i nie ma dokładnego typed inventory; "
            "odczyt authoring jest osobnym dowodem i nie tworzy work-item ani "
            "powiązania usługi."
            if incomplete
            else "Każdy URL journalu ma odpowiadającą pozycję typed inventory."
        ),
        safe_next_step=(
            (
                f"Przywróć i zweryfikuj pełne {_EXPECTED_JOURNAL_RECORD_COUNT} rekordów "
                "kanonicznego journalu przed oceną completeness."
            )
            if not journal_scope_complete
            else "Zarejestruj exact inventory bindingi dla brakujących URL-i, zachowując "
            "oddzielne źródła usług i taxonomy/system; sam odczyt authoring nie "
            "potwierdza finalnego canonical URL."
            if incomplete
            else "Przejdź do weryfikacji aktualnych źródeł, rewizji i claim ledgerów."
        ),
    )


def _canonical_journal_path() -> Path:
    return Path(__file__).resolve().parents[4] / "docs" / "content-status-214.csv"


def _load_journal(path: Path) -> dict[str, str] | None:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not {"path", "content_kind"}.issubset(
                reader.fieldnames
            ):
                return None
            rows: dict[str, str] = {}
            for row in reader:
                raw_path = str(row.get("path") or "").strip()
                content_kind = str(row.get("content_kind") or "").strip()
                if not raw_path or not content_kind:
                    return None
                normalized_path = normalize_content_inventory_journal_path(raw_path)
                if normalized_path in rows:
                    return None
                rows[normalized_path] = content_kind
    except (OSError, csv.Error):
        return None
    return rows or None


def normalize_content_inventory_journal_path(value: str) -> str:
    """Normalize one journal path for exact scope comparisons and projections."""

    normalized = value.strip().rstrip("/")
    return normalized or "/"


def _normalized_path(value: str) -> str:
    """Compatibility alias for the deferred journal-readiness module."""

    return normalize_content_inventory_journal_path(value)


def canonical_content_inventory_journal_paths() -> frozenset[str] | None:
    """Return the independently loaded normalized path scope of the canonical journal."""

    journal = _load_journal(_canonical_journal_path())
    return None if journal is None else frozenset(journal)


__all__ = [
    "ContentInventoryJournalReconciliation",
    "build_content_inventory_journal_reconciliation",
    "canonical_content_inventory_journal_paths",
    "normalize_content_inventory_journal_path",
]
