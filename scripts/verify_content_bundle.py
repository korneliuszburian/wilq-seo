"""Read-only integrity gate for a generated WILQ content bundle.

The bundle itself is an ignored run artifact.  This verifier is deliberately
tracked so a future run can be checked without trusting a run-local receipt
generator.  It never opens credentials, starts services, or writes files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
SAFETY_KEYS = {
    "action_apply",
    "actionobject_apply",
    "apply_allowed",
    "connector_refresh",
    "deployment",
    "env_read",
    "generation_invoked",
    "live_mutation",
    "live_refresh",
    "model_generation",
    "model_invocation",
    "private_packet_read",
    "publish_allowed",
    "publish_ready",
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify_sha_manifest(root: Path) -> dict[str, Any]:
    manifest = root / "SHA256SUMS"
    errors: list[str] = []
    expected: set[str] = set()
    if not manifest.is_file():
        return {"entries": 0, "valid": False, "errors": ["missing_SHA256SUMS"]}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            expected_sha, relative = line.split(None, 1)
        except ValueError:
            errors.append("malformed_SHA256SUMS_line")
            continue
        relative = relative.removeprefix("./")
        expected.add(relative)
        path = root / relative
        if not path.is_file() or sha256(path) != expected_sha:
            errors.append(relative)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS" and "__pycache__" not in path.parts
    }
    errors.extend(sorted(actual - expected))
    return {"entries": len(expected), "valid": not errors and expected == actual, "errors": errors}


def verify_projection(path: Path, run_root: Path) -> dict[str, int]:
    rows = load_jsonl(path)
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
        base = (path.parent / str(row["artifact_base"])).resolve()
        for ref in refs.values():
            artifact_checked += 1
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                artifact_invalid += 1
                continue
            target = (base / ref["path"]).resolve()
            if (
                target != run_root
                and run_root not in target.parents
                or not target.is_file()
                or ref.get("bytes") != target.stat().st_size
                or ref.get("sha256") != sha256(target)
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
            if (
                not path.is_file()
                or path.name == "SHA256SUMS"
                or "__pycache__" in path.parts
                or path.suffix not in {".json", ".jsonl"}
            ):
                continue
            try:
                documents = (
                    load_jsonl(path)
                    if path.suffix == ".jsonl"
                    else [json.loads(path.read_text(encoding="utf-8"))]
                )
            except (OSError, json.JSONDecodeError):
                invalid += 1
                continue

            def visit(value: object, ancestors: tuple[str, ...] = ()) -> None:
                nonlocal arrays, entries, invalid
                if isinstance(value, dict):
                    for key, child in value.items():
                        collection = isinstance(child, list) and (
                            key == "blockers" or key.endswith("_blockers")
                        )
                        singular = key == "blocker" and "claim_ledger" in ancestors
                        if collection:
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
    expected = sha256(cta) if cta.is_file() else None
    checked = missing = invalid = 0
    documents: list[tuple[Path, dict[str, Any]]] = [
        (run_root / "final/content-manifest.jsonl", row)
        for row in load_jsonl(run_root / "final/content-manifest.jsonl")
    ]
    documents.extend(
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((run_root / "final/source-packs").glob("*.json"))
    )
    for owner, document in documents:
        ref = document.get("cta_candidate_ref")
        if not isinstance(ref, dict):
            missing += 1
            continue
        checked += 1
        base = ref.get("path_base")
        target = (
            (owner.parent / base / str(ref.get("path", ""))).resolve()
            if isinstance(base, str)
            else None
        )
        if expected is None or target != cta.resolve() or ref.get("sha256") != expected:
            invalid += 1
    return {
        "expected": checked + missing,
        "checked": checked,
        "valid": checked - invalid,
        "missing": missing,
        "invalid": invalid,
    }


def verify_flags(run_root: Path) -> dict[str, int]:
    true_flags = 0
    files = [
        root for name in ("final", "qa", "target-manifest") for root in (run_root / name).rglob("*")
    ]
    for path in files:
        if (
            not path.is_file()
            or path.suffix not in {".json", ".jsonl"}
            or path.name == "SHA256SUMS"
        ):
            continue
        try:
            documents = (
                load_jsonl(path)
                if path.suffix == ".jsonl"
                else [json.loads(path.read_text(encoding="utf-8"))]
            )
        except (OSError, json.JSONDecodeError):
            continue
        stack: list[object] = list(documents)
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                true_flags += sum(value.get(key) is True for key in SAFETY_KEYS)
                stack.extend(item for item in value.values() if isinstance(item, (dict, list)))
            elif isinstance(value, list):
                stack.extend(value)
    return {"true_flags": true_flags}


def verify_counts(run_root: Path) -> dict[str, Any]:
    robot = load_jsonl(run_root / "final/robot-manifest-v2.jsonl")
    keep = load_jsonl(run_root / "final/keep-content-manifest.jsonl")
    claims = load_jsonl(run_root / "qa/autonomous-adjudication/adjudicated-claim-lineage.jsonl")
    counts = Counter(row.get("final_disposition") for row in robot)
    return {
        "decisions": len(robot),
        "decision_counts": dict(counts),
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
    run_root = args.bundle.resolve()
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
        and counts["decisions"] == sum(counts["decision_counts"].values())
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
        "safety_scope": "read_only verifier evidence; not a historical global attestation",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if integrity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
