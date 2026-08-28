from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from scripts.content_keep_eligibility import (
    EXPECTED_COUNTS,
    EXPECTED_PRIMARY_BLOCKERS,
    CliInputError,
    _parse_json,
    main,
)
from wilq.content.workflow.keep_eligibility import (
    KeepEligibilityError,
    KeepEligibilityInput,
    SourceProvenance,
    build_keep_eligibility_projection,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTHORING_PATH = REPO_ROOT / "docs/content-dev-authoring-inventory-20260828.json"
JOURNAL_PATH = REPO_ROOT / "docs/content-dev-state-journal-20260828.json"
LEDGER_PATH = REPO_ROOT / "docs/content-canonical-ledger-20260828.jsonl"
CONTEXT_PATH = REPO_ROOT / "docs/content-keep-eligibility-context-20260828.json"
ARTIFACT_PATH = REPO_ROOT / "docs/content-keep-eligibility-20260828.json"
SOURCE_PATHS = {
    "authoring_inventory": AUTHORING_PATH,
    "state_journal": JOURNAL_PATH,
    "canonical_ledger": LEDGER_PATH,
    "context": CONTEXT_PATH,
}
SYNTHETIC_PATH = "/"


def test_current_projection_has_exact_partition_and_zero_eligibility() -> None:
    projection = build_keep_eligibility_projection(production_input())
    assert projection == json.loads(ARTIFACT_PATH.read_bytes())
    assert projection["summary"] | {} == {
        "keep_count": 57,
        "exact_authoring_target_count": 57,
        "retained_work_item_count": 27,
        "current_work_item_count": 54,
        "joined_work_item_count": 27,
        "exact_work_item_id_equal_count": 0,
        "reconciled_work_item_count": 0,
        "current_revision_count": 13,
        "exact_service_binding_count": 7,
        "source_pack_work_item_binding_count": 0,
        "existing_generation_identity_count": 9,
        "typed_target_context_count": 0,
        "eligible_count": 0,
        "primary_blocker_counts": dict(EXPECTED_PRIMARY_BLOCKERS),
        "source_refs": {
            key: path.relative_to(REPO_ROOT).as_posix() for key, path in SOURCE_PATHS.items()
        },
        "source_sha256": {
            key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in SOURCE_PATHS.items()
        },
    }
    rows = projection["rows"]
    assert len({row["path"] for row in rows}) == 57
    assert all(row["authoring_target"]["rest_object_observed"] is True for row in rows)
    assert all(row["canonical_lineage"]["source_pack_work_item_ids"] == [] for row in rows)
    assert all(row["target_context"]["validation_status"] == "absent" for row in rows)
    assert all(row["connector_context"]["all_resolved_fresh"] is True for row in rows)
    assert all(
        row["connector_context"]["page_performance_membership_verified"] is False
        and row["keyword_planner"]
        == {
            "status": "blocked",
            "factual_signal_only": True,
            "hard_eligibility_gate": False,
        }
        for row in rows
    )
    assert all_false_authority(rows)


@pytest.mark.parametrize("field", ("identity_reconciliations", "target_contexts"))
def test_digest_only_claims_are_not_accepted_by_public_input(field: str) -> None:
    source = synthetic_input()
    digest_only_claim = {
        "path": SYNTHETIC_PATH,
        "evidence_id": "ev_self_certified",
        "evidence_source": "caller_assertion",
        "revision_digest": "a" * 64,
        "target_contract_digest": "b" * 64,
        "binding_digest": "c" * 64,
        "confirmation_digest": "d" * 64,
        "payload_digest": "e" * 64,
    }

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        replace(source, **{field: (digest_only_claim,)})


def test_unreconciled_work_identity_fork_fails_closed() -> None:
    source = synthetic_input()
    journal = deepcopy(source.state_journal)
    journal["urls"][0]["planning_probe_work_item_id"] = "work_item_retained_fork"
    source = replace(
        source,
        state_journal=journal,
        expected_counts=synthetic_counts(
            exact_work_item_id_equal_count=0,
            source_pack_work_item_binding_count=0,
        ),
        expected_primary_blocker_counts=(("work_item_identity_fork", 1),),
    )
    row = build_keep_eligibility_projection(source)["rows"][0]
    assert row["work_item_identity"]["status"] == "fork"
    assert row["work_item_identity"]["retained_journal_work_item_id"]
    assert row["work_item_identity"]["current_catalog_work_item_id"]
    assert row["work_item_identity"]["resolved_work_item_id"] is None
    assert row["primary_blocker"] == "work_item_identity_fork"


def test_old_journal_service_card_id_is_never_exact_binding_proof() -> None:
    source = synthetic_input()
    journal = deepcopy(source.state_journal)
    journal["urls"][0]["planning_service_card_id"] = "ekologus_service_wrong"
    source = replace(source, state_journal=journal)
    row = build_keep_eligibility_projection(source)["rows"][0]
    assert row["service_binding"]["journal_planning_service_card_id"]
    assert row["service_binding"]["journal_id_used_as_binding_proof"] is False
    assert row["service_binding"]["status"] == "verified"


def test_source_pack_path_join_is_not_work_item_id_binding() -> None:
    source = synthetic_input()
    ledger = deepcopy(source.canonical_ledger)
    ledger[0]["work_item_ids"] = []
    source = replace(
        source,
        canonical_ledger=ledger,
        expected_counts=synthetic_counts(
            source_pack_work_item_binding_count=0,
            eligible_count=0,
        ),
        expected_primary_blocker_counts=(("source_pack_work_item_binding_unverified", 1),),
    )
    row = build_keep_eligibility_projection(source)["rows"][0]
    assert row["canonical_lineage"]["path_join_is_work_item_id_proof"] is False
    assert row["primary_blocker"] == "source_pack_work_item_binding_unverified"


def test_existing_verified_draft_has_first_blocker_precedence() -> None:
    source = synthetic_input()
    journal = deepcopy(source.state_journal)
    journal["drafts"] = [
        {
            "revision_id": "revision_existing",
            "path": SYNTHETIC_PATH,
            "canonical_disposition": "keep",
            "state_class": "dev_draft_verified",
        }
    ]
    source = replace(
        source,
        state_journal=journal,
        expected_counts=synthetic_counts(
            existing_generation_identity_count=1,
            eligible_count=0,
        ),
        expected_primary_blocker_counts=(("existing_verified_draft_or_applied_action", 1),),
    )
    row = build_keep_eligibility_projection(source)["rows"][0]
    assert row["existing_generation_identity"]["verified_keep_draft"] is True
    assert row["primary_blocker"] == "existing_verified_draft_or_applied_action"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("path", "wilq/content/knowledge/wrong.py"),
        ("sha256", "a" * 64),
        ("commit", "441579eb"),
        ("map", "wrong_service_binding_urls"),
    ),
)
def test_domain_rejects_tampered_service_binding_code_source(field: str, value: str) -> None:
    source = production_input()
    context = deepcopy(source.context)
    context["service_bindings"]["current_code_source"][field] = value

    with pytest.raises(KeepEligibilityError, match="service binding current code source"):
        build_keep_eligibility_projection(replace(source, context=context))


