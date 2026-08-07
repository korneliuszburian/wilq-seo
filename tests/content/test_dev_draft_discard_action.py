from __future__ import annotations

from wilq.connectors.wordpress.client import WordPressDraftDiscardReadback
from wilq.content.workflow import dev_draft_discard_action
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain


def _origin_action() -> ActionObject:
    return ActionObject(
        id="act_content_dev_draft_origin",
        title="Utwórz szkic dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.applied,
        evidence_ids=["ev_wordpress"],
        human_diagnosis="Szkic utworzony.",
        recommended_reason="Test.",
        payload={"action_type": "content_dev_draft_create"},
        validation_status="valid",
        created_by="Wilku",
    )


def _readback() -> WordPressDraftDiscardReadback:
    return WordPressDraftDiscardReadback(
        post_id="1930",
        endpoint="posts",
        status="draft",
        title="BDO – wadliwy szkic",
        modified_gmt="2026-08-05T13:21:33",
        content_digest="a" * 64,
        acf_digest="b" * 64,
    )


def test_discard_action_binds_one_exact_draft_to_recoverable_trash(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        dev_draft_discard_action,
        "load_content_target_draft_action",
        lambda _action_id: _origin_action(),
    )
    monkeypatch.setattr(dev_draft_discard_action, "_origin_action_applied", lambda _action_id: True)
    monkeypatch.setattr(
        dev_draft_discard_action,
        "read_wordpress_draft_discard_readback",
        lambda *_args, **_kwargs: _readback(),
    )

    action = dev_draft_discard_action.create_content_dev_draft_discard_action(
        dev_draft_discard_action.ContentDevDraftDiscardActionCommand(
            post_id="1930",
            endpoint="posts",
            origin_action_id="act_content_dev_draft_origin",
            defect_codes=["duplicate_h1", "official_sources_footer"],
            requested_by="Wilku",
        )
    )

    assert action.payload["allowed_operation"] == "trash_wordpress_dev_draft"
    assert action.payload["recoverable_operation"] is True
    assert action.payload["destructive"] is False
    target = action.payload["draft_discard_target"]
    assert target["post_id"] == "1930"
    assert target["content_digest"] == "a" * 64


def test_discard_executor_preserves_fingerprint_and_reports_only_trashed_id(
    monkeypatch,
) -> None:
    action = _origin_action().model_copy(
        update={
            "id": "act_content_dev_draft_discard_test",
            "payload": {
                "action_type": dev_draft_discard_action.CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
                "draft_discard_target": {
                    "post_id": "1930",
                    "endpoint": "posts",
                    "modified_gmt": "2026-08-05T13:21:33",
                    "content_digest": "a" * 64,
                    "acf_digest": "b" * 64,
                },
            },
        }
    )
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    calls: list[dict[str, str]] = []

    def trash(**kwargs: str) -> str:
        calls.append(kwargs)
        return "1930"

    monkeypatch.setattr(dev_draft_discard_action, "trash_wordpress_draft", trash)
    result, errors = dev_draft_discard_action.execute_content_dev_draft_discard_action(action)

    assert errors == []
    assert result is not None
    assert result["trashed_draft_id"] == "1930"
    assert result["force_delete_allowed"] is False
    assert calls == [
        {
            "post_id": "1930",
            "endpoint": "posts",
            "expected_modified_gmt": "2026-08-05T13:21:33",
            "expected_content_digest": "a" * 64,
            "expected_acf_digest": "b" * 64,
        }
    ]


def test_discard_preview_card_names_exact_target_and_recoverable_operation() -> None:
    cards = dev_draft_discard_action.content_dev_draft_discard_preview_cards(
        {
            "draft_discard_target": {
                "post_id": "1930",
                "endpoint": "posts",
                "title": "BDO – wadliwy szkic",
                "origin_action_id": "act_content_dev_draft_origin",
                "defect_codes": ["duplicate_h1", "official_sources_footer"],
            },
            "apply_allowed": True,
            "api_mutation_ready": True,
        },
        preview_row=lambda label, value: {"label": label, "value": value},
        apply_state_label=lambda _value: "zapis zmian dopuszczony",
        system_readiness_label=lambda _value: "system gotowy do zapisu",
    )

    assert cards[0].title_label == "Wadliwy szkic dev do wycofania"
    assert cards[0].rows[0].value == "posts #1930: BDO – wadliwy szkic"
    assert "bez trwałego usunięcia" in cards[0].rows[1].value
    assert "powielony nagłówek H1" in cards[0].rows[2].value
