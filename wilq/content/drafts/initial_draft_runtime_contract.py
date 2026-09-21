"""One bounded deadline contract for the initial-draft Codex run.

The draft path chains one large writer turn with bounded readability, regulatory
and independent-assurance repair rounds, so its wall clock is far larger than a
single model turn. A live Operat 12-section draft with six assurance turns
exceeded the previous 3600-second deadline (``initial_draft_timeout`` /
``assurance_turn_timeouterror``), so the default keeps real margin above that
observed need while the operator never waits on the browser request (the API is
asynchronous).
"""

from __future__ import annotations

from os import environ

DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS = 7200.0


def initial_draft_timeout_seconds() -> float:
    try:
        configured = float(
            environ.get(
                "WILQ_INITIAL_DRAFT_TIMEOUT_SECONDS",
                str(DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        configured = DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS
    return max(30.0, configured)


__all__ = [
    "DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS",
    "initial_draft_timeout_seconds",
]
