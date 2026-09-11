from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import SplitResult, urlsplit

LEDGER_SCHEMA_VERSION = "content_canonical_ledger_row_v1"
JOURNAL_SCHEMA_VERSION = "dev_content_state_journal_v1"
LEDGER_ADJUDICATION_SCHEMA_VERSION = "content_noindex_re_adjudication_v2"
JOURNAL_RESUMPTION_SCHEMA_VERSION = "content_noindex_re_adjudication_resume_v2"
SOURCE_SCHEMA_VERSION = "content_noindex_re_adjudication_source_v2"
OPERATIONAL_SUMMARY_SCHEMA_VERSION = "content_canonical_ledger_summary_v1"

DEV_ORIGIN = "https://ekologus.dev.proudsite.pl"
PUBLIC_ORIGIN = "https://www.ekologus.pl"
GSC_PARTIAL_EVIDENCE_ID = "ev_refresh_refresh_google_search_console_1b3e7318dbb9"
WORDPRESS_PARTIAL_EVIDENCE_ID = "ev_refresh_refresh_wordpress_ekologus_722938c36872"

PACKET_KEYS = frozenset(
    {
        "url",
        "current_disposition",
        "proposed_disposition",
        "target_url",
        "confidence",
        "evidence_ids",
        "decision_basis",
        "blockers",
    }
)
SUPPORTED_ACTIONS = frozenset({"keep", "redirect", "noindex", "blocked"})
OPERATIONAL_DISPOSITIONS = frozenset({"keep", "redirect", "noindex", "remove"})
CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
ROW_SAFETY_FLAGS = ("publish_allowed", "write_authorized", "robot_ready")
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
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

LEDGER_ADJUDICATION_KEYS = frozenset(
    {
        "schema_version",
        "input_reference",
        "adjudication_digest",
        "recommended_action",
        "recommended_target_url",
        "status",
        "confidence",
        "confidence_authority",
        "selected_authority",
        "decision_basis_pl",
        "evidence_ids",
        "blockers",
        "decision_receipt_sha256",
        "input_receipt_sha256",
        "judge_receipt_set_digest",
        "caveat_set_digest",
        "technical_row_digest",
        "strategy_row_digest",
        "tie_breaker_row_digest",
        "operational_promotion",
    }
)
JOURNAL_RESUMPTION_KEYS = frozenset(
    {
        "schema_version",
        "input_reference",
        "adjudication_digest",
        "caveat_set_digest",
        "status",
        "recommended_action",
        "recommended_target_url",
        "operational_promotion",
        "next_gate",
        "blockers",
    }
)


class AdjudicationError(RuntimeError):
    """Raised when the packet or retained authorities fail closed."""


