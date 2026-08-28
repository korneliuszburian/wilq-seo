from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import SplitResult, urlsplit

OUTPUT_SCHEMA_VERSION = "dev_authoring_inventory_v1"
SITEMAP_SCHEMA_VERSION = "public_sitemap_inventory_v1"
ACF_SCHEMA_VERSION = "public_wordpress_acf_inventory_v1"
JOURNAL_SCHEMA_VERSION = "dev_content_state_journal_v1"
LEDGER_SCHEMA_VERSION = "content_canonical_ledger_row_v1"

DEV_SCHEME = "https"
DEV_NETLOC = "ekologus.dev.proudsite.pl"
SOURCE_KEYS = ("sitemap", "acf", "journal", "ledger")
VALID_DISPOSITIONS = frozenset({"keep", "noindex", "redirect", "remove"})
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
ENDPOINT_POST_TYPES = {"pages": "page", "posts": "post", "uslugi": "uslugi"}
JOURNAL_SAFETY_FLAGS = {
    "delete_performed": False,
    "deployment_performed": False,
    "env_values_read": False,
    "generation_performed": False,
    "new_generation_allowed": False,
    "private_packet_read": False,
    "read_only_run": True,
    "vendor_write_performed": False,
}
ROW_SAFETY_FLAGS = {
    "publish_allowed": False,
    "write_authorized": False,
    "robot_ready": False,
}
class InventoryBuildError(RuntimeError):
    """Raised when an input cannot support the read-only projection."""


@dataclass(frozen=True)
class SourceProvenance:
    source_ref: str
    sha256: str


@dataclass(frozen=True)
class ProjectionExpectations:
    target_count: int = 214
    rest_object_count: int = 175
    endpoint_counts: tuple[tuple[str, int], ...] = (
        ("pages", 8),
        ("posts", 115),
        ("uslugi", 52),
    )
    authoring_counts: tuple[tuple[str, int], ...] = (
        ("acf_flexible_content", 58),
        ("acf_flexible_content_empty", 1),
        ("the_content", 116),
    )
    keep_count: int = 57
    keep_rest_object_count: int = 57

    @property
    def rest_object_not_observed_count(self) -> int:
        return self.target_count - self.rest_object_count


PRODUCTION_EXPECTATIONS = ProjectionExpectations()


def build_dev_authoring_inventory(
    sitemap: Mapping[str, Any],
    acf: Mapping[str, Any],
    journal: Mapping[str, Any],
    ledger: Sequence[Mapping[str, Any]],
    *,
    provenance: Mapping[str, SourceProvenance],
    expectations: ProjectionExpectations = PRODUCTION_EXPECTATIONS,
) -> dict[str, Any]:
    """Build a deterministic projection from four verified offline snapshots."""

    _validate_provenance(provenance)
    sitemap_rows, sitemap_generated_at = _validated_sitemap(sitemap, expectations)
    acf_rows, acf_generated_at = _validated_acf(acf, sitemap_rows, expectations)
    journal_rows, journal_generated_at = _validated_journal(
        journal, sitemap_rows, expectations
    )
    _validate_ledger(ledger, sitemap_rows, journal_rows)
    rows = _project_rows(sitemap_rows, acf_rows, journal_rows)
    summary = _projection_summary(
        rows,
        provenance,
        {
            "sitemap": sitemap_generated_at,
            "acf": acf_generated_at,
            "journal": journal_generated_at,
        },
        expectations,
    )
    result = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "inventory_role": "authoring_target",
        "read_only": True,
        "source_refetch_performed": False,
        "generation_performed": False,
        "raw_body_retained": False,
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
        "summary": summary,
        "rows": rows,
    }
    return result


def _project_rows(
    sitemap_rows: Mapping[str, list[str]],
    acf_rows: Mapping[str, Mapping[str, Any]],
    journal_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sitemap_rows):
        journal_row = journal_rows[path]
        row = {
            "inventory_role": "authoring_target",
            "sitemap_observed": True,
            "dev_sitemaps": list(sitemap_rows[path]),
            "path": path,
            "dev_url": journal_row["url"],
            "final_disposition": journal_row["final_disposition"],
            "delivery_status": journal_row["delivery_status"],
            "publish_allowed": False,
            "write_authorized": False,
            "robot_ready": False,
            "new_generation_allowed": False,
        }
        row.update(
            _rest_object_projection(acf_rows[path])
            if path in acf_rows
            else _non_object_projection()
        )
        rows.append(row)
    return rows


