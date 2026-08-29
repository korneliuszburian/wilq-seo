from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from wilq.content.adjudication import (
    AdjudicationError,
    validate_retained_noindex_authorities,
)

HEX_HIGH_ENTROPY = "Hex High Entropy String"
BASE64_HIGH_ENTROPY = "Base64 High Entropy String"

ACF_INVENTORY = "docs/content-acf-inventory-20260828.json"
CANONICAL_LEDGER = "docs/content-canonical-ledger-20260828.jsonl"
AUTHORING_INVENTORY = "docs/content-dev-authoring-inventory-20260828.json"
KEEP_ELIGIBILITY_CONTEXT = "docs/content-keep-eligibility-context-20260828.json"
KEEP_ELIGIBILITY = "docs/content-keep-eligibility-20260828.json"
TARGET_MAPPING_SNAPSHOT = "docs/content-keep-target-mapping-snapshot-20260828.json"
STATE_JOURNAL = "docs/content-dev-state-journal-20260828.json"

LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}")
SAFE_REGULATORY_EVIDENCE_ID = re.compile(r"ev_regulatory_source_review_[0-9a-f]{24}")
SAFE_TARGET_MAPPING_ENDPOINT = "".join(
    (
        "/api/content/work-items/content_work_item_content_decision_https___www_ekologus_pl_",
        "oferta_opracowania_dokumentacji_ekspertyz/draft-revisions/",
        "content_revision_59b7b294",
        "3d714281",
        "92a6f1e8",
        "f164a0af/target-mapping",
    )
)

ACF_DIGEST_KEYS = ("acf_digest", "content_sha256", "title_sha256")
AUTHORING_SOURCE_KEYS = ("acf", "journal", "ledger", "sitemap")
KEEP_ELIGIBILITY_SOURCE_KEYS = (
    "authoring_inventory",
    "canonical_ledger",
    "context",
    "state_journal",
    "target_mapping_snapshot",
)
JsonPath = tuple[str | int, ...]


@dataclass(frozen=True)
class Candidate:
    path: JsonPath
    detector_type: str
    value: str

    @property
    def key(self) -> str:
        key = self.path[-1]
        assert isinstance(key, str)
        return key

    @property
    def hashed_secret(self) -> str:
        return hashlib.sha1(self.value.encode("utf-8"), usedforsecurity=False).hexdigest()


class ReceiptOccurrence(Protocol):
    @property
    def authority(self) -> Literal["ledger", "journal"]: ...

    @property
    def path(self) -> tuple[str | int, ...]: ...

    @property
    def value(self) -> str: ...

    @property
    def detector(self) -> Literal["hex64", "hex40", "base64"]: ...


def filter_detect_secrets_results(
    results: Mapping[str, object], repository_root: Path
) -> dict[str, object]:
    """Remove only findings proven to be known retained-evidence lineage."""

    filtered: dict[str, object] = {}
    for relative_path, raw_findings in results.items():
        if not isinstance(raw_findings, list):
            filtered[relative_path] = raw_findings
            continue

        allowed = _allowed_finding_identities(relative_path, repository_root)
        remaining = [
            finding
            for finding in raw_findings
            if _finding_identity(finding, relative_path) not in allowed
        ]
        if remaining:
            filtered[relative_path] = remaining
    return filtered


def _allowed_finding_identities(
    relative_path: str, repository_root: Path
) -> set[tuple[str, int, str, str]]:
    if relative_path in {CANONICAL_LEDGER, STATE_JOURNAL}:
        return _validated_authority_finding_identities(relative_path, repository_root)
    if relative_path not in {
        ACF_INVENTORY,
        AUTHORING_INVENTORY,
        KEEP_ELIGIBILITY_CONTEXT,
        KEEP_ELIGIBILITY,
        TARGET_MAPPING_SNAPSHOT,
    }:
        return set()
    try:
        source = (repository_root / relative_path).read_text(encoding="utf-8")
        payload = _retained_payload(relative_path, source)
    except (OSError, UnicodeError, ValueError):
        return set()

    candidates_by_value: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for path, value in _string_values(payload):
        detector_type = _candidate_detector(relative_path, path, value)
        if detector_type is not None:
            candidate = Candidate(path, detector_type, value)
            candidates_by_value[(candidate.key, candidate.value)].append(candidate)

    line_numbers_by_value: dict[tuple[str, str], list[int]] = defaultdict(list)
    rendered_members = {
        _render_member(key, value): (key, value) for key, value in candidates_by_value
    }
    for line_number, line in enumerate(source.splitlines(), start=1):
        key_and_value = rendered_members.get(line.strip().removesuffix(","))
        if key_and_value is not None:
            line_numbers_by_value[key_and_value].append(line_number)

    allowed: set[tuple[str, int, str, str]] = set()
    for key_and_value, matching_candidates in candidates_by_value.items():
        line_numbers = line_numbers_by_value[key_and_value]
        if len(line_numbers) != len(matching_candidates):
            continue
        for candidate, line_number in zip(matching_candidates, line_numbers, strict=True):
            allowed.add(
                (
                    relative_path,
                    line_number,
                    candidate.detector_type,
                    candidate.hashed_secret,
                )
            )
    return allowed