@pytest.mark.parametrize(
    ("field", "value"),
    (("api_observed_url_count", 1), ("current_code_url_count", 6)),
)
def test_domain_rejects_tampered_service_binding_counts(field: str, value: int) -> None:
    source = production_input()
    context = deepcopy(source.context)
    context["service_bindings"][field] = value

    with pytest.raises(KeepEligibilityError, match=field):
        build_keep_eligibility_projection(replace(source, context=context))


def test_domain_rejects_tampered_service_binding_row_count() -> None:
    source = production_input()
    context = deepcopy(source.context)
    context["service_bindings"]["current_exact_bindings"].pop()

    with pytest.raises(KeepEligibilityError, match="current exact binding rows"):
        build_keep_eligibility_projection(replace(source, context=context))


def test_binding_rows_must_match_attested_source_map() -> None:
    source = production_input()
    context = deepcopy(source.context)
    context["service_bindings"]["current_exact_bindings"][0]["service_card_id"] = (
        "ekologus_service_environmental_training"
    )

    with pytest.raises(KeepEligibilityError, match="attested source map"):
        build_keep_eligibility_projection(replace(source, context=context))


@pytest.mark.parametrize(
    ("source_name", "mutate", "message"),
    [
        (
            "authoring_inventory",
            lambda value: value.__setitem__("raw_body_retained", True),
            "raw_body_retained",
        ),
        (
            "context",
            lambda value: value["safety"].__setitem__("raw_material_read", True),
            "raw_material_read",
        ),
    ],
)
def test_source_safety_flags_reject_raw_state(source_name: str, mutate: Any, message: str) -> None:
    source = production_input()
    value = deepcopy(getattr(source, source_name))
    mutate(value)
    with pytest.raises(KeepEligibilityError, match=message):
        build_keep_eligibility_projection(replace(source, **{source_name: value}))