def _projection_summary(
    rows: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, SourceProvenance],
    generated_at: Mapping[str, str],
    expectations: ProjectionExpectations,
) -> dict[str, Any]:
    observed = [row for row in rows if row["rest_object_observed"]]
    endpoint_counts = _sorted_counter(row["endpoint"] for row in observed)
    authoring_counts = _sorted_counter(row["authoring_mode"] for row in observed)
    keep_count = sum(row["final_disposition"] == "keep" for row in rows)
    keep_observed = sum(
        row["final_disposition"] == "keep" and row["rest_object_observed"]
        for row in rows
    )
    _require_equal("derived target count", len(rows), expectations.target_count)
    _require_equal("derived REST object count", len(observed), expectations.rest_object_count)
    _require_equal(
        "derived endpoint counts", endpoint_counts, dict(expectations.endpoint_counts)
    )
    _require_equal(
        "derived authoring counts", authoring_counts, dict(expectations.authoring_counts)
    )
    _require_equal("derived keep count", keep_count, expectations.keep_count)
    _require_equal(
        "derived keep REST-observed count",
        keep_observed,
        expectations.keep_rest_object_count,
    )
    return {
        "target_count": len(rows),
        "rest_object_observed_count": len(observed),
        "rest_object_not_observed_count": len(rows) - len(observed),
        "endpoint_counts": endpoint_counts,
        "authoring_counts": authoring_counts,
        "keep_count": keep_count,
        "keep_rest_object_observed_count": keep_observed,
        "input_schema_versions": {
            "sitemap": SITEMAP_SCHEMA_VERSION,
            "acf": ACF_SCHEMA_VERSION,
            "journal": JOURNAL_SCHEMA_VERSION,
            "ledger": LEDGER_SCHEMA_VERSION,
        },
        "input_generated_at": dict(generated_at),
        "source_refs": {key: provenance[key].source_ref for key in SOURCE_KEYS},
        "source_sha256": {key: provenance[key].sha256 for key in SOURCE_KEYS},
    }


def render_inventory(payload: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        )
    except (TypeError, ValueError) as error:
        raise InventoryBuildError("Output is not canonical JSON data.") from error
    return (text + "\n").encode("utf-8")


def main(
    argv: Sequence[str] | None = None,
    *,
    expectations: ProjectionExpectations = PRODUCTION_EXPECTATIONS,
) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        loaded, provenance, input_paths = _load_cli_sources(args)
        output_path = Path(args.output)
        _assert_output_path_is_separate(output_path, input_paths)
        result = build_dev_authoring_inventory(
            loaded["sitemap"],
            loaded["acf"],
            loaded["journal"],
            loaded["ledger"],
            provenance=provenance,
            expectations=expectations,
        )
        rendered = render_inventory(result)
        if args.check:
            if output_path.read_bytes() != rendered:
                raise InventoryBuildError(
                    "Output artifact differs from the deterministic projection."
                )
            print("Inwentarz dev_authoring_inventory jest aktualny.")
        else:
            output_path.write_bytes(rendered)
            print("Zapisano inwentarz dev_authoring_inventory.")
    except InventoryBuildError as error:
        print(f"Błąd inwentarza dev_authoring_inventory: {error}", file=sys.stderr)
        return 1
    except OSError:
        print(
            "Błąd inwentarza dev_authoring_inventory: operacja plikowa nie powiodła się.",
            file=sys.stderr,
        )
        return 1
    return 0


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Buduje wyłącznie offline read-only dev_authoring_inventory."
    )
    for key in SOURCE_KEYS:
        parser.add_argument(f"--{key}", required=True)
        parser.add_argument(f"--{key}-sha256", required=True)
        parser.add_argument(f"--{key}-ref", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Porównuje wynik bajt w bajt bez tworzenia ani przepisywania pliku.",
    )
    return parser


