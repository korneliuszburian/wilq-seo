from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from wilq.content.workflow.keep_eligibility import (
    KeepEligibilityError,
    KeepEligibilityInput,
    SourceProvenance,
    build_keep_eligibility_projection,
)

OUTPUT_SCHEMA_VERSION = "content_keep_eligibility_v1"
SOURCE_KEYS = (
    "authoring_inventory",
    "state_journal",
    "canonical_ledger",
    "context",
    "target_mapping_snapshot",
)


def _digest(*chunks: str) -> str:
    return "".join(chunks)


SOURCE_DEFAULTS = {
    "authoring_inventory": (
        "docs/content-dev-authoring-inventory-20260828.json",
        _digest(
            "6f1a3819",
            "01cdeec7",
            "e2d5215e",
            "12305087",
            "018330c3",
            "85483077",
            "0908a79e",
            "bae122ec",
        ),
    ),
    "state_journal": (
        "docs/content-dev-state-journal-20260828.json",
        _digest(
            "2dafb081",
            "3c591e06",
            "49f464d9",
            "9d895052",
            "74d4f28b",
            "6308f4e5",
            "2e44cf75",
            "74e51f95",
        ),
    ),
    "canonical_ledger": (
        "docs/content-canonical-ledger-20260828.jsonl",
        _digest(
            "b62a4547",
            "6a51768c",
            "829b5878",
            "a934c013",
            "e2c5f0b8",
            "52780f2e",
            "c4498c3b",
            "3feb5506",
        ),
    ),
    "context": (
        "docs/content-keep-eligibility-context-20260828.json",
        _digest(
            "410556ac",
            "65a69c69",
            "77af80f8",
            "89e535ac",
            "fe15640c",
            "3a454fe1",
            "e5d188d4",
            "a0aab46b",
        ),
    ),
    "target_mapping_snapshot": (
        "docs/content-keep-target-mapping-snapshot-20260828.json",
        _digest(
            "a5acb59d",
            "a9895c78",
            "dc5b944d",
            "0952608b",
            "698288e4",
            "eafec293",
            "3c0addef",
            "aa06a63b",
        ),
    ),
}
BINDING_SOURCE = {
    "path": "wilq/content/knowledge/source_facts.py",
    "sha256": _digest(
        "7b8c34a3",
        "83498466",
        "a47b35a2",
        "ea595f12",
        "43078458",
        "23060e63",
        "72c7c592",
        "f1a16356",
    ),
    "commit": "441579ea",
    "map": "ekologus_service_binding_urls",
}

EXPECTED_COUNTS = (
    ("keep_count", 57),
    ("exact_authoring_target_count", 57),
    ("retained_work_item_count", 27),
    ("current_work_item_count", 54),
    ("joined_work_item_count", 27),
    ("exact_work_item_id_equal_count", 0),
    ("reconciled_work_item_count", 0),
    ("current_revision_count", 13),
    ("exact_service_binding_count", 7),
    ("source_pack_work_item_binding_count", 0),
    ("existing_generation_identity_count", 9),
    ("typed_target_context_count", 0),
    ("current_target_mapping_preview_count", 1),
    ("eligible_count", 0),
)
EXPECTED_PRIMARY_BLOCKERS = (
    ("existing_verified_draft_or_applied_action", 9),
    ("work_item_identity_fork", 20),
    ("retained_work_item_missing", 25),
    ("work_item_identity_missing", 3),
)
ALLOWED_OBSERVATIONS = {
    "/api/system/status": 1,
    "/api/content/knowledge-cards": 1,
    "/api/content/service-profile": 1,
    "/api/content/inventory/catalog": 1,
    "/api/evidence/{evidence_id}": 5,
}


class CliInputError(RuntimeError):
    pass


