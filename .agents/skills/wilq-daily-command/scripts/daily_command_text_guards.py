from __future__ import annotations

import unicodedata
from typing import Any

FORBIDDEN_MARKERS = ("fake_metric", "mock_metric", "seed_metric")


def scan_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        lowered = value.lower()
        return [marker for marker in FORBIDDEN_MARKERS if marker in lowered]
    if isinstance(value, dict):
        return [hit for nested in value.values() for hit in scan_strings(nested)]
    if isinstance(value, list):
        return [hit for nested in value for hit in scan_strings(nested)]
    return []


def has_metric_evidence_guardrails(value: str) -> bool:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized
