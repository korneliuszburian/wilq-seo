from __future__ import annotations

import json
import re
from datetime import datetime
from hashlib import sha256
from math import isfinite
from typing import Never, TypeVar, cast

from pydantic import BaseModel, ValidationError

from wilq.content.workflow.decisions.production import (
    Classification,
    ContentProductionAcceptancePolicy,
    ContentProductionAudit,
    ContentProductionBlocker,
    ContentProductionClassificationCounts,
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
    ContentProductionEvidenceDefect,
    ContentProductionFreshness,
    ContentProductionInputReceipt,
    ContentProductionJudgeReceipt,
    ContentProductionRetainedBinding,
    ContentProductionRowReceipt,
    ContentProductionSourceReceipt,
    ContentProductionVerifiedAction,
    ContentProductionVerifiedDraft,
    _build_run,
    _validate_typed_uniqueness,
    canonical_json_digest,
    classification_counts,
)

_ROW_DIGEST_ALGORITHM = (
    "sha256(canonical_json(source_packet_receipts); UTF-8, sorted keys, compact separators)"
)
_DECISION_DIGEST_ALGORITHM = "sha256(canonical_json(rows); UTF-8, sorted keys, compact separators)"
_SignedModel = TypeVar("_SignedModel", bound=BaseModel)


def parse_content_production_classification_impl(
    *,
    packet_bytes: bytes,
    judge_bytes: bytes,
    acceptance_policy: ContentProductionAcceptancePolicy,
    recorded_by: str,
    reviewed_by: str,
    recorded_at: datetime,
) -> ContentProductionClassificationRun:
    try:
        acceptance_policy = ContentProductionAcceptancePolicy.model_validate_json(
            acceptance_policy.model_dump_json()
        )
    except ValidationError:
        _invalid("acceptance_policy_invalid")
    packet_sha256 = sha256(packet_bytes).hexdigest()
    judge_sha256 = sha256(judge_bytes).hexdigest()
    if packet_sha256 != acceptance_policy.packet_sha256:
        _invalid("packet_receipt_mismatch")
    if judge_sha256 != acceptance_policy.judge_sha256:
        _invalid("judge_receipt_mismatch")
    try:
        source = _StrictJson(packet_bytes, judge_bytes)
        _validate_header(source, acceptance_policy)
        source_receipts = _source_receipts(source, acceptance_policy)
        rows = _rows(source, acceptance_policy)
        counts = classification_counts(rows)
        freshness = _freshness(source, acceptance_policy)
        _validate_packet_claims(source, acceptance_policy, rows, counts)
        judge_receipt = _judge_receipt(
            source,
            acceptance_policy,
            packet_sha256=packet_sha256,
        )
        audit = ContentProductionAudit(
            recorded_by=source.safe_identity(recorded_by, "recorded_by_invalid"),
            reviewed_by=source.safe_identity(reviewed_by, "reviewed_by_invalid"),
            recorded_at=recorded_at,
        )
        input_receipt = ContentProductionInputReceipt(
            policy_id=acceptance_policy.policy_id,
            policy_digest=canonical_json_digest(acceptance_policy.model_dump(mode="json")),
            packet_schema_version=source.packet_text("schema_version"),
            packet_sha256=packet_sha256,
            judge_sha256=judge_sha256,
            decision_set_digest=source.packet_text("decision_set_digest"),
            base_revision=source.packet_text("base_revision"),
            packet_generated_at=source.packet_text("generated_at"),
        )
        return _build_run(
            input_receipt=input_receipt,
            counts=counts,
            freshness=freshness,
            source_receipts=source_receipts,
            judge_receipt=judge_receipt,
            rows=rows,
            audit=audit,
        )
    except ContentProductionClassificationValidationError:
        raise
    except (KeyError, StopIteration, TypeError, ValueError, ValidationError):
        _invalid("typed_classification_invalid")


def _validate_header(source: _StrictJson, policy: ContentProductionAcceptancePolicy) -> None:
    if (
        source.packet_text("schema_version") != policy.packet_schema_version
        or source.packet_text("base_revision") != policy.base_revision
        or source.packet_text("row_digest_algorithm") != _ROW_DIGEST_ALGORITHM
        or source.packet_text("decision_set_digest_algorithm") != _DECISION_DIGEST_ALGORITHM
    ):
        _invalid("packet_contract_mismatch")
    source.reject_enabled_generation(source.packet)


