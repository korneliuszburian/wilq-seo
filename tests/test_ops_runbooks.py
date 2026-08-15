from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROTATION_RUNBOOK = REPOSITORY_ROOT / "docs" / "security" / "rotation-runbook.md"
MAINTENANCE_RUNBOOK = REPOSITORY_ROOT / "docs" / "infra" / "maintenance.md"

ROTATION_KEYWORDS = (
    "rollback",
    "weryfikacj",
    "WORDPRESS_EKOLOGUS_APP_PASSWORD",
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "AHREFS_API_TOKEN",
    "GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID",
    "WILQ_ACCESS_PACK_PATH",
)
MAINTENANCE_KEYWORDS = (
    "okno",
    "approved_maintenance_window",
    "storage_proof",
    "reject_newer_sqlite_schema",
    "WILQ_ENABLE_SCHEDULER",
    "SQLite",
    "DuckDB",
    "rollback",
    "weryfikacj",
)
SECRET_MARKERS = (
    "s" + "k-",
    "A" + "KIA",
    "PASSWORD" + "=",
    "TOKEN" + "=",
)
OAUTH_JSON_BLOB = re.compile(
    r'\{[^{}]{0,2000}"(?:client_secret|refresh_token|private_key)"\s*:[^{}]+\}',
    re.IGNORECASE | re.DOTALL,
)
WORDPRESS_APP_PASSWORD = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]{24}|"
    r"(?:[A-Za-z0-9]{4}[ -]){5}[A-Za-z0-9]{4})(?![A-Za-z0-9])"
)


def _read_nonempty(path: Path) -> str:
    assert path.is_file(), f"Brak runbooka: {path}"
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"Pusty runbook: {path}"
    return content


def test_ops_runbooks_cover_required_contract_without_secret_literals() -> None:
    rotation = _read_nonempty(ROTATION_RUNBOOK)
    maintenance = _read_nonempty(MAINTENANCE_RUNBOOK)

    for keyword in ROTATION_KEYWORDS:
        assert keyword.casefold() in rotation.casefold()
    for keyword in MAINTENANCE_KEYWORDS:
        assert keyword.casefold() in maintenance.casefold()

    for path, content in (
        (ROTATION_RUNBOOK, rotation),
        (MAINTENANCE_RUNBOOK, maintenance),
    ):
        for marker in SECRET_MARKERS:
            assert marker.casefold() not in content.casefold(), (
                f"Niedozwolony marker w {path}: {marker}"
            )
        assert OAUTH_JSON_BLOB.search(content) is None
        assert WORDPRESS_APP_PASSWORD.search(content) is None