def render_projection(payload: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CliInputError("Projekcja nie jest kanonicznym JSON-em.") from error
    return (text + "\n").encode()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payloads, provenance, input_paths = _load_sources(args)
        binding_source_path = _verify_binding_source(args)
        context = _object(payloads["context"], "context")
        _validate_context_capture(context)
        output_path = Path(args.output)
        _assert_separate_output(output_path, [*input_paths, binding_source_path])
        result = build_keep_eligibility_projection(
            KeepEligibilityInput(
                authoring_inventory=_object(payloads["authoring_inventory"], "authoring inventory"),
                state_journal=_object(payloads["state_journal"], "state journal"),
                canonical_ledger=_object_list(payloads["canonical_ledger"], "ledger"),
                context=context,
                target_mapping_snapshot=_object(
                    payloads["target_mapping_snapshot"], "target mapping snapshot"
                ),
                provenance=provenance,
                expected_counts=EXPECTED_COUNTS,
                expected_primary_blocker_counts=EXPECTED_PRIMARY_BLOCKERS,
            )
        )
        _validate_projection_safety(result)
        rendered = render_projection(result)
        if args.check:
            if output_path.read_bytes() != rendered:
                raise CliInputError("Artefakt różni się od deterministycznej projekcji.")
            print("Projekcja content_keep_eligibility jest aktualna.")
        else:
            output_path.write_bytes(rendered)
            print("Zapisano projekcję content_keep_eligibility.")
    except (CliInputError, KeepEligibilityError) as error:
        print(f"Błąd projekcji content_keep_eligibility: {error}", file=sys.stderr)
        return 1
    except OSError:
        print(
            "Błąd projekcji content_keep_eligibility: operacja plikowa nie powiodła się.",
            file=sys.stderr,
        )
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Buduje deterministyczną, read-only projekcję 57 keep."
    )
    for key in SOURCE_KEYS:
        flag = key.replace("_", "-")
        source_ref, sha256 = SOURCE_DEFAULTS[key]
        parser.add_argument(f"--{flag}", default=source_ref)
        parser.add_argument(f"--{flag}-ref", default=source_ref)
        parser.add_argument(f"--{flag}-sha256", default=sha256)
    parser.add_argument("--binding-source", default=BINDING_SOURCE["path"])
    parser.add_argument("--binding-source-sha256", default=BINDING_SOURCE["sha256"])
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Porównuje bajt w bajt bez zapisu.",
    )
    return parser


def _load_sources(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, SourceProvenance], list[Path]]:
    payloads: dict[str, Any] = {}
    provenance: dict[str, SourceProvenance] = {}
    paths: list[Path] = []
    for key in SOURCE_KEYS:
        path = Path(getattr(args, key))
        source_ref = _source_ref(getattr(args, f"{key}_ref"))
        expected_sha = _sha256(getattr(args, f"{key}_sha256"), f"SHA {key}")
        raw = _read_exact(path, expected_sha, source_ref)
        payloads[key] = (
            _parse_jsonl(raw, source_ref)
            if key == "canonical_ledger"
            else _parse_json(raw, source_ref)
        )
        provenance[key] = SourceProvenance(source_ref=source_ref, sha256=expected_sha)
        paths.append(path)
    return payloads, provenance, paths


def _verify_binding_source(args: argparse.Namespace) -> Path:
    path = Path(args.binding_source)
    expected_sha = _sha256(args.binding_source_sha256, "SHA binding source")
    if expected_sha != BINDING_SOURCE["sha256"]:
        raise CliInputError("SHA binding source nie odpowiada przypiętej mapie kodu.")
    _read_exact(path, expected_sha, BINDING_SOURCE["path"])
    return path