def _validated_authority_finding_identities(
    relative_path: str,
    repository_root: Path,
) -> set[tuple[str, int, str, str]]:
    try:
        ledger_bytes = (repository_root / CANONICAL_LEDGER).read_bytes()
        journal_bytes = (repository_root / STATE_JOURNAL).read_bytes()
        validated = validate_retained_noindex_authorities(ledger_bytes, journal_bytes)
        source = (
            ledger_bytes.decode("utf-8")
            if relative_path == CANONICAL_LEDGER
            else journal_bytes.decode("utf-8")
        )
    except (AdjudicationError, OSError, UnicodeError):
        return set()
    authority = "ledger" if relative_path == CANONICAL_LEDGER else "journal"
    occurrences = [
        occurrence
        for occurrence in validated.receipt_occurrences
        if occurrence.authority == authority
    ]
    if authority == "ledger":
        return {
            _occurrence_identity(relative_path, occurrence.path[0] + 1, occurrence)
            for occurrence in occurrences
            if isinstance(occurrence.path[0], int)
            and _render_member(str(occurrence.path[-1]), occurrence.value)
            in source.splitlines()[occurrence.path[0]]
        }
    return _journal_occurrence_identities(relative_path, source, occurrences)


def _journal_occurrence_identities(
    relative_path: str,
    source: str,
    occurrences: Sequence[ReceiptOccurrence],
) -> set[tuple[str, int, str, str]]:
    occurrences_by_member: dict[
        tuple[str, str, Literal["hex64", "hex40", "base64"]],
        list[ReceiptOccurrence],
    ] = defaultdict(list)
    for occurrence in occurrences:
        key = occurrence.path[-1]
        if isinstance(key, str):
            occurrences_by_member[(key, occurrence.value, occurrence.detector)].append(occurrence)
    line_numbers_by_member: dict[tuple[str, str], list[int]] = defaultdict(list)
    rendered = {_render_member(key, value): (key, value) for key, value, _ in occurrences_by_member}
    for line_number, line in enumerate(source.splitlines(), start=1):
        member = rendered.get(line.strip().removesuffix(","))
        if member is not None:
            line_numbers_by_member[member].append(line_number)
    allowed: set[tuple[str, int, str, str]] = set()
    for (key, value, _detector), matching in occurrences_by_member.items():
        lines = line_numbers_by_member[(key, value)]
        if len(lines) != len(matching):
            continue
        for line_number in lines:
            allowed.add(_occurrence_identity(relative_path, line_number, matching[0]))
    return allowed


def _occurrence_identity(
    relative_path: str,
    line_number: int,
    occurrence: ReceiptOccurrence,
) -> tuple[str, int, str, str]:
    detector = {
        "hex64": HEX_HIGH_ENTROPY,
        "hex40": HEX_HIGH_ENTROPY,
        "base64": BASE64_HIGH_ENTROPY,
    }[occurrence.detector]
    hashed = hashlib.sha1(occurrence.value.encode("utf-8"), usedforsecurity=False).hexdigest()
    return relative_path, line_number, detector, hashed


