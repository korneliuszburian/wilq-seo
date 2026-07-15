from __future__ import annotations

from tests.content.test_structured_draft_generation import (
    _draft_stack,
)
from tests.content.test_structured_draft_generation import (
    _sales_brief as build_sales_brief,
)
from tests.content.test_structured_draft_preview import _output


def _stack_dicts() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    item, ledger, draft_package = _draft_stack()
    return (
        item.model_dump(mode="json"),
        ledger.model_dump(mode="json"),
        draft_package.model_dump(mode="json"),
    )


def _item(**overrides: object) -> dict[str, object]:
    item, _, _ = _stack_dicts()
    item.update(overrides)
    return item


def _claim_ledger(**overrides: object) -> dict[str, object]:
    _, ledger, _ = _stack_dicts()
    ledger.update(overrides)
    return ledger


def _draft_package(**overrides: object) -> dict[str, object]:
    _, _, draft_package = _stack_dicts()
    draft_package.update(overrides)
    return draft_package


def _sales_brief() -> dict[str, object]:
    item, ledger, _ = _draft_stack()
    return build_sales_brief(item, ledger).model_dump(mode="json")


def _structured_output() -> dict[str, object]:
    return _output().model_dump(mode="json")
