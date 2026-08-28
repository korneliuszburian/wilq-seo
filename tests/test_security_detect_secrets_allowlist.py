from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.filter_detect_secrets import (
    ACF_INVENTORY,
    AUTHORING_INVENTORY,
    BASE64_HIGH_ENTROPY,
    HEX_HIGH_ENTROPY,
    STATE_JOURNAL,
    filter_detect_secrets_results,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_STORE_FIXTURE = REPO_ROOT / "tests/actions/test_audit_store_contracts.py"
KNOWLEDGE_SOURCE_MATERIALS = REPO_ROOT / "wilq/content/knowledge/source_materials.py"
KNOWLEDGE_SURFACE_FIXTURE = REPO_ROOT / "apps/dashboard/src/routes/KnowledgeSurface.test.tsx"
SECURITY_SCRIPT = REPO_ROOT / "scripts/security.sh"
RETAINED_EVIDENCE_PATHS = (
    ACF_INVENTORY,
    "docs/content-canonical-ledger-20260828.jsonl",
    AUTHORING_INVENTORY,
    STATE_JOURNAL,
    "docs/content-sitemap-inventory-20260828.json",
)


def _detect_secret_results(path: Path) -> dict[str, object]:
    if path.is_relative_to(REPO_ROOT):
        cwd = REPO_ROOT
        scan_target = str(path.relative_to(REPO_ROOT))
    else:
        cwd = path.parent
        scan_target = path.name
    completed = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", scan_target],
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    results = payload.get("results")
    assert isinstance(results, dict)
    return results


def _detect_secret_results_from(working_directory: Path, *scan_targets: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", *scan_targets],
        check=True,
        cwd=working_directory,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    results = payload.get("results")
    assert isinstance(results, dict)
    return results


def _detect_secrets_exclude() -> re.Pattern[str]:
    script = SECURITY_SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"^  detect_secrets_exclude='([^']+)'$", script, re.MULTILINE)
    assert match is not None
    return re.compile(match.group(1))


def _write_json(repository_root: Path, relative_path: str, payload: object) -> str:
    path = repository_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    source = json.dumps(payload, indent=2) + "\n"
    path.write_text(source, encoding="utf-8")
    return source


def _finding(
    relative_path: str,
    source: str,
    key: str,
    value: str,
    detector_type: str = HEX_HIGH_ENTROPY,
) -> dict[str, object]:
    rendered_member = f"{json.dumps(key)}: {json.dumps(value)}"
    matching_lines = [
        line_number
        for line_number, line in enumerate(source.splitlines(), start=1)
        if line.strip().removesuffix(",") == rendered_member
    ]
    assert len(matching_lines) == 1
    return {
        "type": detector_type,
        "filename": relative_path,
        "hashed_secret": hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest(),
        "is_verified": False,
        "line_number": matching_lines[0],
    }


def _sha256(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _valid_acf_inventory_findings(repository_root: Path) -> list[dict[str, object]]:
    values = {
        key: _sha256(f"acf-{key}")
        for key in (
            "acf_digest",
            "content_sha256",
            "title_sha256",
        )
    }
    source = _write_json(repository_root, ACF_INVENTORY, {"objects": [values]})
    return [_finding(ACF_INVENTORY, source, key, value) for key, value in values.items()]


def _valid_authoring_inventory_findings(repository_root: Path) -> list[dict[str, object]]:
    values = {key: _sha256(f"authoring-{key}") for key in ("acf", "journal", "ledger", "sitemap")}
    source = _write_json(
        repository_root,
        AUTHORING_INVENTORY,
        {"summary": {"source_sha256": values}},
    )
    return [_finding(AUTHORING_INVENTORY, source, key, value) for key, value in values.items()]


def _valid_state_journal_findings(repository_root: Path) -> list[dict[str, object]]:
    values = {
        "readback_content_digest": _sha256("journal-readback"),
        "revision_digest": _sha256("journal-revision"),
        "content_digest": _sha256("journal-content"),
        "draft_package_digest": _sha256("journal-package"),
        "planning_digest": _sha256("journal-planning"),
        "head": _sha256("journal-head")[:40],
        "origin_main": _sha256("journal-origin-main")[:40],
        "sha256": _sha256("journal-source"),
        "summary_sha256": _sha256("journal-summary"),
        "current_revision_digest": _sha256("journal-current-revision"),
    }
    ledger_digest = _sha256("journal-ledger")
    mutation_id = "mutation_act_apply_wordpress_draft_handoff_" + _sha256("mutation-id")[:12]
    source = _write_json(
        repository_root,
        STATE_JOURNAL,
        {
            "drafts": [
                {
                    "readback_content_digest": values["readback_content_digest"],
                    "revision_digest": values["revision_digest"],
                }
            ],
            "mutation_audits": [
                {
                    "id": mutation_id,
                    "binding": {
                        key: values[key]
                        for key in (
                            "content_digest",
                            "draft_package_digest",
                            "planning_digest",
                        )
                    },
                }
            ],
            "repository": {
                "head": values["head"],
                "origin_main": values["origin_main"],
            },
            "sources": {
                "public_acf_inventory": {"sha256": values["sha256"]},
                "canonical_ledger": {
                    "sha256": ledger_digest,
                    "summary_sha256": values["summary_sha256"],
                },
            },
            "urls": [{"current_revision_digest": values["current_revision_digest"]}],
        },
    )
    return [
        *[_finding(STATE_JOURNAL, source, key, value) for key, value in values.items()],
        _finding(STATE_JOURNAL, source, "sha256", ledger_digest),
        _finding(
            STATE_JOURNAL,
            source,
            "id",
            mutation_id,
            BASE64_HIGH_ENTROPY,
        ),
    ]


def test_audit_redaction_fixture_is_allowlisted_only_on_its_test_line() -> None:
    assert _detect_secret_results(AUDIT_STORE_FIXTURE) == {}


def test_public_material_digest_prefixes_are_allowlisted_at_their_literals() -> None:
    assert _detect_secret_results(KNOWLEDGE_SOURCE_MATERIALS) == {}
    assert _detect_secret_results(KNOWLEDGE_SURFACE_FIXTURE) == {}


def test_detect_secrets_still_flags_the_same_unallowlisted_field_in_another_file(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "unallowlisted_fixture.py"
    field_name = "mapping_" + "secret"
    candidate.write_text(f'fixture = {{"{field_name}": "hide"}}\n')

    assert any(
        isinstance(finding, dict) and finding.get("type") == "Secret Keyword"
        for findings in _detect_secret_results(candidate).values()
        if isinstance(findings, list)
        for finding in findings
    )


def test_security_script_keeps_all_retained_evidence_in_full_repository_scan_scope() -> None:
    script = SECURITY_SCRIPT.read_text()
    exclude = _detect_secrets_exclude()

    assert "python -m detect_secrets scan ." in script
    assert "python scripts/filter_detect_secrets.py" in script
    assert "test_audit_store_contracts.py" not in script
    assert not any(exclude.search(path) for path in RETAINED_EVIDENCE_PATHS)
    assert not any(exclude.search(f"./{path}") for path in RETAINED_EVIDENCE_PATHS)


def test_semantic_filter_suppresses_only_valid_digest_schema_locations(
    tmp_path: Path,
) -> None:
    results: dict[str, object] = {
        ACF_INVENTORY: _valid_acf_inventory_findings(tmp_path),
        AUTHORING_INVENTORY: _valid_authoring_inventory_findings(tmp_path),
        STATE_JOURNAL: _valid_state_journal_findings(tmp_path),
    }

    assert filter_detect_secrets_results(results, tmp_path) == {}


def test_path_type_key_value_and_schema_mismatches_remain(tmp_path: Path) -> None:
    valid_digest = _sha256("valid-acf-digest")
    mismatches: list[tuple[str, dict[str, object]]] = []

    path_root = tmp_path / "path"
    wrong_path = "docs/content-acf-inventory-20260828-copy.json"
    source = _write_json(path_root, wrong_path, {"objects": [{"acf_digest": valid_digest}]})
    mismatches.append(
        ("path", {wrong_path: [_finding(wrong_path, source, "acf_digest", valid_digest)]})
    )

    type_root = tmp_path / "type"
    source = _write_json(type_root, ACF_INVENTORY, {"objects": [{"acf_digest": valid_digest}]})
    mismatches.append(
        (
            "type",
            {
                ACF_INVENTORY: [
                    _finding(
                        ACF_INVENTORY,
                        source,
                        "acf_digest",
                        valid_digest,
                        BASE64_HIGH_ENTROPY,
                    )
                ]
            },
        )
    )

    key_root = tmp_path / "key"
    source = _write_json(
        key_root, ACF_INVENTORY, {"objects": [{"unexpected_digest": valid_digest}]}
    )
    mismatches.append(
        (
            "key",
            {ACF_INVENTORY: [_finding(ACF_INVENTORY, source, "unexpected_digest", valid_digest)]},
        )
    )

    value_root = tmp_path / "value"
    uppercase_digest = valid_digest.upper()
    source = _write_json(value_root, ACF_INVENTORY, {"objects": [{"acf_digest": uppercase_digest}]})
    mismatches.append(
        (
            "value",
            {ACF_INVENTORY: [_finding(ACF_INVENTORY, source, "acf_digest", uppercase_digest)]},
        )
    )

    schema_root = tmp_path / "schema"
    source = _write_json(schema_root, ACF_INVENTORY, {"metadata": {"acf_digest": valid_digest}})
    mismatches.append(
        ("schema", {ACF_INVENTORY: [_finding(ACF_INVENTORY, source, "acf_digest", valid_digest)]})
    )

    roots = {
        "path": path_root,
        "type": type_root,
        "key": key_root,
        "value": value_root,
        "schema": schema_root,
    }
    for name, results in mismatches:
        assert filter_detect_secrets_results(results, roots[name]) == results


def test_decoy_secret_under_exact_retained_filename_remains_reported(
    tmp_path: Path,
) -> None:
    digest = _sha256("scanner-visible-retained-digest")
    field_name = "mapping_" + "secret"
    _write_json(
        tmp_path,
        ACF_INVENTORY,
        {"objects": [{"acf_digest": digest, field_name: "hide"}]},
    )

    results = _detect_secret_results_from(tmp_path, ACF_INVENTORY)
    findings = results.get(ACF_INVENTORY)
    assert isinstance(findings, list)
    assert any(finding.get("type") == HEX_HIGH_ENTROPY for finding in findings)
    assert any(finding.get("type") == "Secret Keyword" for finding in findings)

    remaining = filter_detect_secrets_results(results, tmp_path)

    assert all(finding.get("type") != HEX_HIGH_ENTROPY for finding in remaining[ACF_INVENTORY])
    assert any(finding.get("type") == "Secret Keyword" for finding in remaining[ACF_INVENTORY])


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/content-canonical-ledger-20260828.jsonl",
        "docs/content-sitemap-inventory-20260828.json",
    ),
)
def test_zero_finding_evidence_files_have_no_suppression_rule(
    tmp_path: Path, relative_path: str
) -> None:
    finding = {
        "type": HEX_HIGH_ENTROPY,
        "filename": relative_path,
        "hashed_secret": _sha256("unapproved-finding")[:40],
        "line_number": 1,
    }
    results: dict[str, object] = {relative_path: [finding]}

    assert filter_detect_secrets_results(results, tmp_path) == results