def _source_receipts(
    source: _StrictJson,
    policy: ContentProductionAcceptancePolicy,
) -> tuple[ContentProductionSourceReceipt, ...]:
    raw = source.require_object_member(source.packet, "source_file_receipts")
    expected = {item.name: item for item in policy.source_receipts}
    if set(raw) != set(expected):
        _invalid("source_receipt_scope_mismatch")
    result: list[ContentProductionSourceReceipt] = []
    for name, receipt_policy in expected.items():
        item = source.require_object(raw.get(name), "source_receipt_object_required")
        reference = item.get("path", item.get("artifact_reference"))
        receipt = ContentProductionSourceReceipt(
            name=name,
            reference=source.text(reference, "source_receipt_reference_invalid"),
            sha256=source.text(item.get("sha256"), "source_receipt_sha_invalid"),
            raw_artifact_retained=source.optional_bool(item.get("raw_artifact_retained")),
            retention_status=source.optional_text(item.get("retention_status")),
        )
        if receipt.model_dump(mode="python") != receipt_policy.model_dump(mode="python"):
            _invalid("source_receipt_mismatch")
        result.append(receipt)
    return tuple(result)


def _freshness(
    source: _StrictJson,
    policy: ContentProductionAcceptancePolicy,
) -> ContentProductionFreshness:
    raw = source.require_object_member(source.packet, "wilq_diagnostic_freshness")
    windows = source.require_object_member(raw, "connector_covered_windows")
    connector_ids = tuple(sorted(windows))
    if connector_ids != policy.freshness_connector_ids:
        _invalid("freshness_connector_scope_mismatch")
    return ContentProductionFreshness(
        state=source.text(raw.get("state"), "freshness_state_invalid"),
        checked_at=source.text(raw.get("checked_at"), "freshness_time_invalid"),
        requires_refresh=source.boolean(raw.get("requires_refresh"), "freshness_flag_invalid"),
        connector_ids=connector_ids,
    )


def _rows(
    source: _StrictJson,
    policy: ContentProductionAcceptancePolicy,
) -> tuple[ContentProductionClassificationRow, ...]:
    raw_rows = source.array_member(source.packet, "rows")
    semantic_digest = canonical_json_digest(raw_rows)
    if (
        semantic_digest != source.packet_text("decision_set_digest")
        or semantic_digest != policy.decision_set_digest
    ):
        _invalid("decision_set_digest_mismatch")
    rows = tuple(_row(source, value, policy) for value in raw_rows)
    paths = tuple(row.canonical_path for row in rows)
    if paths != policy.canonical_paths or len(paths) != len(set(paths)):
        _invalid("canonical_scope_mismatch")
    return rows


