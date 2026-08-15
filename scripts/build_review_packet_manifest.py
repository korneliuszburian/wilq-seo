from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

REPORT_TYPE = "review_packet_manifest_v1"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
SAFETY_NOTE = (
    "Manifest przypina pakiet review do jednego commitu repozytorium; "
    "nie zatwierdza treści ani jej jakości."
)

MARKDOWN_IMAGE_PATH_PATTERN = re.compile(
    r"!?\[[^\]\n]*\]\(\s*"
    r"(?:<(?P<angle_path>[^<>\n]+?\.(?:png|jpe?g|webp))>"
    r"|(?P<plain_path>[^)\s]+?\.(?:png|jpe?g|webp)))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)",
    re.IGNORECASE,
)
WRAPPED_IMAGE_PATH_PATTERN = re.compile(
    r"(?:`(?P<backtick_path>[^`\n]+?\.(?:png|jpe?g|webp))`"
    r"|<(?P<angle_path>[^<>\n]+?\.(?:png|jpe?g|webp))>)",
    re.IGNORECASE,
)
BARE_IMAGE_PATH_PATTERN = re.compile(
    r"(?<![\w\[])"
    r"(?P<path>"
    r"(?:\.{1,2}/|/)?"
    r"(?:[^\s`\"'()<>\[\]]+/)*"
    r"[^\s`\"'()<>\[\]/]+\.(?:png|jpe?g|webp)"
    r")",
    re.IGNORECASE,
)
ID_PATTERNS = {
    "revision_ids": re.compile(
        r"(?<![A-Za-z0-9_-])content_revision_[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*"
        r"(?![A-Za-z0-9_-])"
    ),
    "work_item_ids": re.compile(
        r"(?<![A-Za-z0-9_-])content_work_item_[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*"
        r"(?![A-Za-z0-9_-])"
    ),
    "evidence_ids": re.compile(
        r"(?<![A-Za-z0-9_-])ev_[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*"
        r"(?![A-Za-z0-9_-])"
    ),
    "run_ids": re.compile(
        r"(?<![A-Za-z0-9_-])codex_[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*"
        r"(?![A-Za-z0-9_-])"
    ),
}


class ScreenshotRecord(TypedDict):
    path: str
    sha256: str
    size_bytes: int


class ReferencedIds(TypedDict):
    revision_ids: list[str]
    work_item_ids: list[str]
    evidence_ids: list[str]
    run_ids: list[str]


class ReviewPacketManifest(TypedDict):
    report_type: str
    packet_path: str
    fixed_point_commit: str
    tree_dirty: bool
    dirty_paths: list[str]
    generated_at: str
    screenshots: list[ScreenshotRecord]
    referenced_ids: ReferencedIds
    safety_note: str


class ManifestBuildError(RuntimeError):
    """Raised when a review packet cannot be bound to local proof."""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Buduje manifest dowodowy pakietu review: commit Git, stan drzewa, "
            "identyfikatory oraz skróty SHA-256 screenshotów."
        )
    )
    parser.add_argument("packet", help="Ścieżka do pakietu review w Markdown.")
    parser.add_argument(
        "--screenshots-dir",
        help="Opcjonalny katalog, z którego zostaną dodane wszystkie screenshoty.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Ścieżka wyniku JSON. Domyślnie manifest powstaje obok pakietu "
            "jako <nazwa>.manifest.json."
        ),
    )
    args = parser.parse_args()

    packet_path = Path(args.packet).resolve()
    screenshots_dir = (
        Path(args.screenshots_dir).resolve() if args.screenshots_dir is not None else None
    )
    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else packet_path.with_suffix(".manifest.json")
    )

    try:
        repo_root = discover_repo_root(Path.cwd())
        manifest = build_review_packet_manifest(
            packet_path,
            repo_root=repo_root,
            screenshots_dir=screenshots_dir,
        )
        write_manifest(output_path, manifest, repo_root)
    except (ManifestBuildError, OSError) as error:
        print(f"Błąd budowy manifestu pakietu review: {error}", file=sys.stderr)
        return 1

    print(f"Zapisano manifest pakietu review: {display_path(output_path, repo_root)}")
    return 0


def discover_repo_root(start: Path) -> Path:
    root = _git_text(start, "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def build_review_packet_manifest(
    packet_path: Path,
    *,
    repo_root: Path,
    screenshots_dir: Path | None = None,
    generated_at: str | None = None,
) -> ReviewPacketManifest:
    packet_path = packet_path.resolve()
    repo_root = repo_root.resolve()
    if not packet_path.is_file():
        raise ManifestBuildError(f"Nie znaleziono pakietu review: {packet_path}")

    try:
        packet_text = packet_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ManifestBuildError(
            f"Nie można odczytać pakietu review {packet_path}: {error}"
        ) from error

    fixed_point_commit = _git_text(repo_root, "rev-parse", "HEAD")
    dirty_paths = repository_dirty_paths(repo_root)
    screenshot_paths = resolve_screenshot_paths(
        packet_text,
        packet_path=packet_path,
        repo_root=repo_root,
        screenshots_dir=screenshots_dir,
    )

    return {
        "report_type": REPORT_TYPE,
        "packet_path": display_path(packet_path, repo_root),
        "fixed_point_commit": fixed_point_commit,
        "tree_dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
        "generated_at": generated_at or utc_now(),
        "screenshots": [build_screenshot_record(path, repo_root) for path in screenshot_paths],
        "referenced_ids": extract_referenced_ids(packet_text),
        "safety_note": SAFETY_NOTE,
    }


