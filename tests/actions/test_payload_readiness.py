from wilq.actions.payload_readiness import (
    action_preview_item_view_models,
    payload_preview_contract,
    payload_preview_items,
)
from wilq.schemas import ActionObject, ActionPreviewCardViewModel, ActionPreviewRowViewModel


def test_payload_preview_items_keep_contract_priority_and_dict_fallbacks() -> None:
    payload = {
        "preview_contract": "explicit",
        "payload_preview": [{"preview_contract": "payload", "apply_allowed": False}],
        "wordpress_draft_payload_preview": [
            {"preview_contract": "wordpress", "apply_allowed": False},
            "ignore",
        ],
    }

    items = payload_preview_items(payload)

    assert items == [{"preview_contract": "wordpress", "apply_allowed": False}]
    assert payload_preview_contract(payload, items) == "explicit"


def test_payload_preview_items_find_nested_apply_allowed_rows_as_last_resort() -> None:
    payload = {"rows": [{"apply_allowed": False}, {"label": "bez kontraktu"}]}

    assert payload_preview_items(payload) == [{"apply_allowed": False}]
    assert payload_preview_contract(payload, payload_preview_items(payload)) is None


def test_action_preview_item_view_models_project_cards_and_raw_rows() -> None:
    action = ActionObject.model_construct(payload={"preview_contract": "content_brief_preview_v1"})
    card = ActionPreviewCardViewModel(
        id="card-1",
        kind="review",
        title_label="Brief do sprawdzenia",
        status_label="zablokowany",
        rows=[ActionPreviewRowViewModel(label="Powód", value="brak review")],
        apply_state_label="zapis zablokowany",
        system_readiness_label="wymaga kontroli",
    )

    def row(label: str, value: str) -> ActionPreviewRowViewModel:
        return ActionPreviewRowViewModel(label=label, value=value)

    card_items = action_preview_item_view_models(
        action=action,
        raw_items=[
            {"preview_contract": "wordpress_draft_payload_preview_v1", "candidate_id": "c-1"}
        ],
        preview_cards=[card],
        max_items=2,
        preview_row=row,
        apply_state_label=lambda value: "dozwolone" if value else "zablokowane",
        system_readiness_label=lambda value: "gotowe" if value else "wymaga kontroli",
        preview_contract_label=lambda value: value or "brak kontraktu",
    )

    assert card_items[0].candidate_id == "c-1"
    assert [item.label for item in card_items[0].rows[-2:]] == ["Zapis zmian", "Gotowość systemu"]

    raw_items = action_preview_item_view_models(
        action=action,
        raw_items=[
            {
                "issue_type_label": "brak ceny",
                "status_label": "do sprawdzenia",
                "apply_allowed": False,
                "api_mutation_ready": False,
            }
        ],
        preview_cards=[],
        max_items=2,
        preview_row=row,
        apply_state_label=lambda value: "dozwolone" if value else "zablokowane",
        system_readiness_label=lambda value: "gotowe" if value else "wymaga kontroli",
        preview_contract_label=lambda value: value or "brak kontraktu",
    )

    assert raw_items[0].title_label == "brak ceny"
    assert [item.label for item in raw_items[0].rows[-2:]] == ["Zapis zmian", "Gotowość systemu"]
