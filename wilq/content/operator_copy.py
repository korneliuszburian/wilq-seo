"""Shared typed operator-facing blocker copy constructors."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

Model = TypeVar("Model", bound=BaseModel)


def unique(values: Iterable[object]) -> list[str]:
    """Stringify, deduplicate, and preserve the first occurrence of values."""

    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def build_blocker(  # noqa: UP047
    model: type[Model],
    *,
    code: Any,
    label: str,
    reason: str,
    next_step: str,
    source_codes: Sequence[str] | None = None,
) -> Model:
    """Construct any content blocker model through one typed seam."""

    fields: Any = model.model_fields
    values: dict[str, Any] = {
        "code": code,
        "label": label,
        "reason": reason,
        "next_step": next_step,
    }
    if source_codes is not None and "source_codes" in fields:
        values["source_codes"] = list(source_codes)
    return model(**values)


__all__ = ["build_blocker", "unique"]