def without_key(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {item_key: item_value for item_key, item_value in value.items() if item_key != key}


def complete_counts(counts: Counter[str], keys: set[str] | frozenset[str]) -> dict[str, int]:
    return {key: counts.get(key, 0) for key in sorted(keys)}


def digest_json(value: Any) -> str:
    try:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise AdjudicationError("Digest input is not canonical JSON data.") from error
    return hashlib.sha256(raw).hexdigest()


def verified_digest(raw: bytes, expected_sha256: str, context: str) -> str:
    sha256_value(expected_sha256, f"expected SHA-256 for {context}")
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected_sha256:
        raise AdjudicationError(
            f"SHA-256 mismatch for {context}: expected {expected_sha256}, got {observed}."
        )
    return observed


def parse_jsonl(raw: bytes, context: str) -> list[Mapping[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise AdjudicationError(f"{context} is not UTF-8.") from error
    if not lines or any(not line.strip() for line in lines):
        raise AdjudicationError(f"{context} is not non-empty canonical JSONL.")
    return [
        object_value(parse_json(line.encode(), f"{context} line {index}"), context)
        for index, line in enumerate(lines, start=1)
    ]


def parse_json(raw: bytes, context: str) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdjudicationError(f"{context} is not valid JSON.") from error


def validate_input_reference(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9_]+", value):
        raise AdjudicationError("Input reference must be a stable lowercase identifier.")


def false_row_flags(row: Mapping[str, Any], context: str) -> None:
    for key in ROW_SAFETY_FLAGS:
        if row.get(key) is not False:
            raise AdjudicationError(f"{context}.{key} must remain false.")


def required_evidence_ids(ledger_row: Mapping[str, Any], path: str) -> set[str]:
    source_receipt = string_value(
        ledger_row.get("production_readback_receipt_id"),
        f"ledger row {path}.production_readback_receipt_id",
    )
    return {
        GSC_PARTIAL_EVIDENCE_ID,
        WORDPRESS_PARTIAL_EVIDENCE_ID,
        source_receipt,
    }


def dev_path(value: str, context: str) -> str:
    return _url_path(value, DEV_ORIGIN, context)


def public_path(value: str, context: str) -> str:
    return _url_path(value, PUBLIC_ORIGIN, context)


def path_value(value: Any, context: str) -> str:
    path = string_value(value, context)
    normalized = "/" if path == "/" else path.removesuffix("/")
    segments = normalized.split("/")[1:]
    invalid = (
        not normalized.startswith("/")
        or normalized.startswith("//")
        or (normalized != "/" and not segments)
        or (normalized != "/" and "" in segments)
        or any(segment in {".", ".."} for segment in segments)
        or "\\" in normalized
        or "?" in normalized
        or "#" in normalized
    )
    if invalid:
        raise AdjudicationError(f"{context} is not an exact absolute path.")
    return normalized


def sha256_value(value: Any, context: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise AdjudicationError(f"{context} must be an exact lowercase SHA-256.")
    return value


def string_value(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AdjudicationError(f"{context} must be a non-empty trimmed string.")
    return value


def string_list(value: Any, context: str) -> list[str]:
    items = array_value(value, context)
    return [string_value(item, f"{context}[{index}]") for index, item in enumerate(items)]


def array_value(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise AdjudicationError(f"{context} must be an array.")
    return value


def object_value(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise AdjudicationError(f"{context} must be an object.")
    return dict(value)


def object_list(value: Any, context: str) -> list[Mapping[str, Any]]:
    return [
        object_value(item, f"{context} row {index}")
        for index, item in enumerate(array_value(value, context))
    ]


def render_ledger(ledger: Sequence[Mapping[str, Any]]) -> bytes:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) for row in ledger]
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_journal(journal: Mapping[str, Any]) -> bytes:
    return (json.dumps(journal, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def decision_set_digest(path_digests: Sequence[Mapping[str, str]]) -> str:
    return digest_json(
        {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "path_adjudication_digests": sorted(
                path_digests,
                key=lambda item: item["path"],
            ),
        }
    )


def operational_ledger_summary(ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["final_disposition"] for row in ledger)
    return {
        "schema_version": OPERATIONAL_SUMMARY_SCHEMA_VERSION,
        "row_count": len(ledger),
        "final_disposition_counts": complete_counts(counts, OPERATIONAL_DISPOSITIONS),
        "redirect_target_receipt_count": sum(
            row["final_disposition"] == "redirect"
            and isinstance(row.get("target_readback_receipt_id"), str)
            and bool(row["target_readback_receipt_id"])
            for row in ledger
        ),
        "publish_allowed_rows": sum(row.get("publish_allowed") is True for row in ledger),
        "write_authorized_rows": sum(row.get("write_authorized") is True for row in ledger),
        "robot_ready_rows": sum(row.get("robot_ready") is True for row in ledger),
    }


def assert_only_adjudication_changes(
    original_ledger: Sequence[Mapping[str, Any]],
    original_journal: Mapping[str, Any],
    updated_ledger: Sequence[Mapping[str, Any]],
    updated_journal: Mapping[str, Any],
) -> None:
    for before, after in zip(original_ledger, updated_ledger, strict=True):
        if without_key(before, "re_adjudication") != without_key(after, "re_adjudication"):
            raise AdjudicationError("Reconciler attempted an operational ledger mutation.")
    original_rows = {row["path"]: row for row in original_journal["urls"]}
    updated_rows = {row["path"]: row for row in updated_journal["urls"]}
    for path in original_rows:
        if without_key(original_rows[path], "re_adjudication") != without_key(
            updated_rows[path], "re_adjudication"
        ):
            raise AdjudicationError(f"Reconciler attempted an operational journal mutation: {path}")
    for key, value in original_journal.items():
        if key not in {"urls", "sources", "summary"} and updated_journal.get(key) != value:
            raise AdjudicationError(f"Reconciler attempted a top-level journal mutation: {key}")
    original_summary = without_key(
        object_value(original_journal.get("summary"), "journal.summary"),
        "noindex_re_adjudication",
    )
    updated_summary = without_key(
        object_value(updated_journal.get("summary"), "updated journal.summary"),
        "noindex_re_adjudication",
    )
    if original_summary != updated_summary:
        raise AdjudicationError("Reconciler attempted an operational summary mutation.")
    original_sources = object_value(original_journal.get("sources"), "journal.sources")
    updated_sources = object_value(updated_journal.get("sources"), "updated journal.sources")
    original_canonical = object_value(
        original_sources.get("canonical_ledger"),
        "journal.sources.canonical_ledger",
    )
    updated_canonical = object_value(
        updated_sources.get("canonical_ledger"),
        "updated journal.sources.canonical_ledger",
    )
    mutable_canonical_keys = {
        "sha256",
        "summary_sha256",
        "summary_schema_version",
        "summary_digest_algorithm",
        "summary",
    }
    if {
        key: value for key, value in original_canonical.items() if key not in mutable_canonical_keys
    } != {
        key: value for key, value in updated_canonical.items() if key not in mutable_canonical_keys
    }:
        raise AdjudicationError("Reconciler attempted unrelated ledger-source mutation.")
    original_sources_without_owned = {
        key: value
        for key, value in original_sources.items()
        if key not in {"canonical_ledger", "noindex_re_adjudication"}
    }
    updated_sources_without_owned = {
        key: value
        for key, value in updated_sources.items()
        if key not in {"canonical_ledger", "noindex_re_adjudication"}
    }
    if original_sources_without_owned != updated_sources_without_owned:
        raise AdjudicationError("Reconciler attempted unrelated journal-source mutation.")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdjudicationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise AdjudicationError(f"Non-finite JSON number is forbidden: {value}")


def _url_path(value: str, expected_origin: str, context: str) -> str:
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise AdjudicationError(f"{context} contains whitespace or control characters.")
    try:
        parsed: SplitResult = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise AdjudicationError(f"{context} is not a valid URL.") from error
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if (
        origin != expected_origin
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise AdjudicationError(f"{context} must use the exact expected origin.")
    return path_value(parsed.path or "/", context)
