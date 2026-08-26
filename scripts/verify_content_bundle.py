"""Read-only integrity gate for a generated WILQ content bundle.

The bundle itself is an ignored run artifact.  This verifier is deliberately
tracked so a future run can be checked without trusting a run-local receipt
generator.  It never opens credentials, starts services, or writes files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

_PINNED_ROOT_FD: int | None = None
_PINNED_ROOT_PATH: Path | None = None
_PINNED_ROOT_IDENTITY: tuple[int, int] | None = None

REQUIRED_PROJECTION_FILES = (
    "final/content-manifest.jsonl",
    "final/keep-content-manifest.jsonl",
    "final/robot-manifest-v2.jsonl",
    "target-manifest/target-manifest.jsonl",
    "qa/autonomous-adjudication/keep-content-manifest.jsonl",
    "qa/autonomous-adjudication/robot-manifest-v2.jsonl",
)
REQUIRED_ARTIFACT_KINDS = {"rendered", "revision", "source_pack"}
EXPECTED_DISPOSITIONS = {"keep", "noindex", "redirect", "remove"}
EXPECTED_DECISION_COUNTS = {"keep": 57, "noindex": 87, "redirect": 46, "remove": 24}
EXPECTED_DECISION_ROWS = sum(EXPECTED_DECISION_COUNTS.values())
EXPECTED_CONTENT_ROWS = 181
EXPECTED_CLAIM_ROWS = 950
EXPECTED_COMPLETION_BODY_DIGEST = "f661c4f8478363e8680a34e273a1d293dd125453709d56d27040aa7aa09a7f67"
EXPECTED_COMPLETION_REQUIREMENT_IDS = (
    "canonical_decisions",
    "survivor_page_assets",
    "connector_lineage",
    "claim_ledger",
    "dev_target_readback",
    "target_identity",
    "seo_meta_mapping",
    "acf_writable_mapping",
    "cta_and_internal_links",
    "contentdraft_v2_compile",
    "robot_ready_manifest",
)
EXPECTED_COMPLETION_STATUSES = {
    "canonical_decisions": "complete",
    "survivor_page_assets": "blocked",
    "connector_lineage": "complete",
    "claim_ledger": "blocked",
    "dev_target_readback": "complete",
    "target_identity": "partial",
    "seo_meta_mapping": "partial",
    "acf_writable_mapping": "blocked",
    "cta_and_internal_links": "partial",
    "contentdraft_v2_compile": "blocked",
    "robot_ready_manifest": "blocked",
}
EVIDENCE_REGISTRY_PATH = "qa/autonomous-adjudication/connector-lineage.jsonl"
EXPECTED_EVIDENCE_REGISTRY_SHA256 = (
    "d194c7bf8ed258fe4635666da36eed518a588cc2cf72510eba456012fdc8c546"
)
EXPECTED_CLAIM_KEY_FIELDS = ("page_url", "claim_id")
ALLOWED_PYCACHE_FILES = {
    "qa/autonomous-adjudication/__pycache__/adjudicate_canonical.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/attach_connector_context.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/build_claim_lineage.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/build_completion_audit.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/build_cta_candidate_ledger.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/build_robot_manifest.cpython-314.pyc",
    "qa/autonomous-adjudication/__pycache__/build_survivor_site_graph.cpython-314.pyc",
    "review/__pycache__/build_projection_integrity_receipt.cpython-314.pyc",
    "review/__pycache__/normalize_package_blockers.cpython-314.pyc",
}
ALLOWED_PYCACHE_SHA256 = dict(
    (
        (
            "qa/autonomous-adjudication/__pycache__/adjudicate_canonical.cpython-314.pyc",
            "416b818c2991d5f7f2df565650d687883c9c5a7f38e58a2a9a6068c066ae8be4",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/attach_connector_context.cpython-314.pyc",
            "1f36408119ab6902860170fd753da0f6398b2e519f4c560018a15db6c86a5967",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/build_claim_lineage.cpython-314.pyc",
            "50577e0f79266e17ffc4cae50117fcb228066d8bf83e3e81c3e90eda6559b626",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/build_completion_audit.cpython-314.pyc",
            "fbbf837d8f3913283cf953f66d32ceae3629a54d11c0e26b67c6457c9352ad83",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/build_cta_candidate_ledger.cpython-314.pyc",
            "e587205d88d59981938775ee8ad769a93f19108a21d31ea344189a784ff6b7dd",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/build_robot_manifest.cpython-314.pyc",
            "8aaf944383bb3d7332e88a6a1f1971eeb485b894f7b19fa4b1b334a19c83239b",
        ),
        (
            "qa/autonomous-adjudication/__pycache__/build_survivor_site_graph.cpython-314.pyc",
            "f4cb6a054154a4e4f6a11e043a8221c525d148c95d97f2994af9d3037e30df4d",
        ),
        (
            "review/__pycache__/build_projection_integrity_receipt.cpython-314.pyc",
            "d2e8b24a4005d28156430ccb7121471112c294d72407e789a305af3f6d5c6846",
        ),
        (
            "review/__pycache__/normalize_package_blockers.cpython-314.pyc",
            "8b38cdc28be9a73b38f801668c2f05594e63fdd69868199a91638bb494c497ca",
        ),
    )
)
ALLOWED_PYCACHE_DIRS = {
    "qa/autonomous-adjudication/__pycache__",
    "review/__pycache__",
}
SAFETY_KEYS = {
    "action_apply",
    "actionobject_apply",
    "apply_allowed",
    "connector_refresh",
    "deployment",
    "env_read",
    "generation_performed",
    "generation_invoked",
    "live_mutation",
    "live_refresh",
    "manual_lineage_repair",
    "model_generation",
    "model_invocation",
    "private_packet_read",
    "private_content_packet_read",
    "keyword_planner_invented",
    "publish_allowed",
    "publish_ready",
    "production_ready",
    "refresh_performed",
    "robot_ready",
    "vendor_write",
    "wordPress_write",
    "wordpress_write",
    "write_authorized",
    "write_performed",
    "writes_performed",
    "wp_write",
}


REQUIRED_SAFETY_FIELDS = {
    "qa/planning-generation-proof.json": ("safety.manual_lineage_repair",),
    "qa/autonomous-adjudication/pr18-selected-workspace-runtime-readback.json": (
        "safety.private_content_packet_read",
        "interpretation.production_ready",
    ),
}


def _safe_existing_file(path: Path, run_root: Path) -> Path:
    """Return a regular, non-symlink file after lexical containment checks."""

    if _has_symlink_component(run_root):
        raise ValueError("run_root_is_symlink")
    root = _absolute_root(run_root)
    _assert_pinned_root(root)
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path_outside_run_root") from exc
    current = root
    for part in relative.parts:
        current /= part
        try:
            mode = os.lstat(current).st_mode
        except OSError as exc:
            raise ValueError("path_unreadable") from exc
        if stat.S_ISLNK(mode):
            raise ValueError("symlink_not_allowed")
    if not stat.S_ISREG(os.lstat(candidate).st_mode):
        raise ValueError("regular_file_required")
    return candidate


def _has_symlink_component(path: Path) -> bool:
    candidate = Path(os.path.abspath(path))
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                return True
        except OSError:
            return False
    return False


def _safe_tree_entry(path: Path, run_root: Path) -> bool:
    """Check a tree entry without opening it; symlinks are never trusted."""

    if _has_symlink_component(run_root):
        return False
    root = run_root.resolve()
    try:
        candidate = Path(os.path.abspath(path))
        relative = candidate.relative_to(root)
    except (OSError, ValueError):
        return False
    current = root
    for part in relative.parts:
        current /= part
        try:
            mode = os.lstat(current).st_mode
        except OSError:
            return False
        if stat.S_ISLNK(mode):
            return False
    return True


def _safe_read_text(path: Path, run_root: Path) -> str:
    return _safe_read_bytes(path, run_root).decode("utf-8")


def _safe_read_bytes(path: Path, run_root: Path) -> bytes:
    """Read one regular file through a descriptor opened without symlink follow."""

    safe_path = _safe_existing_file(path, run_root)
    root = _absolute_root(run_root)
    relative = safe_path.relative_to(root)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    directory_descriptor = -1
    try:
        if _PINNED_ROOT_FD is not None and root == _PINNED_ROOT_PATH:
            _assert_pinned_root(root)
            directory_descriptor = os.dup(_PINNED_ROOT_FD)
        else:
            directory_descriptor = _open_directory_no_follow(root, directory_flags)
        for component in relative.parts[:-1]:
            child_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = child_descriptor
        descriptor = os.open(relative.parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise ValueError("safe_open_failed") from exc
    finally:
        if directory_descriptor != -1:
            os.close(directory_descriptor)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("regular_file_required")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            return stream.read()
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _open_directory_no_follow(path: Path, flags: int) -> int:
    candidate = Path(os.path.abspath(path))
    descriptor = os.open(candidate.anchor, flags)
    try:
        for component in candidate.parts[1:]:
            child_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child_descriptor
        return descriptor
    except OSError:
        os.close(descriptor)
        raise


def _pin_run_root(path: Path) -> Path:
    global _PINNED_ROOT_FD, _PINNED_ROOT_PATH, _PINNED_ROOT_IDENTITY
    if _has_symlink_component(path):
        raise ValueError("run_root_is_symlink")
    absolute_path = Path(os.path.abspath(path))
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = _open_directory_no_follow(absolute_path, flags)
    try:
        identity = os.fstat(descriptor)
        if not stat.S_ISDIR(identity.st_mode):
            raise ValueError("run_root_directory_required")
        if _PINNED_ROOT_FD is not None:
            os.close(_PINNED_ROOT_FD)
        _PINNED_ROOT_FD = descriptor
        _PINNED_ROOT_PATH = absolute_path
        _PINNED_ROOT_IDENTITY = (identity.st_dev, identity.st_ino)
        return absolute_path
    except OSError as exc:
        os.close(descriptor)
        raise ValueError("run_root_pin_failed") from exc


def _absolute_root(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _assert_pinned_root(path: Path) -> None:
    if _PINNED_ROOT_PATH is None or _PINNED_ROOT_IDENTITY is None:
        return
    if _absolute_root(path) != _PINNED_ROOT_PATH:
        return
    try:
        identity = os.stat(_PINNED_ROOT_PATH, follow_symlinks=False)
    except OSError as exc:
        raise ValueError("run_root_replaced") from exc
    if (identity.st_dev, identity.st_ino) != _PINNED_ROOT_IDENTITY:
        raise ValueError("run_root_replaced")


def sha256(path: Path, run_root: Path | None = None) -> str:
    if run_root is None:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(_safe_read_bytes(path, run_root)).hexdigest()


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_jsonl(path: Path, run_root: Path | None = None) -> list[dict[str, Any]]:
    text = (
        _safe_read_text(path, run_root)
        if run_root is not None
        else path.read_text(encoding="utf-8")
    )
    return [json.loads(line) for line in text.splitlines() if line]


def verify_sha_manifest(root: Path) -> dict[str, Any]:
    manifest = root / "SHA256SUMS"
    errors: list[str] = []
    expected: set[str] = set()
    try:
        manifest = _safe_existing_file(manifest, root)
    except ValueError:
        return {"entries": 0, "valid": False, "errors": ["missing_SHA256SUMS"]}
    for line in _safe_read_text(manifest, root).splitlines():
        if not line:
            continue
        try:
            expected_sha, relative = line.split(None, 1)
        except ValueError:
            errors.append("malformed_SHA256SUMS_line")
            continue
        relative = relative.removeprefix("./")
        expected.add(relative)
        candidate = Path(relative)
        try:
            valid = not candidate.is_absolute()
            if valid:
                path = _safe_existing_file(root / candidate, root)
                valid = sha256(path, root) == expected_sha
        except ValueError:
            valid = False
        if not valid:
            errors.append(relative)
    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append(relative)
            continue
        if not path.is_dir() and not path.is_file():
            errors.append(relative)
            continue
        if path.is_file() and path.name != "SHA256SUMS" and "__pycache__" not in path.parts:
            actual.add(relative)
    errors.extend(sorted(actual - expected))
    return {"entries": len(expected), "valid": not errors and expected == actual, "errors": errors}


def verify_projection(path: Path, run_root: Path) -> dict[str, int]:
    try:
        rows = load_jsonl(path, run_root)
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "rows": 0,
            "self_hash_valid": 0,
            "self_hash_missing": 0,
            "self_hash_mismatch": 0,
            "artifact_checked": 0,
            "artifact_invalid": 1,
            "duplicate_urls": 0,
            "invalid_safety_fields": 1,
            "invalid_blockers": 1,
        }
    self_hash_valid = 0
    self_hash_missing = 0
    self_hash_mismatch = 0
    artifact_checked = 0
    artifact_invalid = 0
    invalid_safety_fields = 0
    invalid_blockers = 0
    urls: list[str] = []
    for row in rows:
        url = row.get("url")
        if not isinstance(url, str) or not url:
            artifact_invalid += 1
        else:
            urls.append(url)
        if row.get("publish_allowed") is not False:
            invalid_safety_fields += 1
        if (
            path.name
            in {
                "keep-content-manifest.jsonl",
                "robot-manifest-v2.jsonl",
                "target-manifest.jsonl",
            }
            and row.get("robot_ready") is not False
        ):
            invalid_safety_fields += 1
        if path.name in {"content-manifest.jsonl", "target-manifest.jsonl"} and (
            row.get("publish_ready") is not False
        ):
            invalid_safety_fields += 1
        blockers = row.get("blockers")
        if not isinstance(blockers, list) or any(not _typed_blocker(item) for item in blockers):
            invalid_blockers += 1
        expected = row.get("manifest_record_sha256")
        if not isinstance(expected, str):
            self_hash_missing += 1
        else:
            unsigned = dict(row)
            unsigned.pop("manifest_record_sha256", None)
            if canonical_digest(unsigned) == expected:
                self_hash_valid += 1
            else:
                self_hash_mismatch += 1
        refs = row.get("artifact_refs")
        required = (
            path.name
            in {"content-manifest.jsonl", "keep-content-manifest.jsonl", "target-manifest.jsonl"}
            or row.get("final_disposition") == "keep"
        )
        if refs is None:
            if required:
                artifact_invalid += 1
            continue
        if not isinstance(refs, dict) or not isinstance(row.get("artifact_base"), str):
            artifact_invalid += 1
            continue
        if required and set(refs) != REQUIRED_ARTIFACT_KINDS:
            artifact_invalid += 1
        if path.name in {"content-manifest.jsonl", "target-manifest.jsonl"} and any(
            not isinstance(row.get(key), str) or not row[key]
            for key in ("url", "slug", "revision_id", "source_pack_id")
        ):
            artifact_invalid += 1
        if path.name == "keep-content-manifest.jsonl" and any(
            not isinstance(row.get(key), str) or not row[key] for key in ("url", "revision_id")
        ):
            artifact_invalid += 1
        if path.name == "robot-manifest-v2.jsonl" and (
            not isinstance(row.get("url"), str)
            or not row["url"]
            or not isinstance(row.get("final_disposition"), str)
            or row["final_disposition"] not in EXPECTED_DISPOSITIONS
        ):
            artifact_invalid += 1
        base_value = str(row["artifact_base"])
        if Path(base_value).is_absolute():
            artifact_invalid += 1
        base = path.parent / base_value
        artifact_documents: dict[str, dict[str, Any]] = {}
        rendered_stems: list[str] = []
        for kind, ref in refs.items():
            artifact_checked += 1
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                artifact_invalid += 1
                continue
            if Path(ref["path"]).is_absolute():
                artifact_invalid += 1
                continue
            try:
                target = _safe_existing_file(base / ref["path"], run_root)
                artifact_bytes = _safe_read_bytes(target, run_root)
                valid = (
                    kind in REQUIRED_ARTIFACT_KINDS
                    and target.suffix
                    == {"rendered": ".md", "revision": ".json", "source_pack": ".json"}.get(kind)
                    and ref.get("bytes") == len(artifact_bytes)
                    and ref.get("sha256") == hashlib.sha256(artifact_bytes).hexdigest()
                )
                if kind == "rendered":
                    rendered_stems.append(target.stem)
                    revision_marker = re.search(
                        rb"^Rewizja:\s+`([^`]+)`", artifact_bytes, flags=re.MULTILINE
                    )
                    valid = valid and revision_marker is not None
                    if row.get("revision_id") is not None:
                        valid = (
                            valid
                            and revision_marker is not None
                            and revision_marker.group(1).decode("utf-8") == row.get("revision_id")
                        )
                elif kind in {"revision", "source_pack"}:
                    document = json.loads(artifact_bytes.decode("utf-8"))
                    artifact_documents[kind] = document
                    valid = valid and document.get("url") == row.get("url")
                    if kind == "revision":
                        valid = valid and isinstance(document.get("revision_id"), str)
                    if kind == "source_pack":
                        valid = valid and isinstance(document.get("source_pack_id"), str)
                    if row.get("slug") is not None:
                        valid = valid and document.get("slug") == row.get("slug")
                    if kind == "revision" and row.get("revision_id") is not None:
                        valid = valid and document.get("revision_id") == row.get("revision_id")
                    if kind == "source_pack" and row.get("source_pack_id") is not None:
                        valid = valid and document.get("source_pack_id") == row.get(
                            "source_pack_id"
                        )
            except (OSError, ValueError):
                valid = False
            if not valid:
                artifact_invalid += 1
        owner_slug = row.get("slug")
        if owner_slug is None:
            owner_slug = next(
                (
                    document.get("slug")
                    for document in artifact_documents.values()
                    if isinstance(document.get("slug"), str)
                ),
                None,
            )
        if owner_slug is None or any(stem != owner_slug for stem in rendered_stems):
            artifact_invalid += 1
        if any(
            document.get("slug") != owner_slug or document.get("url") != row.get("url")
            for document in artifact_documents.values()
        ):
            artifact_invalid += 1
    return {
        "rows": len(rows),
        "self_hash_valid": self_hash_valid,
        "self_hash_missing": self_hash_missing,
        "self_hash_mismatch": self_hash_mismatch,
        "artifact_checked": artifact_checked,
        "artifact_invalid": artifact_invalid,
        "duplicate_urls": len(urls) - len(set(urls)),
        "invalid_safety_fields": invalid_safety_fields,
        "invalid_blockers": invalid_blockers,
    }


def verify_blockers(run_root: Path) -> dict[str, int]:
    arrays = entries = invalid = 0
    for root_name in ("final", "qa", "target-manifest"):
        root = run_root / root_name
        for path in root.rglob("*"):
            if not _safe_tree_entry(path, run_root):
                invalid += 1
                continue
            if (
                not path.is_file()
                or path.name == "SHA256SUMS"
                or "__pycache__" in path.parts
                or path.suffix not in {".json", ".jsonl"}
            ):
                continue
            try:
                documents = (
                    load_jsonl(path, run_root)
                    if path.suffix == ".jsonl"
                    else [json.loads(_safe_read_text(path, run_root))]
                )
            except (OSError, json.JSONDecodeError):
                invalid += 1
                continue

            def visit(value: object, ancestors: tuple[str, ...] = ()) -> None:
                nonlocal arrays, entries, invalid
                if isinstance(value, dict):
                    for key, child in value.items():
                        blocker_key = key == "blockers" or key.endswith("_blockers")
                        collection = blocker_key and isinstance(child, list)
                        singular = key == "blocker" and "claim_ledger" in ancestors
                        if blocker_key and not isinstance(child, list):
                            invalid += 1
                        elif collection:
                            arrays += 1
                            entries += len(child)
                            for item in child:
                                if not _typed_blocker(item):
                                    invalid += 1
                        elif singular and child is not None:
                            entries += 1
                            if not _typed_blocker(child):
                                invalid += 1
                        visit(child, ancestors + (key,))
                elif isinstance(value, list):
                    for item in value:
                        visit(item, ancestors)

            for document in documents:
                visit(document)
    return {"arrays": arrays, "entries": entries, "typed": entries - invalid, "invalid": invalid}


def _typed_blocker(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"code", "status", "detail"}
        and all(isinstance(value[key], str) and value[key] for key in value)
    )


def verify_cta_refs(run_root: Path) -> dict[str, int]:
    cta = run_root / "qa/autonomous-adjudication/cta-candidate-ledger.jsonl"
    try:
        cta_path = _safe_existing_file(cta, run_root)
        expected = sha256(cta_path, run_root)
    except (OSError, ValueError):
        cta_path = None
        expected = None
    checked = missing = invalid = 0
    try:
        documents: list[tuple[Path, dict[str, Any]]] = [
            (run_root / "final/content-manifest.jsonl", row)
            for row in load_jsonl(run_root / "final/content-manifest.jsonl", run_root)
        ]
        documents.extend(
            (path, json.loads(_safe_read_text(path, run_root)))
            for path in sorted((run_root / "final/source-packs").glob("*.json"))
            if _safe_tree_entry(path, run_root)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return {"expected": 0, "checked": 0, "valid": 0, "missing": 0, "invalid": 1}
    for owner, document in documents:
        ref = document.get("cta_candidate_ref")
        if not isinstance(ref, dict):
            missing += 1
            continue
        checked += 1
        base = ref.get("path_base")
        ref_path = ref.get("path")
        if (
            not isinstance(base, str)
            or Path(base).is_absolute()
            or not isinstance(ref_path, str)
            or Path(ref_path).is_absolute()
        ):
            invalid += 1
            continue
        try:
            target = _safe_existing_file(owner.parent / base / ref_path, run_root)
        except (OSError, ValueError):
            target = None
        if expected is None or target != cta_path or ref.get("sha256") != expected:
            invalid += 1
    return {
        "expected": checked + missing,
        "checked": checked,
        "valid": checked - invalid,
        "missing": missing,
        "invalid": invalid,
    }


def verify_decision_projection(
    run_root: Path,
    robot: list[dict[str, Any]],
    adjudicated: list[dict[str, Any]],
) -> dict[str, int]:
    expected = {
        row.get("url"): row.get("final_disposition")
        for row in adjudicated
        if isinstance(row.get("url"), str)
    }
    actual = {
        row.get("url"): row.get("final_disposition")
        for row in robot
        if isinstance(row.get("url"), str)
    }
    expected_urls = [row.get("url") for row in adjudicated]
    actual_urls = [row.get("url") for row in robot]
    expected_string_urls = {url for url in expected_urls if isinstance(url, str)}
    actual_string_urls = {url for url in actual_urls if isinstance(url, str)}
    return {
        "expected": len(expected),
        "actual": len(actual),
        "expected_rows": len(adjudicated),
        "actual_rows": len(robot),
        "expected_duplicates": len(expected_urls) - len(expected_string_urls),
        "actual_duplicates": len(actual_urls) - len(actual_string_urls),
        "invalid_expected_urls": sum(not isinstance(url, str) or not url for url in expected_urls),
        "invalid_actual_urls": sum(not isinstance(url, str) or not url for url in actual_urls),
        "matching": sum(actual.get(url) == disposition for url, disposition in expected.items()),
        "missing": len(set(expected) - set(actual)),
        "unexpected": len(set(actual) - set(expected)),
        "disposition_mismatch": sum(
            url in actual and actual[url] != disposition for url, disposition in expected.items()
        ),
    }


def verify_redirects(
    run_root: Path,
    robot: list[dict[str, Any]],
    adjudicated: list[dict[str, Any]],
) -> dict[str, int | bool]:
    expected = {
        row.get("url"): row for row in adjudicated if row.get("final_disposition") == "redirect"
    }
    readback_path = run_root / "qa/autonomous-adjudication/public-readback.jsonl"
    readback = {
        row.get("receipt_id"): row
        for row in load_jsonl(readback_path, run_root)
        if row.get("receipt_id")
    }
    redirects = [row for row in robot if row.get("final_disposition") == "redirect"]
    projection_matches = 0
    source_resolved = 0
    target_resolved = 0
    target_matches = 0
    for row in redirects:
        source = expected.get(row.get("url"))
        if source is not None and (
            row.get("production_readback_receipt_id")
            == source.get("production_readback_receipt_id")
            and row.get("target_readback_receipt_id") == source.get("target_readback_receipt_id")
        ):
            projection_matches += 1
        source_readback = readback.get(row.get("production_readback_receipt_id"))
        target_readback = readback.get(row.get("target_readback_receipt_id"))
        if source_readback is not None and source_readback.get("source_url") == row.get("url"):
            source_resolved += 1
        if target_readback is None:
            continue
        target_resolved += 1
        target_url = row.get("redirect_target_url")
        if target_url in {
            target_readback.get("public_url"),
            target_readback.get("canonical_url"),
            target_readback.get("final_url"),
        } or (
            source_readback is not None
            and target_readback.get("receipt_id") == source_readback.get("receipt_id")
            and target_url
            in {source_readback.get("canonical_url"), source_readback.get("final_url")}
        ):
            target_matches += 1
    valid = (
        len(redirects) == len(expected)
        and projection_matches == len(redirects)
        and source_resolved == len(redirects)
        and target_resolved == len(redirects)
        and target_matches == len(redirects)
    )
    return {
        "expected": len(expected),
        "actual": len(redirects),
        "projection_matches": projection_matches,
        "source_resolved": source_resolved,
        "target_resolved": target_resolved,
        "target_url_matches": target_matches,
        "valid": valid,
    }


def _resolve_artifact_reference(
    manifest_path: Path, row: dict[str, Any], kind: str, run_root: Path
) -> Path | None:
    refs = row.get("artifact_refs")
    base_value = row.get("artifact_base", ".")
    if not isinstance(refs, dict) or not isinstance(base_value, str):
        return None
    ref = refs.get(kind)
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        return None
    if Path(base_value).is_absolute() or Path(ref["path"]).is_absolute():
        return None
    try:
        return _safe_existing_file(manifest_path.parent / base_value / ref["path"], run_root)
    except (OSError, ValueError):
        return None


def verify_target_bundle(run_root: Path) -> dict[str, int | bool]:
    target_dir = run_root / "target-manifest"
    target_path = target_dir / "target-manifest.jsonl"
    bundle_path = target_dir / "robot-bundle-manifest.jsonl"
    content_path = run_root / "final/content-manifest.jsonl"
    targets = load_jsonl(target_path, run_root)
    bundles = load_jsonl(bundle_path, run_root)
    content_rows = load_jsonl(content_path, run_root)
    by_url = {row.get("url"): row for row in targets if isinstance(row.get("url"), str)}
    target_urls = [row.get("url") for row in targets]
    bundle_urls = [row.get("url") for row in bundles]
    content_urls = [row.get("url") for row in content_rows]
    target_url_set = {url for url in target_urls if isinstance(url, str)}
    bundle_url_set = {url for url in bundle_urls if isinstance(url, str)}
    content_url_set = {url for url in content_urls if isinstance(url, str)}
    selectors = 0
    revisions = 0
    claim_pointers = 0
    target_revision_matches = 0
    bundle_safety_fields_valid = 0
    bundle_blockers_valid = 0
    target_ref_safety_fields_valid = 0
    target_content_matches = 0
    content_by_url = {
        row.get("url"): row for row in content_rows if isinstance(row.get("url"), str)
    }
    for target_row in targets:
        content = content_by_url.get(target_row.get("url"))
        if not isinstance(content, dict):
            continue
        identity_matches = all(
            target_row.get(key) == content.get(key)
            for key in ("url", "slug", "revision_id", "source_pack_id")
        )
        artifact_matches = True
        for kind in REQUIRED_ARTIFACT_KINDS:
            target_artifact = _resolve_artifact_reference(target_path, target_row, kind, run_root)
            content_artifact = _resolve_artifact_reference(content_path, content, kind, run_root)
            target_ref = (target_row.get("artifact_refs") or {}).get(kind)
            content_ref = (content.get("artifact_refs") or {}).get(kind)
            artifact_matches = artifact_matches and target_artifact == content_artifact
            artifact_matches = artifact_matches and isinstance(target_ref, dict)
            artifact_matches = artifact_matches and isinstance(content_ref, dict)
            if isinstance(target_ref, dict) and isinstance(content_ref, dict):
                artifact_matches = artifact_matches and (
                    target_ref.get("bytes") == content_ref.get("bytes")
                    and target_ref.get("sha256") == content_ref.get("sha256")
                )
        if identity_matches and artifact_matches:
            target_content_matches += 1
    for row in bundles:
        bundle_target = by_url.get(row.get("url"))
        if row.get("publish_allowed") is False and row.get("robot_ready") is False:
            bundle_safety_fields_valid += 1
        blockers = row.get("blockers")
        if isinstance(blockers, list) and all(_typed_blocker(item) for item in blockers):
            bundle_blockers_valid += 1
        target_ref = row.get("target_ref") or {}
        if (
            isinstance(target_ref, dict)
            and target_ref.get("publish_allowed") is False
            and target_ref.get("robot_ready") is False
        ):
            target_ref_safety_fields_valid += 1
        selector = target_ref.get("selector") or {}
        if (
            target_ref.get("path") == "target-manifest.jsonl"
            and selector.get("url") == row.get("url")
            and bundle_target is not None
            and bundle_target.get("slug") == row.get("slug")
        ):
            selectors += 1
        revision_ref = row.get("revision_ref") or {}
        revision_ref_path = revision_ref.get("path")
        expected_revision_ref = (
            bundle_target.get("artifact_refs", {}).get("revision")
            if isinstance(bundle_target, dict)
            and isinstance(bundle_target.get("artifact_refs"), dict)
            else None
        )
        if (
            isinstance(expected_revision_ref, dict)
            and revision_ref_path == expected_revision_ref.get("path")
            and revision_ref.get("content_digest") == expected_revision_ref.get("sha256")
            and isinstance(bundle_target, dict)
            and revision_ref.get("revision_id") == bundle_target.get("revision_id")
        ):
            target_revision_matches += 1
        if not isinstance(revision_ref_path, str) or Path(revision_ref_path).is_absolute():
            revision_path = None
            revision_valid = False
        else:
            revision_path = None
            revision_valid = False
        try:
            if revision_path is None and isinstance(revision_ref_path, str):
                revision_path = _safe_existing_file(target_dir / revision_ref_path, run_root)
                revision_valid = revision_ref.get("content_digest") == sha256(
                    revision_path, run_root
                )
        except (OSError, ValueError):
            revision_path = None
            revision_valid = False
        if revision_valid and revision_path is not None:
            revision: dict[str, Any] | None
            try:
                revision = json.loads(_safe_read_text(revision_path, run_root))
            except (OSError, ValueError, json.JSONDecodeError):
                revision = None
                revision_valid = False
            if isinstance(revision, dict):
                revision_valid = revision.get("url") == row.get("url") and revision.get(
                    "slug"
                ) == row.get("slug")
                revision_valid = revision_valid and revision.get("revision_id") == revision_ref.get(
                    "revision_id"
                )
                if bundle_target is not None:
                    revision_valid = revision_valid and revision.get(
                        "revision_id"
                    ) == bundle_target.get("revision_id")
            if revision_valid:
                revisions += 1
        else:
            revision = None
        audit_ref = row.get("audit_ref") or {}
        audit_ref_path = audit_ref.get("path")
        try:
            audit_path = (
                _safe_existing_file(target_dir / audit_ref_path, run_root)
                if isinstance(audit_ref_path, str) and not Path(audit_ref_path).is_absolute()
                else None
            )
        except (OSError, ValueError):
            audit_path = None
        if (
            audit_path == revision_path
            and audit_path is not None
            and audit_ref.get("json_pointer") == "/claim_ledger"
        ):
            if not isinstance(revision, dict):
                revision = json.loads(_safe_read_text(audit_path, run_root))
            if not isinstance(revision, dict):
                continue
            claim_ledger = revision.get("claim_ledger")
            if (
                isinstance(claim_ledger, list)
                and audit_ref.get("claim_ledger_digest") == canonical_digest(claim_ledger)
                and revision.get("url") == row.get("url")
                and revision.get("slug") == row.get("slug")
            ):
                claim_pointers += 1
    valid = (
        len(targets) == len(by_url) == len(bundles)
        and len(target_url_set) == len(targets)
        and len(bundle_url_set) == len(bundles)
        and target_url_set == bundle_url_set
        and len(content_rows) == EXPECTED_CONTENT_ROWS
        and len(content_url_set) == len(content_rows)
        and content_url_set == target_url_set
        and selectors == len(bundles)
        and revisions == len(bundles)
        and claim_pointers == len(bundles)
        and target_revision_matches == len(bundles)
        and bundle_safety_fields_valid == len(bundles)
        and bundle_blockers_valid == len(bundles)
        and target_ref_safety_fields_valid == len(bundles)
        and target_content_matches == len(targets) == EXPECTED_CONTENT_ROWS
    )
    return {
        "targets": len(targets),
        "bundles": len(bundles),
        "content_rows": len(content_rows),
        "selectors": selectors,
        "revision_refs": revisions,
        "claim_pointers": claim_pointers,
        "target_revision_matches": target_revision_matches,
        "bundle_safety_fields_valid": bundle_safety_fields_valid,
        "bundle_blockers_valid": bundle_blockers_valid,
        "target_ref_safety_fields_valid": target_ref_safety_fields_valid,
        "target_content_matches": target_content_matches,
        "valid": valid,
    }


def verify_mirrors(run_root: Path) -> dict[str, int]:
    def comparable(row: dict[str, Any]) -> dict[str, Any]:
        value = dict(row)
        value.pop("artifact_base", None)
        value.pop("manifest_record_sha256", None)
        return value

    result: dict[str, int] = {}
    for name in ("keep-content-manifest.jsonl", "robot-manifest-v2.jsonl"):
        final = load_jsonl(run_root / "final" / name, run_root)
        mirror = load_jsonl(run_root / "qa/autonomous-adjudication" / name, run_root)
        result[name] = sum(
            comparable(a) == comparable(b) for a, b in zip(final, mirror, strict=False)
        )
        result[f"{name}_rows"] = len(final)
        result[f"{name}_mirror_rows"] = len(mirror)
        result[f"{name}_rows_match"] = int(len(final) == len(mirror))
    final_robot = load_jsonl(run_root / "final/robot-manifest-v2.jsonl", run_root)
    qa_robot = load_jsonl(run_root / "qa/autonomous-adjudication/robot-manifest-v2.jsonl", run_root)
    final_keep = load_jsonl(run_root / "final/keep-content-manifest.jsonl", run_root)
    qa_keep = load_jsonl(
        run_root / "qa/autonomous-adjudication/keep-content-manifest.jsonl", run_root
    )
    final_keep_urls = {
        row.get("url")
        for row in final_robot
        if row.get("final_disposition") == "keep" and isinstance(row.get("url"), str)
    }
    qa_keep_urls = {
        row.get("url")
        for row in qa_robot
        if row.get("final_disposition") == "keep" and isinstance(row.get("url"), str)
    }
    final_manifest_urls = {row.get("url") for row in final_keep if isinstance(row.get("url"), str)}
    qa_manifest_urls = {row.get("url") for row in qa_keep if isinstance(row.get("url"), str)}
    result["keep_owner_set_matches"] = int(
        final_keep_urls == final_manifest_urls == qa_keep_urls == qa_manifest_urls
    )
    result["keep_owner_set_rows"] = len(final_keep_urls)
    return result


def _read_nested(value: object, dotted_path: str) -> object:
    current = value
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def verify_flags(run_root: Path) -> dict[str, int]:
    true_flags = 0
    invalid_paths = 0
    required_fields = 0
    files = [
        root for name in ("final", "qa", "target-manifest") for root in (run_root / name).rglob("*")
    ]
    for path in files:
        if not _safe_tree_entry(path, run_root):
            invalid_paths += 1
            continue
        if (
            not path.is_file()
            or path.suffix not in {".json", ".jsonl"}
            or path.name == "SHA256SUMS"
        ):
            continue
        try:
            documents = (
                load_jsonl(path, run_root)
                if path.suffix == ".jsonl"
                else [json.loads(_safe_read_text(path, run_root))]
            )
        except (OSError, ValueError, json.JSONDecodeError):
            invalid_paths += 1
            continue
        relative = path.relative_to(run_root).as_posix()
        for dotted_path in REQUIRED_SAFETY_FIELDS.get(relative, ()):
            required_fields += 1
            if _read_nested(documents[0], dotted_path) is not False:
                invalid_paths += 1
        stack: list[tuple[object, tuple[str, ...]]] = [(document, ()) for document in documents]
        while stack:
            value, value_path = stack.pop()
            if isinstance(value, dict):
                for key, flag in value.items():
                    if key == "path" and isinstance(flag, str) and Path(flag).is_absolute():
                        invalid_paths += 1
                    if key not in SAFETY_KEYS:
                        continue
                    count_exception = (
                        key == "robot_ready"
                        and value_path == ("requirements", "10", "proof")
                        and relative
                        in {
                            "final/completion-audit.json",
                            "qa/autonomous-adjudication/completion-audit.json",
                        }
                    )
                    if count_exception:
                        if not isinstance(flag, int) or isinstance(flag, bool) or flag != 0:
                            invalid_paths += 1
                            continue
                    elif not isinstance(flag, bool):
                        invalid_paths += 1
                        continue
                    if flag is True:
                        true_flags += 1
                stack.extend(
                    (item, value_path + (key,))
                    for key, item in value.items()
                    if isinstance(item, (dict, list))
                )
            elif isinstance(value, list):
                stack.extend((item, value_path + (str(index),)) for index, item in enumerate(value))
    return {
        "true_flags": true_flags,
        "invalid_paths": invalid_paths,
        "required_fields": required_fields,
    }


def verify_delivery_layout(run_root: Path) -> dict[str, Any]:
    forbidden: list[str] = []
    for path in run_root.rglob("*"):
        relative = path.relative_to(run_root).as_posix()
        if (
            "__pycache__" in Path(relative).parts
            and relative not in ALLOWED_PYCACHE_FILES
            and relative not in ALLOWED_PYCACHE_DIRS
        ):
            forbidden.append(relative)
            continue
        if "__pycache__" in Path(relative).parts and path.is_file():
            try:
                if sha256(path, run_root) != ALLOWED_PYCACHE_SHA256.get(relative):
                    forbidden.append(relative)
                    continue
            except (OSError, ValueError):
                forbidden.append(relative)
                continue
        if any(
            part.startswith(("sol-raw", "raw-trace", "model-trace"))
            or part in {"batch-inputs", "batch_inputs"}
            or part == ".env"
            or (part.startswith(".env.") and part != ".env.example")
            or "private" in part.lower()
            or "packet" in part.lower()
            for part in Path(relative).parts
        ):
            forbidden.append(relative)
            continue
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            forbidden.append(relative)
            continue
        if path.is_file() and (
            path.name.startswith("sol-raw")
            or path.name.startswith("raw-trace")
            or path.name.startswith("model-trace")
        ):
            forbidden.append(relative)
        if path.name in {"batch-inputs", "batch_inputs"}:
            forbidden.append(relative)
    return {"forbidden_paths": sorted(set(forbidden)), "valid": not forbidden}


def _registry_evidence_ids(run_root: Path) -> tuple[set[str], bool]:
    path = run_root / EVIDENCE_REGISTRY_PATH
    try:
        if sha256(path, run_root) != EXPECTED_EVIDENCE_REGISTRY_SHA256:
            return set(), False
        rows = load_jsonl(path, run_root)
    except (OSError, ValueError, json.JSONDecodeError):
        return set(), False
    evidence_ids: set[str] = set()

    def visit(value: object, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif (
            key
            in {
                "evidence_ids",
                "decision_evidence_ids",
                "adjudication_evidence_ids",
            }
            and isinstance(value, str)
            and value
        ):
            evidence_ids.add(value)

    for row in rows:
        visit(row)
    return evidence_ids, True


def verify_claim_lineage(run_root: Path) -> dict[str, Any]:
    path = run_root / "qa/autonomous-adjudication/adjudicated-claim-lineage.jsonl"
    try:
        rows = load_jsonl(path, run_root)
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "rows": 0,
            "rendered_without_evidence": 1,
            "approved_without_evidence": 1,
            "approved_without_rendered": 1,
            "invalid_types": 1,
            "unknown_evidence_ids": 1,
            "evidence_ids_checked": 0,
            "invalid_required_fields": 1,
            "duplicate_claim_keys": 1,
            "registry_valid": False,
        }
    known_evidence_ids, registry_valid = _registry_evidence_ids(run_root)
    rendered_without_evidence = 0
    approved_without_evidence = 0
    approved_without_rendered = 0
    invalid_types = 0
    invalid_required_fields = 0
    unknown_evidence_ids = 0
    evidence_ids_checked = 0
    claim_keys: list[tuple[str, str]] = []
    for row in rows:
        evidence_ids = row.get("evidence_ids")
        has_evidence = (
            isinstance(evidence_ids, list)
            and bool(evidence_ids)
            and all(isinstance(evidence_id, str) and evidence_id for evidence_id in evidence_ids)
        )
        if isinstance(evidence_ids, list):
            evidence_ids_checked += sum(isinstance(item, str) for item in evidence_ids)
            unknown_evidence_ids += sum(
                isinstance(item, str) and item not in known_evidence_ids for item in evidence_ids
            )
        if not isinstance(evidence_ids, list) or any(
            not isinstance(item, str) or not item for item in evidence_ids
        ):
            invalid_required_fields += 1
        for key in EXPECTED_CLAIM_KEY_FIELDS:
            if not isinstance(row.get(key), str) or not row[key]:
                invalid_required_fields += 1
        if not isinstance(row.get("source_pack_id"), str) or not row["source_pack_id"]:
            invalid_required_fields += 1
        if not isinstance(row.get("freshness_status"), str) or not row["freshness_status"]:
            invalid_required_fields += 1
        if not isinstance(row.get("owner_review_status"), str) or not row["owner_review_status"]:
            invalid_required_fields += 1
        if row.get("publish_allowed") is not False:
            invalid_required_fields += 1
        approval_blockers = row.get("approval_blockers")
        if not isinstance(approval_blockers, list) or any(
            not _typed_blocker(item) for item in approval_blockers
        ):
            invalid_required_fields += 1
        for key in ("rendered", "approved_for_rendering"):
            if not isinstance(row.get(key), bool):
                invalid_types += 1
        if isinstance(row.get("page_url"), str) and isinstance(row.get("claim_id"), str):
            claim_keys.append((row["page_url"], row["claim_id"]))
        if row.get("rendered") is True and not has_evidence:
            rendered_without_evidence += 1
        if row.get("approved_for_rendering") is True:
            if not has_evidence:
                approved_without_evidence += 1
            if row.get("rendered") is not True:
                approved_without_rendered += 1
    duplicate_claim_keys = len(claim_keys) - len(set(claim_keys))
    return {
        "rows": len(rows),
        "rendered_without_evidence": rendered_without_evidence,
        "approved_without_evidence": approved_without_evidence,
        "approved_without_rendered": approved_without_rendered,
        "invalid_types": invalid_types,
        "unknown_evidence_ids": unknown_evidence_ids,
        "evidence_ids_checked": evidence_ids_checked,
        "invalid_required_fields": invalid_required_fields,
        "duplicate_claim_keys": duplicate_claim_keys,
        "registry_valid": registry_valid,
    }


def verify_counts(run_root: Path) -> dict[str, Any]:
    robot = load_jsonl(run_root / "final/robot-manifest-v2.jsonl", run_root)
    keep = load_jsonl(run_root / "final/keep-content-manifest.jsonl", run_root)
    adjudicated = load_jsonl(
        run_root / "qa/autonomous-adjudication/adjudicated-canonical-ledger.jsonl", run_root
    )
    claims = load_jsonl(
        run_root / "qa/autonomous-adjudication/adjudicated-claim-lineage.jsonl", run_root
    )
    counts = Counter(row.get("final_disposition") for row in robot)
    expected_dispositions = Counter(row.get("final_disposition") for row in adjudicated)
    robot_urls = {row.get("url") for row in robot if isinstance(row.get("url"), str)}
    adjudicated_urls = {row.get("url") for row in adjudicated if isinstance(row.get("url"), str)}
    return {
        "decisions": len(robot),
        "decision_counts": dict(counts),
        "expected_decisions": len(adjudicated),
        "expected_decision_counts": dict(expected_dispositions),
        "decision_rows_match": len(robot) == EXPECTED_DECISION_ROWS,
        "expected_rows_match": len(adjudicated) == EXPECTED_DECISION_ROWS,
        "decision_counts_exact": dict(counts) == EXPECTED_DECISION_COUNTS,
        "expected_decision_counts_exact": dict(expected_dispositions) == EXPECTED_DECISION_COUNTS,
        "decision_projection_matches": dict(counts) == dict(expected_dispositions)
        and robot_urls == adjudicated_urls,
        "keep": len(keep),
        "keep_rows_match": len(keep) == EXPECTED_DECISION_COUNTS["keep"],
        "claims": len(claims),
        "claim_rows_match": len(claims) == EXPECTED_CLAIM_ROWS,
        "rendered_claims": sum(row.get("rendered") is True for row in claims),
        "approved_claims": sum(row.get("approved_for_rendering") is True for row in claims),
        "claims_without_evidence": sum(not row.get("evidence_ids") for row in claims),
    }


def verify_completion_state(run_root: Path) -> dict[str, Any]:
    """Require both completion receipts to describe the same incomplete package.

    The receipts are part of the delivery contract, not an authority to mark a
    bundle complete.  Checking the critical proof fields prevents a coordinated
    deletion or a stale receipt from turning a partial package into a ready one.
    """

    paths = (
        "final/completion-audit.json",
        "qa/autonomous-adjudication/completion-audit.json",
    )
    documents: list[tuple[str, dict[str, Any] | None]] = []
    for relative in paths:
        path = run_root / relative
        try:
            document = json.loads(_safe_read_text(_safe_existing_file(path, run_root), run_root))
        except (OSError, ValueError, json.JSONDecodeError):
            document = None
        documents.append((relative, document if isinstance(document, dict) else None))
    valid_files = 0
    invalid_files = 0
    invalid_reasons: list[str] = []
    expected_ids = set(EXPECTED_COMPLETION_REQUIREMENT_IDS)
    expected_robot = {
        "publish_allowed": False,
        "robot_ready": 0,
        "target_mapping_bindings": 0,
        "target_mapping_rows": EXPECTED_DECISION_COUNTS["keep"],
        "target_mapping_schema_observed": EXPECTED_DECISION_COUNTS["keep"],
        "target_mapping_values_digest_observed": EXPECTED_DECISION_COUNTS["keep"],
    }
    bodies: list[dict[str, Any]] = []
    for relative, document in documents:
        if document is None:
            invalid_files += 1
            invalid_reasons.append(f"{relative}:unreadable")
            continue
        reasons: list[str] = []
        if document.get("goal_complete") is not False:
            reasons.append("goal_complete")
        if document.get("publish_allowed") is not False:
            reasons.append("publish_allowed")
        requirements = document.get("requirements")
        ids = (
            [
                item.get("id")
                for item in requirements
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
            if isinstance(requirements, list)
            else []
        )
        if (
            not isinstance(requirements, list)
            or len(requirements) != len(EXPECTED_COMPLETION_REQUIREMENT_IDS)
            or len(ids) != len(set(ids))
            or set(ids) != expected_ids
        ):
            reasons.append("requirements_shape")
        by_id = (
            {
                item.get("id"): item
                for item in requirements
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            if isinstance(requirements, list)
            else {}
        )
        for requirement_id, expected_status in EXPECTED_COMPLETION_STATUSES.items():
            item = by_id.get(requirement_id)
            if not isinstance(item, dict) or item.get("status") != expected_status:
                reasons.append(f"status:{requirement_id}")
            evidence = item.get("evidence") if isinstance(item, dict) else None
            if not isinstance(evidence, list) or any(
                not isinstance(value, str) or not value for value in evidence
            ):
                reasons.append(f"evidence:{requirement_id}")
            blockers = item.get("blockers") if isinstance(item, dict) else None
            if expected_status in {"blocked", "partial"} and (
                not isinstance(blockers, list)
                or not blockers
                or any(not _typed_blocker(value) for value in blockers)
            ):
                reasons.append(f"blockers:{requirement_id}")
            if expected_status == "complete" and blockers is not None:
                reasons.append(f"blockers:{requirement_id}")
        robot_requirement = by_id.get("robot_ready_manifest")
        robot_proof = (
            robot_requirement.get("proof") if isinstance(robot_requirement, dict) else None
        )
        if not isinstance(robot_proof, dict) or any(
            robot_proof.get(key) != value for key, value in expected_robot.items()
        ):
            reasons.append("robot_ready_manifest_proof")
        compile_requirement = by_id.get("contentdraft_v2_compile")
        compile_proof = (
            compile_requirement.get("proof") if isinstance(compile_requirement, dict) else None
        )
        current_mapping = (
            compile_proof.get("current_runtime_mapping")
            if isinstance(compile_proof, dict)
            else None
        )
        if (
            not isinstance(compile_proof, dict)
            or compile_proof.get("records") != EXPECTED_CONTENT_ROWS
            or not isinstance(current_mapping, dict)
            or current_mapping.get("exact_work_item") != 0
            or current_mapping.get("missing_work_item") != EXPECTED_DECISION_COUNTS["keep"]
        ):
            reasons.append("contentdraft_v2_compile_proof")
        body = {
            "goal_complete": document.get("goal_complete"),
            "publish_allowed": document.get("publish_allowed"),
            "requirements": requirements,
        }
        bodies.append(body)
        if canonical_digest(body) != EXPECTED_COMPLETION_BODY_DIGEST:
            reasons.append("completion_body_digest")
        if reasons:
            invalid_files += 1
            invalid_reasons.extend(f"{relative}:{reason}" for reason in reasons)
        else:
            valid_files += 1
    if len(bodies) == len(paths) and bodies[0] != bodies[1]:
        invalid_files += 1
        invalid_reasons.append("completion_receipts_diverge")
    return {
        "files": len(paths),
        "valid_files": valid_files,
        "invalid_files": invalid_files,
        "invalid_reasons": invalid_reasons,
        "valid": valid_files == len(paths) and invalid_files == 0,
    }


def verify_root_receipt(run_root: Path) -> dict[str, Any]:
    receipt_path = run_root / "review/projection-integrity-repair-receipt.json"
    proof_path = run_root / "review/verifier-mutation-proof.json"
    reasons: list[str] = []
    try:
        receipt = json.loads(_safe_read_text(_safe_existing_file(receipt_path, run_root), run_root))
        mutation = json.loads(_safe_read_text(_safe_existing_file(proof_path, run_root), run_root))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"valid": False, "reasons": ["receipt_unreadable"]}
    try:
        repository_head = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        repository_head = None
    verifier_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fixed_point = receipt.get("repository_fixed_point")
    if (
        not isinstance(fixed_point, dict)
        or fixed_point.get("head") != repository_head
        or fixed_point.get("verifier_path") != "scripts/verify_content_bundle.py"
        or fixed_point.get("verifier_sha256") != verifier_digest
    ):
        reasons.append("repository_fixed_point")
    if receipt.get("status") != "read_only_repaired_incomplete":
        reasons.append("receipt_status")
    if receipt.get("checks", {}).get("integrity_checks_pass") is not True:
        reasons.append("receipt_integrity")
    if receipt.get("canonical") != {
        "keep": EXPECTED_DECISION_COUNTS["keep"],
        "noindex": EXPECTED_DECISION_COUNTS["noindex"],
        "redirect": EXPECTED_DECISION_COUNTS["redirect"],
        "remove": EXPECTED_DECISION_COUNTS["remove"],
        "records": EXPECTED_DECISION_ROWS,
        "redirect_target_receipts": EXPECTED_DECISION_COUNTS["redirect"],
        "redirect_target_receipts_missing": 0,
    }:
        reasons.append("receipt_canonical")
    handoff = receipt.get("survivor_handoff")
    if (
        not isinstance(handoff, dict)
        or handoff.get("publish_allowed") is not False
        or handoff.get("robot_ready") != 0
    ):
        reasons.append("receipt_handoff")
    claims = receipt.get("claims")
    if not isinstance(claims, dict) or claims.get("rows") != EXPECTED_CLAIM_ROWS:
        reasons.append("receipt_claims")
    completion = receipt.get("completion_audit")
    if not isinstance(completion, dict) or completion.get("goal_complete") is not False:
        reasons.append("receipt_completion")
    safety = receipt.get("safety")
    if not isinstance(safety, dict) or any(value is not False for value in safety.values()):
        reasons.append("receipt_safety")
    mutation_ref = receipt.get("verifier_mutation_proof")
    if (
        not isinstance(mutation_ref, dict)
        or mutation_ref.get("path") != "review/verifier-mutation-proof.json"
        or mutation_ref.get("sha256") != sha256(proof_path, run_root)
        or mutation_ref.get("status") != "retained_temporary_copy_proof"
    ):
        reasons.append("mutation_reference")
    if (
        not isinstance(mutation, dict)
        or mutation.get("all_probes_failed_closed") is not True
        or mutation.get("original_bundle_status") != "pass"
        or mutation.get("verifier_commit") != repository_head
        or mutation.get("verifier_sha256") != verifier_digest
    ):
        reasons.append("mutation_proof")
    return {"valid": not reasons, "reasons": reasons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        run_root = _pin_run_root(args.bundle)
    except ValueError:
        print(
            json.dumps(
                {
                    "schema_version": "wilq_content_bundle_verification_v1",
                    "status": "fail",
                    "bundle": str(args.bundle),
                    "error": "unsafe_bundle_path",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    except OSError:
        print(
            json.dumps(
                {
                    "schema_version": "wilq_content_bundle_verification_v1",
                    "status": "fail",
                    "bundle": str(args.bundle),
                    "error": "bundle_not_found",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    manifests = {
        str(path.relative_to(run_root)): verify_projection(path, run_root)
        for path in (run_root / relative for relative in REQUIRED_PROJECTION_FILES)
    }
    sha_manifests = {
        name: verify_sha_manifest(run_root / name)
        for name in ("final", "qa", "qa/autonomous-adjudication", "target-manifest")
    }
    cta = verify_cta_refs(run_root)
    blockers = verify_blockers(run_root)
    flags = verify_flags(run_root)
    claims = verify_claim_lineage(run_root)
    counts = verify_counts(run_root)
    completion = verify_completion_state(run_root)
    root_receipt = verify_root_receipt(run_root)
    robot = load_jsonl(run_root / "final/robot-manifest-v2.jsonl", run_root)
    adjudicated = load_jsonl(
        run_root / "qa/autonomous-adjudication/adjudicated-canonical-ledger.jsonl", run_root
    )
    decision_projection = verify_decision_projection(run_root, robot, adjudicated)
    redirects = verify_redirects(run_root, robot, adjudicated)
    target_bundle = verify_target_bundle(run_root)
    mirrors = verify_mirrors(run_root)
    delivery_layout = verify_delivery_layout(run_root)
    try:
        _assert_pinned_root(run_root)
        root_identity_valid = True
    except ValueError:
        root_identity_valid = False
    integrity_ok = (
        all(value["valid"] for value in sha_manifests.values())
        and all(
            value["self_hash_missing"] == 0 and value["self_hash_mismatch"] == 0
            for value in manifests.values()
        )
        and all(value["artifact_invalid"] == 0 for value in manifests.values())
        and all(value["duplicate_urls"] == 0 for value in manifests.values())
        and all(value["invalid_safety_fields"] == 0 for value in manifests.values())
        and all(value["invalid_blockers"] == 0 for value in manifests.values())
        and cta["invalid"] == 0
        and cta["missing"] == 0
        and blockers["invalid"] == 0
        and claims["rendered_without_evidence"] == 0
        and claims["approved_without_evidence"] == 0
        and claims["approved_without_rendered"] == 0
        and claims["invalid_types"] == 0
        and claims["invalid_required_fields"] == 0
        and claims["duplicate_claim_keys"] == 0
        and claims["registry_valid"]
        and claims["unknown_evidence_ids"] == 0
        and claims["rows"] == EXPECTED_CLAIM_ROWS
        and flags["true_flags"] == 0
        and flags["invalid_paths"] == 0
        and flags["required_fields"] == sum(len(paths) for paths in REQUIRED_SAFETY_FIELDS.values())
        and counts["decisions"] == sum(counts["decision_counts"].values())
        and counts["decision_rows_match"]
        and counts["expected_rows_match"]
        and counts["decision_counts_exact"]
        and counts["expected_decision_counts_exact"]
        and counts["keep_rows_match"]
        and counts["claim_rows_match"]
        and counts["decision_projection_matches"]
        and decision_projection["expected_rows"] == decision_projection["expected"]
        and decision_projection["actual_rows"] == decision_projection["actual"]
        and decision_projection["expected_duplicates"] == 0
        and decision_projection["actual_duplicates"] == 0
        and decision_projection["invalid_expected_urls"] == 0
        and decision_projection["invalid_actual_urls"] == 0
        and decision_projection["matching"] == decision_projection["expected"]
        and decision_projection["missing"] == 0
        and decision_projection["unexpected"] == 0
        and decision_projection["disposition_mismatch"] == 0
        and set(counts["decision_counts"]) <= EXPECTED_DISPOSITIONS
        and redirects["valid"]
        and target_bundle["valid"]
        and completion["valid"]
        and root_receipt["valid"]
        and root_identity_valid
        and mirrors["keep-content-manifest.jsonl"] == mirrors["keep-content-manifest.jsonl_rows"]
        and mirrors["keep-content-manifest.jsonl_rows_match"] == 1
        and mirrors["robot-manifest-v2.jsonl"] == mirrors["robot-manifest-v2.jsonl_rows"]
        and mirrors["robot-manifest-v2.jsonl_rows_match"] == 1
        and mirrors["keep_owner_set_matches"] == 1
        and mirrors["keep_owner_set_rows"] == mirrors["keep-content-manifest.jsonl_rows"]
        and delivery_layout["valid"]
    )
    output = {
        "schema_version": "wilq_content_bundle_verification_v1",
        "status": "pass" if integrity_ok else "fail",
        "bundle": str(run_root),
        "sha_manifests": sha_manifests,
        "projections": manifests,
        "cta_refs": cta,
        "blockers": blockers,
        "claim_lineage": claims,
        "flags": flags,
        "counts": counts,
        "completion": completion,
        "root_receipt": root_receipt,
        "root_identity_valid": root_identity_valid,
        "decision_projection": decision_projection,
        "redirects": redirects,
        "target_bundle": target_bundle,
        "mirrors": mirrors,
        "delivery_layout": delivery_layout,
        "safety_scope": "read_only verifier evidence; not a historical global attestation",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if integrity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
