from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_existing_draft_update_readiness_is_explicitly_dev_only_and_blocked() -> None:
    response = TestClient(app).get(
        "/api/content/wordpress/existing-draft-update-readiness"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract"] == "wordpress_existing_draft_update_readiness_v1"
    assert payload["action_id"] == "act_prepare_wordpress_existing_draft_update"
    assert payload["ready"] is False
    assert payload["update_supported"] is False
    assert payload["current_state_available"] is True
    assert payload["target_post_id"] == "2"
    assert payload["target_url"] == "https://ekologus.dev.proudsite.pl/"
    assert payload["current_section_count"] == 9
    assert payload["proposed_section_count"] == 3
    assert len(payload["section_diff_preview"]) == 3
    assert {row["status"] for row in payload["section_diff_preview"]} <= {
        "unchanged",
        "changed",
        "missing_current",
        "proposed",
    }
    assert payload["publish_allowed"] is False
    assert payload["destructive_update_allowed"] is False
    assert [blocker["code"] for blocker in payload["blockers"]] == [
        "existing_draft_update_contract_not_implemented"
    ]
    assert payload["evidence_ids"]
    assert payload["source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]


def test_existing_draft_update_action_validates_and_previews_without_mutation() -> None:
    client = TestClient(app)
    validation = client.post(
        "/api/actions/act_prepare_wordpress_existing_draft_update/validate"
    )
    preview = client.post(
        "/api/actions/act_prepare_wordpress_existing_draft_update/preview"
    )

    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert preview.status_code == 200
    result = preview.json()
    assert result["status"] == "blocked"
    assert result["dry_run"] is True
    assert result["mutation_allowed"] is False
    assert "action_mode_prepare_only" in result["blockers"]
    assert result["audit_event"]["event_type"] == "action_preview_generated"


def test_existing_draft_update_action_exposes_marketer_preview_card() -> None:
    actions = TestClient(app).get("/api/actions").json()
    action = next(
        item
        for item in actions
        if item["id"] == "act_prepare_wordpress_existing_draft_update"
    )

    assert len(action["preview_cards"]) == 1
    card = action["preview_cards"][0]
    assert card["kind"] == "wordpress_existing_draft_update_review"
    assert card["title_label"] == "Aktualizacja istniejącego szkicu do sprawdzenia"
    assert card["status_label"] == "zapis zmian zablokowany"
    assert card["apply_state_label"] == "zapis zmian zablokowany"
    assert {row["label"] for row in card["rows"]} == {
        "Stan bieżący",
        "Proponowana zmiana",
        "Dozwolony zakres",
    }


def test_existing_draft_update_review_and_confirm_remain_audited_and_blocked() -> None:
    client = TestClient(app)
    client.post("/api/actions/act_prepare_wordpress_existing_draft_update/validate")
    client.post("/api/actions/act_prepare_wordpress_existing_draft_update/preview")
    review = client.post(
        "/api/actions/act_prepare_wordpress_existing_draft_update/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": "Podgląd sekcji sprawdzony; brak zgody na zapis.",
            "checked_items": ["acf_current_vs_proposed_review"],
            "blockers": ["adapter update nie jest gotowy"],
        },
    )
    confirm = client.post(
        "/api/actions/act_prepare_wordpress_existing_draft_update/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Potwierdzam tylko podgląd, nie zapis WordPress.",
            "preview_acknowledged": True,
        },
    )

    assert review.status_code == 200
    assert review.json()["status"] == "recorded"
    assert review.json()["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    assert confirm.json()["confirmed"] is True
    assert confirm.json()["audit_event"]["event_type"] == "action_apply_confirmed"
    assert confirm.json()["review_gate"]["apply_allowed"] is False
