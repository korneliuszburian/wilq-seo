from __future__ import annotations

import pytest

from wilq.content.planning.mode_contracts import (
    ContentPlanningModeAllowedPath,
    ContentPlanningModeRequest,
    content_planning_mode_readiness,
)
from wilq.content.workflow.target.public_to_dev_mapping import ContentPublicToDevMapping

PUBLIC_URL = "https://www.ekologus.pl/bdo/"


def _exact_migration_target() -> ContentPublicToDevMapping:
    return ContentPublicToDevMapping(
        mapping_status="exact",
        public_url=PUBLIC_URL,
        dev_url="https://ekologus.dev.proudsite.pl/bdo/",
        dev_post_id="346",
        evidence_ids=["ev_public_dev_relation_bdo"],
        basis="confirmed_inventory_relation",
        reason="Dokładna relacja została potwierdzona dowodem.",
    )


def test_create_mode_is_allowed_without_a_public_canonical_source() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="create",
            service_card_id="ekologus_service_environmental_audit",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.model_dump(mode="json") == {
        "status": "allowed",
        "mode": "create",
        "path": "create",
        "routing_status": "contract_only",
        "brief_required": True,
        "write_authorized": False,
    }


def test_create_mode_blocks_a_public_canonical_source() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="create",
            service_card_id="ekologus_service_environmental_audit",
            public_canonical_url="https://www.ekologus.pl/audyt-srodowiskowy/",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "create_public_source_conflict"
    assert readiness.outcome.path is None


def test_create_mode_requires_an_explicit_service_identity() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="create",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_create_service_identity"


def test_create_mode_requires_an_explicit_foundation_identity() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="create",
            service_card_id="ekologus_service_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_create_foundation_identity"


def test_create_mode_requires_an_explicit_ia_identity() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="create",
            service_card_id="ekologus_service_environmental_audit",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location=" ",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_create_ia_identity"


def test_migration_mode_keeps_its_own_path_with_source_and_explicit_target() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="migration",
            public_canonical_url=PUBLIC_URL,
            migration_target=_exact_migration_target(),
        )
    )

    assert readiness.outcome.model_dump(mode="json") == {
        "status": "allowed",
        "mode": "migration",
        "path": "migration",
        "routing_status": "contract_only",
        "brief_required": True,
        "write_authorized": False,
    }


def test_migration_mode_cannot_be_relabelled_as_refresh_existing() -> None:
    with pytest.raises(ValueError, match="mode and path"):
        ContentPlanningModeAllowedPath(
            mode="migration",
            path="refresh_existing",
            routing_status="contract_only",
        )


def test_migration_mode_requires_an_existing_public_source() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="migration",
            migration_target=_exact_migration_target(),
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_migration_public_source"


def test_migration_mode_requires_an_explicit_target_identity() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="migration",
            public_canonical_url=PUBLIC_URL,
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_migration_target_identity"


def test_migration_mode_rejects_an_unverified_target_relation() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="migration",
            public_canonical_url=PUBLIC_URL,
            migration_target=ContentPublicToDevMapping(
                mapping_status="unverified",
                public_url=PUBLIC_URL,
                dev_url="https://ekologus.dev.proudsite.pl/bdo/",
                dev_post_id="346",
                basis="observed_only",
                blocker="public_to_dev_relation_unverified",
                reason="Zbieżna ścieżka nie potwierdza relacji.",
                next_step="Potwierdź relację źródła z targetem.",
            ),
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "migration_target_not_exact"


def test_migration_mode_requires_target_identity_for_the_same_public_source() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="migration",
            public_canonical_url="https://www.ekologus.pl/outsourcing-srodowiskowy/",
            migration_target=_exact_migration_target(),
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "migration_target_source_mismatch"