def test_duplicate_rows_and_noncanonical_paths_are_rejected() -> None:
    source = synthetic_input()
    with pytest.raises(KeepEligibilityError, match="Duplicate canonical ledger path"):
        build_keep_eligibility_projection(
            replace(source, canonical_ledger=[*source.canonical_ledger, source.canonical_ledger[0]])
        )
    context = deepcopy(source.context)
    context["inventory"]["rows"][0]["path"] = "/trailing/"
    with pytest.raises(KeepEligibilityError, match="Non-canonical exact path"):
        build_keep_eligibility_projection(replace(source, context=context))


def test_duplicate_json_keys_are_rejected_before_projection() -> None:
    with pytest.raises(CliInputError, match="Powtórzony klucz JSON"):
        _parse_json(b'{"schema_version":"one","schema_version":"two"}', "fixture.json")


def test_cli_check_is_deterministic_and_source_drift_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--output", str(ARTIFACT_PATH), "--check"]) == 0
    drifted = tmp_path / "authoring.json"
    drifted.write_bytes(AUTHORING_PATH.read_bytes() + b"\n")
    assert (
        main(
            [
                "--authoring-inventory",
                str(drifted),
                "--output",
                str(ARTIFACT_PATH),
                "--check",
            ]
        )
        == 1
    )
    assert "Niezgodny SHA-256" in capsys.readouterr().err


def test_cli_check_fails_on_binding_source_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    drifted = tmp_path / "source_facts.py"
    binding_source = REPO_ROOT / "wilq/content/knowledge/source_facts.py"
    drifted.write_bytes(binding_source.read_bytes() + b"\n")

    assert (
        main(
            [
                "--binding-source",
                str(drifted),
                "--output",
                str(ARTIFACT_PATH),
                "--check",
            ]
        )
        == 1
    )
    assert "Niezgodny SHA-256" in capsys.readouterr().err


def production_input() -> KeepEligibilityInput:
    payloads = {
        "authoring_inventory": json.loads(AUTHORING_PATH.read_bytes()),
        "state_journal": json.loads(JOURNAL_PATH.read_bytes()),
        "canonical_ledger": [
            json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines()
        ],
        "context": json.loads(CONTEXT_PATH.read_bytes()),
    }
    provenance = {
        key: SourceProvenance(
            source_ref=path.relative_to(REPO_ROOT).as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for key, path in SOURCE_PATHS.items()
    }
    return KeepEligibilityInput(
        **payloads,
        provenance=provenance,
        expected_counts=EXPECTED_COUNTS,
        expected_primary_blocker_counts=EXPECTED_PRIMARY_BLOCKERS,
    )


def synthetic_input() -> KeepEligibilityInput:
    source = production_input()
    authoring = deepcopy(source.authoring_inventory)
    authoring["rows"] = [row for row in authoring["rows"] if row["path"] == SYNTHETIC_PATH]
    journal = deepcopy(source.state_journal)
    journal["urls"] = [row for row in journal["urls"] if row["path"] == SYNTHETIC_PATH]
    journal["drafts"] = []
    journal["mutation_audits"] = []
    ledger = [
        deepcopy(row)
        for row in source.canonical_ledger
        if row["public_url"] == "https://www.ekologus.pl/"
    ]
    context = deepcopy(source.context)
    context["inventory"]["rows"] = [
        row for row in context["inventory"]["rows"] if row["path"] == SYNTHETIC_PATH
    ]
    journal_row, catalog_row = journal["urls"][0], context["inventory"]["rows"][0]
    current_id = catalog_row["current_work_item_id"]
    journal_row["planning_probe_work_item_id"] = current_id
    ledger[0]["work_item_ids"] = [current_id]
    return KeepEligibilityInput(
        authoring_inventory=authoring,
        state_journal=journal,
        canonical_ledger=ledger,
        context=context,
        provenance=source.provenance,
        expected_counts=synthetic_counts(),
        expected_primary_blocker_counts=(("typed_target_context_absent", 1),),
    )


def synthetic_counts(**overrides: int) -> tuple[tuple[str, int], ...]:
    counts = {
        "keep_count": 1,
        "exact_authoring_target_count": 1,
        "retained_work_item_count": 1,
        "current_work_item_count": 1,
        "joined_work_item_count": 1,
        "exact_work_item_id_equal_count": 1,
        "reconciled_work_item_count": 0,
        "current_revision_count": 1,
        "exact_service_binding_count": 1,
        "source_pack_work_item_binding_count": 1,
        "existing_generation_identity_count": 0,
        "typed_target_context_count": 0,
        "eligible_count": 0,
    }
    counts.update(overrides)
    return tuple(counts.items())


def all_false_authority(rows: list[dict[str, Any]]) -> bool:
    return all(
        row["planning_eligible"] is False
        and row["new_generation_allowed"] is False
        and row["publish_allowed"] is False
        and row["write_authorized"] is False
        and row["robot_ready"] is False
        for row in rows
    )