def _load_cli_sources(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, SourceProvenance], list[Path]]:
    loaded: dict[str, Any] = {}
    provenance: dict[str, SourceProvenance] = {}
    paths = []
    for key in SOURCE_KEYS:
        path = Path(getattr(args, key))
        source_ref = getattr(args, f"{key}_ref")
        _validate_source_ref(source_ref)
        raw_bytes, digest = _read_verified_bytes(
            path,
            expected_sha256=getattr(args, f"{key}_sha256"),
            source_ref=source_ref,
        )
        loaded[key] = (
            _parse_json_lines(raw_bytes, source_ref=source_ref)
            if key == "ledger"
            else _parse_json_document(raw_bytes, source_ref=source_ref)
        )
        provenance[key] = SourceProvenance(source_ref, digest)
        paths.append(path)
    return loaded, provenance, paths


def _validated_sitemap(
    sitemap: Mapping[str, Any], expectations: ProjectionExpectations
) -> tuple[dict[str, list[str]], str]:
    _require_schema(sitemap, SITEMAP_SCHEMA_VERSION, "sitemap")
    _require_exact_bool(sitemap, "read_only", True, "sitemap")
    generated_at = _required_string(sitemap, "generated_at", "sitemap")
    targets: dict[str, list[str]] = {}
    seen_paths: set[str] = set()
    for index, raw_row in enumerate(_required_list(sitemap, "rows", "sitemap")):
        row = _required_mapping(raw_row, f"sitemap row {index}")
        path = _required_path(row, "path", f"sitemap row {index}")
        _reject_duplicate(seen_paths, path, "sitemap path")
        memberships = _string_list(row, "dev_sitemaps", f"sitemap row {index}")
        _reject_list_duplicates(memberships, f"sitemap memberships for {path}")
        if memberships:
            targets[path] = memberships
    _require_equal("sitemap target count", len(targets), expectations.target_count)
    return targets, generated_at


def _validated_acf(
    acf: Mapping[str, Any],
    sitemap_rows: Mapping[str, list[str]],
    expectations: ProjectionExpectations,
) -> tuple[dict[str, Mapping[str, Any]], str]:
    _require_schema(acf, ACF_SCHEMA_VERSION, "ACF")
    _require_exact_bool(acf, "read_only", True, "ACF")
    generated_at = _required_string(acf, "generated_at", "ACF")
    objects = _required_list(acf, "objects", "ACF")
    _require_equal("ACF object count", len(objects), expectations.rest_object_count)
    by_path: dict[str, Mapping[str, Any]] = {}
    object_ids: set[int] = set()
    endpoint_counts: Counter[str] = Counter()
    authoring_counts: Counter[str] = Counter()
    for index, raw_row in enumerate(objects):
        row = _required_mapping(raw_row, f"ACF object {index}")
        path = _required_path(row, "path", f"ACF object {index}")
        if path in by_path:
            raise InventoryBuildError(f"Duplicate ACF path: {path}")
        if path not in sitemap_rows:
            raise InventoryBuildError(f"REST path is outside the sitemap target set: {path}")
        _require_exact_bool(row, "in_dev_sitemap", True, f"ACF object {path}")
        _require_exact_bool(row, "sitemap_match", True, f"ACF object {path}")
        _require_equal(
            f"ACF sitemap membership for {path}",
            _string_list(row, "sitemap", f"ACF object {path}"),
            sitemap_rows[path],
        )
        object_id = _required_int(row, "object_id", f"ACF object {path}")
        if object_id <= 0:
            raise InventoryBuildError(f"ACF object_id must be positive for {path}.")
        _reject_duplicate(object_ids, object_id, "ACF object_id")
        endpoint = _required_string(row, "endpoint", f"ACF object {path}")
        post_type = _required_string(row, "type", f"ACF object {path}")
        if ENDPOINT_POST_TYPES.get(endpoint) != post_type:
            raise InventoryBuildError(
                f"Unsupported endpoint/post type pair for ACF object {path}."
            )
        for key in ("status", "modified", "modified_gmt"):
            _required_string(row, key, f"ACF object {path}")
        authoring_mode = _required_string(row, "authoring_mode", f"ACF object {path}")
        _require_exact_bool(row, "raw_values_retained", False, f"ACF object {path}")
        _validate_acf_names(row, path)
        endpoint_counts[endpoint] += 1
        authoring_counts[authoring_mode] += 1
        by_path[path] = row
    expected_endpoints = dict(expectations.endpoint_counts)
    expected_authoring = dict(expectations.authoring_counts)
    _require_equal("ACF endpoint counts", dict(sorted(endpoint_counts.items())), expected_endpoints)
    _require_equal(
        "ACF authoring counts", dict(sorted(authoring_counts.items())), expected_authoring
    )
    summary = _required_mapping(acf.get("summary"), "ACF summary")
    _require_exact_bool(summary, "raw_values_retained", False, "ACF summary")
    return by_path, generated_at