def _row(
    source: _StrictJson,
    value: object,
    policy: ContentProductionAcceptancePolicy,
) -> ContentProductionClassificationRow:
    raw = source.require_object(value, "row_object_required")
    path = source.text(raw.get("path"), "row_path_invalid")
    expected_url = f"{policy.public_origin}/" if path == "/" else f"{policy.public_origin}{path}/"
    public_url = source.text(raw.get("public_url"), "row_url_invalid")
    if public_url != expected_url:
        _invalid("canonical_url_mismatch")
    if source.boolean(raw.get("generation_allowed"), "generation_flag_invalid"):
        _invalid("generation_not_disabled")
    identity = source.require_object_member(raw, "work_item_identity")
    revision = source.require_object_member(raw, "revision")
    evidence = source.require_object_member(raw, "evidence")
    receipt_raw = source.require_object_member(raw, "source_packet_receipts")
    row_digest = source.text(raw.get("source_packet_row_digest"), "row_digest_invalid")
    if row_digest != canonical_json_digest(receipt_raw):
        _invalid("row_digest_mismatch")
    row = ContentProductionClassificationRow(
        canonical_path=path,
        public_url=public_url,
        decision=source.classification(raw.get("decision")),
        generation_allowed=False,
        current_work_item_id=source.optional_text(identity.get("current_inventory_work_item_id")),
        retained_work_item_id=source.optional_text(identity.get("retained_work_item_id")),
        revision_id=source.optional_text(revision.get("revision_id")),
        revision_digest=source.optional_text(revision.get("digest")),
        revision_approved=source.boolean(revision.get("approved"), "revision_approval_invalid"),
        revision_complete=source.boolean(revision.get("complete"), "revision_complete_invalid"),
        rationale_pl=source.text(raw.get("rationale_pl"), "row_rationale_invalid"),
        next_step_pl=source.text(raw.get("next_step_pl"), "row_next_step_invalid"),
        blockers=tuple(
            source.model(ContentProductionBlocker, item)
            for item in source.array(raw.get("typed_blockers", []), "blockers_invalid")
        ),
        retained_binding=(
            None
            if raw.get("retained_revision_binding") is None
            else source.model(
                ContentProductionRetainedBinding,
                raw["retained_revision_binding"],
            )
        ),
        verified_actions=tuple(
            source.model(ContentProductionVerifiedAction, item)
            for item in source.array_member(
                source.require_object_member(raw, "draft_and_action_state"),
                "verified_current_action_bindings",
            )
        ),
        verified_drafts=tuple(
            source.model(ContentProductionVerifiedDraft, item)
            for item in source.array_member(
                source.require_object_member(raw, "draft_and_action_state"),
                "verified_current_draft_bindings",
            )
        ),
        primary_evidence_ids=source.texts(evidence.get("evidence_ids"), "primary_evidence_invalid"),
        source_connectors=source.texts(
            evidence.get("source_connectors"), "source_connectors_invalid"
        ),
        lineage_evidence_ids=source.texts(
            evidence.get("canonical_ledger_evidence_ids", []), "lineage_invalid"
        ),
        lineage_defects=tuple(
            source.model(ContentProductionEvidenceDefect, item)
            for item in source.array(evidence.get("lineage_defects", []), "lineage_defects_invalid")
        ),
        source_receipt=_row_receipt(source, receipt_raw, evidence, policy),
        source_packet_row_digest=row_digest,
    )
    return row


def _row_receipt(
    source: _StrictJson,
    item: dict[str, object],
    evidence: dict[str, object],
    policy: ContentProductionAcceptancePolicy,
) -> ContentProductionRowReceipt:
    receipt = source.model(ContentProductionRowReceipt, item)
    expected = next(
        value
        for value in policy.source_receipts
        if value.name == f"{receipt.classification_source}_classification"
    )
    if (
        receipt.classification_file_sha256 != expected.sha256
        or receipt.classification_artifact_reference != expected.reference
        or receipt.source_pack_id != evidence.get("source_pack_id")
    ):
        _invalid("classifier_receipt_binding_mismatch")
    return receipt


def _validate_packet_claims(
    source: _StrictJson,
    policy: ContentProductionAcceptancePolicy,
    rows: tuple[ContentProductionClassificationRow, ...],
    counts: ContentProductionClassificationCounts,
) -> None:
    raw_counts = source.require_object_member(source.packet, "counts")
    claimed = ContentProductionClassificationCounts(
        **{
            name: source.integer(raw_counts.get(name), "count_invalid")
            for name in ContentProductionClassificationCounts.model_fields
        }
    )
    if claimed != counts or counts != policy.expected_counts:
        _invalid("derived_counts_mismatch")
    approved = sum(row.revision_approved for row in rows)
    if approved != policy.expected_approved_revisions or approved != counts.reuse:
        _invalid("approved_revision_count_mismatch")
    _validate_typed_uniqueness(rows)
    _validate_evidence_defect(policy, rows)
    _validate_protected_binding(policy, rows)


def _validate_evidence_defect(
    policy: ContentProductionAcceptancePolicy,
    rows: tuple[ContentProductionClassificationRow, ...],
) -> None:
    expected = policy.invalid_evidence
    defects = [defect for row in rows for defect in row.lineage_defects]
    proof_ids = {
        item for row in rows for item in (*row.primary_evidence_ids, *row.lineage_evidence_ids)
    }
    blocker_count = sum(
        blocker.code == expected.blocker_code for row in rows for blocker in row.blockers
    )
    if (
        len(defects) != expected.occurrence_count
        or sum(defect.evidence_id == expected.evidence_id for defect in defects)
        != expected.occurrence_count
        or expected.evidence_id in proof_ids
        or blocker_count != expected.occurrence_count
    ):
        _invalid("invalid_evidence_used_as_proof")


