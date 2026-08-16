from __future__ import annotations

from hashlib import sha256
from json import dumps

from wilq.content.drafts import initial_full_draft_turn, regulatory_patch

_REALISTIC_PATCH_OUTPUT_JSON = (
    '{"sections":['
    '{"section_id":"section_01","mode":"replace",'
    '"body_markdown":"Zwolnienie zależy od spełnienia warunków ustawowych."},'
    '{"section_id":"section_02","mode":"append",'
    '"body_markdown":"KPO stosuje się, gdy przekazanie odpadów podlega ewidencji."}'
    '],"publish_ready":false}'
)
_LEGACY_PATCH_OUTPUT_DIGEST = "2c0f2c6e99444789cb5674aba85045fc7b7e4fed9f6e8cf315f95a5c5b375c92"  # pragma: allowlist secret
_LEGACY_TURN_SCHEMA_DIGEST = "0eccc59fd3450b63c6ce80b8a73e6bf9e3b2d9bb853f5345aa1c74d283d60609"  # pragma: allowlist secret


def test_regulatory_patch_contract_has_one_public_owner() -> None:
    assert hasattr(regulatory_patch, "RegulatorySectionPatch")
    assert hasattr(regulatory_patch, "RegulatoryAssertionRepairOutput")
    assert not hasattr(initial_full_draft_turn, "_RegulatorySectionPatch")
    assert not hasattr(initial_full_draft_turn, "_RegulatoryAssertionRepairOutput")


def test_regulatory_patch_output_round_trips_without_digest_drift() -> None:
    output = regulatory_patch.RegulatoryAssertionRepairOutput.model_validate_json(
        _REALISTIC_PATCH_OUTPUT_JSON
    )

    round_tripped = output.model_dump_json()

    assert round_tripped == _REALISTIC_PATCH_OUTPUT_JSON
    assert sha256(round_tripped.encode()).hexdigest() == _LEGACY_PATCH_OUTPUT_DIGEST


def test_regulatory_patch_turn_schema_keeps_legacy_wire_shape() -> None:
    schema = regulatory_patch.regulatory_assertion_repair_output_schema(
        ["section_01", "section_02"]
    )
    canonical_schema = dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    assert sha256(canonical_schema.encode()).hexdigest() == _LEGACY_TURN_SCHEMA_DIGEST