def repository_dirty_paths(repo_root: Path) -> list[str]:
    status = _git_text(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        strip=False,
    )
    records = status.split("\0")
    dirty_paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        if not record:
            index += 1
            continue
        if len(record) < 4:
            raise ManifestBuildError("Git zwrócił nieprawidłowy wpis stanu drzewa.")
        status_code = record[:2]
        dirty_paths.add(record[3:])
        index += 1
        if "R" in status_code or "C" in status_code:
            if index >= len(records) or not records[index]:
                raise ManifestBuildError("Git zwrócił niepełny wpis zmiany nazwy pliku.")
            dirty_paths.add(records[index])
            index += 1
    return sorted(dirty_paths)


def resolve_screenshot_paths(
    packet_text: str,
    *,
    packet_path: Path,
    repo_root: Path,
    screenshots_dir: Path | None,
) -> list[Path]:
    resolved_paths: dict[Path, None] = {}
    missing_citations: list[str] = []

    for citation in extract_cited_screenshot_paths(packet_text):
        resolved = resolve_cited_path(
            citation,
            packet_path=packet_path,
            repo_root=repo_root,
        )
        if resolved is None:
            missing_citations.append(citation)
        else:
            resolved_paths[resolved] = None

    if missing_citations:
        label = (
            "Brak cytowanego pliku zrzutu ekranu"
            if len(missing_citations) == 1
            else "Brak cytowanych plików zrzutów ekranu"
        )
        raise ManifestBuildError(f"{label}: {', '.join(sorted(missing_citations))}")

    if screenshots_dir is not None:
        screenshots_dir = screenshots_dir.resolve()
        if not screenshots_dir.is_dir():
            raise ManifestBuildError(f"Nie znaleziono katalogu screenshotów: {screenshots_dir}")
        for candidate in screenshots_dir.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
                resolved_paths[candidate.resolve()] = None

    return sorted(resolved_paths, key=lambda path: display_path(path, repo_root))


def extract_cited_screenshot_paths(packet_text: str) -> list[str]:
    cited_paths: dict[str, None] = {}

    def collect_markdown_path(match: re.Match[str]) -> str:
        path = match.group("angle_path") or match.group("plain_path")
        cited_paths[path] = None
        return " " * len(match.group(0))

    def collect_wrapped_path(match: re.Match[str]) -> str:
        path = match.group("backtick_path") or match.group("angle_path")
        cited_paths[path] = None
        return " " * len(match.group(0))

    remaining_text = MARKDOWN_IMAGE_PATH_PATTERN.sub(collect_markdown_path, packet_text)
    remaining_text = WRAPPED_IMAGE_PATH_PATTERN.sub(collect_wrapped_path, remaining_text)
    for match in BARE_IMAGE_PATH_PATTERN.finditer(remaining_text):
        cited_paths[match.group("path")] = None
    return list(cited_paths)


def write_manifest(
    output_path: Path,
    manifest: ReviewPacketManifest,
    repo_root: Path,
) -> None:
    _write_manifest_json(output_path, manifest)
    final_dirty_paths = repository_dirty_paths(repo_root)
    manifest["tree_dirty"] = bool(final_dirty_paths)
    manifest["dirty_paths"] = final_dirty_paths
    _write_manifest_json(output_path, manifest)


def _write_manifest_json(output_path: Path, manifest: ReviewPacketManifest) -> None:
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_cited_path(
    citation: str,
    *,
    packet_path: Path,
    repo_root: Path,
) -> Path | None:
    cited_path = Path(citation)
    candidates = (
        [cited_path]
        if cited_path.is_absolute()
        else [repo_root / cited_path, packet_path.parent / cited_path]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def build_screenshot_record(path: Path, repo_root: Path) -> ScreenshotRecord:
    try:
        screenshot_bytes = path.read_bytes()
    except OSError as error:
        raise ManifestBuildError(
            f"Nie można odczytać pliku zrzutu ekranu {path}: {error}"
        ) from error
    return {
        "path": display_path(path, repo_root),
        "sha256": hashlib.sha256(screenshot_bytes).hexdigest(),
        "size_bytes": len(screenshot_bytes),
    }


def extract_referenced_ids(packet_text: str) -> ReferencedIds:
    return {
        "revision_ids": sorted(set(ID_PATTERNS["revision_ids"].findall(packet_text))),
        "work_item_ids": sorted(set(ID_PATTERNS["work_item_ids"].findall(packet_text))),
        "evidence_ids": sorted(set(ID_PATTERNS["evidence_ids"].findall(packet_text))),
        "run_ids": sorted(set(ID_PATTERNS["run_ids"].findall(packet_text))),
    }


def display_path(path: Path, repo_root: Path) -> str:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(resolved_path)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git_text(
    repo_root: Path,
    *arguments: str,
    strip: bool = True,
) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as error:
        raise ManifestBuildError(f"Nie można uruchomić Git: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "nieznany błąd Git"
        raise ManifestBuildError(f"Nie można odczytać stałego punktu Git: {detail}")
    return completed.stdout.strip() if strip else completed.stdout


if __name__ == "__main__":
    raise SystemExit(main())
