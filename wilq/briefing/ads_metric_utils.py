"""Shared numeric formatting for Ads diagnostic view-models."""

from __future__ import annotations

from collections.abc import Iterable


def sum_attr(rows: Iterable[object], attr: str) -> float | None:
    total: float | None = None
    for row in rows:
        value = getattr(row, attr, None)
        if isinstance(value, int | float):
            total = (total or 0.0) + float(value)
    return total


def round_metric(value: float | None) -> int | float | None:
    if value is None:
        return None
    if value.is_integer():
        return int(value)
    return round(value, 3)


def _format_micros(value: float | None) -> str | None:
    if value is None:
        return None
    account_units = value / 1_000_000
    if account_units >= 100:
        return f"{account_units:.0f}"
    if account_units >= 10:
        return f"{account_units:.1f}"
    return f"{account_units:.2f}"


def format_money_micros(value: float | None, currency_code: str | None) -> str | None:
    formatted_value = _format_micros(value)
    if formatted_value is None:
        return None
    if formatted_value.endswith(".0"):
        formatted_value = formatted_value[:-2]
    if not currency_code:
        return formatted_value
    return f"{formatted_value} {currency_code}"


def clean_metric_tiles(
    tiles: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    clean_tiles: dict[str, int | float | str] = {}
    for label, value in tiles.items():
        if value is None:
            continue
        if isinstance(value, float):
            rounded_value = round_metric(value)
            if rounded_value is not None:
                clean_tiles[label] = rounded_value
        else:
            clean_tiles[label] = value
    return clean_tiles
