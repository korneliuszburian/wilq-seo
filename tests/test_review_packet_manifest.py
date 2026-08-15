from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from scripts.build_review_packet_manifest import build_review_packet_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/build_review_packet_manifest.py"
GENERATED_AT = "2026-08-15T10:00:00Z"


def test_manifest_binds_commit_screenshot_and_referenced_ids(tmp_path: Path) -> None:
    screenshot_bytes = b"deterministic screenshot bytes"
    screenshot_path = tmp_path / "section 01.webp"
    screenshot_path.write_bytes(screenshot_bytes)
    packet_path = tmp_path / "packet.md"
    packet_path.write_text(
        "\n".join(
            [
                "# Pakiet",
                "![Sekcja](<section 01.webp>)",
                "`content_revision_abc123`",
                "`content_work_item_def456`",
                "`ev_ghi789`",
                "`codex_run_jkl012`",
                "`content_revision_abc123`",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_review_packet_manifest(
        packet_path,
        repo_root=REPO_ROOT,
        screenshots_dir=tmp_path,
        generated_at=GENERATED_AT,
    )

    assert manifest["fixed_point_commit"] == git_output(REPO_ROOT, "rev-parse", "HEAD")
    assert manifest["screenshots"] == [
        {
            "path": str(screenshot_path.resolve()),
            "sha256": hashlib.sha256(screenshot_bytes).hexdigest(),
            "size_bytes": len(screenshot_bytes),
        }
    ]
    assert manifest["referenced_ids"] == {
        "revision_ids": ["content_revision_abc123"],
        "work_item_ids": ["content_work_item_def456"],
        "evidence_ids": ["ev_ghi789"],
        "run_ids": ["codex_run_jkl012"],
    }


def test_cli_rejects_missing_screenshot_with_polish_path(tmp_path: Path) -> None:
    packet_path = tmp_path / "missing-screenshot.md"
    packet_path.write_text(
        "Dowód: docs/review-packets/brakujacy-zrzut.png\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(packet_path)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode != 0
    assert "Brak cytowanego pliku zrzutu ekranu" in completed.stderr
    assert "docs/review-packets/brakujacy-zrzut.png" in completed.stderr
    assert not packet_path.with_suffix(".manifest.json").exists()


def test_cli_rejects_missing_packet_with_polish_path(tmp_path: Path) -> None:
    missing_packet = tmp_path / "brakujacy-pakiet.md"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(missing_packet)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode != 0
    assert "Nie znaleziono pakietu review" in completed.stderr
    assert str(missing_packet) in completed.stderr
    assert not missing_packet.with_suffix(".manifest.json").exists()


def test_tree_dirty_detection_matches_git_status_for_clean_and_dirty_repo(
    tmp_path: Path,
) -> None:
    repo_root, packet_path = initialize_git_repo(tmp_path)

    clean_status = git_output(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    clean_manifest = build_review_packet_manifest(
        packet_path,
        repo_root=repo_root,
        generated_at=GENERATED_AT,
    )

    assert clean_manifest["tree_dirty"] is bool(clean_status)
    assert clean_manifest["tree_dirty"] is False
    assert clean_manifest["dirty_paths"] == []

    packet_path.write_text("# Pakiet zmieniony\n", encoding="utf-8")
    unicode_path = repo_root / "zażółć.md"
    unicode_path.write_text("Nieśledzony plik.\n", encoding="utf-8")
    git(repo_root, "mv", "old-name.md", "new-name.md")
    dirty_status = git_output(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    dirty_manifest = build_review_packet_manifest(
        packet_path,
        repo_root=repo_root,
        generated_at=GENERATED_AT,
    )

    assert dirty_manifest["tree_dirty"] is bool(dirty_status)
    assert dirty_manifest["tree_dirty"] is True
    assert dirty_manifest["dirty_paths"] == [
        "new-name.md",
        "old-name.md",
        "packet.md",
        "zażółć.md",
    ]


def test_cli_records_generated_manifest_in_final_dirty_paths(tmp_path: Path) -> None:
    repo_root, packet_path = initialize_git_repo(tmp_path)

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(packet_path)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    output_path = packet_path.with_suffix(".manifest.json")
    manifest = cast(
        dict[str, Any],
        json.loads(output_path.read_text(encoding="utf-8")),
    )
    final_status = git_output(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    assert manifest["tree_dirty"] is bool(final_status)
    assert manifest["tree_dirty"] is True
    assert manifest["dirty_paths"] == ["packet.manifest.json"]


def test_manifest_has_exact_report_type_and_required_keys(tmp_path: Path) -> None:
    packet_path = tmp_path / "schema.md"
    packet_path.write_text("# Pakiet bez screenshotów\n", encoding="utf-8")

    manifest = build_review_packet_manifest(
        packet_path,
        repo_root=REPO_ROOT,
        generated_at=GENERATED_AT,
    )

    assert manifest["report_type"] == "review_packet_manifest_v1"
    assert set(manifest) == {
        "report_type",
        "packet_path",
        "fixed_point_commit",
        "tree_dirty",
        "dirty_paths",
        "generated_at",
        "screenshots",
        "referenced_ids",
        "safety_note",
    }
    assert manifest["screenshots"] == []
    assert "nie zatwierdza treści ani jej jakości" in manifest["safety_note"]


def git(repo_root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def git_output(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def initialize_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git(repo_root, "init", "--quiet")
    packet_path = repo_root / "packet.md"
    packet_path.write_text("# Pakiet\n", encoding="utf-8")
    (repo_root / "old-name.md").write_text("Plik do zmiany nazwy.\n", encoding="utf-8")
    git(repo_root, "add", "packet.md", "old-name.md")
    git(
        repo_root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "initial packet",
    )
    return repo_root, packet_path
