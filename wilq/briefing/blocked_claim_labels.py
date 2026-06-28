from __future__ import annotations

from collections.abc import Iterable

from wilq.operator_labels import blocked_claim_labels


def operator_blocked_claims(claims: Iterable[str]) -> list[str]:
    return blocked_claim_labels(claims)