def _read_exact(path: Path, expected_sha: str, source_ref: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CliInputError(f"Nie można odczytać źródła {source_ref}.") from error
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected_sha:
        raise CliInputError(f"Niezgodny SHA-256 źródła {source_ref}.")
    return raw


def _parse_json(raw: bytes, source_ref: str) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CliInputError(f"Źródło {source_ref} nie jest poprawnym JSON-em.") from error


def _parse_jsonl(raw: bytes, source_ref: str) -> list[Mapping[str, Any]]:
    try:
        lines = raw.decode().splitlines()
    except UnicodeDecodeError as error:
        raise CliInputError(f"Źródło {source_ref} nie jest UTF-8.") from error
    if not lines or any(not line.strip() for line in lines):
        raise CliInputError(f"Źródło {source_ref} nie jest kanonicznym JSONL-em.")
    return [
        _object(_parse_json(line.encode(), f"{source_ref} line {index}"), source_ref)
        for index, line in enumerate(lines, start=1)
    ]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliInputError(f"Powtórzony klucz JSON: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise CliInputError(f"Niedozwolona liczba JSON: {value}")


def _validate_context_capture(context: Mapping[str, Any]) -> None:
    api = _object(context.get("api"), "context.api")
    if api.get("method") != "GET" or api.get("base_url") != "http://127.0.0.1:8000":
        raise CliInputError("Context nie opisuje lokalnego odczytu GET.")
    health = _object(api.get("health"), "context.api.health")
    if health.get("endpoint") != "/api/health" or health.get("runtime_sha_attested") is not False:
        raise CliInputError("Context nie zachowuje jawnej luki runtime SHA.")
    observed: dict[str, int] = {}
    for value in _array(api.get("source_observations"), "context source observations"):
        item = _object(value, "context source observation")
        endpoint, count = item.get("endpoint"), item.get("read_count")
        if not isinstance(endpoint, str) or type(count) is not int or endpoint in observed:
            raise CliInputError("Context ma niejednoznaczny rejestr endpointów.")
        observed[endpoint] = count
    if observed != ALLOWED_OBSERVATIONS:
        raise CliInputError("Context wychodzi poza dozwolony snapshot GET.")
    summary = _object(context.get("connector_summary"), "connector summary")
    if {key: summary.get(key) for key in ("total", "configured", "missing_credentials")} != {
        "total": 12,
        "configured": 9,
        "missing_credentials": 2,
    }:
        raise CliInputError("Context ma inny stan konektorów niż 12/9/2.")
    _validate_service_profile(context)
    _validate_capture_window(context)
    bindings = _object(context.get("service_bindings"), "service bindings")
    source = _object(bindings.get("current_code_source"), "service binding source")
    if {key: source.get(key) for key in BINDING_SOURCE} != BINDING_SOURCE:
        raise CliInputError("Context ma niezgodne źródło exact service binding.")
    _reject_context_leaks(context)


def _validate_service_profile(context: Mapping[str, Any]) -> None:
    profile = _object(context.get("service_profile"), "service profile")
    readiness = _object(profile.get("production_depth_readiness"), "production readiness")
    approval = _object(profile.get("approval_readiness"), "approval readiness")
    counts = (approval.get("approved_current_count"), approval.get("review_required_count"))
    invalid = (
        profile.get("read_only") is not True
        or profile.get("service_card_count") != 11
        or readiness.get("ready_for_daily_content") is not False
        or readiness.get("scope") != "all_knowledge_cards"
        or approval.get("mutation_allowed") is not False
        or any(type(value) is not int for value in counts)
    )
    if invalid:
        raise CliInputError("Service Profile nie jest bezpiecznym read-only snapshotem.")


def _validate_capture_window(context: Mapping[str, Any]) -> None:
    try:
        started = datetime.fromisoformat(str(context["capture_started_at"]).replace("Z", "+00:00"))
        completed = datetime.fromisoformat(
            str(context["capture_completed_at"]).replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as error:
        raise CliInputError("Context nie ma poprawnego okna obserwacji.") from error
    if started.tzinfo is None or completed.tzinfo is None or completed < started:
        raise CliInputError("Context ma niepoprawną kolejność okna obserwacji.")


def _reject_context_leaks(context: Mapping[str, Any]) -> None:
    forbidden = {
        "body",
        "claims",
        "components",
        "content",
        "content_text",
        "fields",
        "notes",
        "raw_ref",
        "raw_value",
        "raw_values",
        "summary",
        "target_contexts",
        "target_reads",
        "title",
    }

    def walk(value: Any, path: tuple[str | int, ...]) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                current = (*path, key)
                if key in forbidden or "digest" in key:
                    raise CliInputError("Context zawiera niedozwolone pole raw/target.")
                if key == "sha256" and current != (
                    "service_bindings",
                    "current_code_source",
                    "sha256",
                ):
                    raise CliInputError("Context zawiera niedozwolony SHA.")
                walk(child, current)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, (*path, index))

    walk(context, ())


def _validate_projection_safety(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        raise CliInputError("Projekcja ma nieobsługiwany schema_version.")
    rows = _array(payload.get("rows"), "projection rows")
    for value in rows:
        row = _object(value, "projection row")
        if any(
            row.get(key) is not False
            for key in ("publish_allowed", "write_authorized", "robot_ready")
        ):
            raise CliInputError("Projekcja rozszerza authority zapisu lub publikacji.")
        if (
            row.get("planning_eligible") is not False
            or row.get("new_generation_allowed") is not False
        ):
            raise CliInputError("Bieżąca projekcja nie może dopuścić generacji.")


def _assert_separate_output(output: Path, inputs: Sequence[Path]) -> None:
    resolved_output = output.resolve()
    for source in inputs:
        resolved_source = source.resolve(strict=True)
        if resolved_output == resolved_source or (output.exists() and output.samefile(source)):
            raise CliInputError("Output nie może nadpisać źródła.")


def _source_ref(value: Any) -> str:
    if not isinstance(value, str):
        raise CliInputError("Source ref musi być tekstem.")
    path = PurePosixPath(value)
    invalid = (
        not value
        or "\\" in value
        or ":" in value
        or path.is_absolute()
        or path.as_posix() != value
        or ".." in value.split("/")
    )
    if invalid:
        raise CliInputError("Source ref musi być znormalizowaną ścieżką repo.")
    return value


def _sha256(value: Any, context: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CliInputError(f"{context} nie jest małym SHA-256.")
    return value


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise CliInputError(f"{context} nie jest obiektem.")
    return value


def _object_list(value: Any, context: str) -> list[Mapping[str, Any]]:
    return [_object(item, f"{context} row") for item in _array(value, context)]


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise CliInputError(f"{context} nie jest tablicą.")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
