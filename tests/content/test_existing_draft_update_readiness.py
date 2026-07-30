from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_existing_draft_update_readiness_is_not_a_public_content_seam() -> None:
    response = TestClient(app).get(
        "/api/content/wordpress/existing-draft-update-readiness"
    )

    assert response.status_code == 404
    assert "/api/content/wordpress/existing-draft-update-readiness" not in app.openapi()["paths"]


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
