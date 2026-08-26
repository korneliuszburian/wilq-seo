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
import stat
from collections import Counter
from pathlib import Path
from typing import Any

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
    root = run_root.resolve()
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
    return _safe_existing_file(path, run_root).read_text(encoding="utf-8")


def sha256(path: Path, run_root: Path | None = None) -> str:
    safe_path = _safe_existing_file(path, run_root) if run_root is not None else path
    return hashlib.sha256(safe_path.read_bytes()).hexdigest()


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
        }
    self_hash_valid = 0
    self_hash_missing = 0
    self_hash_mismatch = 0
    artifact_checked = 0
    artifact_invalid = 0
    for row in rows:
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
            path.name in {"content-manifest.jsonl", "target-manifest.jsonl"}
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
        base = path.parent / str(row["artifact_base"])
        artifact_documents: dict[str, dict[str, Any]] = {}
        rendered_stems: list[str] = []
        for kind, ref in refs.items():
            artifact_checked += 1
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                artifact_invalid += 1
                continue
            try:
                target = _safe_existing_file(base / ref["path"], run_root)
                valid = ref.get("bytes") == os.stat(target).st_size and ref.get("sha256") == sha256(
                    target, run_root
                )
                if kind == "rendered":
                    rendered_stems.append(target.stem)
                elif kind in {"revision", "source_pack"}:
                    document = json.loads(_safe_read_text(target, run_root))
                    artifact_documents[kind] = document
                    valid = valid and document.get("url") == row.get("url")
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
        try:
            target = (
                _safe_existing_file(owner.parent / base / str(ref.get("path", "")), run_root)
                if isinstance(base, str)
                else None
            )
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
    expected = {row.get("url"): row.get("final_disposition") for row in adjudicated}
    actual = {row.get("url"): row.get("final_disposition") for row in robot}
    return {
        "expected": len(expected),
        "actual": len(actual),
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


def verify_target_bundle(run_root: Path) -> dict[str, int | bool]:
    target_dir = run_root / "target-manifest"
    targets = load_jsonl(target_dir / "target-manifest.jsonl", run_root)
    bundles = load_jsonl(target_dir / "robot-bundle-manifest.jsonl", run_root)
    by_url = {row.get("url"): row for row in targets}
    selectors = 0
    revisions = 0
    claim_pointers = 0
    for row in bundles:
        target = by_url.get(row.get("url"))
        target_ref = row.get("target_ref") or {}
        selector = target_ref.get("selector") or {}
        if (
            target_ref.get("path") == "target-manifest.jsonl"
            and selector.get("url") == row.get("url")
            and target is not None
            and target.get("slug") == row.get("slug")
        ):
            selectors += 1
        revision_ref = row.get("revision_ref") or {}
        try:
            revision_path = _safe_existing_file(
                target_dir / str(revision_ref.get("path", "")), run_root
            )
            revision_valid = revision_ref.get("content_digest") == sha256(revision_path, run_root)
        except (OSError, ValueError):
            revision_path = None
            revision_valid = False
        if revision_valid:
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
                if target is not None:
                    revision_valid = revision_valid and revision.get("revision_id") == target.get(
                        "revision_id"
                    )
            if revision_valid:
                revisions += 1
        else:
            revision = None
        audit_ref = row.get("audit_ref") or {}
        try:
            audit_path = _safe_existing_file(target_dir / str(audit_ref.get("path", "")), run_root)
        except (OSError, ValueError):
            audit_path = None
        if (
            audit_path == revision_path
            and audit_path is not None
            and audit_ref.get("json_pointer") == "/claim_ledger"
        ):
            if not isinstance(revision, dict):
                revision = json.loads(_safe_read_text(audit_path, run_root))
            if (
                audit_ref.get("claim_ledger_digest")
                == canonical_digest(revision.get("claim_ledger", []))
                and revision.get("url") == row.get("url")
                and revision.get("slug") == row.get("slug")
            ):
                claim_pointers += 1
    valid = (
        len(targets) == len(by_url) == len(bundles)
        and selectors == len(bundles)
        and revisions == len(bundles)
        and claim_pointers == len(bundles)
    )
    return {
        "targets": len(targets),
        "bundles": len(bundles),
        "selectors": selectors,
        "revision_refs": revisions,
        "claim_pointers": claim_pointers,
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
            comparable(a) == comparable(b) for a, b in zip(final, mirror, strict=True)
        )
        result[f"{name}_rows"] = len(final)
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
        stack: list[object] = list(documents)
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                true_flags += sum(value.get(key) is True for key in SAFETY_KEYS)
                stack.extend(item for item in value.values() if isinstance(item, (dict, list)))
            elif isinstance(value, list):
                stack.extend(value)
    return {
        "true_flags": true_flags,
        "invalid_paths": invalid_paths,
        "required_fields": required_fields,
    }


def verify_delivery_layout(run_root: Path) -> dict[str, Any]:
    forbidden: list[str] = []
    for path in run_root.rglob("*"):
        relative = path.relative_to(run_root).as_posix()
        if path.is_file() and (
            path.name.startswith("sol-raw")
            or path.name.startswith("raw-trace")
            or path.name.startswith("model-trace")
        ):
            forbidden.append(relative)
        if path.name in {"batch-inputs", "batch_inputs"}:
            forbidden.append(relative)
    return {"forbidden_paths": sorted(set(forbidden)), "valid": not forbidden}


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
    return {
        "decisions": len(robot),
        "decision_counts": dict(counts),
        "expected_decisions": len(adjudicated),
        "expected_decision_counts": dict(expected_dispositions),
        "decision_projection_matches": dict(counts) == dict(expected_dispositions)
        and {row.get("url") for row in robot} == {row.get("url") for row in adjudicated},
        "keep": len(keep),
        "claims": len(claims),
        "rendered_claims": sum(row.get("rendered") is True for row in claims),
        "approved_claims": sum(row.get("approved_for_rendering") is True for row in claims),
        "claims_without_evidence": sum(not row.get("evidence_ids") for row in claims),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if _has_symlink_component(args.bundle):
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
    try:
        run_root = args.bundle.resolve(strict=True)
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
    counts = verify_counts(run_root)
    robot = load_jsonl(run_root / "final/robot-manifest-v2.jsonl", run_root)
    adjudicated = load_jsonl(
        run_root / "qa/autonomous-adjudication/adjudicated-canonical-ledger.jsonl", run_root
    )
    decision_projection = verify_decision_projection(run_root, robot, adjudicated)
    redirects = verify_redirects(run_root, robot, adjudicated)
    target_bundle = verify_target_bundle(run_root)
    mirrors = verify_mirrors(run_root)
    delivery_layout = verify_delivery_layout(run_root)
    integrity_ok = (
        all(value["valid"] for value in sha_manifests.values())
        and all(
            value["self_hash_missing"] == 0 and value["self_hash_mismatch"] == 0
            for value in manifests.values()
        )
        and all(value["artifact_invalid"] == 0 for value in manifests.values())
        and cta["invalid"] == 0
        and cta["missing"] == 0
        and blockers["invalid"] == 0
        and flags["true_flags"] == 0
        and flags["invalid_paths"] == 0
        and flags["required_fields"] == sum(len(paths) for paths in REQUIRED_SAFETY_FIELDS.values())
        and counts["decisions"] == sum(counts["decision_counts"].values())
        and counts["decision_projection_matches"]
        and decision_projection["matching"] == decision_projection["expected"]
        and decision_projection["missing"] == 0
        and decision_projection["unexpected"] == 0
        and decision_projection["disposition_mismatch"] == 0
        and set(counts["decision_counts"]) <= EXPECTED_DISPOSITIONS
        and redirects["valid"]
        and target_bundle["valid"]
        and mirrors["keep-content-manifest.jsonl"] == mirrors["keep-content-manifest.jsonl_rows"]
        and mirrors["robot-manifest-v2.jsonl"] == mirrors["robot-manifest-v2.jsonl_rows"]
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
        "flags": flags,
        "counts": counts,
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