def test_structure_mode_blocks_automatic_text_draft_opening() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(requested_mode="structure")
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.mode == "structure"
    assert readiness.outcome.path is None
    assert readiness.outcome.automatic_text_draft_allowed is False
    assert readiness.outcome.blocker.code == "structure_requires_human_decision"
    assert "decyzję o strukturze" in readiness.outcome.blocker.next_step
    assert "szkic" not in readiness.outcome.blocker.next_step.casefold()


def test_no_change_mode_terminates_without_a_brief() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(requested_mode="no_change")
    )

    assert readiness.outcome.model_dump(mode="json") == {
        "status": "terminal",
        "mode": "no_change",
        "path": "end_without_brief",
        "brief_required": False,
        "automatic_text_draft_allowed": False,
        "write_authorized": False,
        "reason": "Decyzja no_change kończy pracę bez przygotowania briefu.",
        "next_step": "Zachowaj decyzję jako wynik tej oceny i nie otwieraj planowania tekstu.",
    }


def test_defer_mode_remains_a_distinct_terminal_without_a_brief() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(requested_mode="defer")
    )

    assert readiness.outcome.status == "terminal"
    assert readiness.outcome.mode == "defer"
    assert readiness.outcome.path == "end_without_brief"
    assert readiness.outcome.brief_required is False
    assert readiness.outcome.automatic_text_draft_allowed is False


def test_unsupported_mode_returns_an_explicit_typed_blocker() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(requested_mode="rewrite_everything")
    )

    assert readiness.requested_mode == "rewrite_everything"
    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.mode is None
    assert readiness.outcome.path is None
    assert readiness.outcome.blocker.code == "unsupported_mode"
    assert all(
        value.strip()
        for value in (
            readiness.outcome.blocker.label,
            readiness.outcome.blocker.reason,
            readiness.outcome.blocker.next_step,
        )
    )


def test_refresh_existing_mode_delegates_only_to_the_existing_flow() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="refresh_existing",
            public_canonical_url=PUBLIC_URL,
        )
    )

    assert readiness.outcome.status == "allowed"
    assert readiness.outcome.mode == "refresh_existing"
    assert readiness.outcome.path == "refresh_existing"
    assert readiness.outcome.routing_status == "existing_flow"


def test_refresh_existing_mode_keeps_the_existing_canonical_requirement() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(requested_mode="refresh_existing")
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_refresh_public_canonical"


def test_refresh_existing_mode_rejects_a_new_page_foundation() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="refresh_existing",
            public_canonical_url=PUBLIC_URL,
            planning_foundation_id="content_foundation_environmental_audit",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "refresh_foundation_conflict"


def test_new_page_mode_delegates_only_to_the_existing_new_page_flow() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="new_page",
            service_card_id="ekologus_service_environmental_audit",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "allowed"
    assert readiness.outcome.mode == "new_page"
    assert readiness.outcome.path == "new_page"
    assert readiness.outcome.routing_status == "existing_flow"


def test_new_page_mode_keeps_the_existing_absent_canonical_requirement() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="new_page",
            service_card_id="ekologus_service_environmental_audit",
            public_canonical_url=PUBLIC_URL,
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "new_page_public_source_conflict"


def test_new_page_mode_keeps_the_existing_service_identity_requirement() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="new_page",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_new_page_service_identity"


def test_new_page_mode_keeps_the_existing_foundation_requirement() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="new_page",
            service_card_id="ekologus_service_environmental_audit",
            proposed_ia_location="Usługi → Audyty środowiskowe",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_new_page_foundation_identity"


def test_new_page_mode_keeps_the_existing_ia_requirement() -> None:
    readiness = content_planning_mode_readiness(
        ContentPlanningModeRequest(
            requested_mode="new_page",
            service_card_id="ekologus_service_environmental_audit",
            planning_foundation_id="content_foundation_environmental_audit",
            proposed_ia_location=" ",
        )
    )

    assert readiness.outcome.status == "blocked"
    assert readiness.outcome.blocker.code == "missing_new_page_ia_identity"
