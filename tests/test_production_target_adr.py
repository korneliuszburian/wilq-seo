from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TARGET_ADR = REPOSITORY_ROOT / "docs" / "architecture" / "production-target-decision.md"
READINESS_AUDIT = (
    REPOSITORY_ROOT / "docs" / "architecture" / "production-readiness-audit.md"
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
    assert path.is_file(), f"Brak dokumentu: {path}"
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"Pusty dokument: {path}"
    return content


def test_production_target_adr_covers_options_and_pending_owner_decisions() -> None:
    adr = _read_nonempty(TARGET_ADR)
    folded = adr.casefold()

    for marker in (
        "A. Lokalny pilot",
        "B. Serwer",
        "C. Cloud VPS",
        "auth",
        "TLS",
        "Codex login",
        "decyzj",
        "Oczekujące decyzje OWNER-a",
        "P1",
        "P2",
        "P3",
        "P4",
    ):
        assert marker.casefold() in folded


def test_production_readiness_audit_marks_closed_slices_and_open_owner_gaps() -> None:
    audit = _read_nonempty(READINESS_AUDIT)

    closed_gaps = (
        ("L4", "S5"),
        ("L5", "S4"),
        ("L6", "S6"),
        ("L7", "S3"),
        ("L8", "S6"),
    )
    for gap, slice_id in closed_gaps:
        assert re.search(rf"\| {gap} \|[^\n]*ZAMKNIĘTE[^\n]*{slice_id}", audit)

    for gap in ("L1", "L2", "L3"):
        assert re.search(rf"\| {gap} \|[^\n]*OTWARTE[^\n]*OWNER", audit)


def test_production_decision_docs_do_not_contain_secret_looking_literals() -> None:
    for path in (TARGET_ADR, READINESS_AUDIT):
        content = _read_nonempty(path)
        for marker in SECRET_MARKERS:
            assert marker.casefold() not in content.casefold(), (
                f"Niedozwolony marker w {path}: {marker}"
            )
        assert OAUTH_JSON_BLOB.search(content) is None
        assert WORDPRESS_APP_PASSWORD.search(content) is None