def _validated_journal(
    journal: Mapping[str, Any],
    sitemap_rows: Mapping[str, list[str]],
    expectations: ProjectionExpectations,
) -> tuple[dict[str, Mapping[str, Any]], str]:
    _require_schema(journal, JOURNAL_SCHEMA_VERSION, "journal")
    generated_at = _required_string(journal, "generated_at", "journal")
    safety = _required_mapping(journal.get("safety"), "journal safety")
    for key, expected in JOURNAL_SAFETY_FLAGS.items():
        _require_exact_bool(safety, key, expected, "journal safety")
    urls = _required_list(journal, "urls", "journal")
    _require_equal("journal URL count", len(urls), expectations.target_count)
    by_path: dict[str, Mapping[str, Any]] = {}
    seen_urls: set[str] = set()
    for index, raw_row in enumerate(urls):
        row = _required_mapping(raw_row, f"journal URL row {index}")
        path = _required_path(row, "path", f"journal URL row {index}")
        if path in by_path:
            raise InventoryBuildError(f"Duplicate journal path: {path}")
        dev_url = _required_string(row, "url", f"journal URL row {path}")
        _reject_duplicate(seen_urls, dev_url, "journal URL")
        _validate_dev_url_path(dev_url, path)
        _required_disposition(row, f"journal URL row {path}")
        _required_string(row, "delivery_status", f"journal URL row {path}")
        for key, expected in ROW_SAFETY_FLAGS.items():
            _require_exact_bool(row, key, expected, f"journal URL row {path}")
        by_path[path] = row
    _require_equal("journal/sitemap path set", set(by_path), set(sitemap_rows))
    keep_count = sum(row["final_disposition"] == "keep" for row in by_path.values())
    _require_equal("journal keep count", keep_count, expectations.keep_count)
    return by_path, generated_at


def _validate_ledger(
    ledger: Sequence[Mapping[str, Any]],
    sitemap_rows: Mapping[str, list[str]],
    journal_rows: Mapping[str, Mapping[str, Any]],
) -> None:
    if isinstance(ledger, (str, bytes, bytearray)):
        raise InventoryBuildError("Ledger must be a sequence of JSON objects.")
    by_path: dict[str, str] = {}
    seen_urls: set[str] = set()
    for index, raw_row in enumerate(ledger):
        row = _required_mapping(raw_row, f"ledger row {index}")
        context = f"ledger row {index}"
        _require_schema(row, LEDGER_SCHEMA_VERSION, context)
        ledger_url = _required_string(row, "url", context)
        _reject_duplicate(seen_urls, ledger_url, "ledger URL")
        path = _normalized_ledger_path(ledger_url)
        if path in by_path:
            raise InventoryBuildError(f"Duplicate normalized ledger path: {path}")
        for key, expected in ROW_SAFETY_FLAGS.items():
            _require_exact_bool(row, key, expected, f"ledger row {path}")
        by_path[path] = _required_disposition(row, f"ledger row {path}")
    _require_equal("ledger/sitemap normalized path set", set(by_path), set(sitemap_rows))
    for path, disposition in by_path.items():
        _require_equal(
            f"ledger disposition for {path}",
            disposition,
            journal_rows[path]["final_disposition"],
        )


def _rest_object_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    layouts = [
        {
            "root_field": layout["root_field"],
            "layout_name": layout["layout_name"],
            "row_index": layout["row_index"],
            "field_names": list(layout["field_names"]),
        }
        for layout in row["acf_layouts"]
    ]
    return {
        "rest_object_observed": True,
        "blocker": None,
        "object_id": row["object_id"],
        "post_type": row["type"],
        "endpoint": row["endpoint"],
        "status": row["status"],
        "modified": row["modified"],
        "modified_gmt": row["modified_gmt"],
        "authoring_mode": row["authoring_mode"],
        "raw_values_retained": False,
        "acf_root_fields": list(row["acf_root_fields"]),
        "acf_field_names": list(row["acf_field_names"]),
        "acf_layouts": layouts,
    }


