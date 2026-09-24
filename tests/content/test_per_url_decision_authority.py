from __future__ import annotations

import importlib
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.current_page_identity_v3 import CurrentPageIdentityV3Response
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.schemas.content import ContentFreshnessAssessment
from wilq.schemas.core import ConnectorCoveredWindow


def _identity(
    work_item_id: str,
    path: str,
    material_digest: str,
    *,
    evidence_suffix: str,
) -> CurrentPageIdentityV3Response:
    page_url = f"https://www.ekologus.pl{path}"
    canonical_path = content_normalized_path(page_url)
    identity_digest = canonical_json_digest(
        {
            "schema_version": "wilq_current_page_identity_v3",
            "work_item_id": work_item_id,
            "page_url": page_url,
            "canonical_path": canonical_path,
            "material_meaning_digest": material_digest,
        }
    )
    current_evidence_ids = (f"ev_current_{evidence_suffix}",)
    catalog_evidence_ids = (f"ev_catalog_{evidence_suffix}",)
    evidence_digest = canonical_json_digest(
        {
            "schema_version": "wilq_current_page_evidence_binding_v3",
            "identity_digest": identity_digest,
            "source_status": "observed_material_current",
            "current_evidence_ids": current_evidence_ids,
            "catalog_evidence_ids": catalog_evidence_ids,
        }
    )
    return CurrentPageIdentityV3Response(
        status="exact_current",
        work_item_id=work_item_id,
        page_url=page_url,
        canonical_path=canonical_path,
        material_meaning_digest=material_digest,
        identity_id=f"current_page_identity_v3_{identity_digest[:24]}",
        identity_digest=identity_digest,
        evidence_digest=evidence_digest,
        source_status="observed_material_current",
        current_evidence_ids=current_evidence_ids,
        catalog_evidence_ids=catalog_evidence_ids,
        safe_next_step="Sprawdź aktualne źródła dla dokładnej strony.",
    )


def _policy_facts(
    authority: object,
    identity: CurrentPageIdentityV3Response,
    *,
    fact_digest: str,
    evidence_suffix: str,
    checked_at: datetime,
    stale_connectors: tuple[str, ...] = (),
) -> object:
    fact_type = authority.ContentPerUrlPolicyFact
    policy_type = authority.ContentPerUrlDecisionPolicyFacts
    fact = fact_type(
        source_fact_id="fact_policy_exact",
        semantic_digest=fact_digest,
        requirement_ids=("requirement_exact",),
        evidence_ids=(f"ev_policy_{evidence_suffix}",),
    )
    return policy_type(
        current_work_item_id=identity.work_item_id,
        public_url=identity.page_url,
        canonical_path=identity.canonical_path,
        policy_id="synthetic_current_acceptance",
        policy_version="policy-v1",
        content_kind="editorial",
        service_card_id=None,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        source_facts=(fact,),
        requirement_ids=("requirement_exact",),
        cta_policy_digest="c" * 64,
        freshness_assessment=ContentFreshnessAssessment(
            state="stale" if stale_connectors else "fresh",
            checked_at=checked_at,
            stale_after_hours=48,
            requires_refresh=bool(stale_connectors),
            missing_connector_ids=[],
            blocked_connector_ids=[],
            stale_connector_ids=list(stale_connectors),
            connector_covered_windows={
                "official_regulatory_review": ConnectorCoveredWindow(
                    snapshot_date=checked_at.date().isoformat(),
                    coverage_scope="exact approved facts",
                    coverage_count=1,
                    covered_count=1,
                ),
                "wordpress_ekologus": ConnectorCoveredWindow(
                    snapshot_date=checked_at.date().isoformat(),
                    coverage_scope="exact current page",
                    coverage_count=1,
                    covered_count=1,
                ),
                "google_search_console": ConnectorCoveredWindow(
                    snapshot_date=checked_at.date().isoformat(),
                    coverage_scope="optional demand evidence",
                    coverage_count=1,
                    covered_count=1,
                ),
            },
            summary="Synthetic exact per-URL connector freshness.",
            next_step="Read exact current sources before deciding.",
        ),
        freshness_connector_ids=("official_regulatory_review", "wordpress_ekologus"),
        freshness_evidence_ids=(f"ev_freshness_{evidence_suffix}",),
    )


def _record_observation(
    authority: object,
    store: object,
    *,
    page_key: str,
    material_digest: str,
    fact_digest: str,
    evidence_suffix: str,
    observed_at: datetime,
    wave_id: str,
    stale_connectors: tuple[str, ...] = (),
) -> object:
    identity = _identity(
        f"work_item_{page_key}",
        f"/page-{page_key}/",
        material_digest,
        evidence_suffix=evidence_suffix,
    )
    policy = _policy_facts(
        authority,
        identity,
        fact_digest=fact_digest,
        evidence_suffix=evidence_suffix,
        checked_at=observed_at,
        stale_connectors=stale_connectors,
    )
    observation = authority.build_content_per_url_decision_observation(
        identity,
        policy,
        observed_at=observed_at,
        source_wave_id=wave_id,
    )
    result = store.record_content_per_url_decision_observation(observation)
    assert result[0] == "created"
    return observation