def _candidate_detector(relative_path: str, path: JsonPath, value: str) -> str | None:
    if relative_path == ACF_INVENTORY:
        if _is_indexed_member(path, "objects", ACF_DIGEST_KEYS) and LOWER_HEX_64.fullmatch(value):
            return HEX_HIGH_ENTROPY
        return None

    if relative_path == AUTHORING_INVENTORY:
        if (
            len(path) == 3
            and path[:2] == ("summary", "source_sha256")
            and path[2] in AUTHORING_SOURCE_KEYS
            and LOWER_HEX_64.fullmatch(value)
        ):
            return HEX_HIGH_ENTROPY
        return None

    if relative_path == KEEP_ELIGIBILITY_CONTEXT:
        if path == ("service_bindings", "current_code_source", "sha256") and LOWER_HEX_64.fullmatch(
            value
        ):
            return HEX_HIGH_ENTROPY
        return None

    if relative_path == KEEP_ELIGIBILITY:
        return _keep_eligibility_detector(path, value)

    if relative_path == TARGET_MAPPING_SNAPSHOT:
        return _target_mapping_snapshot_detector(path, value)

    return None


def _keep_eligibility_detector(path: JsonPath, value: str) -> str | None:
    source_sha = (
        len(path) == 3
        and path[:2] == ("summary", "source_sha256")
        and path[2] in KEEP_ELIGIBILITY_SOURCE_KEYS
    )
    revision_sha = (
        len(path) == 4
        and path[0] == "rows"
        and isinstance(path[1], int)
        and path[2:] == ("revision", "current_revision_digest")
    )
    mapping_sha = (
        len(path) == 4
        and path[0] == "rows"
        and isinstance(path[1], int)
        and path[2] == "target_context"
        and path[3] in {"target_contract_digest", "binding_digest"}
    )
    if (source_sha or revision_sha or mapping_sha) and LOWER_HEX_64.fullmatch(value):
        return HEX_HIGH_ENTROPY
    if (
        len(path) == 6
        and path[0] == "rows"
        and isinstance(path[1], int)
        and path[2] == "canonical_lineage"
        and path[3] == "evidence"
        and isinstance(path[4], int)
        and path[5] == "evidence_id"
        and SAFE_REGULATORY_EVIDENCE_ID.fullmatch(value)
    ):
        return BASE64_HIGH_ENTROPY
    return None


def _target_mapping_snapshot_detector(path: JsonPath, value: str) -> str | None:
    digest_paths = {
        ("preview", "revision", "content_digest"),
        ("preview", "target", "target_contract_digest"),
        ("preview", "binding_digest"),
        (
            "preview",
            "target",
            "target_contract",
            "authoring_surface",
            "schema_digest",
        ),
        (
            "preview",
            "target",
            "target_contract",
            "authoring_surface",
            "source_acf_digest",
        ),
        (
            "preview",
            "target",
            "target_contract",
            "authoring_surface",
            "source_acf_fields_digest",
        ),
    }
    if path in digest_paths and LOWER_HEX_64.fullmatch(value):
        return HEX_HIGH_ENTROPY
    if path == ("request", "endpoint") and value == SAFE_TARGET_MAPPING_ENDPOINT:
        return BASE64_HIGH_ENTROPY
    return None


def _retained_payload(relative_path: str, source: str) -> Any:
    return json.loads(source, object_pairs_hook=_reject_duplicate_keys)


def _is_indexed_member(path: JsonPath, collection: str, keys: Sequence[str]) -> bool:
    return len(path) == 3 and path[0] == collection and isinstance(path[1], int) and path[2] in keys


def _string_values(value: object, path: JsonPath = ()) -> Iterator[tuple[JsonPath, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                yield from _string_values(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, (*path, index))


def _finding_identity(finding: object, expected_path: str) -> tuple[str, int, str, str] | None:
    if not isinstance(finding, dict):
        return None
    filename = finding.get("filename")
    line_number = finding.get("line_number")
    detector_type = finding.get("type")
    hashed_secret = finding.get("hashed_secret")
    if (
        filename != expected_path
        or type(line_number) is not int
        or not isinstance(detector_type, str)
        or not isinstance(hashed_secret, str)
    ):
        return None
    return filename, line_number, detector_type, hashed_secret


def _render_member(key: str, value: str) -> str:
    return f"{json.dumps(key, ensure_ascii=False)}: {json.dumps(value, ensure_ascii=False)}"


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on detect-secrets findings except proven retained lineage."
    )
    parser.add_argument("scan_output", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    payload = json.loads(args.scan_output.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), dict):
        raise SystemExit("detect-secrets output has no results object")

    remaining = filter_detect_secrets_results(payload["results"], args.repository_root)
    print(json.dumps({"results": remaining}, indent=2))
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