def _non_object_projection() -> dict[str, Any]:
    fields = {
        key: None
        for key in (
            "object_id",
            "post_type",
            "endpoint",
            "status",
            "modified",
            "modified_gmt",
            "authoring_mode",
            "raw_values_retained",
            "acf_root_fields",
            "acf_field_names",
            "acf_layouts",
        )
    }
    return {
        "rest_object_observed": False,
        "blocker": {
            "code": "rest_object_not_observed",
            "message": (
                "No REST object was observed for this exact path in the saved "
                "posts/pages/uslugi snapshot."
            ),
        },
        **fields,
    }


def _validate_acf_names(row: Mapping[str, Any], path: str) -> None:
    _string_list(row, "acf_root_fields", f"ACF object {path}")
    _string_list(row, "acf_field_names", f"ACF object {path}")
    for index, raw_layout in enumerate(
        _required_list(row, "acf_layouts", f"ACF object {path}")
    ):
        context = f"ACF layout {index} for {path}"
        layout = _required_mapping(raw_layout, context)
        _required_string(layout, "root_field", context)
        _required_string(layout, "layout_name", context)
        if "row_index" not in layout:
            raise InventoryBuildError(f"{context}.row_index must be explicit null or integer.")
        row_index = layout["row_index"]
        if row_index is not None and (type(row_index) is not int or row_index < 0):
            raise InventoryBuildError(
                f"{context} row_index must be null or a non-negative integer."
            )
        _string_list(layout, "field_names", context)


def _validate_provenance(provenance: Mapping[str, SourceProvenance]) -> None:
    _require_equal("provenance source keys", set(provenance), set(SOURCE_KEYS))
    for key in SOURCE_KEYS:
        item = provenance[key]
        if not isinstance(item, SourceProvenance):
            raise InventoryBuildError(f"Invalid provenance object for {key}.")
        _validate_source_ref(item.source_ref)
        _validate_sha256(item.sha256, f"{key} provenance")


def _validate_source_ref(source_ref: str) -> None:
    if not isinstance(source_ref, str) or not source_ref:
        raise InventoryBuildError("Logical source ref must be a non-empty string.")
    path = PurePosixPath(source_ref)
    invalid = (
        "\\" in source_ref
        or ":" in source_ref
        or "\x00" in source_ref
        or path.is_absolute()
        or source_ref != path.as_posix()
        or ".." in source_ref.split("/")
        or source_ref in {".", ".."}
    )
    if invalid:
        raise InventoryBuildError("Logical source ref must be a normalized repo-relative path.")


def _read_verified_bytes(
    path: Path, *, expected_sha256: str, source_ref: str
) -> tuple[bytes, str]:
    _validate_sha256(expected_sha256, f"expected SHA-256 for {source_ref}")
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise InventoryBuildError(f"Cannot read source labeled {source_ref}.") from error
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest != expected_sha256:
        raise InventoryBuildError(
            f"SHA-256 mismatch for {source_ref}: expected {expected_sha256}, got {digest}."
        )
    return raw_bytes, digest


def _parse_json_document(raw_bytes: bytes, *, source_ref: str) -> Mapping[str, Any]:
    return _required_mapping(
        _parse_json_text(raw_bytes, source_ref),
        f"source {source_ref}",
    )


def _parse_json_lines(raw_bytes: bytes, *, source_ref: str) -> list[Mapping[str, Any]]:
    try:
        lines = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise InventoryBuildError(f"Source {source_ref} is not UTF-8.") from error
    if not lines or any(not line.strip() for line in lines):
        raise InventoryBuildError(f"Source {source_ref} is not non-empty canonical JSONL.")
    return [
        _required_mapping(
            _parse_json_text(line.encode(), f"{source_ref} line {index}"),
            f"source {source_ref} line {index}",
        )
        for index, line in enumerate(lines, start=1)
    ]


def _parse_json_text(raw_bytes: bytes, source_ref: str) -> Any:
    try:
        return json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InventoryBuildError(f"Source {source_ref} is not valid JSON.") from error


def _assert_output_path_is_separate(
    output_path: Path, input_paths: Sequence[Path]
) -> None:
    resolved_output = output_path.resolve()
    for input_path in input_paths:
        resolved_input = input_path.resolve(strict=True)
        if resolved_output == resolved_input:
            raise InventoryBuildError("Output artifact must not overwrite an input source.")
        if output_path.exists() and output_path.samefile(input_path):
            raise InventoryBuildError("Output artifact must not alias an input source.")