def _assert_required_freshness_blocks(
    authority: object,
    identity: CurrentPageIdentityV3Response,
    wave_one: datetime,
    wave_two: datetime,
) -> None:
    stale_policy = _policy_facts(
        authority,
        identity,
        fact_digest="1" * 64,
        evidence_suffix="a_stale",
        checked_at=wave_one,
        stale_connectors=("wordpress_ekologus",),
    )
    with pytest.raises(authority.ContentPerUrlDecisionAuthorityBlocked) as captured:
        authority.build_content_per_url_decision_observation(
            identity,
            stale_policy,
            observed_at=wave_two,
            source_wave_id="classification-wave-two",
        )
    assert captured.value.code == "per_url_required_connector_freshness_blocked"
    expired_policy = _policy_facts(
        authority,
        identity,
        fact_digest="1" * 64,
        evidence_suffix="a_expired",
        checked_at=wave_one - timedelta(hours=49),
    )
    with pytest.raises(authority.ContentPerUrlDecisionAuthorityBlocked) as captured:
        authority.build_content_per_url_decision_observation(
            identity,
            expired_policy,
            observed_at=wave_two,
            source_wave_id="classification-wave-two",
        )
    assert captured.value.code == "per_url_freshness_assessment_expired"


def _assert_observation_is_append_only(store: object, observation: object) -> None:
    with store._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE content_per_url_decision_observations SET payload_json = '{}' "
                "WHERE observation_id = ?",
                (observation.observation_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM content_per_url_decision_observations WHERE observation_id = ?",
                (observation.observation_id,),
            )


def test_per_url_authority_currentness_is_independent_and_append_only(
    tmp_path,
) -> None:
    try:
        authority = importlib.import_module(
            "wilq.content.workflow.per_url_decision_authority"
        )
    except ImportError as error:
        raise AssertionError(
            "Per-URL decision authority must not depend on a classification batch."
        ) from error

    from wilq.content.workflow.store.store import ContentWorkflowStore

    project_currentness = authority.project_content_per_url_currentness
    store = ContentWorkflowStore(tmp_path / "per-url-authority.sqlite3")
    wave_one = datetime(2026, 9, 24, 10, tzinfo=UTC)
    wave_two = datetime(2026, 9, 24, 11, tzinfo=UTC)
    a_one = _record_observation(
        authority, store, page_key="a", material_digest="a" * 64,
        fact_digest="1" * 64, evidence_suffix="a1", observed_at=wave_one,
        wave_id="classification-wave-one",
    )
    b_one = _record_observation(
        authority, store, page_key="b", material_digest="b" * 64,
        fact_digest="2" * 64, evidence_suffix="b1", observed_at=wave_one,
        wave_id="classification-wave-one",
    )
    _assert_required_freshness_blocks(
        authority,
        _identity("work_item_a", "/page-a/", "a" * 64, evidence_suffix="a_stale"),
        wave_one,
        wave_two,
    )
    a_two = _record_observation(
        authority, store, page_key="a", material_digest="a" * 64,
        fact_digest="1" * 64, evidence_suffix="a2", observed_at=wave_two,
        wave_id="classification-wave-two",
        stale_connectors=("google_search_console",),
    )
    b_two = _record_observation(
        authority, store, page_key="b", material_digest="b" * 64,
        fact_digest="3" * 64, evidence_suffix="b2", observed_at=wave_two,
        wave_id="classification-wave-two",
    )
    assert a_one.semantic_row_digest == a_two.semantic_row_digest
    assert a_one.evidence_digest != a_two.evidence_digest
    assert b_one.semantic_row_digest != b_two.semantic_row_digest
    assert store.record_content_per_url_decision_observation(a_two)[0] == "idempotent"

    changed_material_identity = _identity(
        "work_item_a", "/page-a/", "d" * 64, evidence_suffix="a3"
    )
    changed_material_policy = _policy_facts(
        authority,
        changed_material_identity,
        fact_digest="1" * 64,
        evidence_suffix="a3",
        checked_at=wave_two,
    )
    changed_material = authority.build_content_per_url_decision_observation(
        changed_material_identity,
        changed_material_policy,
        observed_at=wave_two,
        source_wave_id="classification-wave-three",
    )
    assert changed_material.semantic_row_digest != a_one.semantic_row_digest
    assert store.load_content_per_url_decision_observation(a_two.observation_id) == a_two
    assert store.list_content_per_url_decision_observations("/page-a") == [a_one, a_two]
    assert project_currentness(a_one, a_two).status == "current"
    assert project_currentness(b_one, b_two).status == "superseded"

    _assert_observation_is_append_only(store, a_two)