def _validate_protected_binding(
    policy: ContentProductionAcceptancePolicy,
    rows: tuple[ContentProductionClassificationRow, ...],
) -> None:
    expected = policy.protected_binding
    row = next((item for item in rows if item.canonical_path == expected.canonical_path), None)
    binding = None if row is None else row.retained_binding
    if row is None or binding is None:
        _invalid("protected_binding_missing")
    if (
        row.decision != "reuse"
        or row.current_work_item_id != expected.current_work_item_id
        or row.retained_work_item_id != expected.retained_work_item_id
        or binding.retained_revision_id != expected.revision_id
        or binding.retained_revision_digest != expected.revision_digest
        or binding.verified_draft_action_ids != expected.action_ids
        or binding.verified_draft_post_ids != expected.draft_post_ids
        or binding.identity_reconciliation_status != expected.identity_status
    ):
        _invalid("protected_binding_drift")


def _judge_receipt(
    source: _StrictJson,
    policy: ContentProductionAcceptancePolicy,
    *,
    packet_sha256: str,
) -> ContentProductionJudgeReceipt:
    if (
        source.judge_text("schema_version") != policy.judge_schema_version
        or source.judge_text("reviewer_role") != policy.judge_reviewer_role
        or source.judge_text("verdict") != "accept"
        or source.judge_text("reviewed_packet_sha256") != packet_sha256
        or source.judge_text("reviewed_decision_set_digest") != policy.decision_set_digest
    ):
        _invalid("judge_review_receipt_mismatch")
    checks = source.require_object_member(source.judge, "checks")
    for name in (
        "packet_sha256_exact",
        "decision_set_digest_recomputed",
        "source_file_receipts_exact",
        "source_row_receipts_exact",
    ):
        if source.boolean(checks.get(name), "judge_check_invalid") is not True:
            _invalid("judge_check_failed")
    if source.integer(
        checks.get("absolute_temp_path_count"), "judge_path_count_invalid"
    ) or source.integer(checks.get("raw_vendor_payload_count"), "judge_payload_count_invalid"):
        _invalid("judge_safety_check_failed")
    _validate_judge_binding(source, checks, policy)
    return ContentProductionJudgeReceipt(
        schema_version=policy.judge_schema_version,
        sha256=policy.judge_sha256,
        reviewer_role=policy.judge_reviewer_role,
        verdict="accept",
        reviewed_packet_sha256=packet_sha256,
        reviewed_decision_set_digest=policy.decision_set_digest,
        generated_at=source.judge_text("generated_at"),
    )


def _validate_judge_binding(
    source: _StrictJson,
    checks: dict[str, object],
    policy: ContentProductionAcceptancePolicy,
) -> None:
    expected = policy.protected_binding
    item = source.require_object_member(checks, policy.judge_protected_binding_check_name)
    if (
        item.get("decision") != "reuse"
        or item.get("revision_id") != expected.revision_id
        or item.get("revision_digest") != expected.revision_digest
        or item.get("action_id") != expected.action_ids[0]
        or item.get("draft_post_id") != expected.draft_post_ids[0]
        or item.get("exact_revision_action_draft_binding") is not True
        or item.get("current_retained_work_item_status") != expected.judge_identity_status
        or item.get("must_not_regenerate") is not True
    ):
        _invalid("judge_protected_binding_drift")


