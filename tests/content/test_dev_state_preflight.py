from __future__ import annotations

import json
from pathlib import Path

from scripts.content_dev_state_preflight import evaluate_journal


def _write_journal(
    tmp_path: Path,
    *,
    url_row: dict,
    drafts: list[dict] | None = None,
    audits: list[dict] | None = None,
) -> Path:
    path = tmp_path / "journal.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "dev_content_state_journal_v1",
                "sources": {},
                "urls": [url_row],
                "drafts": drafts or [],
                "mutation_audits": audits or [],
            }
        ),
        encoding="utf-8",
    )
    return path


def _url_row(**overrides: object) -> dict:
    row = {
        "record_type": "url",
        "path": "/alpha",
        "url": "https://ekologus.dev.proudsite.pl/alpha",
        "final_disposition": "keep",
        "delivery_status": "candidate_blocked",
        "current_revision_id": None,
        "dev_draft_ref": None,
        "planning_probe_status": "ready",
        "planning_probe_work_item_id": "work_alpha",
        "blocker_codes": [],
        "publish_allowed": False,
        "write_authorized": False,
        "robot_ready": False,
    }
    row.update(overrides)
    return row


def test_existing_dev_draft_blocks_repeat_generation(tmp_path: Path) -> None:
    journal = _write_journal(
        tmp_path,
        url_row=_url_row(dev_draft_ref="posts/2001"),
        drafts=[{"post_id": "2001", "path": "/alpha", "state_class": "dev_draft_verified"}],
    )

    result = evaluate_journal(journal)

    decision = result["decisions"][0]
    assert decision["generation_allowed"] is False
    assert decision["state"] == "existing_dev_draft"
    assert decision["existing_draft_refs"] == ["posts/2001"]


def test_non_survivor_is_audit_only(tmp_path: Path) -> None:
    journal = _write_journal(tmp_path, url_row=_url_row(final_disposition="noindex"))

    result = evaluate_journal(journal)

    decision = result["decisions"][0]
    assert decision["generation_allowed"] is False
    assert decision["state"] == "audit_only"


def test_recovered_action_binding_blocks_unknown_vendor_object_replay(tmp_path: Path) -> None:
    recovery = tmp_path / "recovery.json"
    recovery.write_text(
        json.dumps(
            {
                "schema_version": "dev_content_action_binding_recovery_v1",
                "rows": [
                    {
                        "action_id": "action_old",
                        "binding": {
                            "work_item_id": "work_alpha",
                            "revision_id": "revision_alpha",
                            "final_canonical_url": "https://www.ekologus.pl/alpha/",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    journal = _write_journal(
        tmp_path,
        url_row=_url_row(current_revision_id="revision_alpha"),
    )
    data = json.loads(journal.read_text(encoding="utf-8"))
    data["sources"] = {"action_binding_recovery": {"path": recovery.name}}
    journal.write_text(json.dumps(data), encoding="utf-8")

    result = evaluate_journal(journal)

    decision = result["decisions"][0]
    assert decision["generation_allowed"] is False
    assert decision["state"] == "existing_current_revision"
    assert decision["applied_action_ids"] == ["action_old"]


def test_unscoped_action_binding_does_not_block_every_url(tmp_path: Path) -> None:
    journal = _write_journal(
        tmp_path,
        url_row=_url_row(planning_probe_work_item_id=None),
        audits=[
            {
                "record_type": "mutation_audit",
                "id": "audit_old",
                "action_id": "action_old",
                "action_type": "content_dev_draft_create",
                "status": "applied",
                "binding": {
                    "work_item_id": "work_other",
                    "revision_id": "revision_other",
                    "final_canonical_url": None,
                },
            }
        ],
    )

    result = evaluate_journal(journal)

    decision = result["decisions"][0]
    assert decision["state"] == "blocked"
    assert decision["applied_action_ids"] == []


def test_clean_keep_row_is_the_only_eligible_state(tmp_path: Path) -> None:
    journal = _write_journal(tmp_path, url_row=_url_row())

    result = evaluate_journal(journal)

    decision = result["decisions"][0]
    assert decision["generation_allowed"] is True
    assert decision["state"] == "eligible_candidate"