def _split_dev_url(value: str, context: str) -> SplitResult:
    if any(
        character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F
        for character in value
    ):
        raise InventoryBuildError(
            f"{context} must not contain raw whitespace or ASCII control characters."
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise InventoryBuildError(f"{context} is invalid.") from error
    invalid = (
        parsed.scheme != DEV_SCHEME
        or parsed.netloc != DEV_NETLOC
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
    )
    if invalid:
        raise InventoryBuildError(f"{context} must use the exact dev origin.")
    return parsed


def _validate_dev_url_path(dev_url: str, expected_path: str) -> None:
    parsed = _split_dev_url(dev_url, f"Dev URL for path {expected_path}")
    if (parsed.path or "/") != expected_path:
        raise InventoryBuildError(f"Dev URL/path mismatch for {expected_path}.")


def _normalized_ledger_path(ledger_url: str) -> str:
    path = _split_dev_url(ledger_url, "Ledger URL").path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    _validate_path_value(path, "normalized ledger path")
    return path


def _require_schema(value: Mapping[str, Any], expected: str, context: str) -> None:
    _require_equal(
        f"{context} schema_version",
        _required_string(value, "schema_version", context),
        expected,
    )


def _required_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InventoryBuildError(f"{context} must be an object.")
    return value


def _required_list(value: Mapping[str, Any], key: str, context: str) -> list[Any]:
    item = value.get(key)
    if not isinstance(item, list):
        raise InventoryBuildError(f"{context}.{key} must be an array.")
    return item


def _required_string(value: Mapping[str, Any], key: str, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise InventoryBuildError(f"{context}.{key} must be a non-empty string.")
    return item


def _required_disposition(value: Mapping[str, Any], context: str) -> str:
    disposition = _required_string(value, "final_disposition", context)
    if disposition not in VALID_DISPOSITIONS:
        raise InventoryBuildError(
            f"{context}.final_disposition must be keep/noindex/redirect/remove."
        )
    return disposition


def _required_path(value: Mapping[str, Any], key: str, context: str) -> str:
    path = _required_string(value, key, context)
    _validate_path_value(path, f"{context}.{key}")
    return path


def _validate_path_value(path: str, context: str) -> None:
    segments = path.split("/")[1:]
    invalid = (
        not path.startswith("/")
        or path.startswith("//")
        or (path != "/" and path.endswith("/"))
        or (path != "/" and "" in segments)
        or any(segment in {".", ".."} for segment in segments)
        or "\\" in path
        or "?" in path
        or "#" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    )
    if invalid:
        raise InventoryBuildError(f"{context} must be an exact absolute URL path.")


def _required_int(value: Mapping[str, Any], key: str, context: str) -> int:
    item = value.get(key)
    if type(item) is not int:
        raise InventoryBuildError(f"{context}.{key} must be an integer.")
    return item


def _require_exact_bool(
    value: Mapping[str, Any], key: str, expected: bool, context: str
) -> None:
    item = value.get(key)
    if type(item) is not bool or item is not expected:
        raise InventoryBuildError(f"{context}.{key} must be {str(expected).lower()}.")


def _string_list(value: Mapping[str, Any], key: str, context: str) -> list[str]:
    items = _required_list(value, key, context)
    if any(not isinstance(item, str) or not item for item in items):
        raise InventoryBuildError(f"{context}.{key} must contain only non-empty strings.")
    return items


def _validate_sha256(value: str, context: str) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise InventoryBuildError(f"{context} must be an exact lowercase SHA-256.")


def _reject_duplicate(seen: set[Any], value: Any, context: str) -> None:
    if value in seen:
        raise InventoryBuildError(f"Duplicate {context}: {value}")
    seen.add(value)


def _reject_list_duplicates(values: Sequence[str], context: str) -> None:
    if len(values) != len(set(values)):
        raise InventoryBuildError(f"Duplicate value in {context}.")


def _require_equal(context: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise InventoryBuildError(f"{context} does not match the required contract.")


def _sorted_counter(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(values)
    if any(not isinstance(key, str) for key in counts):
        raise InventoryBuildError("Derived counter contains a non-string key.")
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
