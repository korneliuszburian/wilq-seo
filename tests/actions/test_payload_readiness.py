from wilq.actions.payload_readiness import payload_preview_contract, payload_preview_items


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