class _StrictJson:
    _PUBLIC_PATH_LOCATIONS = frozenset(
        {
            ("packet", "rows", "path"),
            ("packet", "identity_validation", "stale_applied_action_paths"),
            ("packet", "identity_validation", "quarantined_draft_paths"),
            ("packet", "coverage_validation", "missing_paths"),
            ("packet", "coverage_validation", "extra_paths"),
            ("judge", "checks", "canonical_keep_scope", "missing_paths"),
            ("judge", "checks", "canonical_keep_scope", "extra_paths"),
        }
    )
    _PUBLIC_ENDPOINT_LOCATIONS = frozenset(
        {
            (
                "packet",
                "source_file_receipts",
                "wilq_content_diagnostics",
                "endpoint",
            )
        }
    )
    _PUBLIC_PATH_RE = re.compile(r"/[^\s?#\\]*\Z")
    _PUBLIC_ENDPOINT_RE = re.compile(r"GET /[^\s?#\\]*\Z")
    _ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9:/.])/(?!/)")
    _HTTPS_URL_RE = re.compile(r"(?i)https://[^\s]+\Z")
    _URI_USERINFO_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s?#@]*@")
    _SENSITIVE_PATH_COMPONENT_RE = re.compile(
        r"(?ix)(?:^|/)(?:\.env(?:\.[^/\s]*)?|\.ssh|credentials?[^/\s]*|"
        r"id_(?:dsa|ecdsa|ed25519|rsa)(?:\.[^/\s]*)?|authorized_keys|known_hosts|"
        r"private[_-]?key(?:\.[^/\s]*)?|[^/\s]+\.(?:key|p12|pem|pfx|ppk))"
        r"(?:/|$)"
    )
    _FILESYSTEM_LOCATOR_RE = re.compile(
        r"(?ix)(?:\b(?:file|nfs|scp|smb|ssh):/{1,3}|"
        r"(?<![A-Za-z0-9])(?:[A-Z]:/|~(?:[A-Za-z0-9._-]+)?(?:/|$))|"
        r"(?:\$(?:HOME|USERPROFILE)|\$\{(?:HOME|USERPROFILE)\}|"
        r"\$env:(?:HOME|USERPROFILE)|\$\{env:(?:HOME|USERPROFILE)\}|"
        r"%(?:HOME|HOMEPATH|USERPROFILE)%|%HOMEDRIVE%%HOMEPATH%)(?=/|$)|"
        r"(?<!:)//[^/\s]+/[^/\s]+|"
        r"(?<![A-Za-z0-9.])\.\.(?:/|$)|/\.\.(?:/|$))"
    )
    _SECRET_KEY_RE = re.compile(
        r"(?i)(?:^|[_-])(?:access[_-]?token|api[_-]?key|client[_-]?secret|"
        r"credentials?|password|refresh[_-]?token|secret|token|authorization|"
        r"private(?:[_-]?key)?)(?:$|[_-])"
    )
    _SECRET_VALUE_RE = re.compile(
        r"(?i)(?:gh[opusr]_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_-]{16,}|"
        r"ya29\.[A-Za-z0-9._-]{16,}|AKIA[A-Z0-9]{16}|"
        r"Bearer\s+\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
        r"Basic\s+\S+|"
        r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|"
        r"[?&](?:access_token|api_key|authorization|client_secret|password|"
        r"private_key|refresh_token|token)=|"
        r"(?<![A-Za-z0-9_-])(?:access[_-]?token|api[_-]?key|authorization|"
        r"client[_-]?secret|credentials?|password|private[_-]?key|refresh[_-]?token|"
        r"secret|token)\s*(?:=|:)\s*\S+)"
    )
    _IDENTITY_PUNCTUATION = frozenset("_ .@:-")

    def __init__(self, packet_bytes: bytes, judge_bytes: bytes) -> None:
        self.packet = self._decode(packet_bytes, "packet")
        self.judge = self._decode(judge_bytes, "judge")

    def packet_text(self, key: str) -> str:
        return self.text(self.packet.get(key), "packet_text_invalid")

    def judge_text(self, key: str) -> str:
        return self.text(self.judge.get(key), "judge_text_invalid")

    def safe_identity(self, value: str, code: str) -> str:
        self._reject_unsafe(value)
        identity = self.text(value, code)
        if any(
            not (character.isalnum() or character in self._IDENTITY_PUNCTUATION)
            for character in identity
        ):
            _invalid(code)
        return identity

    @staticmethod
    def model(model_type: type[_SignedModel], value: object) -> _SignedModel:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return model_type.model_validate_json(encoded, strict=True)

    @classmethod
    def _decode(cls, data: bytes, document: str) -> dict[str, object]:
        try:
            decoded = json.loads(
                data.decode("utf-8"),
                object_pairs_hook=cls._unique_object,
                parse_constant=cls._reject_nonfinite,
                parse_float=cls._parse_finite_float,
            )
        except (TypeError, UnicodeDecodeError, ValueError):
            _invalid("invalid_json")
        if not isinstance(decoded, dict):
            _invalid("json_object_required")
        result = cast(dict[str, object], decoded)
        cls._reject_unsafe(result, (document,))
        return result

    @staticmethod
    def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    @staticmethod
    def _reject_nonfinite(_: str) -> Never:
        raise ValueError("non-finite JSON")

    @staticmethod
    def _parse_finite_float(value: str) -> float:
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("non-finite JSON")
        return parsed

    @classmethod
    def _reject_unsafe(cls, value: object, field_path: tuple[str, ...] = ()) -> None:
        if isinstance(value, str):
            normalized = value.replace("\\", "/")
            is_public_locator = cls._is_public_locator(field_path, value)
            if (
                cls._FILESYSTEM_LOCATOR_RE.search(normalized)
                or cls._URI_USERINFO_RE.search(value)
                or cls._SECRET_VALUE_RE.search(value)
                or (
                    cls._SENSITIVE_PATH_COMPONENT_RE.search(normalized)
                    and cls._HTTPS_URL_RE.fullmatch(value) is None
                    and not is_public_locator
                )
                or (cls._ABSOLUTE_PATH_RE.search(normalized) and not is_public_locator)
            ):
                _invalid("unsafe_signed_material")
        elif isinstance(value, list):
            for item in value:
                cls._reject_unsafe(item, field_path)
        elif isinstance(value, dict):
            for key, item in cast(dict[str, object], value).items():
                if cls._SECRET_KEY_RE.search(key):
                    _invalid("unsafe_signed_material")
                cls._reject_unsafe(key)
                cls._reject_unsafe(item, (*field_path, key))

    @classmethod
    def _is_public_locator(cls, field_path: tuple[str, ...], value: str) -> bool:
        if field_path in cls._PUBLIC_PATH_LOCATIONS:
            return cls._PUBLIC_PATH_RE.fullmatch(value) is not None
        if field_path in cls._PUBLIC_ENDPOINT_LOCATIONS:
            return cls._PUBLIC_ENDPOINT_RE.fullmatch(value) is not None
        return False

    @classmethod
    def reject_enabled_generation(cls, value: object) -> None:
        if isinstance(value, list):
            for item in value:
                cls.reject_enabled_generation(item)
        elif isinstance(value, dict):
            for key, item in cast(dict[str, object], value).items():
                generation_key = key in {
                    "generation_allowed",
                    "new_generation_allowed",
                    "initial_generation_allowed",
                }
                if (
                    generation_key
                    and item is not False
                    and not (key == "generation_allowed" and type(item) is int and item == 0)
                ):
                    _invalid("generation_not_disabled")
                cls.reject_enabled_generation(item)

    @staticmethod
    def require_object(value: object, code: str) -> dict[str, object]:
        if not isinstance(value, dict):
            _invalid(code)
        return cast(dict[str, object], value)

    @classmethod
    def require_object_member(cls, value: dict[str, object], key: str) -> dict[str, object]:
        return cls.require_object(value.get(key), "object_member_required")

    @staticmethod
    def array(value: object, code: str) -> list[object]:
        if not isinstance(value, list):
            _invalid(code)
        return cast(list[object], value)

    @classmethod
    def array_member(cls, value: dict[str, object], key: str) -> list[object]:
        return cls.array(value.get(key), "array_member_required")

    @staticmethod
    def text(value: object, code: str) -> str:
        if not isinstance(value, str) or not value.strip():
            _invalid(code)
        return value

    @classmethod
    def optional_text(cls, value: object) -> str | None:
        return None if value is None else cls.text(value, "optional_text_invalid")

    @classmethod
    def texts(cls, value: object, code: str) -> tuple[str, ...]:
        return tuple(cls.text(item, code) for item in cls.array(value, code))

    @staticmethod
    def boolean(value: object, code: str) -> bool:
        if not isinstance(value, bool):
            _invalid(code)
        return value

    @staticmethod
    def optional_bool(value: object) -> bool | None:
        if value is None:
            return None
        if not isinstance(value, bool):
            _invalid("optional_boolean_invalid")
        return value

    @staticmethod
    def integer(value: object, code: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            _invalid(code)
        return value

    @staticmethod
    def classification(value: object) -> Classification:
        if value not in {"reuse", "refresh", "write", "blocked"}:
            _invalid("classification_invalid")
        return cast(Classification, value)


def _invalid(code: str) -> Never:
    raise ContentProductionClassificationValidationError(code)


__all__ = ["parse_content_production_classification_impl"]
